import json
import logging
import os
import uuid
from collections import namedtuple
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Tuple,
)

from gxformat2 import (
    from_galaxy_native,
    ImporterGalaxyInterface,
    ImportOptions,
    python_to_workflow,
)
from pydantic import BaseModel
from sqlalchemy import (
    and_,
    desc,
    false,
    or_,
    true,
)
from sqlalchemy.orm import (
    aliased,
    joinedload,
    Query,
    subqueryload,
)

from galaxy import (
    exceptions,
    model,
    util,
)
from galaxy.job_execution.actions.post import ActionBox
from galaxy.managers import sharable
from galaxy.managers.context import ProvidesUserContext
from galaxy.model.index_filter_util import (
    append_user_filter,
    raw_text_column_filter,
    tag_filter,
    text_column_filter,
)
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.schema.schema import WorkflowIndexQueryPayload
from galaxy.structured_app import MinimalManagerApp
from galaxy.tools.parameters import (
    params_to_incoming,
    visit_input_values,
)
from galaxy.tools.parameters.basic import (
    DataCollectionToolParameter,
    DataToolParameter,
    RuntimeValue,
    workflow_building_modes,
)
from galaxy.util.json import (
    safe_dumps,
    safe_loads,
)
from galaxy.util.sanitize_html import sanitize_html
from galaxy.util.search import (
    FilteredTerm,
    parse_filters_structured,
    RawTextTerm,
)
from galaxy.web import url_for
from galaxy.workflow.modules import (
    is_tool_module_type,
    module_factory,
    ToolModule,
    WorkflowModuleInjector,
)
from galaxy.workflow.refactor.execute import WorkflowRefactorExecutor
from galaxy.workflow.refactor.schema import (
    RefactorActionExecution,
    RefactorActions,
)
from galaxy.workflow.reports import generate_report
from galaxy.workflow.resources import get_resource_mapper_function
from galaxy.workflow.steps import attach_ordered_steps
from .base import decode_id
from .executables import artifact_class

log = logging.getLogger(__name__)


INDEX_SEARCH_FILTERS = {
    "name": "name",
    "tag": "tag",
    "n": "name",
    "t": "tag",
    "user": "user",
    "u": "user",
    "is": "is",
}


class WorkflowsManager(sharable.SharableModelManager):
    """Handle CRUD type operations related to workflows. More interesting
    stuff regarding workflow execution, step sorting, etc... can be found in
    the galaxy.workflow module.
    """

    model_class = model.StoredWorkflow
    foreign_key_name = "stored_workflow"
    user_share_model = model.StoredWorkflowUserShareAssociation

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.app = app

    def index_query(
        self, trans: ProvidesUserContext, payload: WorkflowIndexQueryPayload, include_total_count: bool = False
    ) -> Tuple[Query, Optional[int]]:
        show_published = payload.show_published
        show_hidden = payload.show_hidden
        show_deleted = payload.show_deleted
        show_shared = payload.show_shared

        if show_shared is None:
            show_shared = not show_hidden and not show_deleted

        if show_shared and show_deleted:
            message = "show_shared and show_deleted cannot both be specified as true"
            raise exceptions.RequestParameterInvalidException(message)
        if show_shared and show_hidden:
            message = "show_shared and show_hidden cannot both be specified as true"
            raise exceptions.RequestParameterInvalidException(message)

        filters = [
            model.StoredWorkflow.user == trans.user,
        ]
        user = trans.user
        if user and show_shared:
            filters.append(model.StoredWorkflowUserShareAssociation.user == user)

        if show_published or user is None and show_published is None:
            filters.append((model.StoredWorkflow.published == true()))

        query = trans.sa_session.query(model.StoredWorkflow)
        if show_shared:
            query = query.outerjoin(model.StoredWorkflow.users_shared_with)
        query = query.outerjoin(model.StoredWorkflow.tags)

        latest_workflow_load = joinedload("latest_workflow")
        if not payload.skip_step_counts:
            latest_workflow_load = latest_workflow_load.undefer("step_count")
        latest_workflow_load = latest_workflow_load.lazyload("steps")

        query = query.options(joinedload(model.StoredWorkflow.annotations))
        query = query.options(latest_workflow_load)
        query = query.filter(or_(*filters))
        query = query.filter(model.StoredWorkflow.table.c.hidden == (true() if show_hidden else false()))
        query = query.filter(model.StoredWorkflow.table.c.deleted == (true() if show_deleted else false()))
        if payload.search:
            search_query = payload.search
            parsed_search = parse_filters_structured(search_query, INDEX_SEARCH_FILTERS)

            def w_tag_filter(term_text: str, quoted: bool):
                nonlocal query
                alias = aliased(model.StoredWorkflowTagAssociation)
                query = query.outerjoin(model.StoredWorkflow.tags.of_type(alias))
                return tag_filter(alias, term_text, quoted)

            def name_filter(term):
                return text_column_filter(model.StoredWorkflow.name, term)

            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    q = term.text
                    if key == "tag":
                        tf = w_tag_filter(term.text, term.quoted)
                        query = query.filter(tf)
                    elif key == "name":
                        query = query.filter(name_filter(term))
                    elif key == "user":
                        query = append_user_filter(query, model.StoredWorkflow, term)
                    elif key == "is":
                        if q == "published":
                            query = query.filter(model.StoredWorkflow.published == true())
                        elif q == "shared_with_me":
                            if not show_shared:
                                message = "Can only use tag is:shared_with_me if show_shared parameter also true."
                                raise exceptions.RequestParameterInvalidException(message)
                            query = query.filter(model.StoredWorkflowUserShareAssociation.user == user)
                elif isinstance(term, RawTextTerm):
                    tf = w_tag_filter(term.text, False)
                    alias = aliased(model.User)
                    query = query.outerjoin(model.StoredWorkflow.user.of_type(alias))
                    query = query.filter(
                        raw_text_column_filter(
                            [
                                model.StoredWorkflow.name,
                                tf,
                                alias.username,
                            ],
                            term,
                        )
                    )
        if include_total_count:
            total_matches = query.count()
        else:
            total_matches = None
        if payload.sort_by is None:
            if user:
                query = query.order_by(desc(model.StoredWorkflow.user == user))
            query = query.order_by(desc(model.StoredWorkflow.table.c.update_time))
        else:
            sort_column = getattr(model.StoredWorkflow, payload.sort_by)
            if payload.sort_desc:
                sort_column = sort_column.desc()
            query = query.order_by(sort_column)
        if payload.limit is not None:
            query = query.limit(payload.limit)
        if payload.offset is not None:
            query = query.offset(payload.offset)
        return query, total_matches

    def get_stored_workflow(self, trans, workflow_id, by_stored_id=True):
        """Use a supplied ID (UUID or encoded stored workflow ID) to find
        a workflow.
        """
        if util.is_uuid(workflow_id):
            # see if they have passed in the UUID for a workflow that is attached to a stored workflow
            workflow_uuid = uuid.UUID(workflow_id)
            workflow_query = trans.sa_session.query(trans.app.model.StoredWorkflow).filter(
                and_(
                    trans.app.model.StoredWorkflow.id == trans.app.model.Workflow.stored_workflow_id,
                    trans.app.model.Workflow.uuid == workflow_uuid,
                )
            )
        elif by_stored_id:
            workflow_id = decode_id(self.app, workflow_id)
            workflow_query = trans.sa_session.query(trans.app.model.StoredWorkflow).filter(
                trans.app.model.StoredWorkflow.id == workflow_id
            )
        else:
            workflow_id = decode_id(self.app, workflow_id)
            workflow_query = trans.sa_session.query(trans.app.model.StoredWorkflow).filter(
                and_(
                    trans.app.model.StoredWorkflow.id == trans.app.model.Workflow.stored_workflow_id,
                    trans.app.model.Workflow.id == workflow_id,
                )
            )
        stored_workflow = workflow_query.options(
            joinedload("annotations"),
            joinedload("tags"),
            subqueryload("latest_workflow").joinedload("steps").joinedload("*"),
        ).first()
        if stored_workflow is None:
            if not by_stored_id:
                # May have a subworkflow without attached StoredWorkflow object, this was the default prior to 20.09 release.
                workflow = trans.sa_session.query(trans.app.model.Workflow).get(workflow_id)
                stored_workflow = self.attach_stored_workflow(trans=trans, workflow=workflow)
                if stored_workflow:
                    return stored_workflow
            raise exceptions.ObjectNotFound("No such workflow found.")
        return stored_workflow

    def get_stored_accessible_workflow(self, trans, workflow_id, by_stored_id=True):
        """Get a stored workflow from a encoded stored workflow id and
        make sure it accessible to the user.
        """
        stored_workflow = self.get_stored_workflow(trans, workflow_id, by_stored_id=by_stored_id)

        # check to see if user has permissions to selected workflow
        if stored_workflow.user != trans.user and not trans.user_is_admin and not stored_workflow.published:
            if (
                trans.sa_session.query(trans.app.model.StoredWorkflowUserShareAssociation)
                .filter_by(user=trans.user, stored_workflow=stored_workflow)
                .count()
                == 0
            ):
                message = "Workflow is not owned by or shared with current user"
                raise exceptions.ItemAccessibilityException(message)

        return stored_workflow

    def attach_stored_workflow(self, trans, workflow):
        """Attach and return stored workflow if possible."""
        # Imported Subworkflows are not created with a StoredWorkflow association
        # To properly serialize them we do need a StoredWorkflow, so we create and attach one here.
        # We hide the new StoredWorkflow to avoid cluttering the default workflow view.
        if workflow and workflow.stored_workflow is None and self.check_security(trans, has_workflow=workflow):
            stored_workflow = trans.app.model.StoredWorkflow(
                user=trans.user, name=workflow.name, workflow=workflow, hidden=True
            )
            trans.sa_session.add(stored_workflow)
            trans.sa_session.flush()
            return stored_workflow

    def get_owned_workflow(self, trans, encoded_workflow_id):
        """Get a workflow (non-stored) from a encoded workflow id and
        make sure it accessible to the user.
        """
        workflow_id = decode_id(self.app, encoded_workflow_id)
        workflow = trans.sa_session.query(model.Workflow).get(workflow_id)
        self.check_security(trans, workflow, check_ownership=True)
        return workflow

    def check_security(self, trans, has_workflow, check_ownership=True, check_accessible=True):
        """check accessibility or ownership of workflows, storedworkflows, and
        workflowinvocations. Throw an exception or returns True if user has
        needed level of access.
        """
        if not check_ownership and not check_accessible:
            return True

        # If given an invocation verify ownership of invocation
        if isinstance(has_workflow, model.WorkflowInvocation):
            # We use the the owner of the history that is associated to the invocation as a proxy
            # for the owner of the invocation.
            if trans.user != has_workflow.history.user and not trans.user_is_admin:
                raise exceptions.ItemOwnershipException()
            else:
                return True

        # stored workflow contains security stuff - follow that workflow to
        # that unless given a stored workflow.
        if isinstance(has_workflow, model.Workflow):
            stored_workflow = has_workflow.top_level_stored_workflow
        else:
            stored_workflow = has_workflow

        if stored_workflow.user != trans.user and not trans.user_is_admin:
            if check_ownership:
                raise exceptions.ItemOwnershipException()
            # else check_accessible...
            if (
                trans.sa_session.query(model.StoredWorkflowUserShareAssociation)
                .filter_by(user=trans.user, stored_workflow=stored_workflow)
                .count()
                == 0
            ):
                raise exceptions.ItemAccessibilityException()

        return True

    def get_invocation(self, trans, decoded_invocation_id, eager=False):
        q = trans.sa_session.query(self.app.model.WorkflowInvocation)
        if eager:
            q = q.options(
                subqueryload(self.app.model.WorkflowInvocation.steps)
                .joinedload("implicit_collection_jobs")
                .joinedload("jobs")
                .joinedload("job")
                .joinedload("input_datasets")
            )
        workflow_invocation = q.get(decoded_invocation_id)
        if not workflow_invocation:
            encoded_wfi_id = trans.security.encode_id(decoded_invocation_id)
            message = f"'{encoded_wfi_id}' is not a valid workflow invocation id"
            raise exceptions.ObjectNotFound(message)
        self.check_security(trans, workflow_invocation, check_ownership=True, check_accessible=False)
        return workflow_invocation

    def get_invocation_report(self, trans, invocation_id, **kwd):
        decoded_workflow_invocation_id = trans.security.decode_id(invocation_id)
        workflow_invocation = self.get_invocation(trans, decoded_workflow_invocation_id)
        generator_plugin_type = kwd.get("generator_plugin_type")
        runtime_report_config_json = kwd.get("runtime_report_config_json")
        invocation_markdown = kwd.get("invocation_markdown", None)
        target_format = kwd.get("format", "json")
        if invocation_markdown:
            runtime_report_config_json = {"markdown": invocation_markdown}
        return generate_report(
            trans,
            workflow_invocation,
            runtime_report_config_json=runtime_report_config_json,
            plugin_type=generator_plugin_type,
            target_format=target_format,
        )

    def cancel_invocation(self, trans, decoded_invocation_id):
        workflow_invocation = self.get_invocation(trans, decoded_invocation_id)
        cancelled = workflow_invocation.cancel()

        if cancelled:
            trans.sa_session.add(workflow_invocation)
            trans.sa_session.flush()
        else:
            # TODO: More specific exception?
            raise exceptions.MessageException("Cannot cancel an inactive workflow invocation.")

        return workflow_invocation

    def get_invocation_step(self, trans, decoded_workflow_invocation_step_id):
        try:
            workflow_invocation_step = trans.sa_session.query(model.WorkflowInvocationStep).get(
                decoded_workflow_invocation_step_id
            )
        except Exception:
            raise exceptions.ObjectNotFound()
        self.check_security(
            trans, workflow_invocation_step.workflow_invocation, check_ownership=True, check_accessible=False
        )
        return workflow_invocation_step

    def update_invocation_step(self, trans, decoded_workflow_invocation_step_id, action):
        if action is None:
            raise exceptions.RequestParameterMissingException(
                "Updating workflow invocation step requires an action parameter. "
            )

        workflow_invocation_step = self.get_invocation_step(trans, decoded_workflow_invocation_step_id)
        workflow_invocation = workflow_invocation_step.workflow_invocation
        if not workflow_invocation.active:
            raise exceptions.RequestParameterInvalidException(
                "Attempting to modify the state of a completed workflow invocation."
            )

        step = workflow_invocation_step.workflow_step
        module = module_factory.from_workflow_step(trans, step)
        performed_action = module.do_invocation_step_action(step, action)
        workflow_invocation_step.action = performed_action
        trans.sa_session.add(workflow_invocation_step)
        trans.sa_session.flush()
        return workflow_invocation_step

    def build_invocations_query(
        self,
        trans: ProvidesUserContext,
        stored_workflow_id=None,
        history_id=None,
        job_id=None,
        user_id=None,
        include_terminal=True,
        limit=None,
        offset=None,
        sort_by=None,
        sort_desc=None,
    ) -> Tuple[Query, int]:
        """Get invocations owned by the current user."""
        sa_session = trans.sa_session
        invocations_query = sa_session.query(model.WorkflowInvocation)
        if stored_workflow_id is not None:
            stored_workflow = sa_session.query(model.StoredWorkflow).get(stored_workflow_id)
            if not stored_workflow:
                raise exceptions.ObjectNotFound()
            invocations_query = invocations_query.join(model.Workflow).filter(
                model.Workflow.table.c.stored_workflow_id == stored_workflow_id
            )
        if user_id is not None:
            invocations_query = invocations_query.join(model.History).filter(model.History.table.c.user_id == user_id)
        if history_id is not None:
            invocations_query = invocations_query.filter(model.WorkflowInvocation.table.c.history_id == history_id)
        if job_id is not None:
            invocations_query = invocations_query.join(model.WorkflowInvocationStep).filter(
                model.WorkflowInvocationStep.table.c.job_id == job_id
            )
        if not include_terminal:
            invocations_query = invocations_query.filter(
                model.WorkflowInvocation.table.c.state.in_(model.WorkflowInvocation.non_terminal_states)
            )
        total_matches = invocations_query.count()
        if sort_by:
            sort_column = getattr(model.WorkflowInvocation, sort_by)
            if sort_desc:
                sort_column = sort_column.desc()
            invocations_query = invocations_query.order_by(sort_column)
        else:
            invocations_query = invocations_query.order_by(model.WorkflowInvocation.table.c.id.desc())
        if limit is not None:
            invocations_query = invocations_query.limit(limit)
        if offset is not None:
            invocations_query = invocations_query.offset(offset)
        invocations = [
            inv
            for inv in invocations_query
            if self.check_security(trans, inv, check_ownership=True, check_accessible=False)
        ]
        return invocations, total_matches


CreatedWorkflow = namedtuple("CreatedWorkflow", ["stored_workflow", "workflow", "missing_tools"])


class WorkflowSerializer(sharable.SharableModelSerializer):
    """
    Interface/service object for serializing stored workflows into dictionaries.

    These are used for simple workflow operations - much more detailed serialization operations
    that allow recovering the workflow in its entirity or rendering it in a workflow
    editor are available inside the WorkflowContentsManager.
    """

    model_manager_class = WorkflowsManager
    SINGLE_CHAR_ABBR = "w"

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)

    def add_serializers(self):
        super().add_serializers()
        self.serializers.update({})


class WorkflowContentsManager(UsesAnnotations):
    def __init__(self, app: MinimalManagerApp):
        self.app = app
        self._resource_mapper_function = get_resource_mapper_function(app)

    def ensure_raw_description(self, dict_or_raw_description):
        if not isinstance(dict_or_raw_description, RawWorkflowDescription):
            dict_or_raw_description = RawWorkflowDescription(dict_or_raw_description)
        return dict_or_raw_description

    def normalize_workflow_format(self, trans, as_dict):
        """Process incoming workflow descriptions for consumption by other methods.

        Currently this mostly means converting format 2 workflows into standard Galaxy
        workflow JSON for consumption for the rest of this module. In the future we will
        want to be a lot more precise about this - preserve the original description along
        side the data model and apply updates in a way that largely preserves YAML structure
        so workflows can be extracted.
        """
        workflow_directory = None
        workflow_path = None

        if as_dict.get("src", None) == "from_path":
            if not trans.user_is_admin:
                raise exceptions.AdminRequiredException()

            workflow_path = as_dict.get("path")
            workflow_directory = os.path.normpath(os.path.dirname(workflow_path))

        workflow_class, as_dict, object_id = artifact_class(trans, as_dict)
        if workflow_class == "GalaxyWorkflow" or "yaml_content" in as_dict:
            # Format 2 Galaxy workflow.
            galaxy_interface = Format2ConverterGalaxyInterface()
            import_options = ImportOptions()
            import_options.deduplicate_subworkflows = True
            as_dict = python_to_workflow(
                as_dict, galaxy_interface, workflow_directory=workflow_directory, import_options=import_options
            )

        return RawWorkflowDescription(as_dict, workflow_path)

    def build_workflow_from_raw_description(
        self,
        trans,
        raw_workflow_description,
        workflow_create_options,
        source=None,
        add_to_menu=False,
        hidden=False,
    ):
        data = raw_workflow_description.as_dict
        # Put parameters in workflow mode
        trans.workflow_building_mode = workflow_building_modes.ENABLED
        # If there's a source, put it in the workflow name.
        if "name" not in data:
            raise exceptions.RequestParameterInvalidException(f"Invalid workflow format detected [{data}]")

        workflow_input_name = data["name"]
        imported_sufix = f"(imported from {source})"
        if source and imported_sufix not in workflow_input_name:
            name = f"{workflow_input_name} {imported_sufix}"
        else:
            name = workflow_input_name
        workflow, missing_tool_tups = self._workflow_from_raw_description(
            trans,
            raw_workflow_description,
            workflow_create_options,
            name=name,
        )
        if "uuid" in data:
            workflow.uuid = data["uuid"]

        # Connect up
        stored = model.StoredWorkflow()
        stored.from_path = raw_workflow_description.workflow_path
        stored.name = workflow.name
        workflow.stored_workflow = stored
        stored.latest_workflow = workflow
        stored.user = trans.user
        stored.published = workflow_create_options.publish
        stored.hidden = hidden
        if data["annotation"]:
            annotation = sanitize_html(data["annotation"])
            self.add_item_annotation(trans.sa_session, stored.user, stored, annotation)
        workflow_tags = data.get("tags", [])
        trans.app.tag_handler.set_tags_from_list(user=trans.user, item=stored, new_tags_list=workflow_tags)

        # Persist
        trans.sa_session.add(stored)

        if add_to_menu:
            if trans.user.stored_workflow_menu_entries is None:
                trans.user.stored_workflow_menu_entries = []
            menuEntry = model.StoredWorkflowMenuEntry()
            menuEntry.stored_workflow = stored
            trans.user.stored_workflow_menu_entries.append(menuEntry)

        trans.sa_session.flush()

        return CreatedWorkflow(stored_workflow=stored, workflow=workflow, missing_tools=missing_tool_tups)

    def update_workflow_from_raw_description(
        self, trans, stored_workflow, raw_workflow_description, workflow_update_options
    ):
        raw_workflow_description = self.ensure_raw_description(raw_workflow_description)

        # Put parameters in workflow mode
        trans.workflow_building_mode = workflow_building_modes.ENABLED
        dry_run = workflow_update_options.dry_run
        workflow, missing_tool_tups = self._workflow_from_raw_description(
            trans,
            raw_workflow_description,
            workflow_update_options,
            name=stored_workflow.name,
            dry_run=dry_run,
        )

        if missing_tool_tups and not workflow_update_options.allow_missing_tools:
            errors = []
            for missing_tool_tup in missing_tool_tups:
                errors.append("Step %i: Requires tool '%s'." % (int(missing_tool_tup[3]) + 1, missing_tool_tup[0]))
            raise MissingToolsException(workflow, errors)

        # Connect up
        if not dry_run:
            workflow.stored_workflow = stored_workflow
            stored_workflow.latest_workflow = workflow
        else:
            stored_workflow = model.StoredWorkflow()  # detached
            stored_workflow.latest_workflow = workflow
            workflow.stored_workflow = stored_workflow

        if workflow_update_options.update_stored_workflow_attributes:
            update_dict = raw_workflow_description.as_dict
            if "name" in update_dict:
                sanitized_name = sanitize_html(update_dict["name"])
                workflow.name = sanitized_name
                stored_workflow.name = sanitized_name
            if "annotation" in update_dict:
                newAnnotation = sanitize_html(update_dict["annotation"])
                sa_session = None if dry_run else trans.sa_session
                self.add_item_annotation(sa_session, stored_workflow.user, stored_workflow, newAnnotation)

        # Persist
        if not dry_run:
            trans.sa_session.flush()
            if stored_workflow.from_path:
                self._sync_stored_workflow(trans, stored_workflow)
        # Return something informative
        errors = []
        if workflow.has_errors:
            errors.append("Some steps in this workflow have validation errors")
        if workflow.has_cycles:
            errors.append("This workflow contains cycles")
        return workflow, errors

    def _workflow_from_raw_description(
        self, trans, raw_workflow_description, workflow_state_resolution_options, name, **kwds
    ):
        # don't commit the workflow or attach its part to the sa session - just build a
        # a transient model to operate on or render.
        dry_run = kwds.pop("dry_run", False)

        data = raw_workflow_description.as_dict
        if isinstance(data, str):
            data = json.loads(data)

        # Create new workflow from source data
        workflow = model.Workflow()
        workflow.name = name

        if "report" in data:
            workflow.reports_config = data["report"]
        workflow.license = data.get("license")
        workflow.creator_metadata = data.get("creator")

        if hasattr(workflow_state_resolution_options, "archive_source"):
            if workflow_state_resolution_options.archive_source:
                source_metadata = {}
                if workflow_state_resolution_options.archive_source == "trs_tool":
                    source_metadata["trs_tool_id"] = workflow_state_resolution_options.trs_tool_id
                    source_metadata["trs_version_id"] = workflow_state_resolution_options.trs_version_id
                    source_metadata["trs_server"] = workflow_state_resolution_options.trs_server
                elif not workflow_state_resolution_options.archive_source.startswith("file://"):  # URL import
                    source_metadata["url"] = workflow_state_resolution_options.archive_source
                workflow_state_resolution_options.archive_source = None  # so trs_id is not set for subworkflows
                workflow.source_metadata = source_metadata

        # Assume no errors until we find a step that has some
        workflow.has_errors = False
        # Create each step
        steps: List[model.WorkflowStep] = []
        # The editor will provide ids for each step that we don't need to save,
        # but do need to use to make connections
        steps_by_external_id: Dict[str, model.WorkflowStep] = {}

        # Preload dependent workflows with locally defined content_ids.
        subworkflows = data.get("subworkflows")
        subworkflow_id_map = None
        if subworkflows:
            subworkflow_id_map = {}
            for key, subworkflow_dict in subworkflows.items():
                subworkflow = self.__build_embedded_subworkflow(
                    trans, subworkflow_dict, workflow_state_resolution_options
                )
                subworkflow_id_map[key] = subworkflow

        # Keep track of tools required by the workflow that are not available in
        # the local Galaxy instance.  Each tuple in the list of missing_tool_tups
        # will be ( tool_id, tool_name, tool_version ).
        missing_tool_tups = []
        for step_dict in self.__walk_step_dicts(data):
            if not dry_run:
                self.__load_subworkflows(
                    trans, step_dict, subworkflow_id_map, workflow_state_resolution_options, dry_run=dry_run
                )

        module_kwds = workflow_state_resolution_options.dict()
        module_kwds.update(kwds)  # TODO: maybe drop this?
        for step_dict in self.__walk_step_dicts(data):
            module, step = self.__module_from_dict(trans, steps, steps_by_external_id, step_dict, **module_kwds)
            is_tool = is_tool_module_type(module.type)
            if is_tool and module.tool is None:
                missing_tool_tup = (module.tool_id, module.get_name(), module.tool_version, step_dict["id"])
                if missing_tool_tup not in missing_tool_tups:
                    missing_tool_tups.append(missing_tool_tup)
            if module.get_errors():
                workflow.has_errors = True

        # Second pass to deal with connections between steps
        self.__connect_workflow_steps(steps, steps_by_external_id, dry_run)

        # Order the steps if possible
        attach_ordered_steps(workflow, steps)

        return workflow, missing_tool_tups

    def workflow_to_dict(self, trans, stored, style="export", version=None, history=None):
        """Export the workflow contents to a dictionary ready for JSON-ification and to be
        sent out via API for instance. There are three styles of export allowed 'export', 'instance', and
        'editor'. The Galaxy team will do its best to preserve the backward compatibility of the
        'export' style - this is the export method meant to be portable across Galaxy instances and over
        time. The 'editor' style is subject to rapid and unannounced changes. The 'instance' export
        option describes the workflow in a context more tied to the current Galaxy instance and includes
        fields like 'url' and 'url' and actual unencoded step ids instead of 'order_index'.
        """

        def to_format_2(wf_dict, **kwds):
            return from_galaxy_native(wf_dict, None, **kwds)

        if version == "":
            version = None
        if version is not None:
            version = int(version)
        workflow = stored.get_internal_version(version)
        if style == "export":
            style = self.app.config.default_workflow_export_format
        if style == "editor":
            wf_dict = self._workflow_to_dict_editor(trans, stored, workflow)
        elif style == "legacy":
            wf_dict = self._workflow_to_dict_instance(stored, workflow=workflow, legacy=True)
        elif style == "instance":
            wf_dict = self._workflow_to_dict_instance(stored, workflow=workflow, legacy=False)
        elif style == "run":
            wf_dict = self._workflow_to_dict_run(trans, stored, workflow=workflow, history=history or trans.history)
        elif style == "preview":
            wf_dict = self._workflow_to_dict_preview(trans, workflow=workflow)
        elif style == "format2":
            wf_dict = self._workflow_to_dict_export(trans, stored, workflow=workflow)
            wf_dict = to_format_2(wf_dict)
        elif style == "format2_wrapped_yaml":
            wf_dict = self._workflow_to_dict_export(trans, stored, workflow=workflow)
            wf_dict = to_format_2(wf_dict, json_wrapper=True)
        elif style == "ga":
            wf_dict = self._workflow_to_dict_export(trans, stored, workflow=workflow)
        else:
            raise exceptions.RequestParameterInvalidException(f"Unknown workflow style {style}")
        if version is not None:
            wf_dict["version"] = version
        else:
            wf_dict["version"] = len(stored.workflows) - 1
        return wf_dict

    def _sync_stored_workflow(self, trans, stored_workflow):
        workflow_path = stored_workflow.from_path
        workflow = stored_workflow.latest_workflow
        with open(workflow_path, "w") as f:
            if workflow_path.endswith(".ga"):
                wf_dict = self._workflow_to_dict_export(trans, stored_workflow, workflow=workflow)
                json.dump(wf_dict, f, indent=4)
            else:
                wf_dict = self._workflow_to_dict_export(trans, stored_workflow, workflow=workflow)
                wf_dict = from_galaxy_native(wf_dict, None, json_wrapper=True)
                f.write(wf_dict["yaml_content"])

    def _workflow_to_dict_run(self, trans, stored, workflow, history=None):
        """
        Builds workflow dictionary used by run workflow form
        """
        if len(workflow.steps) == 0:
            raise exceptions.MessageException("Workflow cannot be run because it does not have any steps.")
        if attach_ordered_steps(workflow, workflow.steps):
            raise exceptions.MessageException("Workflow cannot be run because it contains cycles.")
        trans.workflow_building_mode = workflow_building_modes.USE_HISTORY
        module_injector = WorkflowModuleInjector(trans)
        has_upgrade_messages = False
        step_version_changes = []
        missing_tools = []
        errors = {}
        for step in workflow.steps:
            try:
                module_injector.inject(step, steps=workflow.steps, exact_tools=False)
            except exceptions.ToolMissingException as e:
                # FIXME: if a subworkflow lacks multiple tools we report only the first missing tool
                if e.tool_id not in missing_tools:
                    missing_tools.append(e.tool_id)
                continue
            if step.upgrade_messages:
                has_upgrade_messages = True
            if step.type in ("tool", "subworkflow", None):
                if step.module.version_changes:
                    step_version_changes.extend(step.module.version_changes)
                step_errors = step.module.get_errors()
                if step_errors:
                    errors[step.id] = step_errors
        if missing_tools:
            workflow.annotation = self.get_item_annotation_str(trans.sa_session, trans.user, workflow)
            raise exceptions.MessageException(f"Following tools missing: {', '.join(missing_tools)}")
        workflow.annotation = self.get_item_annotation_str(trans.sa_session, trans.user, workflow)
        step_order_indices = {}
        for step in workflow.steps:
            step_order_indices[step.id] = step.order_index
        step_models = []
        for step in workflow.steps:
            step_model = None
            if step.type == "tool":
                incoming: Dict[str, Any] = {}
                tool = trans.app.toolbox.get_tool(
                    step.tool_id, tool_version=step.tool_version, tool_uuid=step.tool_uuid
                )
                params_to_incoming(incoming, tool.inputs, step.state.inputs, trans.app)
                step_model = tool.to_json(
                    trans, incoming, workflow_building_mode=workflow_building_modes.USE_HISTORY, history=history
                )
                step_model["post_job_actions"] = [
                    {
                        "short_str": ActionBox.get_short_str(pja),
                        "action_type": pja.action_type,
                        "output_name": pja.output_name,
                        "action_arguments": pja.action_arguments,
                    }
                    for pja in step.post_job_actions
                ]
            else:
                inputs = step.module.get_runtime_inputs(connections=step.output_connections)
                step_model = {"inputs": [input.to_dict(trans) for input in inputs.values()]}
            step_model["replacement_parameters"] = step.module.get_replacement_parameters(step)
            step_model["step_type"] = step.type
            step_model["step_label"] = step.label
            step_model["step_name"] = step.module.get_name()
            step_model["step_version"] = step.module.get_version()
            step_model["step_index"] = step.order_index
            step_model["output_connections"] = [
                {
                    "input_step_index": step_order_indices.get(oc.input_step_id),
                    "output_step_index": step_order_indices.get(oc.output_step_id),
                    "input_name": oc.input_name,
                    "output_name": oc.output_name,
                }
                for oc in step.output_connections
            ]
            if step.annotations:
                step_model["annotation"] = step.annotations[0].annotation
            if step.upgrade_messages:
                step_model["messages"] = step.upgrade_messages
            step_models.append(step_model)
        return {
            "id": trans.app.security.encode_id(stored.id),
            "history_id": trans.app.security.encode_id(history.id) if history else None,
            "name": stored.name,
            "steps": step_models,
            "step_version_changes": step_version_changes,
            "has_upgrade_messages": has_upgrade_messages,
            "workflow_resource_parameters": self._workflow_resource_parameters(trans, stored, workflow),
        }

    def _workflow_to_dict_preview(self, trans, workflow):
        """
        Builds workflow dictionary containing input labels and values.
        Used to create embedded workflow previews.
        """
        if len(workflow.steps) == 0:
            raise exceptions.MessageException("Workflow cannot be run because it does not have any steps.")
        if attach_ordered_steps(workflow, workflow.steps):
            raise exceptions.MessageException("Workflow cannot be run because it contains cycles.")

        # Ensure that the user has a history
        trans.get_history(most_recent=True, create=True)

        def row_for_param(input_dict, param, raw_value, other_values, prefix, step):
            input_dict["label"] = param.get_label()
            value = None
            if isinstance(param, DataToolParameter) or isinstance(param, DataCollectionToolParameter):
                if (prefix + param.name) in step.input_connections_by_name:
                    conns = step.input_connections_by_name[prefix + param.name]
                    if not isinstance(conns, list):
                        conns = [conns]
                    value_list = [
                        "Output '%s' from Step %d." % (conn.output_name, int(conn.output_step.order_index) + 1)
                        for conn in conns
                    ]
                    value = ",".join(value_list)
                else:
                    value = "Select at Runtime."
            else:
                value = param.value_to_display_text(raw_value) or "Unavailable."
            input_dict["value"] = value
            if hasattr(step, "upgrade_messages") and step.upgrade_messages and param.name in step.upgrade_messages:
                input_dict["upgrade_messages"] = step.upgrade_messages[param.name]

        def do_inputs(inputs, values, prefix, step, other_values=None):
            input_dicts = []
            for input in inputs.values():
                input_dict = {}
                input_dict["type"] = input.type
                if input.type == "repeat":
                    repeat_values = values[input.name]
                    if len(repeat_values) > 0:
                        input_dict["title"] = input.title_plural
                        nested_input_dicts = []
                        for i in range(len(repeat_values)):
                            nested_input_dict = {}
                            index = repeat_values[i]["__index__"]
                            nested_input_dict["title"] = "%i. %s" % (i + 1, input.title)
                            nested_input_dict["inputs"] = do_inputs(
                                input.inputs,
                                repeat_values[i],
                                f"{prefix + input.name}_{str(index)}|",
                                step,
                                other_values,
                            )
                            nested_input_dicts.append(nested_input_dict)
                        input_dict["inputs"] = nested_input_dicts
                elif input.type == "conditional":
                    group_values = values[input.name]
                    current_case = group_values["__current_case__"]
                    new_prefix = f"{prefix + input.name}|"
                    row_for_param(
                        input_dict, input.test_param, group_values[input.test_param.name], other_values, prefix, step
                    )
                    input_dict["inputs"] = do_inputs(
                        input.cases[current_case].inputs, group_values, new_prefix, step, other_values
                    )
                elif input.type == "section":
                    new_prefix = f"{prefix + input.name}|"
                    group_values = values[input.name]
                    input_dict["title"] = input.title
                    input_dict["inputs"] = do_inputs(input.inputs, group_values, new_prefix, step, other_values)
                else:
                    row_for_param(input_dict, input, values[input.name], other_values, prefix, step)
                input_dicts.append(input_dict)
            return input_dicts

        step_dicts = []
        for step in workflow.steps:
            module_injector = WorkflowModuleInjector(trans)
            step_dict = {}
            step_dict["order_index"] = step.order_index
            if hasattr(step, "annotation") and step.annotation is not None:
                step_dict["annotation"] = step.annotation
            try:
                module_injector.inject(step, steps=workflow.steps, exact_tools=False)
            except exceptions.ToolMissingException as e:
                step_dict["label"] = f"Unknown Tool with id '{e.tool_id}'"
                step_dicts.append(step_dict)
                continue
            if step.type == "tool" or step.type is None:
                tool = trans.app.toolbox.get_tool(step.tool_id)
                if tool:
                    step_dict["label"] = step.label or tool.name
                else:
                    step_dict["label"] = f"Unknown Tool with id '{step.tool_id}'"
                step_dict["inputs"] = do_inputs(tool.inputs, step.state.inputs, "", step)
            elif step.type == "subworkflow":
                step_dict["label"] = step.label or (step.subworkflow.name if step.subworkflow else "Missing workflow.")
                errors = step.module.get_errors()
                if errors:
                    step_dict["errors"] = errors
                subworkflow_dict = self._workflow_to_dict_preview(trans, step.subworkflow)
                step_dict["inputs"] = subworkflow_dict["steps"]
            else:
                module = step.module
                step_dict["label"] = module.name
                step_dict["inputs"] = do_inputs(module.get_runtime_inputs(), step.state.inputs, "", step)
            step_dicts.append(step_dict)
        return {
            "steps": step_dicts,
        }

    def _workflow_resource_parameters(self, trans, stored, workflow):
        """Get workflow scheduling resource parameters for this user and workflow or None if not configured."""
        return self._resource_mapper_function(trans=trans, stored_workflow=stored, workflow=workflow)

    def _workflow_to_dict_editor(self, trans, stored, workflow, tooltip=True, is_subworkflow=False):
        # Pack workflow data into a dictionary and return
        data = {}
        data["name"] = workflow.name
        data["steps"] = {}
        data["upgrade_messages"] = {}
        data["report"] = workflow.reports_config or {}
        data["license"] = workflow.license
        data["creator"] = workflow.creator_metadata
        data["source_metadata"] = workflow.source_metadata
        data["annotation"] = self.get_item_annotation_str(trans.sa_session, trans.user, stored) or ""

        output_label_index = set()
        input_step_types = set(workflow.input_step_types)
        # For each step, rebuild the form and encode the state
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step(trans, step, exact_tools=False)
            if not module:
                raise exceptions.MessageException(f"Unrecognized step type: {step.type}")
            # Load label from state of data input modules, necessary for backward compatibility
            self.__set_default_label(step, module, step.tool_inputs)
            # Fix any missing parameters
            upgrade_message_dict = module.check_and_update_state() or {}
            if hasattr(module, "version_changes") and module.version_changes:
                upgrade_message_dict[module.get_name()] = "\n".join(module.version_changes)
            # Get user annotation.
            config_form = module.get_config_form(step=step)
            annotation_str = self.get_item_annotation_str(trans.sa_session, trans.user, step) or ""
            # Pack attributes into plain dictionary
            step_dict = {
                "id": step.order_index,
                "type": module.type,
                "label": module.label,
                "content_id": module.get_content_id(),
                "name": module.get_name(),
                "tool_state": module.get_tool_state(),
                "errors": module.get_errors(),
                "inputs": module.get_all_inputs(connectable_only=True),
                "outputs": module.get_all_outputs(),
                "config_form": config_form,
                "annotation": annotation_str,
                "post_job_actions": {},
                "uuid": str(step.uuid) if step.uuid else None,
                "workflow_outputs": [],
            }
            if tooltip:
                step_dict["tooltip"] = module.get_tooltip(static_path=url_for("/static"))
            # Connections
            input_connections = step.input_connections
            input_connections_type = {}
            multiple_input = {}  # Boolean value indicating if this can be multiple
            if (step.type is None or step.type == "tool") and module.tool:
                # Determine full (prefixed) names of valid input datasets
                data_input_names = {}

                def callback(input, prefixed_name, **kwargs):
                    if isinstance(input, DataToolParameter) or isinstance(input, DataCollectionToolParameter):
                        data_input_names[prefixed_name] = True
                        multiple_input[prefixed_name] = input.multiple
                        if isinstance(input, DataToolParameter):
                            input_connections_type[input.name] = "dataset"
                        if isinstance(input, DataCollectionToolParameter):
                            input_connections_type[input.name] = "dataset_collection"

                visit_input_values(module.tool.inputs, module.state.inputs, callback)
                # post_job_actions
                pja_dict = {}
                for pja in step.post_job_actions:
                    pja_dict[pja.action_type + pja.output_name] = dict(
                        action_type=pja.action_type, output_name=pja.output_name, action_arguments=pja.action_arguments
                    )
                step_dict["post_job_actions"] = pja_dict

            # workflow outputs
            outputs = []
            output_label_duplicate = set()
            for output in step.unique_workflow_outputs:
                if output.workflow_step.type not in input_step_types:
                    output_label = output.label
                    output_name = output.output_name
                    output_uuid = str(output.uuid) if output.uuid else None
                    outputs.append({"output_name": output_name, "uuid": output_uuid, "label": output_label})
                    if output_label is not None:
                        if output_label in output_label_index:
                            if output_label not in output_label_duplicate:
                                output_label_duplicate.add(output_label)
                        else:
                            output_label_index.add(output_label)
            step_dict["workflow_outputs"] = outputs
            if len(output_label_duplicate) > 0:
                output_label_duplicate_string = ", ".join(output_label_duplicate)
                upgrade_message_dict[
                    "output_label_duplicate"
                ] = f"Ignoring duplicate labels: {output_label_duplicate_string}."
            if upgrade_message_dict:
                data["upgrade_messages"][step.order_index] = upgrade_message_dict

            # Encode input connections as dictionary
            input_conn_dict: model.InputConnDictType = {}
            for conn in input_connections:
                input_type = "dataset"
                if conn.input_name in input_connections_type:
                    input_type = input_connections_type[conn.input_name]
                conn_dict = dict(id=conn.output_step.order_index, output_name=conn.output_name, input_type=input_type)
                if conn.input_name in multiple_input:
                    if conn.input_name in input_conn_dict:
                        cast(list, input_conn_dict[conn.input_name]).append(conn_dict)
                    else:
                        input_conn_dict[conn.input_name] = [conn_dict]
                else:
                    input_conn_dict[conn.input_name] = conn_dict
            step_dict["input_connections"] = input_conn_dict

            # Position
            step_dict["position"] = step.position
            # Add to return value
            data["steps"][step.order_index] = step_dict
        if is_subworkflow:
            data["steps"] = self._resolve_collection_type(data["steps"])
        return data

    @staticmethod
    def get_step_map_over(current_step, steps):
        """
        Given a tool step and its input steps guess that maximum level of mapping over.
        All data outputs of a step need to be mapped over to this level.
        """
        max_map_over = ""
        for input_name, input_connections in current_step["input_connections"].items():
            if isinstance(input_connections, dict):
                # if input does not accept multiple inputs
                input_connections = [input_connections]
            for input_value in input_connections:
                current_data_input = None
                for current_input in current_step["inputs"]:
                    if current_input["name"] == input_name:
                        current_data_input = current_input
                        # we've got one of the tools' input data definitions
                        break
                if current_data_input is None:
                    log.info(f"failed to find input {input_name} for get_step_map_over")
                    continue
                input_step = steps[input_value["id"]]
                for input_step_data_output in input_step["outputs"]:
                    if input_step_data_output["name"] == input_value["output_name"]:
                        collection_type = input_step_data_output.get("collection_type")
                        # This is the defined incoming collection type, in reality there may be additional
                        # mapping over of the workflows' data input, but this should be taken care of by the workflow editor /
                        # outer workflow.
                        if collection_type:
                            if current_data_input.get("input_type") == "dataset" and current_data_input.get("multiple"):
                                # We reduce the innermost collection
                                if ":" in collection_type:
                                    # more than one layer of nesting and multiple="true" input,
                                    # we consume the innermost collection
                                    collection_type = ":".join(collection_type.rsplit(":")[:-1])
                                else:
                                    # We've reduced a list or a pair
                                    collection_type = None
                            elif current_data_input.get("input_type") == "dataset_collection":
                                current_collection_types = current_data_input["collection_types"]
                                if not current_collection_types:
                                    # Accepts any input dataset collection, no mapping
                                    collection_type = None
                                elif collection_type in current_collection_types:
                                    # incoming collection type is an exact match, no mapping over
                                    collection_type = None
                                else:
                                    outer_map_over = collection_type
                                    for accepted_collection_type in current_data_input["collection_types"]:
                                        # need to find the lowest level of mapping over,
                                        # for collection_type = 'list:list:list' and accepted_collection_type = ['list:list', 'list']
                                        # it'd be outer_map_over == 'list'
                                        if collection_type.endswith(accepted_collection_type):
                                            _outer_map_over = collection_type[: -(len(accepted_collection_type) + 1)]
                                            if len(_outer_map_over.split(":")) < len(outer_map_over.split(":")):
                                                outer_map_over = _outer_map_over
                                    collection_type = outer_map_over
                            # If there is mapping over, we're going to assume it is linked, everything else is (probably)
                            # too hard to display in the workflow editor. With this assumption we should be able to
                            # set the maximum mapping over level to the most deeply nested map_over
                            if collection_type and len(collection_type.split(":")) >= len(max_map_over.split(":")):
                                max_map_over = collection_type
        if max_map_over:
            return max_map_over
        return None

    def _resolve_collection_type(self, steps):
        """
        Fill in collection type for step outputs.
        This can either be via collection_type_source and / or "inherited" from the step's input.

        This information is only needed in the workflow editor.
        """
        for order_index in sorted(steps):
            step = steps[order_index]
            if step["type"] == "tool" and not step.get("errors"):
                map_over = self.get_step_map_over(step, steps)
                for step_data_output in step["outputs"]:
                    if step_data_output.get("collection_type_source") and step_data_output["collection_type"] is None:
                        collection_type_source = step_data_output["collection_type_source"]
                        for input_connection in step["input_connections"].get(collection_type_source, []):
                            input_step = steps[input_connection["id"]]
                            for input_step_data_output in input_step["outputs"]:
                                if input_step_data_output["name"] == input_connection["output_name"]:
                                    step_data_output["collection_type"] = input_step_data_output.get("collection_type")
                    if map_over:
                        collection_type = map_over
                        step_data_output["collection"] = True
                        if step_data_output.get("collection_type"):
                            collection_type = f"{map_over}:{step_data_output['collection_type']}"
                        step_data_output["collection_type"] = collection_type
        return steps

    def _workflow_to_dict_export(self, trans, stored=None, workflow=None, internal=False):
        """Export the workflow contents to a dictionary ready for JSON-ification and export.

        If internal, use content_ids instead subworkflow definitions.
        """
        annotation_str = ""
        tag_str = ""
        if stored is not None:
            if stored.id:
                annotation_str = self.get_item_annotation_str(trans.sa_session, trans.user, stored) or ""
                tag_str = stored.make_tag_string_list()
            else:
                # dry run with flushed workflow objects, just use the annotation
                annotations = stored.annotations
                if annotations and len(annotations) > 0:
                    annotation_str = util.unicodify(annotations[0].annotation)

        # Pack workflow data into a dictionary and return
        data: Dict[str, Any] = {}
        data["a_galaxy_workflow"] = "true"  # Placeholder for identifying galaxy workflow
        data["format-version"] = "0.1"
        data["name"] = workflow.name
        data["annotation"] = annotation_str
        data["tags"] = tag_str
        if workflow.uuid is not None:
            data["uuid"] = str(workflow.uuid)
        steps: Dict[int, Dict[str, Any]] = {}
        data["steps"] = steps
        if workflow.reports_config:
            data["report"] = workflow.reports_config
        if workflow.creator_metadata:
            data["creator"] = workflow.creator_metadata
        if workflow.license:
            data["license"] = workflow.license
        if workflow.source_metadata:
            data["source_metadata"] = workflow.source_metadata
        # For each step, rebuild the form and encode the state
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step(trans, step)
            if not module:
                raise exceptions.MessageException(f"Unrecognized step type: {step.type}")
            # Get user annotation.
            annotation_str = self.get_item_annotation_str(trans.sa_session, trans.user, step) or ""
            content_id = module.get_content_id()
            # Export differences for backward compatibility
            tool_state = module.get_export_state()
            # Step info
            step_dict = {
                "id": step.order_index,
                "type": module.type,
                "content_id": content_id,
                "tool_id": content_id,  # For workflows exported to older Galaxies,
                # eliminate after a few years...
                "tool_version": step.tool_version,
                "name": module.get_name(),
                "tool_state": json.dumps(tool_state),
                "errors": module.get_errors(),
                "uuid": str(step.uuid),
                "label": step.label or None,
                "annotation": annotation_str,
            }
            # Add tool shed repository information and post-job actions to step dict.
            if module.type == "tool":
                if module.tool and module.tool.tool_shed:
                    step_dict["tool_shed_repository"] = {
                        "name": module.tool.repository_name,
                        "owner": module.tool.repository_owner,
                        "changeset_revision": module.tool.changeset_revision,
                        "tool_shed": module.tool.tool_shed,
                    }

                tool_representation = None
                dynamic_tool = step.dynamic_tool
                if dynamic_tool:
                    tool_representation = dynamic_tool.value
                    step_dict["tool_representation"] = tool_representation
                    if util.is_uuid(step_dict["content_id"]):
                        step_dict["content_id"] = None
                        step_dict["tool_id"] = None

                pja_dict = {}
                for pja in step.post_job_actions:
                    pja_dict[pja.action_type + pja.output_name] = dict(
                        action_type=pja.action_type, output_name=pja.output_name, action_arguments=pja.action_arguments
                    )
                step_dict["post_job_actions"] = pja_dict

            if module.type == "subworkflow" and not internal:
                del step_dict["content_id"]
                del step_dict["errors"]
                del step_dict["tool_version"]
                del step_dict["tool_state"]
                subworkflow = step.subworkflow
                subworkflow_as_dict = self._workflow_to_dict_export(trans, stored=None, workflow=subworkflow)
                step_dict["subworkflow"] = subworkflow_as_dict

            # Data inputs, legacy section not used anywhere within core
            input_dicts = []
            step_state = module.state.inputs or {}
            if module.type != "tool":
                name = step_state.get("name") or module.label
                if name:
                    input_dicts.append({"name": name, "description": annotation_str})
            for name, val in step_state.items():
                input_type = type(val)
                if input_type == RuntimeValue:
                    input_dicts.append({"name": name, "description": f"runtime parameter for tool {module.get_name()}"})
                elif input_type == dict:
                    # Input type is described by a dict, e.g. indexed parameters.
                    for partval in val.values():
                        if type(partval) == RuntimeValue:
                            input_dicts.append(
                                {"name": name, "description": f"runtime parameter for tool {module.get_name()}"}
                            )
            step_dict["inputs"] = input_dicts

            # User outputs
            workflow_outputs_dicts = []
            for workflow_output in step.unique_workflow_outputs:
                workflow_output_dict = dict(
                    output_name=workflow_output.output_name,
                    label=workflow_output.label,
                    uuid=str(workflow_output.uuid) if workflow_output.uuid is not None else None,
                )
                workflow_outputs_dicts.append(workflow_output_dict)
            step_dict["workflow_outputs"] = workflow_outputs_dicts

            # All step outputs
            step_dict["outputs"] = []
            if type(module) is ToolModule:
                for output in module.get_data_outputs():
                    step_dict["outputs"].append({"name": output["name"], "type": output["extensions"][0]})

            step_in = {}
            for step_input in step.inputs:
                if step_input.default_value_set:
                    step_in[step_input.name] = {"default": step_input.default_value}

            if step_in:
                step_dict["in"] = step_in

            # Connections
            input_connections = step.input_connections
            if step.type is None or step.type == "tool":
                # Determine full (prefixed) names of valid input datasets
                data_input_names = {}

                def callback(input, prefixed_name, **kwargs):
                    if isinstance(input, DataToolParameter) or isinstance(input, DataCollectionToolParameter):
                        data_input_names[prefixed_name] = True

                # FIXME: this updates modules silently right now; messages from updates should be provided.
                module.check_and_update_state()
                if module.tool:
                    # If the tool is installed we attempt to verify input values
                    # and connections, otherwise the last known state will be dumped without modifications.
                    visit_input_values(module.tool.inputs, module.state.inputs, callback)

            # Encode input connections as dictionary
            input_conn_dict: Dict[str, List[Dict[str, Any]]] = {}
            unique_input_names = {conn.input_name for conn in input_connections}
            for input_name in unique_input_names:
                input_conn_dicts = []
                for conn in input_connections:
                    if conn.input_name != input_name:
                        continue
                    input_conn = dict(id=conn.output_step.order_index, output_name=conn.output_name)
                    if conn.input_subworkflow_step is not None:
                        subworkflow_step_id = conn.input_subworkflow_step.order_index
                        input_conn["input_subworkflow_step_id"] = subworkflow_step_id

                    input_conn_dicts.append(input_conn)
                input_conn_dict[input_name] = input_conn_dicts

            # Preserve backward compatibility. Previously Galaxy
            # assumed input connections would be dictionaries not
            # lists of dictionaries, so replace any singleton list
            # with just the dictionary so that workflows exported from
            # newer Galaxy instances can be used with older Galaxy
            # instances if they do no include multiple input
            # tools. This should be removed at some point. Mirrored
            # hack in _workflow_from_raw_description should never be removed so
            # existing workflow exports continue to function.
            back_compat_input_conn_dict: model.InputConnDictType = {}
            for input_name, input_conn_list in dict(input_conn_dict).items():
                if len(input_conn_list) == 1:
                    back_compat_input_conn_dict[input_name] = input_conn_list[0]
                else:
                    back_compat_input_conn_dict[input_name] = input_conn_list
            step_dict["input_connections"] = back_compat_input_conn_dict
            # Position
            step_dict["position"] = step.position
            # Add to return value
            steps[step.order_index] = step_dict
        return data

    def _workflow_to_dict_instance(self, stored, workflow, legacy=True):
        encode = self.app.security.encode_id
        sa_session = self.app.model.context
        item = stored.to_dict(view="element", value_mapper={"id": encode})
        item["name"] = workflow.name
        item["url"] = url_for("workflow", id=item["id"])
        item["owner"] = stored.user.username
        inputs = {}
        for step in workflow.input_steps:
            step_type = step.type
            step_label = step.label or step.tool_inputs.get("name")
            if step_label:
                label = step_label
            elif step_type == "data_input":
                label = "Input Dataset"
            elif step_type == "data_collection_input":
                label = "Input Dataset Collection"
            elif step_type == "parameter_input":
                label = "Input Parameter"
            else:
                raise ValueError(f"Invalid step_type {step_type}")
            if legacy:
                index = step.id
            else:
                index = step.order_index
            step_uuid = str(step.uuid) if step.uuid else None
            inputs[index] = {"label": label, "value": "", "uuid": step_uuid}
        item["inputs"] = inputs
        item["annotation"] = self.get_item_annotation_str(sa_session, stored.user, stored)
        item["license"] = workflow.license
        item["creator"] = workflow.creator_metadata
        item["source_metadata"] = workflow.source_metadata
        steps = {}
        steps_to_order_index = {}
        for step in workflow.steps:
            steps_to_order_index[step.id] = step.order_index
        for step in workflow.steps:
            step_id = step.id if legacy else step.order_index
            step_type = step.type
            step_dict = {
                "id": step_id,
                "type": step_type,
                "tool_id": step.tool_id,
                "tool_version": step.tool_version,
                "annotation": self.get_item_annotation_str(sa_session, stored.user, step),
                "tool_inputs": step.tool_inputs,
                "input_steps": {},
            }

            if step_type == "subworkflow":
                del step_dict["tool_id"]
                del step_dict["tool_version"]
                del step_dict["tool_inputs"]
                step_dict["workflow_id"] = encode(step.subworkflow.id)

            for conn in step.input_connections:
                step_id = step.id if legacy else step.order_index
                source_id = conn.output_step_id
                source_step = source_id if legacy else steps_to_order_index[source_id]
                step_dict["input_steps"][conn.input_name] = {
                    "source_step": source_step,
                    "step_output": conn.output_name,
                }

            steps[step_id] = step_dict

        item["steps"] = steps
        return item

    def __walk_step_dicts(self, data):
        """Walk over the supplied step dictionaries and return them in a way
        designed to preserve step order when possible.
        """
        supplied_steps = data["steps"]
        # Try to iterate through imported workflow in such a way as to
        # preserve step order.
        step_indices = list(supplied_steps.keys())
        try:
            step_indices = sorted(step_indices, key=int)
        except ValueError:
            # to defensive, were these ever or will they ever not be integers?
            pass

        discovered_labels = set()
        discovered_uuids = set()

        discovered_output_labels = set()
        discovered_output_uuids = set()

        # First pass to build step objects and populate basic values
        for step_index in step_indices:
            step_dict = supplied_steps[step_index]
            uuid = step_dict.get("uuid", None)
            if uuid and uuid != "None":
                if uuid in discovered_uuids:
                    raise exceptions.DuplicatedIdentifierException(f"Duplicate step UUID '{uuid}' in request.")
                discovered_uuids.add(uuid)
            label = step_dict.get("label", None)
            if label:
                if label in discovered_labels:
                    raise exceptions.DuplicatedIdentifierException(f"Duplicated step label '{label}' in request.")
                discovered_labels.add(label)

            if "workflow_outputs" in step_dict:
                outputs = step_dict["workflow_outputs"]
                # outputs may be list of name (deprecated legacy behavior)
                # or dictionary of names to {uuid: <uuid>, label: <label>}
                if isinstance(outputs, dict):
                    for output_name in outputs:
                        output_dict = outputs[output_name]
                        output_label = output_dict.get("label", None)
                        if output_label:
                            if label in discovered_output_labels:
                                raise exceptions.DuplicatedIdentifierException(
                                    f"Duplicated workflow output label '{label}' in request."
                                )
                            discovered_output_labels.add(label)

                        output_uuid = step_dict.get("output_uuid", None)
                        if output_uuid:
                            if output_uuid in discovered_output_uuids:
                                raise exceptions.DuplicatedIdentifierException(
                                    f"Duplicate workflow output UUID '{output_uuid}' in request."
                                )
                            discovered_output_uuids.add(uuid)

            yield step_dict

    def __load_subworkflows(
        self, trans, step_dict, subworkflow_id_map, workflow_state_resolution_options, dry_run=False
    ):
        step_type = step_dict.get("type", None)
        if step_type == "subworkflow":
            subworkflow = self.__load_subworkflow_from_step_dict(
                trans, step_dict, subworkflow_id_map, workflow_state_resolution_options, dry_run=dry_run
            )
            step_dict["subworkflow"] = subworkflow

    def __module_from_dict(
        self,
        trans,
        steps: List[model.WorkflowStep],
        steps_by_external_id: Dict[str, model.WorkflowStep],
        step_dict,
        **kwds,
    ):
        """Create a WorkflowStep model object and corresponding module
        representing type-specific functionality from the incoming dictionary.
        """
        dry_run = kwds.get("dry_run", False)
        step = model.WorkflowStep()
        step.position = step_dict.get("position", model.WorkflowStep.DEFAULT_POSITION)
        if step_dict.get("uuid", None) and step_dict["uuid"] != "None":
            step.uuid = step_dict["uuid"]
        if "label" in step_dict:
            step.label = step_dict["label"]

        module = module_factory.from_dict(trans, step_dict, detached=dry_run, **kwds)
        self.__set_default_label(step, module, step_dict.get("tool_state"))
        module.save_to_step(step, detached=dry_run)

        annotation = step_dict.get("annotation")
        if annotation:
            annotation = sanitize_html(annotation)
            sa_session = None if dry_run else trans.sa_session
            self.add_item_annotation(sa_session, trans.get_user(), step, annotation)

        # Stick this in the step temporarily
        step.temp_input_connections = step_dict.get("input_connections", {})

        # Create the model class for the step
        steps.append(step)
        external_id = step_dict["id"]
        steps_by_external_id[external_id] = step
        if "workflow_outputs" in step_dict:
            workflow_outputs = step_dict["workflow_outputs"]
            found_output_names = set()
            for workflow_output in workflow_outputs:
                # Allow workflow outputs as list of output_names for backward compatibility.
                if not isinstance(workflow_output, dict):
                    workflow_output = {"output_name": workflow_output}
                output_name = workflow_output["output_name"]
                if output_name in found_output_names:
                    raise exceptions.ObjectAttributeInvalidException(
                        f"Duplicate workflow outputs with name [{output_name}] found."
                    )
                if not output_name:
                    raise exceptions.ObjectAttributeInvalidException("Workflow output with empty name encountered.")
                found_output_names.add(output_name)
                uuid = workflow_output.get("uuid", None)
                label = workflow_output.get("label", None)
                m = step.create_or_update_workflow_output(
                    output_name=output_name,
                    uuid=uuid,
                    label=label,
                )
                if not dry_run:
                    trans.sa_session.add(m)

        if "in" in step_dict:
            for input_name, input_dict in step_dict["in"].items():
                step_input = step.get_or_add_input(input_name)
                NO_DEFAULT_DEFINED = object()
                default = input_dict.get("default", NO_DEFAULT_DEFINED)
                if default is not NO_DEFAULT_DEFINED:
                    step_input.default_value = default
                    step_input.default_value_set = True

        if dry_run and step in trans.sa_session:
            trans.sa_session.expunge(step)
        return module, step

    def __load_subworkflow_from_step_dict(
        self, trans, step_dict, subworkflow_id_map, workflow_state_resolution_options, dry_run=False
    ):
        embedded_subworkflow = step_dict.get("subworkflow", None)
        subworkflow_id = step_dict.get("content_id", None)
        if embedded_subworkflow and subworkflow_id:
            raise Exception("Subworkflow step defines both subworkflow and content_id, only one may be specified.")

        if not embedded_subworkflow and not subworkflow_id:
            raise Exception("Subworkflow step must define either subworkflow or content_id.")

        if embedded_subworkflow:
            assert not dry_run
            subworkflow = self.__build_embedded_subworkflow(
                trans, embedded_subworkflow, workflow_state_resolution_options
            )
        elif subworkflow_id_map is not None:
            assert not dry_run
            # Interpret content_id as a workflow local thing.
            subworkflow = subworkflow_id_map[subworkflow_id[1:]]
        else:
            subworkflow = self.app.workflow_manager.get_owned_workflow(trans, subworkflow_id)

        return subworkflow

    def __build_embedded_subworkflow(self, trans, data, workflow_state_resolution_options):
        raw_workflow_description = self.ensure_raw_description(data)
        subworkflow = self.build_workflow_from_raw_description(
            trans, raw_workflow_description, workflow_state_resolution_options, hidden=True
        ).workflow
        return subworkflow

    def __connect_workflow_steps(self, steps: List[model.WorkflowStep], steps_by_external_id, dry_run: bool) -> None:
        """Second pass to deal with connections between steps.

        Create workflow connection objects using externally specified ids
        using during creation or update.
        """
        for step in steps:
            # Input connections
            if step.temp_input_connections:  # populated by __module_from_dict
                for input_name, conn_list in step.temp_input_connections.items():
                    if not conn_list:
                        continue
                    if not isinstance(conn_list, list):  # Older style singleton connection
                        conn_list = [conn_list]

                    for conn_dict in conn_list:
                        if "output_name" not in conn_dict or "id" not in conn_dict:
                            template = "Invalid connection [%s] - must be dict with output_name and id fields."
                            message = template % conn_dict
                            raise exceptions.MessageException(message)
                        external_id = conn_dict["id"]
                        if external_id not in steps_by_external_id:
                            raise KeyError(f"Failed to find external id {external_id} in {steps_by_external_id.keys()}")
                        output_step = steps_by_external_id[external_id]

                        output_name = conn_dict["output_name"]
                        input_subworkflow_step_index = conn_dict.get("input_subworkflow_step_id", None)

                        if dry_run:
                            input_subworkflow_step_index = None
                        step.add_connection(input_name, output_name, output_step, input_subworkflow_step_index)

            step.temp_input_connections = None

    def __set_default_label(self, step, module, state):
        """Previously data input modules had a `name` attribute to rename individual steps. Here, this value is transferred
        to the actual `label` attribute which is available for all module types, unique, and mapped to its own database column.
        """
        if not module.label and module.type in ["data_input", "data_collection_input"]:
            new_state = safe_loads(state)
            default_label = new_state.get("name")
            if default_label and util.unicodify(default_label).lower() not in [
                "input dataset",
                "input dataset collection",
            ]:
                step.label = module.label = default_label

    def do_refactor(self, trans, stored_workflow, refactor_request):
        """Apply supplied actions to stored_workflow.latest_workflow to build a new version."""
        workflow = stored_workflow.latest_workflow
        as_dict = self._workflow_to_dict_export(trans, stored_workflow, workflow=workflow, internal=True)
        raw_workflow_description = self.normalize_workflow_format(trans, as_dict)
        workflow_update_options = WorkflowUpdateOptions(
            fill_defaults=False,
            allow_missing_tools=True,
            dry_run=refactor_request.dry_run,
        )

        module_injector = WorkflowModuleInjector(trans)
        refactor_executor = WorkflowRefactorExecutor(raw_workflow_description, workflow, module_injector)
        action_executions = refactor_executor.refactor(refactor_request)
        refactored_workflow, errors = self.update_workflow_from_raw_description(
            trans,
            stored_workflow,
            raw_workflow_description,
            workflow_update_options,
        )
        # errors could be three things:
        # - we allow missing tools so it won't be that.
        # - might have cycles or might have state validation issues, but it still saved...
        #   so this is really more of a warning - we disregard it the other two places
        #   it is used also. These same messages will appear in the dictified version we
        #   we send back anyway
        return refactored_workflow, action_executions

    def refactor(self, trans, stored_workflow, refactor_request):
        refactored_workflow, action_executions = self.do_refactor(trans, stored_workflow, refactor_request)
        return RefactorResponse(
            action_executions=action_executions,
            workflow=self.workflow_to_dict(trans, refactored_workflow.stored_workflow, style=refactor_request.style),
            dry_run=refactor_request.dry_run,
        )

    def get_all_tools(self, workflow):
        tools = []
        for step in workflow.steps:
            if step.type == "tool":
                if step.tool_id:
                    if {"tool_id": step.tool_id, "tool_version": step.tool_version} not in tools:
                        tools.append({"tool_id": step.tool_id, "tool_version": step.tool_version})
            elif step.type == "subworkflow":
                tools.extend(self.get_all_tools(step.subworkflow))
        return tools


class RefactorRequest(RefactorActions):
    style: str = "export"


class RefactorResponse(BaseModel):
    action_executions: List[RefactorActionExecution]
    workflow: dict
    dry_run: bool

    class Config:
        # Workflows have dictionaries with integer keys, which pydantic doesn't coerce to strings.
        # Integer object keys aren't valid JSON, so the client fails.
        json_dumps = safe_dumps


class WorkflowStateResolutionOptions(BaseModel):
    # fill in default tool state when updating, may change tool_state
    fill_defaults: bool = False
    # If True, assume all tool state coming from generated form instead of potentially simpler json stored in DB/exported
    from_tool_form: bool = False
    # If False, allow running with less exact tool versions
    exact_tools: bool = True


class WorkflowUpdateOptions(WorkflowStateResolutionOptions):
    # Only used internally, don't set. If using the API assume updating the workflows
    # representation with name or annotation for instance, updates the corresponding
    # stored workflow
    update_stored_workflow_attributes: bool = True
    allow_missing_tools: bool = False
    dry_run: bool = False


# Workflow update options but with some different defaults - we allow creating
# workflows with missing tools by default but not updating.
class WorkflowCreateOptions(WorkflowStateResolutionOptions):
    import_tools: bool = False

    publish: bool = False
    # true or false, effectively defaults to ``publish`` if None/unset
    importable: Optional[bool] = None

    # following are install options, only used if import_tools is true
    install_repository_dependencies: bool = False
    install_resolver_dependencies: bool = False
    install_tool_dependencies: bool = False
    new_tool_panel_section_label: str = ""
    tool_panel_section_id: str = ""
    tool_panel_section_mapping: Dict = {}
    shed_tool_conf: Optional[str] = None

    # for workflows imported by archive source
    archive_source: Optional[str] = ""
    trs_tool_id: str = ""
    trs_version_id: str = ""
    trs_server: str = ""

    @property
    def is_importable(self):
        # if self.importable is None, use self.publish that has a default.
        if self.importable is None:
            return self.publish
        else:
            return self.importable

    @property
    def install_options(self):
        return {
            "install_repository_dependencies": self.install_repository_dependencies,
            "install_resolver_dependencies": self.install_resolver_dependencies,
            "install_tool_dependencies": self.install_tool_dependencies,
            "new_tool_panel_section_label": self.new_tool_panel_section_label,
            "tool_panel_section_id": self.tool_panel_section_id,
            "tool_panel_section_mapping": self.tool_panel_section_mapping,
            "shed_tool_conf": self.shed_tool_conf,
        }


class MissingToolsException(exceptions.MessageException):
    def __init__(self, workflow, errors):
        self.workflow = workflow
        self.errors = errors


class RawWorkflowDescription:
    def __init__(self, as_dict, workflow_path=None):
        self.as_dict = as_dict
        self.workflow_path = workflow_path


class Format2ConverterGalaxyInterface(ImporterGalaxyInterface):
    def import_workflow(self, workflow, **kwds):
        raise NotImplementedError(
            "Direct format 2 import of nested workflows is not yet implemented, use bioblend client."
        )
