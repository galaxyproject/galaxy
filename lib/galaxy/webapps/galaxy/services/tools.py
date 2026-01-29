import logging
import os
import shutil
import tempfile
from json import dumps
from typing import (
    Any,
    cast,
    Literal,
    Optional,
    Union,
)

from starlette.datastructures import UploadFile

from galaxy import (
    exceptions,
    util,
)
from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions.utils import api_error_to_dict
from galaxy.managers.collections_util import dictify_dataset_collection_instance
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.histories import HistoryManager
from galaxy.managers.tools import (
    get_tool_from_trans,
    ToolRunReference,
)
from galaxy.model import (
    LibraryDatasetDatasetAssociation,
    PostJobAction,
    User,
)
from galaxy.schema.credentials import CredentialsContext
from galaxy.schema.fetch_data import (
    CreateDataLandingPayload,
    CreateFileLandingPayload,
    DataElementsTarget,
    FetchDataFormPayload,
    FetchDataPayload,
    FilesPayload,
    HdaDestination,
    HdcaDataItemsTarget,
    HdcaDestination,
    NestedElement,
    TargetsAdapter,
    UrlDataElement,
)
from galaxy.schema.schema import CreateToolLandingRequestPayload
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.tool_util_models.parameters import (
    CollectionElementCollectionRequestUri,
    CollectionElementDataRequestUri,
    DataRequestCollectionUri,
    DataRequestUri,
    FileRequestUri,
)
from galaxy.tools import Tool
from galaxy.tools.search import ToolBoxSearch
from galaxy.util.path import safe_contains
from galaxy.webapps.galaxy.services._fetch_util import validate_and_normalize_targets
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)

ToolRunPayload = dict[str, Any]
JobCreateResponse = dict[str, Any]


def get_tool(trans: ProvidesHistoryContext, tool_ref: ToolRunReference) -> Tool:
    tool: Optional[Tool] = None
    if tool_ref.tool_uuid and trans.user:
        tool = trans.app.toolbox.get_unprivileged_tool_or_none(trans.user, tool_uuid=tool_ref.tool_uuid)
    if not tool:
        tool_id = tool_ref.tool_id
        tool_uuid = tool_ref.tool_uuid
        tool_version = tool_ref.tool_version
        tool = trans.app.toolbox.get_tool(
            tool_id=tool_id,
            tool_uuid=tool_uuid,
            tool_version=tool_version,
        )
    if not tool:
        log.debug(f"Not found tool with kwds [{tool_ref}]")
        raise exceptions.ToolMissingException("Tool not found.")
    return tool


def validate_tool_for_running(trans: ProvidesHistoryContext, tool_ref: ToolRunReference) -> Tool:
    if trans.user_is_bootstrap_admin:
        raise exceptions.RealUserRequiredException("Only real users can execute tools or run jobs.")

    if tool_ref.tool_id is None and tool_ref.tool_uuid is None:
        raise exceptions.RequestParameterMissingException("Must specify a valid tool_id to use this endpoint.")

    tool = get_tool_from_trans(trans, tool_ref)
    if not tool.allow_user_access(trans.user):
        raise exceptions.ItemAccessibilityException("Tool not accessible.")
    return tool


def file_landing_payload_to_fetch_targets(data_landing_payload: CreateFileLandingPayload):
    """Convert a CreateDataLandingPayload with DataOrCollectionRequest format to FetchDataPayload with Targets format.

    This function transforms data/collection requests (used in workflow landing and data request payloads) into the fetch API's target format.
    """
    targets: list[Union[DataElementsTarget, HdcaDataItemsTarget]] = []

    for request_item in data_landing_payload.request_state:
        if isinstance(request_item, (DataRequestUri, FileRequestUri)):
            # Convert single file/URL request to a DataElementsTarget
            element = UrlDataElement(
                src="url",
                url=str(request_item.url),
                ext=request_item.ext,
                dbkey=request_item.dbkey,
                name=request_item.name,
                deferred=request_item.deferred,
                info=request_item.info,
                tags=request_item.tags,
                space_to_tab=request_item.space_to_tab,
                to_posix_lines=request_item.to_posix_lines,
                created_from_basename=request_item.created_from_basename,
            )

            targets.append(
                DataElementsTarget(
                    destination=HdaDestination(type="hdas"),
                    elements=[element],
                )
            )

        elif isinstance(request_item, DataRequestCollectionUri):
            # Convert collection request to HdcaDataItemsTarget
            def convert_collection_element(elem):
                """Convert a collection element (file or nested collection) recursively."""
                if isinstance(elem, CollectionElementDataRequestUri):
                    # This is a file element
                    return UrlDataElement(
                        src="url",
                        url=str(elem.url),
                        ext=elem.ext,
                        dbkey=elem.dbkey,
                        name=elem.identifier,
                        deferred=elem.deferred,
                        info=elem.info,
                        tags=elem.tags,
                        space_to_tab=elem.space_to_tab,
                        to_posix_lines=elem.to_posix_lines,
                        created_from_basename=elem.created_from_basename,
                    )
                elif isinstance(elem, CollectionElementCollectionRequestUri):
                    # This is a nested collection element
                    # Recursively convert its elements
                    nested_elements = [convert_collection_element(nested_elem) for nested_elem in elem.elements]
                    return NestedElement(
                        name=elem.identifier,
                        elements=nested_elements,
                        collection_type=elem.collection_type,
                    )
                else:
                    raise ValueError(f"Unknown collection element type: {type(elem)}")

            elements = [convert_collection_element(elem) for elem in request_item.elements]

            targets.append(
                HdcaDataItemsTarget(
                    destination=HdcaDestination(type="hdca"),
                    elements=elements,
                    collection_type=request_item.collection_type,
                    name=request_item.name,
                )
            )

    return [target.model_dump(mode="json", exclude_unset=True) for target in TargetsAdapter.validate_python(targets)]


class ToolsService(ServiceBase):
    def __init__(
        self,
        config: GalaxyAppConfiguration,
        toolbox_search: ToolBoxSearch,
        security: IdEncodingHelper,
        history_manager: HistoryManager,
    ):
        super().__init__(security)
        self.config = config
        self.toolbox_search = toolbox_search
        self.history_manager = history_manager

    def file_landing_to_tool_landing(
        self,
        trans: ProvidesUserContext,
        file_landing_payload: CreateFileLandingPayload,
    ) -> CreateToolLandingRequestPayload:
        request_version = "1"
        payload = {"targets": file_landing_payload_to_fetch_targets(file_landing_payload)}
        validate_and_normalize_targets(trans, payload, set_internal_fields=False)
        request_state = {
            "request_version": request_version,
            "request_json": {
                "targets": payload["targets"],
            },
            "file_count": "0",
        }
        return CreateToolLandingRequestPayload(
            tool_id="__DATA_FETCH__",
            tool_version=None,
            request_state=request_state,
            client_secret=file_landing_payload.client_secret,
            public=file_landing_payload.public,
        )

    def data_landing_to_tool_landing(
        self,
        trans: ProvidesUserContext,
        data_landing_payload: CreateDataLandingPayload,
    ) -> CreateToolLandingRequestPayload:
        request_version = "1"
        payload = data_landing_payload.model_dump(exclude_unset=True)["request_state"]
        validate_and_normalize_targets(trans, payload, set_internal_fields=False)
        validated_back_to_model = TargetsAdapter.validate_python(payload["targets"])
        request_state = {
            "request_version": request_version,
            "request_json": {"targets": TargetsAdapter.dump_python(validated_back_to_model, exclude_unset=True)},
            "file_count": "0",
        }
        return CreateToolLandingRequestPayload(
            tool_id="__DATA_FETCH__",
            tool_version=None,
            request_state=request_state,
            client_secret=data_landing_payload.client_secret,
            public=data_landing_payload.public,
        )

    def create_fetch(
        self,
        trans: ProvidesHistoryContext,
        fetch_payload: Union[FetchDataFormPayload, FetchDataPayload],
        files: Optional[list[UploadFile]] = None,
    ) -> JobCreateResponse:
        payload = fetch_payload.model_dump(exclude_unset=True)
        request_version = "1"
        history_id = payload.pop("history_id")
        clean_payload = {}
        files_payload = {}
        if files:
            for i, upload_file in enumerate(files):
                with tempfile.NamedTemporaryFile(
                    dir=trans.app.config.new_file_path, prefix="upload_file_data_", delete=False
                ) as dest:
                    shutil.copyfileobj(upload_file.file, dest)
                    util.umask_fix_perms(dest.name, trans.app.config.umask, 0o0666)
                upload_file.file.close()
                files_payload[f"files_{i}|file_data"] = FilesPayload(
                    filename=upload_file.filename, local_filename=dest.name
                )
        for key, value in payload.items():
            if key == "key":
                continue
            if key.startswith("files_") or key.startswith("__files_"):
                files_payload[key] = value
                continue
            clean_payload[key] = value
        clean_payload["check_content"] = self.config.check_upload_content
        validate_and_normalize_targets(trans, clean_payload)
        request = dumps(clean_payload)
        create_payload: ToolRunPayload = {
            "tool_id": "__DATA_FETCH__",
            "history_id": history_id,
            "inputs": {
                "request_version": request_version,
                "request_json": request,
                "file_count": str(len(files_payload)),
            },
        }
        create_payload.update(files_payload)
        return self._create(trans, create_payload)

    def _create(self, trans: ProvidesHistoryContext, payload: ToolRunPayload, **kwd) -> JobCreateResponse:
        action = payload.get("action")
        if action == "rerun":
            raise Exception("'rerun' action has been deprecated")

        tool_run_reference = ToolRunReference(
            payload.get("tool_id"), payload.get("tool_uuid"), payload.get("tool_version")
        )
        tool = validate_tool_for_running(trans, tool_run_reference)

        # Set running history from payload parameters.
        # History not set correctly as part of this API call for
        # dataset upload.
        if history_id := payload.get("history_id"):
            history_id = trans.security.decode_id(history_id) if isinstance(history_id, str) else history_id
            target_history = self.history_manager.get_mutable(history_id, trans.user, current_history=trans.history)
        else:
            target_history = None

        # Set up inputs.
        inputs = payload.get("inputs", {})
        if not isinstance(inputs, dict):
            raise exceptions.RequestParameterInvalidException(f"inputs invalid {inputs}")

        # Find files coming in as multipart file data and add to inputs.
        for k, v in payload.items():
            if k.startswith("files_") or k.startswith("__files_"):
                inputs[k] = v

        # for inputs that are coming from the Library, copy them into the history
        self._patch_library_inputs(trans, inputs, target_history)

        # TODO: encode data ids and decode ids.
        # TODO: handle dbkeys
        params = util.Params(inputs, sanitize=False)
        incoming = params.__dict__

        # use_cached_job can be passed in via the top-level payload or among the tool inputs.
        # I think it should be a top-level parameter, but because the selector is implemented
        # as a regular tool parameter we accept both.
        use_cached_job = payload.get("use_cached_job", False) or util.string_as_bool(
            inputs.get("use_cached_job", "false")
        )
        preferred_object_store_id = payload.get("preferred_object_store_id")
        credentials_context = payload.get("credentials_context")
        input_format = str(payload.get("input_format", "legacy"))
        if input_format not in ("legacy", "21.01"):
            raise exceptions.RequestParameterInvalidException(f"input_format invalid {input_format}")
        input_format = cast(Literal["legacy", "21.01"], input_format)
        if "data_manager_mode" in payload:
            incoming["__data_manager_mode"] = payload["data_manager_mode"]
        tags = payload.get("__tags")
        vars = tool.handle_input(
            trans,
            incoming,
            history=target_history,
            use_cached_job=use_cached_job,
            input_format=input_format,
            preferred_object_store_id=preferred_object_store_id,
            credentials_context=CredentialsContext(root=credentials_context) if credentials_context else None,
            tags=tags,
        )

        new_pja_flush = False
        for job in vars.get("jobs", []):
            if inputs.get("send_email_notification", False):
                # Unless an anonymous user is invoking this via the API it
                # should never be an option, but check and enforce that here
                if trans.user is None:
                    raise exceptions.ToolExecutionError("Anonymously run jobs cannot send an email notification.")
                else:
                    job_email_action = PostJobAction("EmailAction")
                    job.add_post_job_action(job_email_action)
                    new_pja_flush = True

        if new_pja_flush:
            trans.sa_session.commit()

        return self._handle_inputs_output_to_api_response(trans, tool, target_history, vars)

    def _handle_inputs_output_to_api_response(self, trans, tool, target_history, vars) -> JobCreateResponse:
        # TODO: check for errors and ensure that output dataset(s) are available.
        output_datasets = vars.get("out_data", [])
        rval: dict[str, Any] = {"outputs": [], "output_collections": [], "jobs": [], "implicit_collections": []}
        rval["produces_entry_points"] = tool.produces_entry_points
        if job_errors := vars.get("job_errors", []):
            # If we are here - some jobs were successfully executed but some failed.
            # TODO: We should probably alter the response status code and have a component that knows
            # how to template in things like src and id, so we don't have to rely just on a textual error message.
            execution_errors = [
                (
                    trans.security.encode_all_ids(api_error_to_dict(exception=e))
                    if isinstance(e, exceptions.MessageException)
                    else e
                )
                for e in job_errors
            ]
            rval["errors"] = execution_errors

        outputs = rval["outputs"]
        # TODO:?? poss. only return ids?
        for output_name, output in output_datasets:
            output_dict = output.to_dict()
            # add the output name back into the output data structure
            # so it's possible to figure out which newly created elements
            # correspond with which tool file outputs
            output_dict["output_name"] = output_name
            outputs.append(output_dict)

        for job in vars.get("jobs", []):
            rval["jobs"].append(job.to_dict(view="collection"))

        for output_name, collection_instance in vars.get("output_collections", []):
            history = target_history or trans.history
            output_dict = dictify_dataset_collection_instance(
                collection_instance,
                security=trans.security,
                url_builder=trans.url_builder,
                parent=history,
            )
            output_dict["output_name"] = output_name
            rval["output_collections"].append(output_dict)

        for output_name, collection_instance in vars.get("implicit_collections", {}).items():
            history = target_history or trans.history
            output_dict = dictify_dataset_collection_instance(
                collection_instance,
                security=trans.security,
                url_builder=trans.url_builder,
                parent=history,
            )
            output_dict["output_name"] = output_name
            rval["implicit_collections"].append(output_dict)

        trans.security.encode_all_ids(rval, recursive=True)
        return rval

    def _search(self, q: str, view: Optional[str]) -> list[str]:
        """
        Perform the search on the given query.
        Boosts and numer of results are configurable in galaxy.ini file.

        :param q: the query to search with
        :type  q: str

        :return:      Dictionary containing the tools' ids of the best hits.
        :return type: dict
        """
        panel_view = view or self.config.default_panel_view

        results = self.toolbox_search.search(
            q=q,
            panel_view=panel_view,
            config=self.config,
        )
        return results

    def _patch_library_inputs(self, trans: ProvidesHistoryContext, inputs, target_history):
        """
        Transform inputs from the data library to history items.
        """
        for k, v in inputs.items():
            new_value = self._patch_library_dataset(trans, v, target_history)
            if new_value:
                v = new_value
            elif isinstance(v, dict) and "values" in v:
                for index, value in enumerate(v["values"]):
                    patched = self._patch_library_dataset(trans, value, target_history)
                    if patched:
                        v["values"][index] = patched
            inputs[k] = v

    def _patch_library_dataset(self, trans: ProvidesHistoryContext, v, target_history):
        if isinstance(v, dict) and "id" in v and v.get("src") == "ldda":
            ldda = trans.sa_session.get(LibraryDatasetDatasetAssociation, self.decode_id(v["id"]))
            if not ldda:
                raise exceptions.ObjectNotFound("Could not find library dataset dataset association.")
            if trans.user_is_admin or trans.app.security_agent.can_access_dataset(
                trans.get_current_user_roles(), ldda.dataset
            ):
                return ldda.to_history_dataset_association(target_history, add_to_history=True)

    #
    # -- Helper methods --
    #
    def _get_tool(
        self, trans: ProvidesUserContext, id, tool_version=None, tool_uuid=None, user: Optional[User] = None
    ) -> Tool:
        tool = trans.app.toolbox.get_tool(id, tool_version)
        if not tool:
            if user:
                # FIXME: id as tool_uuid is for raw_tool_source endpoint, port to fastapi and fix
                if id == tool_uuid:
                    id = None
                tool = trans.app.toolbox.get_tool(user=user, tool_id=id, tool_uuid=tool_uuid)
                if tool:
                    return tool
            raise exceptions.ObjectNotFound(f"Could not find tool with id '{id or tool_uuid}'.")
        if not tool.allow_user_access(user):
            raise exceptions.AuthenticationFailed(f"Access denied, please login for tool with id '{id}'.")
        return tool

    def _detect(self, trans: ProvidesUserContext, tool_id):
        """
        Detect whether the tool with the given id is installed.

        :param tool_id: exact id of the tool
        :type tool_id:  str

        :return:      list with available versions
        "return type: list
        """
        tools = trans.app.toolbox.get_tool(tool_id, get_all_versions=True)
        detected_versions = []
        if tools:
            for tool in tools:
                if tool and tool.allow_user_access(trans.user):
                    detected_versions.append(tool.version)
        return detected_versions

    def get_tool_icon_path(self, trans, tool_id, tool_version=None) -> Optional[str]:
        tool = self._get_tool(trans, tool_id, tool_version)
        if tool and tool.icon:
            icon_file_path = tool.icon
            if icon_file_path and tool.tool_dir:
                # Prevent any path traversal attacks. The icon_src must be in the tool's directory.
                if not safe_contains(tool.tool_dir, icon_file_path):
                    raise Exception(
                        f"Invalid icon path for tool '{tool_id}'. Path must be within the tool's directory."
                    )
                file_path = os.path.join(tool.tool_dir, icon_file_path)
                if os.path.exists(file_path):
                    return file_path
        return None
