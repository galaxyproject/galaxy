"""
Shared operations layer for AI agents (MCP and internal pydantic-ai).

Delegates to the Galaxy service layer for validation, permission checks, and pagination.
"""

import logging
from typing import (
    Any,
    Literal,
    Optional,
)

from sqlalchemy import select

from galaxy.agents import iwc
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.hdas import HDAManager
from galaxy.managers.tools import DynamicToolManager
from galaxy.model import UserDynamicToolAssociation
from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
)
from galaxy.schema.fetch_data import (
    DataElementsTarget,
    FetchDataPayload,
    HdaDestination,
    UrlDataElement,
)
from galaxy.schema.invocation import InvocationSerializationParams
from galaxy.schema.schema import (
    CreateHistoryPayload,
    CreatePagePayload,
    DatasetSourceType,
    InvocationIndexPayload,
    PageIndexQueryPayload,
    UpdatePagePayload,
    WorkflowIndexPayload,
)
from galaxy.schema.workflows import InvokeWorkflowPayload
from galaxy.structured_app import MinimalManagerApp
from galaxy.tool_util_models.dynamic_tool_models import DynamicUnprivilegedToolCreatePayload

log = logging.getLogger(__name__)

ID_FIELDS = {
    "id",
    "history_id",
    "dataset_id",
    "job_id",
    "workflow_id",
    "invocation_id",
    "user_id",
    "hda_id",
    "hdca_id",
    "collection_id",
    "creating_job",
}


class AgentOperationsManager:
    """Shared operations for AI agents, delegating to Galaxy's service layer."""

    def __init__(self, app: MinimalManagerApp, trans: ProvidesUserContext):
        self.app = app
        self.trans = trans
        self._tools_service: Optional[Any] = None
        self._histories_service: Optional[Any] = None
        self._jobs_service: Optional[Any] = None
        self._datasets_service: Optional[Any] = None
        self._workflows_service: Optional[Any] = None
        self._invocations_service: Optional[Any] = None
        self._hda_manager: Optional[HDAManager] = None
        self._dataset_collections_service: Optional[Any] = None
        self._dynamic_tools_manager: Optional[Any] = None
        self._file_source_instances_manager: Optional[Any] = None
        self._pages_service: Optional[Any] = None

    def _encode_id(self, value: int) -> str:
        return self.trans.security.encode_id(value)

    def _search_toolbox(self, query: str) -> list[str]:
        panel_view = self.app.config.default_panel_view
        return self.app.toolbox_search.search(q=query, panel_view=panel_view, config=self.app.config)  # type: ignore[attr-defined]

    def _get_toolbox_tool(self, tool_id: str):
        return self.app.toolbox.get_tool(tool_id)

    def _encode_ids_in_response(self, data: Any) -> Any:
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if key in ID_FIELDS and isinstance(value, int):
                    result[key] = self._encode_id(value)
                else:
                    result[key] = self._encode_ids_in_response(value)
            return result
        elif isinstance(data, list):
            return [self._encode_ids_in_response(item) for item in data]
        else:
            return data

    @property
    def tools_service(self):
        if self._tools_service is None:
            from galaxy.webapps.galaxy.services.tools import ToolsService

            self._tools_service = self.app[ToolsService]
        return self._tools_service

    @property
    def histories_service(self):
        if self._histories_service is None:
            from galaxy.webapps.galaxy.services.histories import HistoriesService

            self._histories_service = self.app[HistoriesService]
        return self._histories_service

    @property
    def jobs_service(self):
        if self._jobs_service is None:
            from galaxy.webapps.galaxy.services.jobs import JobsService

            self._jobs_service = self.app[JobsService]
        return self._jobs_service

    @property
    def datasets_service(self):
        if self._datasets_service is None:
            from galaxy.webapps.galaxy.services.datasets import DatasetsService

            self._datasets_service = self.app[DatasetsService]
        return self._datasets_service

    @property
    def workflows_service(self):
        if self._workflows_service is None:
            from galaxy.webapps.galaxy.services.workflows import WorkflowsService

            self._workflows_service = self.app[WorkflowsService]
        return self._workflows_service

    @property
    def invocations_service(self):
        if self._invocations_service is None:
            from galaxy.webapps.galaxy.services.invocations import InvocationsService

            self._invocations_service = self.app[InvocationsService]
        return self._invocations_service

    @property
    def hda_manager(self):
        if self._hda_manager is None:
            self._hda_manager = self.app[HDAManager]
        return self._hda_manager

    @property
    def dataset_collections_service(self):
        if self._dataset_collections_service is None:
            from galaxy.webapps.galaxy.services.dataset_collections import DatasetCollectionsService

            self._dataset_collections_service = self.app[DatasetCollectionsService]
        return self._dataset_collections_service

    @property
    def dynamic_tools_manager(self):
        if self._dynamic_tools_manager is None:
            self._dynamic_tools_manager = self.app[DynamicToolManager]
        return self._dynamic_tools_manager

    @property
    def file_source_instances_manager(self):
        if self._file_source_instances_manager is None:
            from galaxy.managers.file_source_instances import FileSourceInstancesManager

            self._file_source_instances_manager = self.app[FileSourceInstancesManager]
        return self._file_source_instances_manager

    @property
    def pages_service(self):
        if self._pages_service is None:
            from galaxy.webapps.galaxy.services.pages import PagesService

            self._pages_service = self.app[PagesService]
        return self._pages_service

    def connect(self) -> dict[str, Any]:
        config = self.app.config
        user = self.trans.user

        if not user:
            raise ValueError("User must be authenticated")

        return {
            "connected": True,
            "server": {
                "version": config.version_major,
                "brand": getattr(config, "brand", "Galaxy"),
                "url": getattr(config, "galaxy_infrastructure_url", "http://localhost:8080"),
            },
            "user": {
                "id": self.trans.security.encode_id(user.id),
                "email": user.email,
                "username": user.username,
            },
        }

    def search_tools(self, query: str) -> dict[str, Any]:
        tool_ids = self._search_toolbox(query)

        tools = []
        for tool_id in tool_ids:
            try:
                tool = self._get_toolbox_tool(tool_id)
                if tool:
                    tools.append(
                        {
                            "id": tool.id,
                            "name": tool.name,
                            "description": tool.description or "",
                            "version": tool.version,
                        }
                    )
            except (KeyError, AttributeError) as e:
                log.debug(f"Skipping tool {tool_id}: {e}")
                continue

        return {"query": query, "tools": tools, "count": len(tools)}

    def get_tool_details(self, tool_id: str, io_details: bool = False) -> dict[str, Any]:
        tool = self._get_toolbox_tool(tool_id)

        if tool is None:
            raise ValueError(f"Tool '{tool_id}' not found")

        tool_info = {
            "id": tool.id,
            "name": tool.name,
            "version": tool.version,
            "description": tool.description or "",
            "help": str(tool.help) if getattr(tool, "help", None) else "",
        }

        if io_details:
            tool_info["inputs"] = []
            for input_param in tool.inputs.values():
                tool_info["inputs"].append(
                    {
                        "name": input_param.name,
                        "type": input_param.type,
                        "label": getattr(input_param, "label", input_param.name),
                        "help": getattr(input_param, "help", ""),
                        "optional": getattr(input_param, "optional", False),
                    }
                )

            tool_info["outputs"] = []
            for output in tool.outputs.values():
                tool_info["outputs"].append(
                    {
                        "name": output.name,
                        "format": getattr(output, "format", "data"),
                        "label": getattr(output, "label", output.name),
                    }
                )

        return tool_info

    def list_histories(self, limit: int = 50, offset: int = 0, name: str | None = None) -> dict[str, Any]:
        serialization_params = SerializationParams(view="summary")

        q: list[str] | None = None
        qv: list[str] | None = None
        if name is not None:
            q = ["name-contains"]
            qv = [name]

        filter_params = FilterQueryParams(limit=limit, offset=offset, q=q, qv=qv)

        histories = self.histories_service.index(
            trans=self.trans,
            serialization_params=serialization_params,
            filter_query_params=filter_params,
            deleted_only=False,
            all_histories=False,
        )

        encoded_histories = self._encode_ids_in_response(histories)

        return {
            "histories": encoded_histories,
            "count": len(encoded_histories),
            "pagination": {"limit": limit, "offset": offset},
        }

    def run_tool(self, history_id: str, tool_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "history_id": history_id,
            "tool_id": tool_id,
            "inputs": inputs,
        }

        result = self.tools_service._create(self.trans, payload)
        return self._encode_ids_in_response(result)

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        decoded_job_id = self.trans.security.decode_id(job_id)

        job_details = self.jobs_service.show(
            trans=self.trans,
            id=decoded_job_id,
            full=False,
        )

        return {"job": self._encode_ids_in_response(job_details), "job_id": job_id}

    def create_history(self, name: str) -> dict[str, Any]:
        payload = CreateHistoryPayload(name=name)
        serialization_params = SerializationParams(view="summary")

        history = self.histories_service.create(
            trans=self.trans,
            payload=payload,
            serialization_params=serialization_params,
        )

        return self._encode_ids_in_response(history)

    def get_history_details(self, history_id: str) -> dict[str, Any]:
        decoded_history_id = self.trans.security.decode_id(history_id)
        serialization_params = SerializationParams(view="detailed")

        history = self.histories_service.show(
            trans=self.trans,
            serialization_params=serialization_params,
            history_id=decoded_history_id,
        )

        return {
            "history": self._encode_ids_in_response(history),
            "history_id": history_id,
        }

    def get_history_contents(
        self,
        history_id: str,
        limit: int = 100,
        offset: int = 0,
        order: str = "hid-asc",
        deleted: bool | None = None,
        visible: bool | None = None,
    ) -> dict[str, Any]:
        decoded_history_id = self.trans.security.decode_id(history_id)
        serialization_params = SerializationParams(view="summary")

        q: list[str] = []
        qv: list[str] = []
        if deleted is not None:
            q.append("deleted-eq")
            qv.append(str(deleted))
        if visible is not None:
            q.append("visible-eq")
            qv.append(str(visible))

        filter_params = FilterQueryParams(limit=limit, offset=offset, order=order, q=q or None, qv=qv or None)

        contents, total_count = self.datasets_service.index(
            trans=self.trans,
            history_id=decoded_history_id,
            serialization_params=serialization_params,
            filter_query_params=filter_params,
        )

        has_next = (offset + limit) < total_count
        has_previous = offset > 0
        current_page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = ((total_count - 1) // limit) + 1 if limit > 0 and total_count > 0 else 1

        return {
            "history_id": history_id,
            "contents": self._encode_ids_in_response(contents),
            "pagination": {
                "total_items": total_count,
                "returned_items": len(contents),
                "limit": limit,
                "offset": offset,
                "current_page": current_page,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
            },
        }

    def get_history_graph(
        self,
        history_id: str,
        seed_src: Optional[str] = None,
        seed_id: Optional[str] = None,
        direction: Literal["backward", "forward", "both"] = "both",
        depth: int = 5,
        limit: int = 200,
        include_deleted: bool = False,
        seed_scope_src: Optional[str] = None,
        seed_scope_id: Optional[str] = None,
    ) -> dict[str, Any]:
        decoded_history_id = self.trans.security.decode_id(history_id)
        response = self.histories_service.graph(
            trans=self.trans,
            history_id=decoded_history_id,
            limit=limit,
            include_deleted=include_deleted,
            seed_src=seed_src,
            seed_id=seed_id,
            direction=direction,
            depth=depth,
            seed_scope_src=seed_scope_src,
            seed_scope_id=seed_scope_id,
        )
        return response.model_dump()

    def get_dataset_details(self, dataset_id: str) -> dict[str, Any]:
        decoded_dataset_id = self.trans.security.decode_id(dataset_id)
        serialization_params = SerializationParams(view="detailed")

        dataset = self.datasets_service.show(
            trans=self.trans,
            dataset_id=decoded_dataset_id,
            hda_ldda=DatasetSourceType.hda,
            serialization_params=serialization_params,
        )

        return {
            "dataset": self._encode_ids_in_response(dataset),
            "dataset_id": dataset_id,
        }

    def get_collection_details(self, collection_id: str, max_elements: int = 500) -> dict[str, Any]:
        decoded_collection_id = self.trans.security.decode_id(collection_id)

        collection_info = self.dataset_collections_service.show(
            trans=self.trans,
            id=decoded_collection_id,
            instance_type="history",
            view="element",
        )

        result = self._encode_ids_in_response(collection_info)

        if "elements" in result:
            elements = result["elements"]
            if len(elements) > max_elements:
                result["elements"] = elements[:max_elements]
                result["elements_truncated"] = True
                result["total_elements"] = len(elements)

        return {"collection": result, "collection_id": collection_id}

    def upload_file_from_url(
        self,
        history_id: str,
        url: str,
        file_type: str = "auto",
        dbkey: str = "?",
        file_name: str | None = None,
    ) -> dict[str, Any]:
        decoded_history_id = self.trans.security.decode_id(history_id)
        fetch_payload = FetchDataPayload(
            history_id=decoded_history_id,
            targets=[
                DataElementsTarget(
                    destination=HdaDestination(type="hdas"),
                    elements=[
                        UrlDataElement(
                            src="url",
                            url=url,
                            ext=file_type,
                            dbkey=dbkey,
                            name=file_name,
                        )
                    ],
                )
            ],
        )
        result = self.tools_service.create_fetch(self.trans, fetch_payload)
        return self._encode_ids_in_response(result)

    def list_workflows(
        self,
        limit: int = 50,
        offset: int = 0,
        show_published: bool = False,
        show_shared: bool = True,
        search: str | None = None,
    ) -> dict[str, Any]:
        payload = WorkflowIndexPayload(
            limit=limit,
            offset=offset,
            show_published=show_published,
            show_shared=show_shared,
            search=search,
        )

        workflows, total_count = self.workflows_service.index(
            trans=self.trans,
            payload=payload,
            include_total_count=True,
        )

        encoded_workflows = self._encode_ids_in_response(workflows)

        return {
            "workflows": encoded_workflows,
            "count": len(encoded_workflows),
            "total_count": total_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
            },
        }

    def get_workflow_details(self, workflow_id: str, version: int | None = None) -> dict[str, Any]:
        decoded_workflow_id = self.trans.security.decode_id(workflow_id)

        workflow = self.workflows_service.show_workflow(
            trans=self.trans,
            workflow_id=decoded_workflow_id,
            instance=False,
            legacy=False,
            version=version,
        )

        return {
            "workflow": self._encode_ids_in_response(workflow),
            "workflow_id": workflow_id,
        }

    def invoke_workflow(
        self,
        workflow_id: str,
        history_id: str | None = None,
        inputs: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
        history_name: str | None = None,
    ) -> dict[str, Any]:
        if not history_id and not history_name:
            raise ValueError("Either history_id or history_name must be provided")

        decoded_workflow_id = self.trans.security.decode_id(workflow_id)

        payload = InvokeWorkflowPayload(
            history_id=history_id,
            new_history_name=history_name if not history_id else None,
            inputs=inputs or {},
            parameters=parameters or {},
        )

        result = self.workflows_service.invoke_workflow(
            trans=self.trans,
            workflow_id=decoded_workflow_id,
            payload=payload,
        )

        return self._encode_ids_in_response(result)

    def get_invocations(
        self,
        workflow_id: str | None = None,
        history_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        decoded_workflow_id = None
        if workflow_id:
            decoded_workflow_id = self.trans.security.decode_id(workflow_id)

        decoded_history_id = None
        if history_id:
            decoded_history_id = self.trans.security.decode_id(history_id)

        payload = InvocationIndexPayload(
            workflow_id=decoded_workflow_id,
            history_id=decoded_history_id,
            limit=limit,
            offset=offset,
        )
        serialization_params = InvocationSerializationParams(view="collection")

        invocations, total_count = self.invocations_service.index(
            trans=self.trans,
            invocation_payload=payload,
            serialization_params=serialization_params,
        )

        encoded_invocations = self._encode_ids_in_response(invocations)

        return {
            "invocations": encoded_invocations,
            "count": len(encoded_invocations),
            "total_count": total_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
            },
        }

    def get_invocation_details(self, invocation_id: str) -> dict[str, Any]:
        decoded_invocation_id = self.trans.security.decode_id(invocation_id)
        serialization_params = InvocationSerializationParams(view="element")

        invocation = self.invocations_service.show(
            trans=self.trans,
            invocation_id=decoded_invocation_id,
            serialization_params=serialization_params,
        )

        return {
            "invocation": self._encode_ids_in_response(invocation),
            "invocation_id": invocation_id,
        }

    def cancel_workflow_invocation(self, invocation_id: str) -> dict[str, Any]:
        decoded_invocation_id = self.trans.security.decode_id(invocation_id)
        serialization_params = InvocationSerializationParams(view="element")

        invocation = self.invocations_service.cancel(
            trans=self.trans,
            invocation_id=decoded_invocation_id,
            serialization_params=serialization_params,
        )

        return {
            "invocation": self._encode_ids_in_response(invocation),
            "invocation_id": invocation_id,
            "cancelled": True,
        }

    def get_tool_panel(self, view: str | None = None) -> dict[str, Any]:
        if view is None:
            view = self.app.toolbox._default_panel_view(self.trans)

        tool_panel = self.app.toolbox.to_panel_view(self.trans, view=view)

        return {"tool_panel": tool_panel, "view": view}

    def get_tool_run_examples(self, tool_id: str, tool_version: str | None = None) -> dict[str, Any]:
        tool = self._get_toolbox_tool(tool_id)
        if tool and tool_version:
            versioned = self.app.toolbox.get_tool(tool_id, tool_version=tool_version)
            if versioned:
                tool = versioned

        if tool is None:
            raise ValueError(f"Tool '{tool_id}' not found")

        test_cases = []
        if hasattr(tool, "tests") and tool.tests:
            for i, test in enumerate(tool.tests):
                inputs: dict[str, Any] = {}
                outputs: dict[str, Any] = {}
                if hasattr(test, "inputs"):
                    for name, value in test.inputs.items():
                        inputs[name] = str(value) if value is not None else None

                if hasattr(test, "outputs"):
                    for output in test.outputs:
                        outputs[output.name] = {
                            "file": getattr(output, "file", None),
                            "value": getattr(output, "value", None),
                        }

                test_cases.append({"index": i, "inputs": inputs, "outputs": outputs})

        return {
            "tool_id": tool_id,
            "tool_name": tool.name,
            "tool_version": tool.version,
            "test_cases": test_cases,
            "count": len(test_cases),
        }

    def get_tool_citations(self, tool_id: str) -> dict[str, Any]:
        tool = self._get_toolbox_tool(tool_id)

        if tool is None:
            raise ValueError(f"Tool '{tool_id}' not found")

        citations = []
        if hasattr(tool, "citations") and tool.citations:
            for citation in tool.citations:
                citation_info = {
                    "type": getattr(citation, "type", "unknown"),
                }
                if hasattr(citation, "doi"):
                    citation_info["doi"] = citation.doi
                if hasattr(citation, "bibtex"):
                    citation_info["bibtex"] = citation.bibtex
                if hasattr(citation, "url"):
                    citation_info["url"] = citation.url
                citations.append(citation_info)

        return {
            "tool_id": tool_id,
            "tool_name": tool.name,
            "tool_version": tool.version,
            "citations": citations,
            "count": len(citations),
        }

    def search_tools_by_keywords(self, keywords: list[str]) -> dict[str, Any]:
        keywords_lower = [k.lower() for k in keywords]
        matching_tools = []
        seen_tool_ids = set()

        for keyword in keywords:
            tool_ids = self._search_toolbox(keyword)

            for tool_id in tool_ids:
                if tool_id in seen_tool_ids:
                    continue

                try:
                    tool = self._get_toolbox_tool(tool_id)
                    if tool:
                        name_lower = (tool.name or "").lower()
                        desc_lower = (tool.description or "").lower()

                        matches = []
                        for kw in keywords_lower:
                            if kw in name_lower or kw in desc_lower:
                                matches.append(kw)

                        matching_tools.append(
                            {
                                "id": tool.id,
                                "name": tool.name,
                                "description": tool.description or "",
                                "version": tool.version,
                                "matched_keywords": matches,
                            }
                        )
                        seen_tool_ids.add(tool_id)
                except Exception as e:
                    log.debug(f"Skipping tool {tool_id}: {str(e)}")
                    continue

        matching_tools.sort(key=lambda x: len(x["matched_keywords"]), reverse=True)

        return {
            "keywords": keywords,
            "tools": matching_tools,
            "count": len(matching_tools),
        }

    def list_history_ids(self, limit: int = 100) -> dict[str, Any]:
        serialization_params = SerializationParams(view="summary")
        filter_params = FilterQueryParams(limit=limit, offset=0)

        histories = self.histories_service.index(
            trans=self.trans,
            serialization_params=serialization_params,
            filter_query_params=filter_params,
            deleted_only=False,
            all_histories=False,
        )

        simplified = [
            {
                "id": self._encode_id(h["id"]) if isinstance(h["id"], int) else h["id"],
                "name": h["name"],
            }
            for h in histories
        ]

        return {"histories": simplified, "count": len(simplified)}

    def get_job_details(self, dataset_id: str, history_id: str | None = None) -> dict[str, Any]:
        """Get details about the job that created a dataset."""
        decoded_dataset_id = self.trans.security.decode_id(dataset_id)
        hda = self.hda_manager.get_accessible(decoded_dataset_id, self.trans.user)

        if not hda:
            raise ValueError(f"Dataset '{dataset_id}' not found or not accessible")

        job = hda.creating_job
        if not job:
            return {
                "dataset_id": dataset_id,
                "job": None,
                "message": "No creating job found for this dataset",
            }

        return {
            "dataset_id": dataset_id,
            "job_id": self.trans.security.encode_id(job.id),
            "job": {
                "tool_id": job.tool_id,
                "tool_version": job.tool_version,
                "state": job.state,
                "create_time": job.create_time.isoformat() if job.create_time else None,
                "update_time": job.update_time.isoformat() if job.update_time else None,
            },
        }

    def get_job_errors(self, dataset_id: str) -> dict[str, Any]:
        """Get error details (stderr, stdout, exit code) for a failed job."""
        decoded_dataset_id = self.trans.security.decode_id(dataset_id)
        hda = self.hda_manager.get_accessible(decoded_dataset_id, self.trans.user)

        if not hda:
            raise ValueError(f"Dataset '{dataset_id}' not found or not accessible")

        job = hda.creating_job
        if not job:
            return {
                "dataset_id": dataset_id,
                "error": "No creating job found for this dataset",
            }

        # Truncate large outputs to avoid overwhelming the LLM
        max_output_length = 4000

        stderr = job.stderr or ""
        stdout = job.stdout or ""
        info = job.info or ""

        return {
            "dataset_id": dataset_id,
            "job_id": self.trans.security.encode_id(job.id),
            "tool_id": job.tool_id,
            "tool_version": job.tool_version,
            "state": job.state,
            "exit_code": job.exit_code,
            "info": info[:max_output_length] if info else None,
            "stderr": stderr[:max_output_length] if stderr else None,
            "stdout": stdout[:max_output_length] if stdout else None,
            "truncated": len(stderr) > max_output_length or len(stdout) > max_output_length,
        }

    def peek_dataset_content(self, dataset_id: str) -> dict[str, Any]:
        """Preview the content of a dataset (text-based datasets only)."""
        decoded_dataset_id = self.trans.security.decode_id(dataset_id)
        hda = self.hda_manager.get_accessible(decoded_dataset_id, self.trans.user)

        if not hda:
            raise ValueError(f"Dataset '{dataset_id}' not found or not accessible")

        if hda.state != "ok":
            return {
                "dataset_id": dataset_id,
                "state": hda.state,
                "error": f"Dataset is not ready (state: {hda.state})",
            }

        result: dict[str, Any] = {
            "dataset_id": dataset_id,
            "name": hda.name,
            "extension": hda.extension,
            "file_size": hda.get_size(),
            "peek": hda.peek or "",
        }

        try:
            truncated, text_data = self.hda_manager.text_data(hda, preview=True)
            result["content_preview"] = text_data or ""
            result["truncated"] = truncated
        except Exception:
            log.debug(f"Content preview unavailable for dataset {dataset_id}", exc_info=True)
            result["content_preview"] = ""
            result["truncated"] = False
            result["note"] = "Content preview not available (non-text dataset or encoding issue)"

        return result

    def download_dataset(self, dataset_id: str) -> dict[str, Any]:
        """Get download URL and metadata for a dataset."""
        decoded_dataset_id = self.trans.security.decode_id(dataset_id)
        hda = self.hda_manager.get_accessible(decoded_dataset_id, self.trans.user)

        if not hda:
            raise ValueError(f"Dataset '{dataset_id}' not found or not accessible")

        if hda.state != "ok":
            return {
                "dataset_id": dataset_id,
                "state": hda.state,
                "error": f"Dataset is not ready for download (state: {hda.state})",
            }

        base_url = getattr(self.app.config, "galaxy_infrastructure_url", "http://localhost:8080")
        download_url = f"{base_url}/api/datasets/{dataset_id}/display"

        return {
            "dataset_id": dataset_id,
            "name": hda.name,
            "extension": hda.extension,
            "file_size": hda.get_size(),
            "state": hda.state,
            "download_url": download_url,
        }

    def get_server_info(self) -> dict[str, Any]:
        config = self.app.config

        return {
            "server": {
                "version": config.version_major,
                "version_minor": getattr(config, "version_minor", ""),
                "brand": getattr(config, "brand", "Galaxy"),
                "url": getattr(config, "galaxy_infrastructure_url", "http://localhost:8080"),
            },
            "capabilities": {
                "allow_user_creation": getattr(config, "allow_user_creation", True),
                "allow_user_dataset_purge": getattr(config, "allow_user_dataset_purge", True),
                "enable_quotas": getattr(config, "enable_quotas", False),
                "support_url": getattr(config, "support_url", ""),
                "terms_url": getattr(config, "terms_url", ""),
            },
        }

    # ==================== IWC ====================

    def search_iwc_workflows(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Rank IWC manifest workflows by token overlap against name, description, tags, and tools."""
        workflows = iwc.all_workflows(iwc.fetch_manifest())
        results = iwc.search_workflows(workflows, query, limit=limit)
        return {
            "query": query,
            "workflows": results,
            "count": len(results),
        }

    def get_iwc_workflow_details(self, trs_id: str) -> dict[str, Any]:
        """Return the full enriched entry for a single IWC workflow."""
        workflows = iwc.all_workflows(iwc.fetch_manifest())
        for wf in workflows:
            if wf.get("trsID") == trs_id:
                return iwc.enrich_workflow(wf, include_full_readme=True)
        raise ValueError(
            f"IWC workflow with trsID {trs_id!r} not found. Use search_iwc_workflows() to discover trsIDs."
        )

    def import_workflow_from_iwc(self, trs_id: str) -> dict[str, Any]:
        """Import an IWC workflow into the user's stored workflows by TRS id.

        IWC ships its catalog on Dockstore, so this delegates to the shared TRS
        import pipeline (same one ``POST /api/workflows`` uses for
        ``archive_source=trs_tool``) rather than building from the manifest's
        embedded definition. That preserves de-dup by (trs_id, trs_version, user),
        source-metadata recording, and the shared subworkflow-from-TRS resolution.
        Tools that aren't installed locally are surfaced as ``missing_tools`` so
        the agent can flag a workflow that imported but won't run yet.
        """
        if not trs_id:
            raise ValueError("trs_id is required")
        user = self.trans.user
        if not user:
            raise ValueError("User must be authenticated to import a workflow")

        contents_manager = self.app.workflow_contents_manager
        stored_workflow = contents_manager.get_or_create_workflow_from_trs(
            self.trans,
            trs_url=None,
            trs_id=trs_id,
            trs_version="main",
            trs_server="dockstore",
        )

        missing_tools: list[str] = []
        latest = stored_workflow.latest_workflow
        if latest is not None:
            toolbox = self.app.toolbox
            seen: set[str] = set()
            for tool in contents_manager.get_all_tools(latest):
                tool_id = tool["tool_id"]
                if tool_id in seen:
                    continue
                seen.add(tool_id)
                if not toolbox.has_tool(
                    tool_id,
                    tool_version=tool.get("tool_version"),
                    tool_uuid=tool.get("tool_uuid"),
                ):
                    missing_tools.append(tool_id)

        return {
            "id": self.trans.security.encode_id(stored_workflow.id),
            "name": stored_workflow.name,
            "trsID": trs_id,
            "missing_tools": missing_tools,
        }

    def get_user(self) -> dict[str, Any]:
        user = self.trans.user

        if not user:
            raise ValueError("User must be authenticated")

        return {
            "id": self.trans.security.encode_id(user.id),
            "email": user.email,
            "username": user.username,
            "is_admin": self.trans.user_is_admin,
            "active": user.active,
            "deleted": user.deleted,
            "create_time": user.create_time.isoformat() if user.create_time else None,
        }

    # ==================== User-Defined Tools (UDT) ====================

    def list_user_tools(self, active: bool = True) -> dict[str, Any]:
        user = self.trans.user
        if not user:
            raise ValueError("User must be authenticated")

        tools = list(self.dynamic_tools_manager.list_unprivileged_tools(user, active=active))
        return {
            "tools": [t.to_dict() for t in tools],
            "count": len(tools),
        }

    def create_user_tool(self, representation: dict[str, Any]) -> dict[str, Any]:
        user = self.trans.user
        if not user:
            raise ValueError("User must be authenticated")

        payload = DynamicUnprivilegedToolCreatePayload(src="representation", representation=representation)
        dynamic_tool = self.dynamic_tools_manager.create_unprivileged_tool(user, payload)
        return dynamic_tool.to_dict()

    def delete_user_tool(self, uuid: str) -> dict[str, Any]:
        user = self.trans.user
        if not user:
            raise ValueError("User must be authenticated")

        dynamic_tool = self.dynamic_tools_manager.get_unprivileged_tool_by_uuid(user, uuid)
        if dynamic_tool is None:
            raise ValueError(f"User-defined tool {uuid!r} not found")

        self.dynamic_tools_manager.deactivate_unprivileged_tool(user, dynamic_tool)
        return {"uuid": uuid, "deactivated": True}

    def run_user_tool(self, history_id: str, tool_uuid: str, inputs: dict[str, Any]) -> dict[str, Any]:
        user = self.trans.user
        if not user:
            raise ValueError("User must be authenticated")

        dynamic_tool = self.dynamic_tools_manager.get_unprivileged_tool_by_uuid(user, tool_uuid)
        if dynamic_tool is None:
            raise ValueError(f"User-defined tool {tool_uuid!r} not found")
        # UDT deactivation is per-user by design: deactivate_unprivileged_tool only
        # flips the user-association, leaving DynamicTool.active intact so other
        # users sharing the underlying tool aren't affected. The runtime check has
        # to look at the association, not just dynamic_tool.active.
        session = self.dynamic_tools_manager.session()
        assoc_active = session.scalar(
            select(UserDynamicToolAssociation.active).where(
                UserDynamicToolAssociation.user_id == user.id,
                UserDynamicToolAssociation.dynamic_tool_id == dynamic_tool.id,
            )
        )
        if not dynamic_tool.active or not assoc_active:
            raise ValueError(f"User-defined tool {tool_uuid!r} is deactivated")

        payload = {
            "history_id": history_id,
            "tool_uuid": tool_uuid,
            "inputs": inputs,
        }
        result = self.tools_service._create(self.trans, payload)
        return self._encode_ids_in_response(result)

    # ==================== File sources (remote data repositories) ====================

    def list_file_source_templates(self) -> dict[str, Any]:
        """Return the catalog of file source plugin templates available to configure.

        Each template corresponds to a remote data repository Galaxy can connect
        to (Omero, Dropbox, S3, Zenodo, etc.). Templates are the catalog; the
        user instantiates one to get a working file source. Hidden (deprecated)
        templates are filtered out.
        """
        summaries = self.file_source_instances_manager.summaries
        templates = [t.model_dump(mode="json") for t in summaries.root if not t.hidden]
        return {
            "templates": templates,
            "count": len(templates),
        }

    def list_user_file_sources(self) -> dict[str, Any]:
        """Return the file source instances configured by the current user.

        These are the user's active connections to remote data repositories,
        usable as both data sources and export destinations.
        """
        if not self.trans.user:
            raise ValueError("User must be authenticated")
        instances = self.file_source_instances_manager.index(self.trans)
        file_sources = [i.model_dump(mode="json") for i in instances]
        return {
            "file_sources": file_sources,
            "count": len(file_sources),
        }

    # ==================== Pages (notebooks and reports) ====================

    def _dump_page(self, model, include_rendered: bool = False) -> dict[str, Any]:
        """Serialize a page/revision schema, dropping the large rendered form by default.

        content_editor (editable encoded-id markdown) is always kept; content (the
        embed-expanded render form) is included only when include_rendered is True.
        """
        result = model.model_dump(mode="json")
        if not include_rendered:
            result.pop("content", None)
        return result

    def list_pages(
        self,
        history_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        show_published: bool = False,
        show_shared: bool = False,
        deleted: bool = False,
    ) -> dict[str, Any]:
        """List pages viewable by the current user.

        When history_id is set, only pages attached to that history (Galaxy
        Notebooks) are returned. Defaults to the user's own pages; published or
        shared pages are included only when explicitly requested.
        """
        payload = PageIndexQueryPayload(
            history_id=history_id,
            search=search,
            limit=limit,
            offset=offset,
            show_own=True,
            show_published=show_published,
            show_shared=show_shared,
            deleted=deleted,
        )
        pages, total_matches = self.pages_service.index(self.trans, payload, include_total_count=True)
        return {
            "pages": pages.model_dump(mode="json"),
            "count": len(pages.root),
            "total_matches": total_matches,
        }

    def get_page(self, page_id: str, include_rendered: bool = False) -> dict[str, Any]:
        """Return a page with its latest-revision content.

        content_editor (editable markdown with encoded-id directives) is always
        returned. The embed-expanded render form (content) can be large and is
        included only when include_rendered is True.
        """
        decoded_page_id = self.trans.security.decode_id(page_id)
        details = self.pages_service.show(self.trans, decoded_page_id)
        return self._dump_page(details, include_rendered)

    def create_page(
        self,
        history_id: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[str] = None,
        annotation: Optional[str] = None,
        slug: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a markdown page. Attach it to a history (notebook) by passing history_id.

        Standalone reports (no history_id) require a unique slug and a title.
        """
        payload = CreatePagePayload(
            history_id=history_id,
            title=title,
            content=content,
            content_format="markdown",
            annotation=annotation,
            slug=slug,
        )
        details = self.pages_service.create(self.trans, payload)
        return self._dump_page(details)

    def update_page(
        self,
        page_id: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
    ) -> dict[str, Any]:
        """Update a page. Supplying content creates a new revision tagged edit_source=agent."""
        decoded_page_id = self.trans.security.decode_id(page_id)
        payload = UpdatePagePayload(
            content=content,
            title=title,
            edit_source="agent",
        )
        details = self.pages_service.update(self.trans, decoded_page_id, payload)
        return self._dump_page(details)

    def list_page_revisions(self, page_id: str, sort_desc: bool = False) -> dict[str, Any]:
        """List the revision history of a page (provenance via edit_source)."""
        decoded_page_id = self.trans.security.decode_id(page_id)
        revisions = self.pages_service.list_revisions(self.trans, decoded_page_id, sort_desc=sort_desc)
        return {
            "revisions": revisions.model_dump(mode="json"),
            "count": len(revisions.root),
        }

    def get_page_revision(self, page_id: str, revision_id: str, include_rendered: bool = False) -> dict[str, Any]:
        """Return a single page revision with its content.

        Mirrors get_page: content_editor (editable encoded-id markdown) is always
        returned; the embed-expanded render form (content) is included only when
        include_rendered is True.
        """
        decoded_page_id = self.trans.security.decode_id(page_id)
        decoded_revision_id = self.trans.security.decode_id(revision_id)
        revision = self.pages_service.show_revision(self.trans, decoded_page_id, decoded_revision_id)
        return self._dump_page(revision, include_rendered)

    def revert_page_revision(self, page_id: str, revision_id: str) -> dict[str, Any]:
        """Roll a page back to an earlier revision (creates a new 'restore' revision)."""
        decoded_page_id = self.trans.security.decode_id(page_id)
        decoded_revision_id = self.trans.security.decode_id(revision_id)
        revision = self.pages_service.revert_revision(self.trans, decoded_page_id, decoded_revision_id)
        return self._dump_page(revision)
