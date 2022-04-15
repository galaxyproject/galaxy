from typing import (
    Any,
    Dict,
    List,
)

from sqlalchemy import (
    desc,
    false,
    or_,
    true,
)
from sqlalchemy.orm import joinedload

from galaxy import (
    exceptions,
    model,
    web,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.workflows import (
    WorkflowContentsManager,
    WorkflowSerializer,
    WorkflowsManager,
)
from galaxy.schema.schema import WorkflowIndexPayload
from galaxy.tool_shed.tool_shed_registry import Registry
from galaxy.webapps.galaxy.services.base import ServiceBase
from galaxy.webapps.galaxy.services.sharable import ShareableService


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
    ) -> List[Dict[str, Any]]:
        show_published = payload.show_published
        show_hidden = payload.show_hidden
        show_deleted = payload.show_deleted
        missing_tools = payload.missing_tools
        show_shared = payload.show_shared

        if show_shared is None:
            show_shared = not show_hidden and not show_deleted

        if show_shared and show_deleted:
            message = "show_shared and show_deleted cannot both be specified as true"
            raise exceptions.RequestParameterInvalidException(message)
        if show_shared and show_hidden:
            message = "show_shared and show_hidden cannot both be specified as true"
            raise exceptions.RequestParameterInvalidException(message)

        rval = []
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

        query = (
            query.options(joinedload("annotations"))
            .options(joinedload("latest_workflow").undefer("step_count").lazyload("steps"))
            .options(joinedload("tags"))
        )
        query = query.filter(or_(*filters))
        query = query.filter(model.StoredWorkflow.table.c.hidden == (true() if show_hidden else false()))
        query = query.filter(model.StoredWorkflow.table.c.deleted == (true() if show_deleted else false()))
        if payload.sort_by is None:
            if user:
                query = query.order_by(desc(model.StoredWorkflow.user == user))
            query = query.order_by(desc(model.StoredWorkflow.table.c.update_time))
        else:
            sort_column = getattr(model.StoredWorkflow, payload.sort_by)
            query = query.order_by(sort_column)
        for wf in query.all():
            item = wf.to_dict(value_mapper={"id": trans.security.encode_id})
            encoded_id = trans.security.encode_id(wf.id)
            item["annotations"] = [x.annotation for x in wf.annotations]
            item["url"] = web.url_for("workflow", id=encoded_id)
            item["owner"] = wf.user.username
            item["source_metadata"] = wf.latest_workflow.source_metadata
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
            return workflows
        return rval

    def __get_full_shed_url(self, url):
        for shed_url in self._tool_shed_registry.tool_sheds.values():
            if url in shed_url:
                return shed_url
        return None
