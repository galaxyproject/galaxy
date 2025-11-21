"""Service for handling chat-side Pyodide execution results.

This keeps `lib/galaxy/webapps/galaxy/api/chat.py` thin by moving the
business logic for persisting execution results + follow-up reasoning
into a manager/service layer (similar to other Galaxy managers).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from galaxy.managers.agents import AgentService
from galaxy.managers.chat import ChatManager
from galaxy.managers.collections_util import api_payload_to_create_params
from galaxy.managers.context import ProvidesHistoryContext, ProvidesUserContext
from galaxy.model import User
from galaxy.schema.schema import PyodideResultPayload
from galaxy.util.pyodide import merge_execution_metadata

log = logging.getLogger(__name__)


class ChatExecutionService:
    """Handle Pyodide execution result submissions for a chat exchange."""

    def __init__(self, chat_manager: ChatManager, agent_service: AgentService):
        self.chat_manager = chat_manager
        self.agent_service = agent_service

    async def handle_pyodide_result(
        self,
        exchange_id: int,
        payload: PyodideResultPayload,
        trans: ProvidesHistoryContext,
        user: User,
    ) -> dict[str, Any]:
        """Persist execution results and generate a follow-up agent response.

        Returns a dict suitable for the API response payload (JSON serialisable).
        """

        started = time.time()

        # Ensure the exchange exists and belongs to the user (ChatManager enforces ownership).
        exchange = self.chat_manager.get_exchange_by_id(trans, exchange_id)
        if not exchange:
            return {"message": "Chat exchange not found"}

        metadata = dict(payload.metadata or {})

        # Best effort: aggregate artifact datasets into a collection for convenience.
        if payload.artifacts:
            try:
                collection_info = self._create_artifact_collection(trans, payload.artifacts, metadata.get("original_query"))
                if collection_info:
                    metadata["artifacts_collection"] = collection_info
            except Exception as exc:  # pragma: no cover - best effort logging
                log.warning("Unable to aggregate artifacts into collection: %s", exc)

        execution_message = json.dumps(
            {
                "role": "execution_result",
                "task_id": payload.task_id,
                "stdout": payload.stdout,
                "stderr": payload.stderr,
                "artifacts": payload.artifacts,
                "metadata": metadata,
                "success": payload.success,
            }
        )
        self.chat_manager.add_message(trans, exchange_id, execution_message)

        try:
            self._apply_execution_result_to_exchange(trans, exchange_id, payload)
        except Exception as exc:  # pragma: no cover - protective path
            log.warning(
                "Unable to merge execution metadata into exchange %s for task %s: %s",
                exchange_id,
                payload.task_id,
                exc,
                exc_info=True,
            )

        conversation_history = self.chat_manager.get_chat_history(trans, exchange_id, format_for_pydantic_ai=False)

        raw_dataset_ids = metadata.get("selected_dataset_ids")
        if isinstance(raw_dataset_ids, list):
            dataset_ids = [str(ds_id) for ds_id in raw_dataset_ids]
        else:
            dataset_ids = []

        agent_type = metadata.get("agent_type")
        original_query = metadata.get("original_query")

        # Fall back to values stored in earlier exchange messages (source of truth).
        refreshed_exchange = self.chat_manager.get_exchange_by_id(trans, exchange_id)
        if refreshed_exchange:
            for message in refreshed_exchange.messages:
                raw = getattr(message, "message", None)
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except (json.JSONDecodeError, TypeError, AttributeError):
                    continue

                if not agent_type and data.get("agent_type"):
                    agent_type = data.get("agent_type")
                if not dataset_ids and data.get("dataset_ids"):
                    dataset_ids = [str(ds_id) for ds_id in data.get("dataset_ids") or []]
                if not original_query and data.get("query"):
                    original_query = data.get("query")

        query_text = original_query
        if not query_text:
            for entry in reversed(conversation_history):
                if entry.get("role") == "user" and entry.get("content"):
                    query_text = entry.get("content")
                    break
        if not query_text:
            query_text = "Continue the analysis based on the latest execution result."

        context: dict[str, Any] = {"conversation_history": conversation_history}
        if dataset_ids:
            context["dataset_ids"] = dataset_ids

        agent_type_to_use = agent_type or "auto"

        try:
            followup_response = await self.agent_service.route_and_execute(
                query=query_text,
                trans=trans,
                user=user,
                context=context,
                agent_type=agent_type_to_use,
            )
        except Exception as exc:
            log.error(
                "Failed to generate follow-up after Pyodide execution for exchange %s: %s",
                exchange_id,
                exc,
                exc_info=True,
            )
            return {
                "message": "Execution result stored",
                "error": str(exc),
                "dataset_ids": dataset_ids,
                "exchange_id": exchange_id,
                "task_id": payload.task_id,
            }

        followup_message = json.dumps(
            {
                "response": followup_response.content,
                "agent_type": followup_response.agent_type or agent_type_to_use,
                "agent_response": followup_response.model_dump(),
                "dataset_ids": dataset_ids,
            }
        )
        self.chat_manager.add_message(trans, exchange_id, followup_message)

        duration_ms = int((time.time() - started) * 1000)
        log.info(
            "pyodide_execution_completed",
            extra={
                "exchange_id": exchange_id,
                "task_id": payload.task_id,
                "success": payload.success,
                "artifacts_count": len(payload.artifacts or []),
                "followup_generated": True,
                "duration_ms": duration_ms,
            },
        )

        return {
            "message": "Execution result stored",
            "response": followup_response.content,
            "agent_response": followup_response.model_dump(),
            "dataset_ids": dataset_ids,
            "exchange_id": exchange_id,
            "task_id": payload.task_id,
        }

    def _create_artifact_collection(
        self,
        trans: ProvidesHistoryContext,
        artifacts: list[dict[str, Any]],
        query_text: Optional[str],
    ) -> Optional[dict[str, Any]]:
        history = getattr(trans, "history", None)
        if not history or not artifacts or len(artifacts) < 2:
            return None

        element_identifiers: list[dict[str, str]] = []
        used_names: set[str] = set()
        for index, artifact in enumerate(artifacts, start=1):
            dataset_id = artifact.get("dataset_id")
            if not dataset_id:
                continue
            try:
                decoded_id = trans.security.decode_id(dataset_id)
            except Exception:
                log.warning("Failed to decode dataset id '%s' while building artifact collection", dataset_id)
                continue
            base_name = (artifact.get("name") or f"artifact_{index}").strip() or f"artifact_{index}"
            candidate = base_name
            suffix = 1
            while candidate in used_names:
                suffix += 1
                candidate = f"{base_name}_{suffix}"
            used_names.add(candidate)
            element_identifiers.append({"name": candidate, "src": "hda", "id": decoded_id})

        if len(element_identifiers) < 2:
            return None

        base_name = (query_text or "Chat artifacts").strip()
        words = base_name.split()
        if len(words) > 10:
            base_name = " ".join(words[:10])
        if not base_name:
            base_name = "Chat artifacts"

        payload = {
            "collection_type": "list",
            "name": base_name,
            "hide_source_items": True,
            "element_identifiers": element_identifiers,
        }
        create_params = api_payload_to_create_params(payload)
        dataset_collection_manager = trans.app.dataset_collection_manager
        collection_instance = dataset_collection_manager.create(
            trans,
            parent=history,
            history=history,
            **create_params,
        )
        trans.sa_session.flush()
        return {
            "id": trans.security.encode_id(collection_instance.id),
            "name": collection_instance.name,
            "elements": len(element_identifiers),
        }

    def _apply_execution_result_to_exchange(
        self,
        trans: ProvidesUserContext,
        exchange_id: int,
        payload: PyodideResultPayload,
    ) -> None:
        if not payload.task_id:
            return
        exchange = self.chat_manager.get_exchange_by_id(trans, exchange_id)
        if not exchange:
            return

        target = None
        target_payload: Optional[dict[str, Any]] = None
        task_id = str(payload.task_id)

        for message in reversed(exchange.messages):
            raw = getattr(message, "message", None)
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue
            agent_response = data.get("agent_response")
            metadata = agent_response.get("metadata") if isinstance(agent_response, dict) else None
            if not isinstance(metadata, dict):
                continue
            candidate_id = self._extract_task_id(metadata)
            if candidate_id and candidate_id == task_id:
                target = message
                target_payload = data
                break

        if not target or not target_payload:
            return

        agent_response = target_payload.get("agent_response") or {}
        metadata = agent_response.get("metadata") or {}
        if not isinstance(metadata, dict):
            return

        merge_execution_metadata(
            metadata,
            task_id=payload.task_id,
            success=payload.success,
            stdout=payload.stdout,
            stderr=payload.stderr,
            artifacts=payload.artifacts or [],
        )
        agent_response["metadata"] = metadata
        target_payload["agent_response"] = agent_response
        target.message = json.dumps(target_payload)
        trans.sa_session.add(target)
        trans.sa_session.commit()

    def _extract_task_id(self, metadata: dict[str, Any]) -> Optional[str]:
        pyodide_task = metadata.get("pyodide_task")
        if isinstance(pyodide_task, dict):
            candidate = pyodide_task.get("task_id")
            if candidate:
                return str(candidate)
        executed_task = metadata.get("executed_task")
        if isinstance(executed_task, dict):
            candidate = executed_task.get("task_id")
            if candidate:
                return str(candidate)
        return None
