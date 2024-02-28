import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from gxformat2._yaml import ordered_dump

from galaxy import (
    exceptions,
    model,
    util,
    web,
)
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.histories import HistoryManager
from galaxy.managers.workflows import (
    RefactorResponse,
    WorkflowContentsManager,
    WorkflowSerializer,
    WorkflowsManager,
)
from galaxy.model import StoredWorkflow
from galaxy.model.base import transaction
from galaxy.schema.invocation import WorkflowInvocationResponse
from galaxy.schema.schema import (
    InvocationsStateCounts,
    WorkflowIndexQueryPayload,
)
from galaxy.schema.workflows import (
    InvokeWorkflowPayload,
    SetWorkflowMenuPayload,
    SetWorkflowMenuSummary,
    StoredWorkflowDetailed,
)
from galaxy.util.tool_shed.tool_shed_registry import Registry
from galaxy.web import format_return_as_json
from galaxy.webapps.galaxy.services.base import ServiceBase
from galaxy.webapps.galaxy.services.notifications import NotificationService
from galaxy.webapps.galaxy.services.sharable import ShareableService
from galaxy.workflow.run import queue_invoke
from galaxy.workflow.run_request import build_workflow_run_configs

log = logging.getLogger(__name__)


class WorkflowIndexPayload(WorkflowIndexQueryPayload):
    missing_tools: bool = False


class WorkflowsService(ServiceBase):
    def __init__(
        self,
        workflows_manager: WorkflowsManager,
        workflow_contents_manager: WorkflowContentsManager,
        serializer: WorkflowSerializer,
        tool_shed_registry: Registry,
        notification_service: NotificationService,
        history_manager: HistoryManager,
    ):
        self._workflows_manager = workflows_manager
        self._workflow_contents_manager = workflow_contents_manager
        self._serializer = serializer
        self.shareable_service = ShareableService(workflows_manager, serializer, notification_service)
        self._tool_shed_registry = tool_shed_registry
        self._history_manager = history_manager

    def download_workflow(self, trans, workflow_id, history_id, style, format, version, instance):
        stored_workflow = self._workflows_manager.get_stored_workflow(trans, workflow_id, by_stored_id=not instance)
        history = None
        if history_id:
            history = self._history_manager.get_accessible(history_id, trans.user, current_history=trans.history)
        ret_dict = self._workflow_contents_manager.workflow_to_dict(
            trans, stored_workflow, style=style, version=version, history=history
        )
        if format == "json-download":
            sname = stored_workflow.name
            sname = "".join(c in util.FILENAME_VALID_CHARS and c or "_" for c in sname)[0:150]
            if ret_dict.get("format-version", None) == "0.1":
                extension = "ga"
            else:
                extension = "gxwf.json"
            trans.response.headers["Content-Disposition"] = (
                f'attachment; filename="Galaxy-Workflow-{sname}.{extension}"'
            )
            trans.response.set_content_type("application/galaxy-archive")

        if style == "format2" and format != "json-download":
            return ordered_dump(ret_dict)
        else:
            return ret_dict

    def index(
        self,
        trans: ProvidesUserContext,
        payload: WorkflowIndexPayload,
        include_total_count: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Optional[int]]:
        user = trans.user
        missing_tools = payload.missing_tools
        query, total_matches = self._workflows_manager.index_query(trans, payload, include_total_count)
        rval = []
        for wf in query.all():
            item = wf.to_dict(value_mapper={"id": trans.security.encode_id})
            encoded_id = trans.security.encode_id(wf.id)
            item["annotations"] = [x.annotation for x in wf.annotations]
            item["url"] = web.url_for("workflow", id=encoded_id)
            item["owner"] = wf.user.username
            item["source_metadata"] = wf.latest_workflow.source_metadata
            if not payload.skip_step_counts:
                item["number_of_steps"] = wf.latest_workflow.step_count
            item["show_in_tool_panel"] = False
            if user is not None:
                item["show_in_tool_panel"] = wf.show_in_tool_panel(user_id=user.id)
            rval.append(item)
        if missing_tools:
            workflows_missing_tools = []
            workflows = []
            workflows_by_toolshed = {}
            for value in rval:
                stored_workflow = self._workflows_manager.get_stored_workflow(trans, value["id"], by_stored_id=True)
                tools = self._workflow_contents_manager.get_all_tools(stored_workflow.latest_workflow)
                missing_tool_ids = [
                    tool["tool_id"] for tool in tools if trans.app.toolbox.is_missing_shed_tool(tool["tool_id"])
                ]
                if len(missing_tool_ids) > 0:
                    value["missing_tools"] = missing_tool_ids
                    workflows_missing_tools.append(value)
            for workflow in workflows_missing_tools:
                for tool_id in workflow["missing_tools"]:
                    toolshed, _, owner, name, tool, version = tool_id.split("/")
                    shed_url = self.__get_full_shed_url(toolshed)
                    repo_identifier = "/".join((toolshed, owner, name))
                    if repo_identifier not in workflows_by_toolshed:
                        workflows_by_toolshed[repo_identifier] = dict(
                            shed=shed_url.rstrip("/"),
                            repository=name,
                            owner=owner,
                            tools=[tool_id],
                            workflows=[workflow["name"]],
                        )
                    else:
                        if tool_id not in workflows_by_toolshed[repo_identifier]["tools"]:
                            workflows_by_toolshed[repo_identifier]["tools"].append(tool_id)
                        if workflow["name"] not in workflows_by_toolshed[repo_identifier]["workflows"]:
                            workflows_by_toolshed[repo_identifier]["workflows"].append(workflow["name"])
            for repo_tag in workflows_by_toolshed:
                workflows.append(workflows_by_toolshed[repo_tag])
            return workflows, total_matches
        return rval, total_matches

    def invoke_workflow(
        self,
        trans,
        workflow_id,
        payload: InvokeWorkflowPayload,
    ) -> Union[WorkflowInvocationResponse, List[WorkflowInvocationResponse]]:
        if trans.anonymous:
            raise exceptions.AuthenticationRequired("You need to be logged in to run workflows.")
        trans.check_user_activation()
        # Get workflow + accessibility check.
        by_stored_id = not payload.instance
        stored_workflow = self._workflows_manager.get_stored_accessible_workflow(trans, workflow_id, by_stored_id)
        version = payload.version
        workflow = stored_workflow.get_internal_version(version)
        run_configs = build_workflow_run_configs(trans, workflow, payload.model_dump(exclude_unset=True))
        is_batch = payload.batch
        if not is_batch and len(run_configs) != 1:
            raise exceptions.RequestParameterInvalidException("Must specify 'batch' to use batch parameters.")

        require_exact_tool_versions = payload.require_exact_tool_versions
        tools = self._workflow_contents_manager.get_all_tools(workflow)
        missing_tools = [
            tool
            for tool in tools
            if not trans.app.toolbox.has_tool(
                tool["tool_id"], tool_version=tool["tool_version"], exact=require_exact_tool_versions
            )
        ]
        if missing_tools:
            missing_tools_message = "Workflow was not invoked; the following required tools are not installed: "
            if require_exact_tool_versions:
                missing_tools_message += ", ".join(
                    [f"{tool['tool_id']} (version {tool['tool_version']})" for tool in missing_tools]
                )
            else:
                missing_tools_message += ", ".join([tool["tool_id"] for tool in missing_tools])
            raise exceptions.MessageException(missing_tools_message)

        invocations = []
        for run_config in run_configs:
            workflow_scheduler_id = payload.scheduler
            # TODO: workflow scheduler hints
            work_request_params = dict(scheduler=workflow_scheduler_id)
            workflow_invocation = queue_invoke(
                trans=trans,
                workflow=workflow,
                workflow_run_config=run_config,
                request_params=work_request_params,
                flush=False,
            )
            invocations.append(workflow_invocation)

        with transaction(trans.sa_session):
            trans.sa_session.commit()
        encoded_invocations = [WorkflowInvocationResponse(**invocation.to_dict()) for invocation in invocations]
        if is_batch:
            return encoded_invocations
        else:
            return encoded_invocations[0]

    def delete(self, trans, workflow_id):
        workflow_to_delete = self._workflows_manager.get_stored_workflow(trans, workflow_id)
        self._workflows_manager.check_security(trans, workflow_to_delete)
        self._workflows_manager.delete(workflow_to_delete)

    def undelete(self, trans, workflow_id):
        workflow_to_undelete = self._workflows_manager.get_stored_workflow(trans, workflow_id)
        self._workflows_manager.check_security(trans, workflow_to_undelete)
        self._workflows_manager.undelete(workflow_to_undelete)

    def get_versions(self, trans, workflow_id, instance: bool):
        stored_workflow: StoredWorkflow = self._workflows_manager.get_stored_accessible_workflow(
            trans, workflow_id, by_stored_id=not instance
        )
        return [
            {"version": i, "update_time": w.update_time.isoformat(), "steps": len(w.steps)}
            for i, w in enumerate(reversed(stored_workflow.workflows))
        ]

    def invocation_counts(self, trans, workflow_id, instance: bool) -> InvocationsStateCounts:
        stored_workflow: StoredWorkflow = self._workflows_manager.get_stored_accessible_workflow(
            trans, workflow_id, by_stored_id=not instance
        )
        return stored_workflow.invocation_counts()

    def get_workflow_menu(self, trans, payload):
        ids_in_menu = [x.stored_workflow_id for x in trans.user.stored_workflow_menu_entries]
        workflows = self._get_workflows_list(
            trans,
            payload,
        )
        return {"ids_in_menu": ids_in_menu, "workflows": workflows}

    def refactor(
        self,
        trans,
        workflow_id,
        payload,
        instance: bool,
    ) -> RefactorResponse:
        stored_workflow = self._workflows_manager.get_stored_workflow(trans, workflow_id, by_stored_id=not instance)
        return self._workflow_contents_manager.refactor(trans, stored_workflow, payload)

    def set_workflow_menu(
        self,
        payload: Optional[SetWorkflowMenuPayload],
        trans: ProvidesHistoryContext,
    ) -> SetWorkflowMenuSummary:
        user = trans.user
        if payload:
            workflow_ids = payload.workflow_ids
            if not isinstance(workflow_ids, list):
                workflow_ids = [workflow_ids]
        else:
            workflow_ids = []
        session = trans.sa_session
        # This explicit remove seems like a hack, need to figure out
        # how to make the association do it automatically.
        for m in user.stored_workflow_menu_entries:
            session.delete(m)
        user.stored_workflow_menu_entries = []
        # To ensure id list is unique
        seen_workflow_ids = set()
        for wf_id in workflow_ids:
            if wf_id in seen_workflow_ids:
                continue
            else:
                seen_workflow_ids.add(wf_id)
            m = model.StoredWorkflowMenuEntry()
            m.stored_workflow = session.get(model.StoredWorkflow, wf_id)

            user.stored_workflow_menu_entries.append(m)
        with transaction(session):
            session.commit()
        message = "Menu updated."
        # TODO - It seems like this populates a mako template, is it necessary?
        # trans.set_message(message)
        return SetWorkflowMenuSummary(message=message, status="done")

    def show_workflow(self, trans, workflow_id, instance, legacy, version) -> StoredWorkflowDetailed:
        stored_workflow = self._workflows_manager.get_stored_workflow(trans, workflow_id, by_stored_id=not instance)
        if stored_workflow.importable is False and stored_workflow.user != trans.user and not trans.user_is_admin:
            wf_count = 0 if not trans.user else trans.user.count_stored_workflow_user_assocs(stored_workflow)
            if wf_count == 0:
                message = "Workflow is neither importable, nor owned by or shared with current user"
                raise exceptions.ItemAccessibilityException(message)
        if legacy:
            style = "legacy"
        else:
            style = "instance"
        if version is None and instance:
            # A Workflow instance may not be the latest workflow version attached to StoredWorkflow.
            # This figures out the correct version so that we return the correct Workflow and version.
            for i, workflow in enumerate(reversed(stored_workflow.workflows)):
                if workflow.id == workflow_id:
                    version = i
                    break
        detailed_workflow = StoredWorkflowDetailed(
            **self._workflow_contents_manager.workflow_to_dict(trans, stored_workflow, style=style, version=version)
        )
        return detailed_workflow

    def _get_workflows_list(
        self,
        trans: ProvidesUserContext,
        payload,
    ):
        workflows, _ = self.index(trans, payload)
        return workflows

    def __get_full_shed_url(self, url):
        for shed_url in self._tool_shed_registry.tool_sheds.values():
            if url in shed_url:
                return shed_url
        return None
