"""
API operations for Workflows
"""

import json
import logging
import os
from io import BytesIO
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Union,
)

from fastapi import (
    Body,
    Path,
    Query,
    Response,
    status,
)
from pydantic import (
    UUID1,
    UUID4,
)
from starlette.responses import StreamingResponse
from typing_extensions import Annotated

from galaxy import (
    exceptions,
    model,
    util,
)
from galaxy.files.uris import (
    stream_url_to_str,
    validate_uri_access,
)
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.workflows import (
    MissingToolsException,
    RefactorRequest,
    RefactorResponse,
    WorkflowCreateOptions,
    WorkflowUpdateOptions,
)
from galaxy.model.base import transaction
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.invocation import (
    CreateInvocationFromStore,
    CreateInvocationsFromStorePayload,
    InvocationJobsResponse,
    InvocationReport,
    InvocationSerializationParams,
    InvocationStep,
    InvocationStepJobsResponseCollectionJobsModel,
    InvocationStepJobsResponseJobModel,
    InvocationStepJobsResponseStepModel,
    InvocationUpdatePayload,
    WorkflowInvocationResponse,
)
from galaxy.schema.schema import (
    AsyncFile,
    AsyncTaskResultSummary,
    InvocationSortByEnum,
    InvocationsStateCounts,
    SetSlugPayload,
    ShareWithPayload,
    ShareWithStatus,
    SharingStatus,
    WorkflowSortByEnum,
)
from galaxy.schema.workflows import (
    InvokeWorkflowPayload,
    SetWorkflowMenuPayload,
    SetWorkflowMenuSummary,
    StoredWorkflowDetailed,
    WorkflowDictEditorSummary,
    WorkflowDictExportSummary,
    WorkflowDictFormat2Summary,
    WorkflowDictFormat2WrappedYamlSummary,
    WorkflowDictPreviewSummary,
    WorkflowDictRunSummary,
)
from galaxy.structured_app import StructuredApp
from galaxy.tool_shed.galaxy_install.install_manager import InstallRepositoryManager
from galaxy.tools import recommendations
from galaxy.tools._types import ParameterValidationErrorsT
from galaxy.tools.parameters import populate_state
from galaxy.tools.parameters.workflow_utils import workflow_building_modes
from galaxy.web import expose_api
from galaxy.webapps.base.controller import (
    SharableMixin,
    url_for,
    UsesStoredWorkflowMixin,
)
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from galaxy.webapps.galaxy.api import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    IndexQueryTag,
    Router,
    search_query_param,
)
from galaxy.webapps.galaxy.api.common import SerializationViewQueryParam
from galaxy.webapps.galaxy.services.base import (
    ConsumesModelStores,
    ServesExportStores,
)
from galaxy.webapps.galaxy.services.invocations import (
    InvocationIndexPayload,
    InvocationsService,
    PrepareStoreDownloadPayload,
    WriteInvocationStoreToPayload,
)
from galaxy.webapps.galaxy.services.workflows import (
    WorkflowIndexPayload,
    WorkflowsService,
)
from galaxy.workflow.extract import extract_workflow
from galaxy.workflow.modules import module_factory

log = logging.getLogger(__name__)

router = Router(tags=["workflows"])


class WorkflowsAPIController(
    BaseGalaxyAPIController,
    UsesStoredWorkflowMixin,
    UsesAnnotations,
    SharableMixin,
    ServesExportStores,
    ConsumesModelStores,
):
    service: WorkflowsService = depends(WorkflowsService)

    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self.history_manager = app.history_manager
        self.workflow_manager = app.workflow_manager
        self.workflow_contents_manager = app.workflow_contents_manager
        self.tool_recommendations = recommendations.ToolRecommendations()

    @expose_api
    def create(self, trans: GalaxyWebTransaction, payload=None, **kwd):
        """
        POST /api/workflows

        Create workflows in various ways.

        :param  from_history_id:             Id of history to extract a workflow from.
        :type   from_history_id:             str

        :param  job_ids:                     If from_history_id is set - optional list of jobs to include when extracting a workflow from history
        :type   job_ids:                     str

        :param  dataset_ids:                 If from_history_id is set - optional list of HDA "hid"s corresponding to workflow inputs when extracting a workflow from history
        :type   dataset_ids:                 str

        :param  dataset_collection_ids:      If from_history_id is set - optional list of HDCA "hid"s corresponding to workflow inputs when extracting a workflow from history
        :type   dataset_collection_ids:      str

        :param  workflow_name:               If from_history_id is set - name of the workflow to create when extracting a workflow from history
        :type   workflow_name:               str

        """
        ways_to_create = {
            "archive_file",
            "archive_source",
            "from_history_id",
            "from_path",
            "shared_workflow_id",
            "workflow",
        }

        if trans.user_is_bootstrap_admin:
            raise exceptions.RealUserRequiredException("Only real users can create or run workflows.")

        if payload is None or len(ways_to_create.intersection(payload)) == 0:
            message = f"One parameter among - {', '.join(ways_to_create)} - must be specified"
            raise exceptions.RequestParameterMissingException(message)

        if len(ways_to_create.intersection(payload)) > 1:
            message = f"Only one parameter among - {', '.join(ways_to_create)} - must be specified"
            raise exceptions.RequestParameterInvalidException(message)

        if "archive_source" in payload or "archive_file" in payload:
            archive_source = payload.get("archive_source")
            archive_file = payload.get("archive_file")
            archive_data = None
            if archive_source:
                validate_uri_access(archive_source, trans.user_is_admin, trans.app.config.fetch_url_allowlist_ips)
                if archive_source.startswith("file://"):
                    workflow_src = {"src": "from_path", "path": archive_source[len("file://") :]}
                    payload["workflow"] = workflow_src
                    return self.__api_import_new_workflow(trans, payload, **kwd)
                elif archive_source == "trs_tool":
                    server = None
                    trs_tool_id = None
                    trs_version_id = None
                    import_source = None
                    if "trs_url" in payload:
                        parts = self.app.trs_proxy.match_url(
                            payload["trs_url"], trans.app.config.fetch_url_allowlist_ips
                        )
                        if parts:
                            server = self.app.trs_proxy.server_from_url(parts["trs_base_url"])
                            trs_tool_id = parts["tool_id"]
                            trs_version_id = parts["version_id"]
                            payload["trs_tool_id"] = trs_tool_id
                            payload["trs_version_id"] = trs_version_id
                        else:
                            raise exceptions.RequestParameterInvalidException(f"Invalid TRS URL {payload['trs_url']}.")
                    else:
                        trs_server = payload.get("trs_server")
                        server = self.app.trs_proxy.get_server(trs_server)
                        trs_tool_id = payload.get("trs_tool_id")
                        trs_version_id = payload.get("trs_version_id")

                    archive_data = server.get_version_descriptor(trs_tool_id, trs_version_id)
                else:
                    try:
                        archive_data = stream_url_to_str(
                            archive_source, trans.app.file_sources, prefix="gx_workflow_download"
                        )
                        import_source = "URL"
                    except Exception:
                        raise exceptions.MessageException(f"Failed to open URL '{archive_source}'.")
            elif hasattr(archive_file, "file"):
                uploaded_file = archive_file.file
                uploaded_file_name = uploaded_file.name
                if os.path.getsize(os.path.abspath(uploaded_file_name)) > 0:
                    archive_data = util.unicodify(uploaded_file.read())
                    import_source = "uploaded file"
                else:
                    raise exceptions.MessageException("You attempted to upload an empty file.")
            else:
                raise exceptions.MessageException("Please provide a URL or file.")
            return self.__api_import_from_archive(trans, archive_data, import_source, payload=payload)

        if "from_history_id" in payload:
            from_history_id = payload.get("from_history_id")
            from_history_id = self.decode_id(from_history_id)
            history = self.history_manager.get_accessible(from_history_id, trans.user, current_history=trans.history)

            job_ids = [self.decode_id(_) for _ in payload.get("job_ids", [])]
            dataset_ids = payload.get("dataset_ids", [])
            dataset_collection_ids = payload.get("dataset_collection_ids", [])
            workflow_name = payload["workflow_name"]
            stored_workflow = extract_workflow(
                trans=trans,
                user=trans.user,
                history=history,
                job_ids=job_ids,
                dataset_ids=dataset_ids,
                dataset_collection_ids=dataset_collection_ids,
                workflow_name=workflow_name,
            )
            item = stored_workflow.to_dict(value_mapper={"id": trans.security.encode_id})
            item["url"] = url_for("workflow", id=item["id"])
            return item

        if "from_path" in payload:
            from_path = payload.get("from_path")
            object_id = payload.get("object_id")
            workflow_src = {"src": "from_path", "path": from_path}
            if object_id is not None:
                workflow_src["object_id"] = object_id
            payload["workflow"] = workflow_src
            return self.__api_import_new_workflow(trans, payload, **kwd)

        if "shared_workflow_id" in payload:
            workflow_id = payload["shared_workflow_id"]
            return self.__api_import_shared_workflow(trans, workflow_id, payload)

        if "workflow" in payload:
            return self.__api_import_new_workflow(trans, payload, **kwd)

        # This was already raised above, but just in case...
        raise exceptions.RequestParameterMissingException("No method for workflow creation supplied.")

    @expose_api
    def import_new_workflow_deprecated(self, trans: GalaxyWebTransaction, payload, **kwd):
        """
        POST /api/workflows/upload
        Importing dynamic workflows from the api. Return newly generated workflow id.
        Author: rpark

        # currently assumes payload['workflow'] is a json representation of a workflow to be inserted into the database

        Deprecated in favor to POST /api/workflows with encoded 'workflow' in
        payload the same way.
        """
        return self.__api_import_new_workflow(trans, payload, **kwd)

    @expose_api
    def update(self, trans: GalaxyWebTransaction, id, payload, **kwds):
        """
        PUT /api/workflows/{id}

        Update the workflow stored with ``id``.

        :type   id:      str
        :param  id:      the encoded id of the workflow to update
        :param  instance: true if fetch by Workflow ID instead of StoredWorkflow id, false by default.
        :type   instance: boolean
        :type   payload: dict
        :param  payload: a dictionary containing any or all the

            :workflow:

                the json description of the workflow as would be
                produced by GET workflows/<id>/download or
                given to `POST workflows`

                The workflow contents will be updated to target this.

            :name:

                optional string name for the workflow, if not present in payload,
                name defaults to existing name

            :annotation:

                optional string annotation for the workflow, if not present in payload,
                annotation defaults to existing annotation

            :menu_entry:

                optional boolean marking if the workflow should appear in the user\'s menu,
                if not present, workflow menu entries are not modified

            :tags:

                optional list containing list of tags to add to the workflow (overwriting
                existing tags), if not present, tags are not modified

            :from_tool_form:

                True iff encoded state coming in is encoded for the tool form.


        :rtype:     dict
        :returns:   serialized version of the workflow
        """
        stored_workflow = self.__get_stored_workflow(trans, id, **kwds)
        workflow_dict = payload.get("workflow", {})
        workflow_dict.update({k: v for k, v in payload.items() if k not in workflow_dict})
        if workflow_dict:
            require_flush = False
            raw_workflow_description = self.__normalize_workflow(trans, workflow_dict)
            workflow_dict = raw_workflow_description.as_dict
            new_workflow_name = workflow_dict.get("name")
            old_workflow = stored_workflow.latest_workflow
            name_updated = new_workflow_name and new_workflow_name != stored_workflow.name
            steps_updated = "steps" in workflow_dict
            if name_updated and not steps_updated:
                sanitized_name = new_workflow_name or old_workflow.name
                if not sanitized_name:
                    raise exceptions.MessageException("Workflow must have a valid name.")
                workflow = old_workflow.copy(user=trans.user)
                workflow.stored_workflow = stored_workflow
                workflow.name = sanitized_name
                stored_workflow.name = sanitized_name
                stored_workflow.latest_workflow = workflow
                trans.sa_session.add(workflow, stored_workflow)
                require_flush = True

            if "hidden" in workflow_dict and stored_workflow.hidden != workflow_dict["hidden"]:
                stored_workflow.hidden = workflow_dict["hidden"]
                require_flush = True

            if "published" in workflow_dict and stored_workflow.published != workflow_dict["published"]:
                stored_workflow.published = workflow_dict["published"]
                require_flush = True

            if "importable" in workflow_dict and stored_workflow.importable != workflow_dict["importable"]:
                stored_workflow.importable = workflow_dict["importable"]
                require_flush = True

            if "annotation" in workflow_dict and not steps_updated:
                newAnnotation = workflow_dict["annotation"]
                self.add_item_annotation(trans.sa_session, trans.user, stored_workflow, newAnnotation)
                require_flush = True

            if "menu_entry" in workflow_dict or "show_in_tool_panel" in workflow_dict:
                show_in_panel = workflow_dict.get("menu_entry") or workflow_dict.get("show_in_tool_panel")
                stored_workflow_menu_entries = trans.user.stored_workflow_menu_entries
                decoded_id = trans.security.decode_id(id)
                if show_in_panel:
                    workflow_ids = [wf.stored_workflow_id for wf in stored_workflow_menu_entries]
                    if decoded_id not in workflow_ids:
                        menu_entry = model.StoredWorkflowMenuEntry()
                        menu_entry.stored_workflow = stored_workflow
                        stored_workflow_menu_entries.append(menu_entry)
                        trans.sa_session.add(menu_entry)
                        require_flush = True
                else:
                    # remove if in list
                    entries = {x.stored_workflow_id: x for x in stored_workflow_menu_entries}
                    if decoded_id in entries:
                        stored_workflow_menu_entries.remove(entries[decoded_id])
                        require_flush = True
            # set tags
            if "tags" in workflow_dict:
                trans.tag_handler.set_tags_from_list(
                    user=trans.user,
                    item=stored_workflow,
                    new_tags_list=workflow_dict["tags"],
                )

            if require_flush:
                with transaction(trans.sa_session):
                    trans.sa_session.commit()

            if "steps" in workflow_dict or "comments" in workflow_dict:
                try:
                    workflow_update_options = WorkflowUpdateOptions(**payload)
                    workflow, errors = self.workflow_contents_manager.update_workflow_from_raw_description(
                        trans,
                        stored_workflow,
                        raw_workflow_description,
                        workflow_update_options,
                    )
                except MissingToolsException:
                    raise exceptions.MessageException(
                        "This workflow contains missing tools. It cannot be saved until they have been removed from the workflow or installed."
                    )

        else:
            message = "Updating workflow requires dictionary containing 'workflow' attribute with new JSON description."
            raise exceptions.RequestParameterInvalidException(message)
        return self.workflow_contents_manager.workflow_to_dict(trans, stored_workflow, style="instance")

    @expose_api
    def build_module(self, trans: GalaxyWebTransaction, payload=None):
        """
        POST /api/workflows/build_module
        Builds module models for the workflow editor.
        """
        # payload is tool state
        if payload is None:
            payload = {}
        inputs = payload.get("inputs", {})
        trans.workflow_building_mode = workflow_building_modes.ENABLED
        module = module_factory.from_dict(trans, payload, from_tool_form=True)
        if "tool_state" not in payload:
            module_state: Dict[str, Any] = {}
            errors: ParameterValidationErrorsT = {}
            populate_state(trans, module.get_inputs(), inputs, module_state, errors=errors, check=True)
            module.recover_state(module_state, from_tool_form=True)
            module.check_and_update_state()
        step_dict = {
            "name": module.get_name(),
            "tool_state": module_state,
            "content_id": module.get_content_id(),
            "inputs": module.get_all_inputs(connectable_only=True),
            "outputs": module.get_all_outputs(),
            "config_form": module.get_config_form(),
            "errors": errors or None,
        }
        if payload["type"] == "tool":
            step_dict["tool_version"] = module.get_version()
        return step_dict

    @expose_api
    def get_tool_predictions(self, trans: ProvidesUserContext, payload, **kwd):
        """
        POST /api/workflows/get_tool_predictions
        Fetch predicted tools for a workflow
        :type   payload: dict
        :param  payload:
            a dictionary containing two parameters
            'tool_sequence' - comma separated sequence of tool ids
            'remote_model_url' - (optional) path to the deep learning model
        """
        remote_model_url = payload.get("remote_model_url", trans.app.config.tool_recommendation_model_path)
        tool_sequence = payload.get("tool_sequence", "")
        if "tool_sequence" not in payload or remote_model_url is None:
            return
        tool_sequence, recommended_tools = self.tool_recommendations.get_predictions(
            trans, tool_sequence, remote_model_url
        )
        return {"current_tool": tool_sequence, "predicted_data": recommended_tools}

    #
    # -- Helper methods --
    #
    def __api_import_from_archive(self, trans: GalaxyWebTransaction, archive_data, source=None, payload=None):
        payload = payload or {}
        try:
            data = json.loads(archive_data)
        except Exception:
            if "GalaxyWorkflow" in archive_data:
                data = {"yaml_content": archive_data}
            else:
                raise exceptions.MessageException("The data content does not appear to be a valid workflow.")
        if not data:
            raise exceptions.MessageException("The data content is missing.")
        raw_workflow_description = self.__normalize_workflow(trans, data)
        workflow_create_options = WorkflowCreateOptions(**payload)
        workflow, missing_tool_tups = self._workflow_from_dict(
            trans, raw_workflow_description, workflow_create_options, source=source
        )
        workflow_id = workflow.id
        workflow = workflow.latest_workflow

        response = {
            "message": f"Workflow '{workflow.name}' imported successfully.",
            "status": "success",
            "id": trans.security.encode_id(workflow_id),
        }
        if workflow.has_errors:
            response["message"] = "Imported, but some steps in this workflow have validation errors."
            response["status"] = "error"
        elif len(workflow.steps) == 0:
            response["message"] = "Imported, but this workflow has no steps."
            response["status"] = "error"
        elif workflow.has_cycles:
            response["message"] = "Imported, but this workflow contains cycles."
            response["status"] = "error"
        return response

    def __api_import_new_workflow(self, trans: GalaxyWebTransaction, payload, **kwd):
        data = payload["workflow"]
        raw_workflow_description = self.__normalize_workflow(trans, data)
        workflow_create_options = WorkflowCreateOptions(**payload)
        workflow, missing_tool_tups = self._workflow_from_dict(
            trans,
            raw_workflow_description,
            workflow_create_options,
        )
        # galaxy workflow newly created id
        workflow_id = workflow.id
        # api encoded, id
        encoded_id = trans.security.encode_id(workflow_id)
        item = workflow.to_dict(value_mapper={"id": trans.security.encode_id})
        item["annotations"] = [x.annotation for x in workflow.annotations]
        item["url"] = url_for("workflow", id=encoded_id)
        item["owner"] = workflow.user.username
        item["number_of_steps"] = len(workflow.latest_workflow.steps)
        return item

    def __normalize_workflow(self, trans: GalaxyWebTransaction, as_dict):
        return self.workflow_contents_manager.normalize_workflow_format(trans, as_dict)

    @expose_api
    def import_shared_workflow_deprecated(self, trans: GalaxyWebTransaction, payload, **kwd):
        """
        POST /api/workflows/import
        Import a workflow shared by other users.

        :param  workflow_id:      the workflow id (required)
        :type   workflow_id:      str

        :raises: exceptions.MessageException, exceptions.ObjectNotFound
        """
        # Pull parameters out of payload.
        workflow_id = payload.get("workflow_id", None)
        if workflow_id is None:
            raise exceptions.ObjectAttributeMissingException("Missing required parameter 'workflow_id'.")
        self.__api_import_shared_workflow(trans, workflow_id, payload)

    def __api_import_shared_workflow(self, trans: GalaxyWebTransaction, workflow_id, payload, **kwd):
        try:
            stored_workflow = self.get_stored_workflow(trans, workflow_id, check_ownership=False)
        except Exception:
            raise exceptions.ObjectNotFound("Malformed workflow id specified.")
        if stored_workflow.importable is False:
            raise exceptions.ItemAccessibilityException(
                "The owner of this workflow has disabled imports via this link."
            )
        elif stored_workflow.deleted:
            raise exceptions.ItemDeletionException("You can't import this workflow because it has been deleted.")
        imported_workflow = self._import_shared_workflow(trans, stored_workflow)
        item = imported_workflow.to_dict(value_mapper={"id": trans.security.encode_id})
        encoded_id = trans.security.encode_id(imported_workflow.id)
        item["url"] = url_for("workflow", id=encoded_id)
        return item

    def _workflow_from_dict(self, trans, data, workflow_create_options, source=None):
        """Creates a workflow from a dict.

        Created workflow is stored in the database and returned.
        """
        publish = workflow_create_options.publish
        importable = workflow_create_options.is_importable
        if publish and not importable:
            raise exceptions.RequestParameterInvalidException("Published workflow must be importable.")

        workflow_contents_manager = self.app.workflow_contents_manager
        raw_workflow_description = workflow_contents_manager.ensure_raw_description(data)
        created_workflow = workflow_contents_manager.build_workflow_from_raw_description(
            trans,
            raw_workflow_description,
            workflow_create_options,
            source=source,
        )
        if importable:
            self._make_item_accessible(trans.sa_session, created_workflow.stored_workflow)
            with transaction(trans.sa_session):
                trans.sa_session.commit()

        self._import_tools_if_needed(trans, workflow_create_options, raw_workflow_description)
        return created_workflow.stored_workflow, created_workflow.missing_tools

    def _import_tools_if_needed(self, trans, workflow_create_options, raw_workflow_description):
        if not workflow_create_options.import_tools:
            return

        if not trans.user_is_admin:
            raise exceptions.AdminRequiredException()

        data = raw_workflow_description.as_dict

        tools = {}
        for key in data["steps"]:
            item = data["steps"][key]
            if item is not None:
                if "tool_shed_repository" in item:
                    tool_shed_repository = item["tool_shed_repository"]
                    if (
                        "owner" in tool_shed_repository
                        and "changeset_revision" in tool_shed_repository
                        and "name" in tool_shed_repository
                        and "tool_shed" in tool_shed_repository
                    ):
                        toolstr = (
                            tool_shed_repository["owner"]
                            + tool_shed_repository["changeset_revision"]
                            + tool_shed_repository["name"]
                            + tool_shed_repository["tool_shed"]
                        )
                        tools[toolstr] = tool_shed_repository

        irm = InstallRepositoryManager(self.app)
        install_options = workflow_create_options.install_options
        for k in tools:
            item = tools[k]
            tool_shed_url = f"https://{item['tool_shed']}/"
            name = item["name"]
            owner = item["owner"]
            changeset_revision = item["changeset_revision"]
            irm.install(tool_shed_url, name, owner, changeset_revision, install_options)

    def __get_stored_workflow(self, trans, workflow_id, **kwd):
        instance = util.string_as_bool(kwd.get("instance", "false"))
        return self.workflow_manager.get_stored_workflow(trans, workflow_id, by_stored_id=not instance)


StoredWorkflowIDPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Stored Workflow ID", description="The encoded database identifier of the Stored Workflow."),
]

InvocationIDPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(..., title="Invocation ID", description="The encoded database identifier of the Invocation."),
]

WorkflowInvocationStepIDPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(
        ...,
        title="WorkflowInvocationStep ID",
        description="The encoded database identifier of the WorkflowInvocationStep.",
    ),
]

InvocationsInstanceQueryParam = Annotated[
    Optional[bool],
    Query(
        title="Instance",
        description="Is provided workflow id for Workflow instead of StoredWorkflow?",
    ),
]

MultiTypeWorkflowIDPathParam = Annotated[
    Union[UUID4, UUID1, DecodedDatabaseIdField],
    Path(
        ...,
        title="Workflow ID",
        description="The database identifier - UUID or encoded - of the Workflow.",
    ),
]

DeletedQueryParam: bool = Query(
    default=False, title="Display deleted", description="Whether to restrict result to deleted workflows."
)

HiddenQueryParam: bool = Query(
    default=False, title="Display hidden", description="Whether to restrict result to hidden workflows."
)

MissingToolsQueryParam: bool = Query(
    default=False,
    title="Display missing tools",
    description="Whether to include a list of missing tools per workflow entry",
)

ShowPublishedQueryParam: Optional[bool] = Query(default=None, title="Include published workflows.", description="")

ShowSharedQueryParam: Optional[bool] = Query(
    default=None, title="Include workflows shared with authenticated user.", description=""
)

SortByQueryParam: Optional[WorkflowSortByEnum] = Query(
    default=None,
    title="Sort workflow index by this attribute",
    description="In unspecified, default ordering depends on other parameters but generally the user's own workflows appear first based on update time",
)

SortDescQueryParam: Optional[bool] = Query(
    default=None,
    title="Sort Descending",
    description="Sort in descending order?",
)

LimitQueryParam: Optional[int] = Query(default=None, ge=1, title="Limit number of queries.")

OffsetQueryParam: Optional[int] = Query(
    default=0,
    ge=0,
    title="Number of workflows to skip in sorted query (to enable pagination).",
)

InstanceQueryParam = Annotated[
    Optional[bool],
    Query(
        title="True when fetching by Workflow ID, False when fetching by StoredWorkflow ID.",
    ),
]

LegacyQueryParam = Annotated[
    Optional[bool],
    Query(
        title="Legacy",
        description="Use the legacy workflow format.",
    ),
]

VersionQueryParam = Annotated[
    Optional[int],
    Query(
        title="Version",
        description="The version of the workflow to fetch.",
    ),
]

query_tags = [
    IndexQueryTag("name", "The stored workflow's name.", "n"),
    IndexQueryTag(
        "tag",
        "The workflow's tag, if the tag contains a colon an approach will be made to match the key and value of the tag separately.",
        "t",
    ),
    IndexQueryTag("user", "The stored workflow's owner's username.", "u"),
    IndexQueryTag(
        "is:published",
        "Include only published workflows in the final result. Be sure the query parameter `show_published` is set to `true` if to include all published workflows and not just the requesting user's.",
    ),
    IndexQueryTag(
        "is:importable",
        "Include only importable workflows in the final result.",
    ),
    IndexQueryTag(
        "is:deleted",
        "Include only deleted workflows in the final result.",
    ),
    IndexQueryTag(
        "is:shared_with_me",
        "Include only workflows shared with the requesting user.  Be sure the query parameter `show_shared` is set to `true` if to include shared workflows.",
    ),
    IndexQueryTag(
        "is:bookmarked",
        "Include only workflows bookmarked by the requesting user.",
    ),
]

SearchQueryParam: Optional[str] = search_query_param(
    model_name="Stored Workflow",
    tags=query_tags,
    free_text_fields=["name", "tag", "user"],
)

SkipStepCountsQueryParam: bool = Query(
    default=False,
    title="Skip step counts.",
    description="Set this to true to skip joining workflow step counts and optimize the resulting index query. Response objects will not contain step counts.",
)

StyleQueryParam = Annotated[
    Optional[
        Literal["export", "format2", "editor", "legacy", "instance", "run", "preview", "format2_wrapped_yaml", "ga"]
    ],
    Query(
        title="Style of export",
        description="The default is 'export', which is meant to be used with workflow import endpoints. Other formats such as 'instance', 'editor', 'run' are tied to the GUI and should not be considered stable APIs. The default format for 'export' is specified by the admin with the `default_workflow_export_format` config option. Style can be specified as either 'ga' or 'format2' directly to be explicit about which format to download.",
    ),
]

FormatQueryParam = Annotated[
    Optional[str],
    Query(
        title="Format",
        description="The format to download the workflow in.",
    ),
]

WorkflowsHistoryIDQueryParam = Annotated[
    Optional[DecodedDatabaseIdField],
    Query(
        title="History ID",
        description="The history id to import a workflow from.",
    ),
]

InvokeWorkflowBody = Annotated[
    InvokeWorkflowPayload,
    Body(
        default=...,
        title="Invoke workflow",
        description="The values to invoke a workflow.",
    ),
]

RefactorWorkflowBody = Annotated[
    RefactorRequest,
    Body(
        default=...,
        title="Refactor workflow",
        description="The values to refactor a workflow.",
    ),
]

SetWorkflowMenuBody = Annotated[
    Optional[SetWorkflowMenuPayload],
    Body(
        title="Set workflow menu",
        description="The values to set a workflow menu.",
    ),
]

DownloadWorkflowSummary = Union[
    WorkflowDictEditorSummary,
    StoredWorkflowDetailed,
    WorkflowDictRunSummary,
    WorkflowDictPreviewSummary,
    WorkflowDictFormat2Summary,
    WorkflowDictExportSummary,
    WorkflowDictFormat2WrappedYamlSummary,
]


@router.cbv
class FastAPIWorkflows:
    service: WorkflowsService = depends(WorkflowsService)

    @router.get(
        "/api/workflows",
        summary="Lists stored workflows viewable by the user.",
        response_description="A list with summary stored workflow information per viewable entry.",
    )
    def index(
        self,
        response: Response,
        trans: ProvidesUserContext = DependsOnTrans,
        show_deleted: bool = DeletedQueryParam,
        show_hidden: bool = HiddenQueryParam,
        missing_tools: bool = MissingToolsQueryParam,
        show_published: Optional[bool] = ShowPublishedQueryParam,
        show_shared: Optional[bool] = ShowSharedQueryParam,
        sort_by: Optional[WorkflowSortByEnum] = SortByQueryParam,
        sort_desc: Optional[bool] = SortDescQueryParam,
        limit: Optional[int] = LimitQueryParam,
        offset: Optional[int] = OffsetQueryParam,
        search: Optional[str] = SearchQueryParam,
        skip_step_counts: bool = SkipStepCountsQueryParam,
    ) -> List[Dict[str, Any]]:
        """Lists stored workflows viewable by the user."""
        payload = WorkflowIndexPayload.model_construct(
            show_published=show_published,
            show_hidden=show_hidden,
            show_deleted=show_deleted,
            show_shared=show_shared,
            missing_tools=missing_tools,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
            search=search,
            skip_step_counts=skip_step_counts,
        )
        workflows, total_matches = self.service.index(trans, payload, include_total_count=True)
        response.headers["total_matches"] = str(total_matches)
        return workflows

    @router.get(
        "/api/workflows/{workflow_id}/sharing",
        summary="Get the current sharing status of the given item.",
    )
    def sharing(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Return the sharing status of the item."""
        return self.service.shareable_service.sharing(trans, workflow_id)

    @router.get(
        "/api/workflows/{workflow_id}/download",
        summary="Returns a selected workflow.",
        response_model_exclude_unset=True,
    )
    # Preserve the following download route for now for dependent applications  -- deprecate at some point
    @router.get(
        "/api/workflows/download/{workflow_id}",
        summary="Returns a selected workflow.",
        response_model_exclude_unset=True,
    )
    def workflow_dict(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        history_id: WorkflowsHistoryIDQueryParam = None,
        style: StyleQueryParam = "export",
        format: FormatQueryParam = None,
        version: VersionQueryParam = None,
        instance: InstanceQueryParam = False,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> DownloadWorkflowSummary:
        return self.service.download_workflow(trans, workflow_id, history_id, style, format, version, instance)

    @router.put(
        "/api/workflows/{workflow_id}/enable_link_access",
        summary="Makes this item accessible by a URL link.",
    )
    def enable_link_access(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item accessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.enable_link_access(trans, workflow_id)

    @router.put(
        "/api/workflows/{workflow_id}/disable_link_access",
        summary="Makes this item inaccessible by a URL link.",
    )
    def disable_link_access(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item inaccessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.disable_link_access(trans, workflow_id)

    @router.put(
        "/api/workflows/{workflow_id}/refactor",
        summary="Updates the workflow stored with the given ID.",
    )
    def refactor(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        payload: RefactorWorkflowBody,
        instance: InstanceQueryParam = False,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> RefactorResponse:
        return self.service.refactor(trans, workflow_id, payload, instance or False)

    @router.put(
        "/api/workflows/{workflow_id}/publish",
        summary="Makes this item public and accessible by a URL link.",
    )
    def publish(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Makes this item publicly available by a URL link and return the current sharing status."""
        return self.service.shareable_service.publish(trans, workflow_id)

    @router.put(
        "/api/workflows/{workflow_id}/unpublish",
        summary="Removes this item from the published list.",
    )
    def unpublish(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> SharingStatus:
        """Removes this item from the published list and return the current sharing status."""
        return self.service.shareable_service.unpublish(trans, workflow_id)

    @router.put(
        "/api/workflows/menu",
        summary="Save workflow menu to be shown in the tool panel",
    )
    def set_workflow_menu(
        self,
        payload: SetWorkflowMenuBody = None,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> SetWorkflowMenuSummary:
        return self.service.set_workflow_menu(payload, trans)

    @router.put(
        "/api/workflows/{workflow_id}/share_with_users",
        summary="Share this item with specific users.",
    )
    def share_with_users(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: ShareWithPayload = Body(...),
    ) -> ShareWithStatus:
        """Shares this item with specific users and return the current sharing status."""
        return self.service.shareable_service.share_with_users(trans, workflow_id, payload)

    @router.put(
        "/api/workflows/{workflow_id}/slug",
        summary="Set a new slug for this shared item.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def set_slug(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: SetSlugPayload = Body(...),
    ):
        """Sets a new slug to access this item by URL. The new slug must be unique."""
        self.service.shareable_service.set_slug(trans, workflow_id, payload)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.delete(
        "/api/workflows/{workflow_id}",
        summary="Add the deleted flag to a workflow.",
    )
    def delete_workflow(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        self.service.delete(trans, workflow_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/api/workflows/{workflow_id}/undelete",
        summary="Remove the deleted flag from a workflow.",
    )
    def undelete_workflow(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        self.service.undelete(trans, workflow_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @router.post(
        "/api/workflows/{workflow_id}/invocations",
        name="Invoke workflow",
        summary="Schedule the workflow specified by `workflow_id` to run.",
    )
    @router.post(
        "/api/workflows/{workflow_id}/usage",
        name="Invoke workflow",
        summary="Schedule the workflow specified by `workflow_id` to run.",
        deprecated=True,
    )
    def invoke(
        self,
        payload: InvokeWorkflowBody,
        workflow_id: MultiTypeWorkflowIDPathParam,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> Union[WorkflowInvocationResponse, List[WorkflowInvocationResponse]]:
        return self.service.invoke_workflow(trans, workflow_id, payload)

    @router.get(
        "/api/workflows/{workflow_id}/versions",
        summary="List all versions of a workflow.",
    )
    def show_versions(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        instance: InstanceQueryParam = False,
    ):
        return self.service.get_versions(trans, workflow_id, instance or False)

    @router.get(
        "/api/workflows/{workflow_id}/counts",
        summary="Get state counts for accessible workflow.",
        name="invocation_state_counts",
        operation_id="workflows__invocation_counts",
    )
    def invocation_counts(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        instance: InvocationsInstanceQueryParam = False,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InvocationsStateCounts:
        return self.service.invocation_counts(trans, workflow_id, instance or False)

    @router.get(
        "/api/workflows/menu",
        summary="Get workflows present in the tools panel.",
    )
    def get_workflow_menu(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        show_deleted: Optional[bool] = DeletedQueryParam,
        show_hidden: Optional[bool] = HiddenQueryParam,
        missing_tools: Optional[bool] = MissingToolsQueryParam,
        show_published: Optional[bool] = ShowPublishedQueryParam,
        show_shared: Optional[bool] = ShowSharedQueryParam,
    ):
        payload = WorkflowIndexPayload(
            show_published=show_published,
            show_hidden=show_hidden,
            show_deleted=show_deleted,
            show_shared=show_shared,
            missing_tools=missing_tools,
        )
        return self.service.get_workflow_menu(
            trans,
            payload=payload,
        )

    @router.get(
        "/api/workflows/{workflow_id}",
        summary="Displays information needed to run a workflow.",
        name="show_workflow",
    )
    def show_workflow(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        instance: InstanceQueryParam = False,
        legacy: LegacyQueryParam = False,
        version: VersionQueryParam = None,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> StoredWorkflowDetailed:
        return self.service.show_workflow(trans, workflow_id, instance, legacy, version)


StepDetailQueryParam = Annotated[
    bool,
    Query(
        title="Include step details",
        description=(
            "Include details for individual invocation steps and populate a steps attribute in the resulting dictionary."
        ),
    ),
]
LegacyJobStateQueryParam = Annotated[
    bool,
    Query(
        title="Replace with job state",
        description=(
            """Populate the invocation step state with the job state instead of the invocation step state.
        This will also produce one step per job in mapping jobs to mimic the older behavior with respect to collections.
        Partially scheduled steps may provide incomplete information and the listed steps outputs
        are not the mapped over step outputs but the individual job outputs."""
        ),
    ),
]

WorkflowIdQueryParam = Annotated[
    Optional[DecodedDatabaseIdField],
    Query(
        title="Workflow ID",
        description="Return only invocations for this Workflow ID",
    ),
]

InvocationsHistoryIdQueryParam = Annotated[
    Optional[DecodedDatabaseIdField],
    Query(
        title="History ID",
        description="Return only invocations for this History ID",
    ),
]

JobIdQueryParam = Annotated[
    Optional[DecodedDatabaseIdField],
    Query(
        title="Job ID",
        description="Return only invocations for this Job ID",
    ),
]

UserIdQueryParam = Annotated[
    Optional[DecodedDatabaseIdField],
    Query(
        title="User ID",
        description="Return invocations for this User ID.",
    ),
]

InvocationsSortByQueryParam = Annotated[
    Optional[InvocationSortByEnum],
    Query(
        title="Sort By",
        description="Sort Workflow Invocations by this attribute",
    ),
]

InvocationsSortDescQueryParam = Annotated[
    bool,
    Query(
        title="Sort Descending",
        description="Sort in descending order?",
    ),
]

InvocationsIncludeTerminalQueryParam = Annotated[
    Optional[bool],
    Query(
        title="Include Terminal",
        description="Set to false to only include terminal Invocations.",
    ),
]

InvocationsLimitQueryParam = Annotated[
    Optional[int],
    Query(
        ge=1,
        title="Limit",
        description="Limit the number of invocations to return.",
    ),
]

InvocationsOffsetQueryParam = Annotated[
    Optional[int],
    Query(
        ge=0,
        title="Offset",
        description="Number of invocations to skip.",
    ),
]


CreateInvocationsFromStoreBody = Annotated[
    CreateInvocationsFromStorePayload,
    Body(
        default=...,
        title="Create invocations from store",
        description="The values and serialization parameters for creating invocations from a supplied model store.",
    ),
]


@router.cbv
class FastAPIInvocations:
    invocations_service: InvocationsService = depends(InvocationsService)

    @router.post(
        "/api/invocations/from_store",
        name="create_invocations_from_store",
        description="Create invocation(s) from a supplied model store.",
    )
    def create_invocations_from_store(
        self,
        payload: CreateInvocationsFromStoreBody,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> List[WorkflowInvocationResponse]:
        """
        Input can be an archive describing a Galaxy model store containing an
        workflow invocation - for instance one created with with write_store
        or prepare_store_download endpoint.
        """
        create_payload = CreateInvocationFromStore(**payload.model_dump())
        serialization_params = InvocationSerializationParams(**payload.model_dump())
        return self.invocations_service.create_from_store(trans, create_payload, serialization_params)

    @router.get(
        "/api/invocations",
        summary="Get the list of a user's workflow invocations.",
        name="index_invocations",
    )
    def index_invocations(
        self,
        response: Response,
        workflow_id: WorkflowIdQueryParam = None,
        history_id: InvocationsHistoryIdQueryParam = None,
        job_id: JobIdQueryParam = None,
        user_id: UserIdQueryParam = None,
        sort_by: InvocationsSortByQueryParam = None,
        sort_desc: InvocationsSortDescQueryParam = False,
        include_terminal: InvocationsIncludeTerminalQueryParam = True,
        limit: InvocationsLimitQueryParam = None,
        offset: InvocationsOffsetQueryParam = None,
        instance: InvocationsInstanceQueryParam = False,
        view: SerializationViewQueryParam = None,
        step_details: StepDetailQueryParam = False,
        include_nested_invocations: bool = True,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[WorkflowInvocationResponse]:
        if not trans.user:
            # Anon users don't have accessible invocations (currently, though published invocations should be a thing)
            response.headers["total_matches"] = "0"
            return []
        invocation_payload = InvocationIndexPayload(
            workflow_id=workflow_id,
            history_id=history_id,
            job_id=job_id,
            user_id=user_id,
            sort_by=sort_by,
            sort_desc=sort_desc,
            include_terminal=include_terminal,
            limit=limit,
            offset=offset,
            instance=instance,
            include_nested_invocations=include_nested_invocations,
        )
        serialization_params = InvocationSerializationParams(
            view=view,
            step_details=step_details,
        )
        invocations, total_matches = self.invocations_service.index(trans, invocation_payload, serialization_params)
        response.headers["total_matches"] = str(total_matches)
        return invocations

    @router.get(
        "/api/workflows/{workflow_id}/invocations",
        summary="Get the list of a user's workflow invocations.",
        name="index_invocations",
    )
    @router.get(
        "/api/workflows/{workflow_id}/usage",
        summary="Get the list of a user's workflow invocations.",
        name="index_invocations",
        deprecated=True,
    )
    def index_workflow_invocations(
        self,
        response: Response,
        workflow_id: StoredWorkflowIDPathParam,
        history_id: InvocationsHistoryIdQueryParam = None,
        job_id: JobIdQueryParam = None,
        user_id: UserIdQueryParam = None,
        sort_by: InvocationsSortByQueryParam = None,
        sort_desc: InvocationsSortDescQueryParam = False,
        include_terminal: InvocationsIncludeTerminalQueryParam = True,
        limit: InvocationsLimitQueryParam = None,
        offset: InvocationsOffsetQueryParam = None,
        instance: InvocationsInstanceQueryParam = False,
        view: SerializationViewQueryParam = None,
        step_details: StepDetailQueryParam = False,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[WorkflowInvocationResponse]:
        invocations = self.index_invocations(
            response=response,
            workflow_id=workflow_id,
            history_id=history_id,
            job_id=job_id,
            user_id=user_id,
            sort_by=sort_by,
            sort_desc=sort_desc,
            include_terminal=include_terminal,
            limit=limit,
            offset=offset,
            instance=instance,
            view=view,
            step_details=step_details,
            trans=trans,
        )
        return invocations

    @router.post(
        "/api/invocations/{invocation_id}/prepare_store_download",
        summary="Prepare a workflow invocation export-style download.",
    )
    def prepare_store_download(
        self,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: PrepareStoreDownloadPayload = Body(...),
    ) -> AsyncFile:
        return self.invocations_service.prepare_store_download(
            trans,
            invocation_id,
            payload,
        )

    @router.post(
        "/api/invocations/{invocation_id}/write_store",
        summary="Prepare a workflow invocation export-style download and write to supplied URI.",
    )
    def write_store(
        self,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: WriteInvocationStoreToPayload = Body(...),
    ) -> AsyncTaskResultSummary:
        rval = self.invocations_service.write_store(
            trans,
            invocation_id,
            payload,
        )
        return rval

    @router.get("/api/invocations/{invocation_id}", summary="Get detailed description of a workflow invocation.")
    def show_invocation(
        self,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        step_details: StepDetailQueryParam = False,
        legacy_job_state: LegacyJobStateQueryParam = False,
    ) -> WorkflowInvocationResponse:
        serialization_params = InvocationSerializationParams(
            step_details=step_details, legacy_job_state=legacy_job_state
        )
        return self.invocations_service.show(trans, invocation_id, serialization_params, eager=True)

    @router.get(
        "/api/workflows/{workflow_id}/invocations/{invocation_id}",
        summary="Get detailed description of a workflow invocation.",
    )
    @router.get(
        "/api/workflows/{workflow_id}/usage/{invocation_id}",
        summary="Get detailed description of a workflow invocation.",
        deprecated=True,
    )
    def show_workflow_invocation(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        step_details: StepDetailQueryParam = False,
        legacy_job_state: LegacyJobStateQueryParam = False,
    ) -> WorkflowInvocationResponse:
        """An alias for `GET /api/invocations/{invocation_id}`. `workflow_id` is ignored."""
        return self.show_invocation(
            trans=trans, invocation_id=invocation_id, step_details=step_details, legacy_job_state=legacy_job_state
        )

    @router.delete("/api/invocations/{invocation_id}", summary="Cancel the specified workflow invocation.")
    def cancel_invocation(
        self,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        step_details: StepDetailQueryParam = False,
        legacy_job_state: LegacyJobStateQueryParam = False,
    ) -> WorkflowInvocationResponse:
        serialization_params = InvocationSerializationParams(
            step_details=step_details, legacy_job_state=legacy_job_state
        )
        return self.invocations_service.cancel(trans, invocation_id, serialization_params)

    @router.delete(
        "/api/workflows/{workflow_id}/invocations/{invocation_id}", summary="Cancel the specified workflow invocation."
    )
    @router.delete(
        "/api/workflows/{workflow_id}/usage/{invocation_id}",
        summary="Cancel the specified workflow invocation.",
        deprecated=True,
    )
    def cancel_workflow_invocation(
        self,
        invocation_id: InvocationIDPathParam,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        step_details: StepDetailQueryParam = False,
        legacy_job_state: LegacyJobStateQueryParam = False,
    ) -> WorkflowInvocationResponse:
        """An alias for `DELETE /api/invocations/{invocation_id}`. `workflow_id` is ignored."""

        return self.cancel_invocation(
            trans=trans, invocation_id=invocation_id, step_details=step_details, legacy_job_state=legacy_job_state
        )

    @router.get(
        "/api/invocations/{invocation_id}/report",
        summary="Get JSON summarizing invocation for reporting.",
    )
    def show_invocation_report(
        self,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InvocationReport:
        return self.invocations_service.show_invocation_report(trans, invocation_id)

    @router.get(
        "/api/workflows/{workflow_id}/invocations/{invocation_id}/report",
        summary="Get JSON summarizing invocation for reporting.",
    )
    @router.get(
        "/api/workflows/{workflow_id}/usage/{invocation_id}/report",
        summary="Get JSON summarizing invocation for reporting.",
        deprecated=True,
    )
    def show_workflow_invocation_report(
        self,
        invocation_id: InvocationIDPathParam,
        workflow_id: StoredWorkflowIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InvocationReport:
        """An alias for `GET /api/invocations/{invocation_id}/report`. `workflow_id` is ignored."""
        return self.show_invocation_report(trans=trans, invocation_id=invocation_id)

    @router.get(
        "/api/invocations/{invocation_id}/report.pdf",
        summary="Get PDF summarizing invocation for reporting.",
        response_class=StreamingResponse,
    )
    def show_invocation_report_pdf(
        self,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        wfi_report = self.invocations_service.show_invocation_report(trans, invocation_id, format="pdf")
        return StreamingResponse(
            content=BytesIO(wfi_report),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="report_galaxy_invocation_{trans.security.encode_id(invocation_id)}.pdf"',
                "Access-Control-Expose-Headers": "Content-Disposition",
            },
        )

    @router.get(
        "/api/workflows/{workflow_id}/invocations/{invocation_id}/report.pdf",
        summary="Get PDF summarizing invocation for reporting.",
        response_class=StreamingResponse,
    )
    @router.get(
        "/api/workflows/{workflow_id}/usage/{invocation_id}/report.pdf",
        summary="Get PDF summarizing invocation for reporting.",
        response_class=StreamingResponse,
        deprecated=True,
    )
    def show_workflow_invocation_report_pdf(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """An alias for `GET /api/invocations/{invocation_id}/report.pdf`. `workflow_id` is ignored."""
        return self.show_invocation_report_pdf(trans=trans, invocation_id=invocation_id)

    @router.get(
        "/api/invocations/steps/{step_id}",
        summary="Show details of workflow invocation step.",
    )
    def step(
        self,
        step_id: WorkflowInvocationStepIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InvocationStep:
        return self.invocations_service.show_invocation_step(trans, step_id)

    @router.get(
        "/api/invocations/{invocation_id}/steps/{step_id}",
        summary="Show details of workflow invocation step.",
    )
    def invocation_step(
        self,
        invocation_id: InvocationIDPathParam,
        step_id: WorkflowInvocationStepIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InvocationStep:
        """An alias for `GET /api/invocations/steps/{step_id}`. `invocation_id` is ignored."""
        return self.step(trans=trans, step_id=step_id)

    @router.get(
        "/api/workflows/{workflow_id}/invocations/{invocation_id}/steps/{step_id}",
        summary="Show details of workflow invocation step.",
    )
    @router.get(
        "/api/workflows/{workflow_id}/usage/{invocation_id}/steps/{step_id}",
        summary="Show details of workflow invocation step.",
        deprecated=True,
    )
    def workflow_invocation_step(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        invocation_id: InvocationIDPathParam,
        step_id: WorkflowInvocationStepIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InvocationStep:
        """An alias for `GET /api/invocations/{invocation_id}/steps/{step_id}`. `workflow_id` and `invocation_id` are ignored."""
        return self.invocation_step(trans=trans, invocation_id=invocation_id, step_id=step_id)

    @router.put(
        "/api/invocations/{invocation_id}/steps/{step_id}",
        summary="Update state of running workflow step invocation - still very nebulous but this would be for stuff like confirming paused steps can proceed etc.",
    )
    def update_invocation_step(
        self,
        invocation_id: InvocationIDPathParam,
        step_id: WorkflowInvocationStepIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: InvocationUpdatePayload = Body(...),
    ) -> InvocationStep:
        return self.invocations_service.update_invocation_step(trans=trans, step_id=step_id, action=payload.action)

    @router.put(
        "/api/workflows/{workflow_id}/invocations/{invocation_id}/steps/{step_id}",
        summary="Update state of running workflow step invocation.",
    )
    @router.put(
        "/api/workflows/{workflow_id}/usage/{invocation_id}/steps/{step_id}",
        summary="Update state of running workflow step invocation.",
        deprecated=True,
    )
    def update_workflow_invocation_step(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        invocation_id: InvocationIDPathParam,
        step_id: WorkflowInvocationStepIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: InvocationUpdatePayload = Body(...),
    ) -> InvocationStep:
        """An alias for `PUT /api/invocations/{invocation_id}/steps/{step_id}`. `workflow_id` is ignored."""
        return self.update_invocation_step(trans=trans, invocation_id=invocation_id, step_id=step_id, payload=payload)

    @router.get(
        "/api/invocations/{invocation_id}/step_jobs_summary",
        summary="Get job state summary info aggregated per step of the workflow invocation.",
    )
    def invocation_step_jobs_summary(
        self,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[
        Union[
            InvocationStepJobsResponseStepModel,
            InvocationStepJobsResponseJobModel,
            InvocationStepJobsResponseCollectionJobsModel,
        ]
    ]:
        """
        Warning: We allow anyone to fetch job state information about any object they
        can guess an encoded ID for - it isn't considered protected data. This keeps
        polling IDs as part of state calculation for large histories and collections as
        efficient as possible.
        """
        step_jobs_summary = self.invocations_service.show_invocation_step_jobs_summary(trans, invocation_id)
        return [
            (
                InvocationStepJobsResponseStepModel(**summary)
                if summary["model"] == "WorkflowInvocationStep"
                else (
                    InvocationStepJobsResponseJobModel(**summary)
                    if summary["model"] == "Job"
                    else InvocationStepJobsResponseCollectionJobsModel(**summary)
                )
            )
            for summary in step_jobs_summary
        ]

    @router.get(
        "/api/workflows/{workflow_id}/invocations/{invocation_id}/step_jobs_summary",
        summary="Get job state summary info aggregated per step of the workflow invocation.",
    )
    @router.get(
        "/api/workflows/{workflow_id}/usage/{invocation_id}/step_jobs_summary",
        summary="Get job state summary info aggregated per step of the workflow invocation.",
        deprecated=True,
    )
    def workflow_invocation_step_jobs_summary(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> List[
        Union[
            InvocationStepJobsResponseStepModel,
            InvocationStepJobsResponseJobModel,
            InvocationStepJobsResponseCollectionJobsModel,
        ]
    ]:
        """An alias for `GET /api/invocations/{invocation_id}/step_jobs_summary`. `workflow_id` is ignored."""
        return self.invocation_step_jobs_summary(trans=trans, invocation_id=invocation_id)

    @router.get(
        "/api/invocations/{invocation_id}/jobs_summary",
        summary="Get job state summary info aggregated across all current jobs of the workflow invocation.",
    )
    def invocation_jobs_summary(
        self,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InvocationJobsResponse:
        """
        Warning: We allow anyone to fetch job state information about any object they
        can guess an encoded ID for - it isn't considered protected data. This keeps
        polling IDs as part of state calculation for large histories and collections as
        efficient as possible.
        """
        jobs_summary = self.invocations_service.show_invocation_jobs_summary(trans, invocation_id)
        return InvocationJobsResponse(**jobs_summary)

    @router.get(
        "/api/workflows/{workflow_id}/invocations/{invocation_id}/jobs_summary",
        summary="Get job state summary info aggregated across all current jobs of the workflow invocation.",
    )
    @router.get(
        "/api/workflows/{workflow_id}/usage/{invocation_id}/jobs_summary",
        summary="Get job state summary info aggregated across all current jobs of the workflow invocation.",
        deprecated=True,
    )
    def workflow_invocation_jobs_summary(
        self,
        workflow_id: StoredWorkflowIDPathParam,
        invocation_id: InvocationIDPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InvocationJobsResponse:
        """An alias for `GET /api/invocations/{invocation_id}/jobs_summary`. `workflow_id` is ignored."""
        return self.invocation_jobs_summary(trans=trans, invocation_id=invocation_id)
