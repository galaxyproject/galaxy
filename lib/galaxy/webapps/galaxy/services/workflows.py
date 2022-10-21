import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from galaxy import web
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.workflows import (
    WorkflowContentsManager,
    WorkflowSerializer,
    WorkflowsManager,
)
from galaxy.schema.schema import WorkflowIndexQueryPayload
from galaxy.util.tool_shed.tool_shed_registry import Registry
from galaxy.webapps.galaxy.services.base import ServiceBase
from galaxy.webapps.galaxy.services.sharable import ShareableService

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
    ):
        self._workflows_manager = workflows_manager
        self._workflow_contents_manager = workflow_contents_manager
        self._serializer = serializer
        self.shareable_service = ShareableService(workflows_manager, serializer)
        self._tool_shed_registry = tool_shed_registry

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
            workflows_by_toolshed = dict()
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

    def delete(self, trans, workflow_id):
        workflow_to_delete = self._workflows_manager.get_stored_workflow(trans, workflow_id)
        self._workflows_manager.check_security(trans, workflow_to_delete)
        self._workflows_manager.delete(workflow_to_delete)

    def undelete(self, trans, workflow_id):
        workflow_to_undelete = self._workflows_manager.get_stored_workflow(trans, workflow_id)
        self._workflows_manager.check_security(trans, workflow_to_undelete)
        self._workflows_manager.undelete(workflow_to_undelete)

    def get_versions(self, trans, workflow_id, instance):
        stored_workflow = self._workflows_manager.get_stored_accessible_workflow(
            trans, workflow_id, by_stored_id=not instance
        )
        return [
            {"version": i, "update_time": w.update_time.isoformat(), "steps": len(w.steps)}
            for i, w in enumerate(reversed(stored_workflow.workflows))
        ]

    def get_workflow_menu(self, trans, payload):
        ids_in_menu = [x.stored_workflow_id for x in trans.user.stored_workflow_menu_entries]
        workflows = self._get_workflows_list(
            trans,
            payload,
        )
        return {"ids_in_menu": ids_in_menu, "workflows": workflows}

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
