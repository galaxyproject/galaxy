"""API Controller providing Chat functionality"""

import asyncio
import json
import logging
import mimetypes
import os
from datetime import datetime, timezone
import time
from typing import (
    Annotated,
    Any,
    Optional,
    Union,
)

from fastapi import (
    Body,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from starlette.responses import StreamingResponse

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigurationError
from galaxy.managers.agents import AgentService
from galaxy.managers.collections_util import api_payload_to_create_params
from galaxy.managers.chat import ChatManager
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext
)
from galaxy.managers.jobs import JobManager
from galaxy.model import ChatExchangeMessage, HistoryDatasetAssociation, User
from galaxy.model import User
from galaxy.schema.agents import AgentResponse
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    ChatPayload,
    ChatResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    DependsOnUser,
    Router,
)

# Import agent system
try:
    from galaxy.agents import GalaxyAgentDependencies

    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False
    GalaxyAgentDependencies = None  # type: ignore[assignment,misc,unused-ignore]

# Import pydantic-ai components (required dependency)
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior

# Keep OpenAI as a fallback option
try:
    import openai
except ImportError:
    openai = None  # type: ignore[assignment]

log = logging.getLogger(__name__)


router = Router(tags=["chat"])

DEFAULT_PROMPT = """
Please only say that something went wrong when configuing the ai prompt in your response.
"""

JobIdQueryParam = Annotated[
    Optional[DecodedDatabaseIdField],
    Field(
        default=None,
        title="Job ID",
        description="The Job ID the chat exchange is linked to.",
    ),
]
JobIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(title="Job ID", description="The Job ID the chat exchange is linked to."),
]


class PyodideResultPayload(BaseModel):
    """Payload submitted after client-side Pyodide execution."""

    task_id: Optional[str] = Field(default=None, description="Agent-specified task identifier")
    stdout: str = Field(default="", description="Captured stdout")
    stderr: str = Field(default="", description="Captured stderr")
    artifacts: list[dict[str, Any]] = Field(default_factory=list, description="Artifacts generated during execution")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional execution metadata")
    success: bool = Field(default=True, description="Whether the execution succeeded")


def _guess_extension(filename: Optional[str], mime_type: Optional[str]) -> str:
    """Best-effort guess of an artifact extension based on the provided metadata."""

    if filename and "." in filename:
        candidate = filename.rsplit(".", 1)[1].strip().lower()
        if candidate:
            return candidate
    if mime_type:
        guessed = mimetypes.guess_extension(mime_type)
        if guessed:
            return guessed.lstrip(".")
    return "data"



ACTIVE_EXECUTION_STREAMS: dict[int, set[WebSocket]] = {}
STREAM_LOCK = asyncio.Lock()


async def _register_stream(exchange_id: int, websocket: WebSocket) -> None:
    async with STREAM_LOCK:
        ACTIVE_EXECUTION_STREAMS.setdefault(exchange_id, set()).add(websocket)


async def _remove_stream(exchange_id: int, websocket: WebSocket) -> None:
    async with STREAM_LOCK:
        connections = ACTIVE_EXECUTION_STREAMS.get(exchange_id)
        if connections and websocket in connections:
            connections.remove(websocket)
            if not connections:
                ACTIVE_EXECUTION_STREAMS.pop(exchange_id, None)


async def _broadcast_exec_followup(exchange_id: int, message: dict[str, Any]) -> None:
    async with STREAM_LOCK:
        targets = list(ACTIVE_EXECUTION_STREAMS.get(exchange_id, set()))
    if not targets:
        return
    stale: list[WebSocket] = []
    for ws in targets:
        try:
            await ws.send_json(message)
        except Exception:
            stale.append(ws)
    if stale:
        async with STREAM_LOCK:
            connections = ACTIVE_EXECUTION_STREAMS.get(exchange_id)
            if connections:
                for ws in stale:
                    connections.discard(ws)
                if not connections:
                    ACTIVE_EXECUTION_STREAMS.pop(exchange_id, None)



@router.cbv
class ChatAPI:
    """Chat interface for AI agents.

    **BETA**: This API is experimental and may change without notice.
    """

    config: GalaxyAppConfiguration = depends(GalaxyAppConfiguration)
    chat_manager: ChatManager = depends(ChatManager)
    job_manager: JobManager = depends(JobManager)
    agent_service: AgentService = depends(AgentService)

    @property
    def pyodide_timeout_seconds(self) -> int:
        raw_value = getattr(self.config, "chat_pyodide_timeout_seconds", 600)
        try:
            timeout = int(raw_value)
        except (TypeError, ValueError):
            timeout = 600
        return max(timeout, 0)

    @router.post("/api/chat", unstable=True)
    async def query(
        self,
        job_id: Optional[
            Annotated[
                DecodedDatabaseIdField,
                Query(title="Job ID", description="The Job ID for backwards compatibility"),
            ]
        ] = None,
        payload: Optional[ChatPayload] = None,
        query: Optional[str] = Query(default=None, description="Query string for general chat"),
        agent_type: str = Query(default="auto", description="Agent type to use for the query"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> ChatResponse:
        """ChatGXY endpoint - handles both job-based and general chat queries

        Backwards compatible with both formats:
        1. Old format: job_id in query params + payload body with query/context
        2. New format: query and agent_type in query params for general chat

        Returns enhanced response with agent metadata and action suggestions.
        """
        start_time = time.time()

        # Initialize response structure
        result: dict[str, Any] = {
            "response": "",
            "error_code": 0,
            "error_message": "",
            "agent_response": None,
            "processing_time": None,
        }

        dataset_ids: list[str] = []

        # Determine query source - either from payload (job-based) or query param (general)
        regenerate = False
        if payload and payload.query:
            # Old format: payload body with query and context string
            query_text = payload.query
            # Context from payload is a string (e.g., "tool_error"), convert to dict for agent system
            context_str = payload.context if hasattr(payload, "context") else None
            query_context = {"context_type": context_str} if context_str else {}
            regenerate = bool(payload.regenerate) if hasattr(payload, "regenerate") else False
            raw_dataset_ids = getattr(payload, "dataset_ids", None) or getattr(payload, "selected_dataset_ids", None)
            if raw_dataset_ids:
                dataset_ids = [str(ds_id) for ds_id in raw_dataset_ids or []]
        elif query:
            # New format: query parameters (context not supported in this path)
            query_text = query
            query_context = {}
        else:
            result["error_code"] = 400
            result["error_message"] = "No query provided"
            return ChatResponse(**result)

        job = None
        if job_id:
            # Job-based chat - check for existing responses (unless regenerate requested)
            job = self.job_manager.get_accessible_job(trans, job_id)
            if job and not regenerate:
                existing_response = self.chat_manager.get(trans, job.id)
                if existing_response and existing_response.messages[0]:
                    return ChatResponse(
                        response=existing_response.messages[0].message,
                        error_code=0,
                        error_message="",
                        exchange_id=existing_response.id,
                    )

        # Check if we're continuing an existing conversation (do this ONCE at the beginning)
        exchange_id = None
        if payload is not None and hasattr(payload, "exchange_id") and payload.exchange_id:
            exchange_id = payload.exchange_id

        # Use new agent system if available, otherwise fallback to legacy
        try:
            if HAS_AGENTS:
                log.info("Chat query received agent=%s datasets=%s exchange_id=%s", agent_type, dataset_ids, exchange_id)
                # Build context with conversation history
                full_context: dict[str, Any] = query_context.copy() if query_context else {}
                if dataset_ids:
                    full_context["dataset_ids"] = dataset_ids

                # If we have an exchange_id, ALWAYS load conversation history from database (source of truth)
                if exchange_id:
                    db_history = self.chat_manager.get_chat_history(trans, exchange_id, format_for_pydantic_ai=False)
                    if db_history:
                        full_context["conversation_history"] = db_history
                    else:
                        # No history found for this exchange, start fresh
                        full_context["conversation_history"] = []
                else:
                    # New conversation - no history needed
                    full_context["conversation_history"] = []

                # Get full agent response with metadata
                agent_response = await self._get_agent_response_full(
                    query_text, agent_type, trans, user, job, full_context
                )
                result["response"] = agent_response.content
                result["agent_response"] = agent_response
                result["dataset_ids"] = dataset_ids
            else:
                # Fallback to legacy implementation
                self._ensure_ai_configured()
                # For legacy, use context_type from query_context if it exists
                context_type = query_context.get("context_type") if isinstance(query_context, dict) else None
                answer = self._get_ai_response(query_text, trans, context_type)
                result["response"] = answer

            # Save chat exchange to database
            if job:
                # Job-based chat
                exchange = self.chat_manager.create(trans, job.id, str(result["response"]))
                result["exchange_id"] = exchange.id
            elif trans.user:
                # Use the exchange_id we already extracted at the beginning
                if exchange_id:
                    # Add to existing conversation
                    agent_resp = result.get("agent_response")
                    conversation_data = {
                        "query": query_text,
                        "response": result.get("response", ""),
                        "agent_type": agent_type,
                        "agent_response": agent_resp.model_dump() if agent_resp else None,
                        "dataset_ids": dataset_ids,
                    }
                    message_content = json.dumps(conversation_data)
                    self.chat_manager.add_message(trans, exchange_id, message_content)
                    result["exchange_id"] = exchange_id
                else:
                    # Create new exchange for first message
                    # Serialize agent_response for JSON storage
                    agent_resp = result.get("agent_response")
                    storable_result = {
                        "response": result.get("response", ""),
                        "agent_response": agent_resp.model_dump() if agent_resp else None,
                    }
                    exchange = self.chat_manager.create_general_chat(trans, query_text, storable_result, agent_type)
                    result["exchange_id"] = exchange.id

            result["processing_time"] = time.time() - start_time

        except Exception as e:
            log.error(f"Error getting AI response: {e}")
            result["response"] = "Sorry, there was an error processing your query. Please try again later."
            result["error_code"] = 500
            result["error_message"] = "Internal error"
            result["processing_time"] = time.time() - start_time

        # Return the enhanced response structure
        return ChatResponse(**result)

    @router.get("/api/chat/history", unstable=True)
    def get_chat_history(
        self,
        limit: int = Query(default=50, description="Maximum number of chats to return"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> list[dict[str, Any]]:
        """Get user's chat history."""
        if not user:
            return []

        exchanges = self.chat_manager.get_user_chat_history(trans, limit=limit, include_job_chats=False)

        # Format exchanges for frontend
        history = []

        for exchange in exchanges:
            # For now, still return just the first message of each exchange for compatibility
            # TODO: Eventually return full conversation threads
            if exchange.messages:
                message = exchange.messages[0]  # Get first message
                try:
                    # Parse JSON content
                    data = json.loads(message.message)
                    history.append(
                        {
                            "id": exchange.id,
                            "query": data.get("query", ""),
                            "response": data.get("response", ""),
                            "agent_type": data.get("agent_type", "unknown"),
                            "agent_response": data.get(
                                "agent_response"
                            ),  # Include full agent response with suggestions
                            "timestamp": message.create_time.isoformat() if message.create_time else None,
                            "feedback": message.feedback,
                            "message_count": len(exchange.messages),  # Add count to show it's a conversation
                        }
                    )
                except (json.JSONDecodeError, AttributeError):
                    # Fallback for non-JSON messages (legacy job-based chats)
                    pass

        return history

    @router.delete("/api/chat/history", unstable=True)
    def clear_chat_history(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> dict[str, str]:
        """Clear user's chat history (non-job chats only)."""
        if not user:
            return {"message": "No user logged in"}

        try:
            # Get all non-job chat exchanges for user
            exchanges = self.chat_manager.get_user_chat_history(trans, limit=1000, include_job_chats=False)

            # Delete them and their messages
            count = 0
            message_count = 0
            for exchange in exchanges:
                # First delete all messages associated with this exchange
                for message in exchange.messages:
                    trans.sa_session.delete(message)
                    message_count += 1
                # Then delete the exchange itself
                trans.sa_session.delete(exchange)
                count += 1

            # Force the commit
            trans.sa_session.commit()
            log.info(f"Successfully deleted {count} exchanges with {message_count} messages for user {user.id}")
            return {"message": f"Cleared {count} chat exchanges with {message_count} messages"}
        except Exception:
            trans.sa_session.rollback()
            log.exception("Error clearing chat history")
            return {"message": "Error clearing history"}

    @router.put("/api/chat/{job_id}/feedback", unstable=True)
    def feedback(
        self,
        job_id: JobIdPathParam,
        feedback: int,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Union[int, None]:
        """Provide feedback on the chatbot response."""
        job = self.job_manager.get_accessible_job(trans, job_id)
        chat_response = self.chat_manager.set_feedback_for_job(trans, job.id, feedback)
        return chat_response.messages[0].feedback

    @router.put("/api/chat/exchange/{exchange_id}/feedback", unstable=True)
    def set_exchange_feedback(
        self,
        exchange_id: int,
        feedback: int = Body(..., description="Feedback value: 0 for negative, 1 for positive"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> dict[str, Any]:
        """Set feedback for a general chat exchange."""
        chat_exchange = self.chat_manager.set_feedback_for_exchange(trans, exchange_id, feedback)
        return {
            "message": "Feedback saved",
            "feedback": chat_exchange.messages[0].feedback,
        }

    @router.get("/api/chat/exchange/{exchange_id}/messages", unstable=True)
    def get_exchange_messages(
        self,
        exchange_id: int,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> list[dict[str, Any]]:
        """Get all messages for a specific chat exchange."""
        exchange = self.chat_manager.get_exchange_by_id(trans, exchange_id)
        if not exchange:
            return []

        messages = []

        for msg in exchange.messages:
            try:
                # Parse JSON content to extract individual messages
                data = json.loads(msg.message)
                # Add both user query and assistant response
                if "query" in data:
                    messages.append(
                        {
                            "role": "user",
                            "content": data["query"],
                            "timestamp": msg.create_time.isoformat() if msg.create_time else None,
                            "dataset_ids": data.get("dataset_ids", []),
                        }
                    )
                if "response" in data:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": data["response"],
                            "agent_type": data.get("agent_type", "unknown"),
                            "agent_response": data.get("agent_response"),
                            "timestamp": msg.create_time.isoformat() if msg.create_time else None,
                            "feedback": msg.feedback,
                            "dataset_ids": data.get("dataset_ids", []),
                        }
                    )
                    assistant_payload = messages[-1]
                    agent_response = assistant_payload.get("agent_response")
                    if isinstance(agent_response, dict):
                        metadata = agent_response.get("metadata")
                        if isinstance(metadata, dict):
                            self._expire_stale_pyodide_task(metadata, msg.create_time)
                            self._ensure_pyodide_completion_state(metadata)
                        self._refresh_artifact_download_urls(trans, agent_response)
                elif data.get("role") == "execution_result":
                    messages.append(
                        {
                            "role": "execution_result",
                            "task_id": data.get("task_id"),
                            "stdout": data.get("stdout", ""),
                            "stderr": data.get("stderr", ""),
                            "artifacts": data.get("artifacts", []),
                            "metadata": data.get("metadata", {}),
                            "success": data.get("success", False),
                            "timestamp": msg.create_time.isoformat() if msg.create_time else None,
                        }
                    )
                    self._refresh_artifact_download_urls(trans, messages[-1])
            except (json.JSONDecodeError, AttributeError):
                # Fallback for non-JSON messages
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.message,
                        "timestamp": msg.create_time.isoformat() if msg.create_time else None,
                        "feedback": msg.feedback,
                    }
                )

        return messages

    @router.get("/api/chat/datasets/{dataset_id}/download", response_class=StreamingResponse)
    async def download_dataset_for_execution(
        self,
        dataset_id: str,
        token: str = Query(..., description="Signed dataset download token"),
        trans: ProvidesHistoryContext = DependsOnTrans,
        user: User = DependsOnUser,
    ):
        """Stream a history dataset referenced by a signed execution token."""

        if not token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing download token")

        try:
            self.agent_service.verify_dataset_download_token(trans, dataset_id, token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

        try:
            decoded_id = trans.security.decode_id(dataset_id)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found") from exc

        hda_manager = trans.app.hda_manager
        try:
            hda = hda_manager.get_accessible(decoded_id, user, current_history=trans.history, trans=trans)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dataset is not accessible") from exc

        try:
            hda_manager.ensure_dataset_on_disk(trans, hda)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        dataset = hda.dataset
        file_path = dataset.get_file_name()
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file not found")

        mime_type = hda.get_mime() or "application/octet-stream"
        try:
            display_name = hda.display_name()
        except Exception:
            display_name = hda.name or dataset_id
        safe_name = (display_name or dataset_id).replace('\\', '').replace('"', '')
        headers = {
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Content-Length": str(os.path.getsize(file_path)),
        }

        def iter_file():
            with open(file_path, "rb") as handle:
                while True:
                    chunk = handle.read(65536)
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(iter_file(), media_type=mime_type, headers=headers)

    @router.post("/api/chat/exchange/{exchange_id}/artifacts")
    async def upload_pyodide_artifact(
        self,
        exchange_id: int,
        file: UploadFile = File(...),
        name: Optional[str] = Form(default=None),
        mime_type: Optional[str] = Form(default=None),
        size: Optional[int] = Form(default=None),
        trans: ProvidesHistoryContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> dict[str, Any]:
        """Persist an artifact generated by the Pyodide worker as a history dataset."""

        if not user:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authentication required")

        exchange = self.chat_manager.get_exchange_by_id(trans, exchange_id)
        if not exchange:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat exchange not found")

        history = trans.history
        if history is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active history available")

        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Artifact contains no data")

        artifact_name = name or file.filename or "artifact"
        artifact_mime = mime_type or file.content_type or "application/octet-stream"
        artifact_size = size or len(raw_bytes)

        extension = _guess_extension(artifact_name, artifact_mime)

        hda = HistoryDatasetAssociation(
            history=history,
            name=artifact_name,
            extension=extension,
            create_dataset=True,
            sa_session=trans.sa_session,
        )
        trans.sa_session.add(hda)
        history.add_dataset(hda, set_hid=True)

        permissions = trans.app.security_agent.history_get_default_permissions(history)
        trans.app.security_agent.set_all_dataset_permissions(hda.dataset, permissions, new=True, flush=False)

        dataset = hda.dataset
        try:
            trans.app.object_store.create(dataset)
        except Exception as exc:  # pragma: no cover - object store allocation failure
            trans.sa_session.rollback()
            log.exception("Unable to allocate object store for artifact upload")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        file_path = dataset.get_file_name()
        try:
            with open(file_path, "wb") as handle:
                handle.write(raw_bytes)
        except Exception as exc:
            trans.sa_session.rollback()
            log.exception("Failed writing artifact to object store")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        hda.state = hda.states.OK
        try:
            hda.set_size()
            hda.set_total_size()
        except Exception:
            pass
        try:
            hda.set_meta()
        except Exception:
            pass
        try:
            hda.set_peek()
        except Exception:
            pass

        trans.sa_session.flush()
        trans.sa_session.commit()

        encoded_dataset_id = trans.security.encode_id(hda.id)
        download_url = self.agent_service._dataset_download_url(trans, encoded_dataset_id)

        return {
            "dataset_id": encoded_dataset_id,
            "history_id": trans.security.encode_id(history.id),
            "name": artifact_name,
            "mime_type": artifact_mime,
            "size": artifact_size,
            "download_url": download_url,
        }


    @router.websocket("/api/chat/exchange/{exchange_id}/stream")
    async def chat_exchange_stream(
        self,
        exchange_id: int,
        websocket: WebSocket,
    ) -> None:
        await websocket.accept()
        await _register_stream(exchange_id, websocket)
        try:
            while True:
                try:
                    message = await websocket.receive_text()
                except WebSocketDisconnect:
                    break
                if message and message.lower().startswith("ping"):
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            pass
        finally:
            await _remove_stream(exchange_id, websocket)


    @router.post("/api/chat/exchange/{exchange_id}/pyodide_result")
    async def submit_pyodide_result(
        self,
        exchange_id: int,
        payload: PyodideResultPayload,
        trans: ProvidesHistoryContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> dict[str, Any]:
        """Persist results from client-side Pyodide execution and trigger follow-up reasoning."""

        if not user:
            return {"message": "Authentication required"}

        exchange = self.chat_manager.get_exchange_by_id(trans, exchange_id)
        if not exchange:
            return {"message": "Chat exchange not found"}

        import json

        if payload.artifacts:
            try:
                collection_info = self._create_artifact_collection(
                    trans, payload.artifacts, payload.metadata.get("original_query")
                )
                if collection_info:
                    payload.metadata["artifacts_collection"] = collection_info
            except Exception as exc:  # pragma: no cover - best effort logging
                log.warning("Unable to aggregate artifacts into collection: %s", exc)

        execution_message = json.dumps(
            {
                "role": "execution_result",
                "task_id": payload.task_id,
                "stdout": payload.stdout,
                "stderr": payload.stderr,
                "artifacts": payload.artifacts,
                "metadata": payload.metadata,
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

        raw_dataset_ids = payload.metadata.get("selected_dataset_ids") if payload.metadata else None
        if isinstance(raw_dataset_ids, list):
            dataset_ids = [str(ds_id) for ds_id in raw_dataset_ids]
        else:
            dataset_ids = []

        agent_type = payload.metadata.get("agent_type") if payload.metadata else None
        original_query = payload.metadata.get("original_query") if payload.metadata else None

        refreshed_exchange = self.chat_manager.get_exchange_by_id(trans, exchange_id)
        if refreshed_exchange:
            for message in refreshed_exchange.messages:
                try:
                    data = json.loads(message.message)
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

        followup_response: Optional[dict[str, Any]] = None
        agent_type_to_use = agent_type or "auto"

        try:
            followup_response = await self._get_agent_response_full(
                query_text,
                agent_type_to_use,
                trans,
                user,
                job=None,
                context=context,
            )
        except Exception as exc:
            log.error(
                "Failed to generate follow-up after Pyodide execution for exchange %s: %s",
                exchange_id,
                exc,
                exc_info=True,
            )
            return {"message": "Execution result stored", "error": str(exc)}

        response_agent_type = followup_response.get("agent_type", agent_type_to_use)

        followup_message = json.dumps(
            {
                "response": followup_response.get("content", ""),
                "agent_type": response_agent_type,
                "agent_response": followup_response,
                "dataset_ids": dataset_ids,
            }
        )
        self.chat_manager.add_message(trans, exchange_id, followup_message)

        log.info(
            "Stored Pyodide execution result and generated follow-up for exchange %s (task_id=%s, success=%s)",
            exchange_id,
            payload.task_id,
            payload.success,
        )

        response_payload = {
            "message": "Execution result stored",
            "response": followup_response.get("content", ""),
            "agent_response": followup_response,
            "dataset_ids": dataset_ids,
            "exchange_id": exchange_id,
            "task_id": payload.task_id,
        }

        await _broadcast_exec_followup(
            exchange_id,
            {
                "type": "exec_followup",
                "exchange_id": exchange_id,
                "task_id": payload.task_id,
                "payload": response_payload,
            },
        )

        return response_payload

    def _create_artifact_collection(
        self,
        trans: ProvidesHistoryContext,
        artifacts: list[dict[str, Any]],
        query_text: Optional[str],
    ) -> Optional[dict[str, Any]]:
        history = trans.history
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

    def _refresh_artifact_download_urls(self, trans: ProvidesUserContext, payload: Any) -> Any:
        if isinstance(payload, dict):
            for key, value in list(payload.items()):
                if key == "artifacts" and isinstance(value, list):
                    payload[key] = [self._refresh_single_artifact_entry(trans, entry) for entry in value]
                else:
                    self._refresh_artifact_download_urls(trans, value)
        elif isinstance(payload, list):
            for item in payload:
                self._refresh_artifact_download_urls(trans, item)
        return payload

    def _refresh_single_artifact_entry(self, trans: ProvidesUserContext, artifact: Any) -> Any:
        if not isinstance(artifact, dict):
            return artifact
        entry = dict(artifact)
        dataset_id = entry.get("dataset_id")
        if dataset_id:
            try:
                entry["download_url"] = self.agent_service._dataset_download_url(trans, dataset_id)
            except Exception:  # pragma: no cover - best effort
                log.warning("Unable to refresh download URL for dataset %s", dataset_id)
        return entry

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

        target: Optional[ChatExchangeMessage] = None
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

        self._merge_execution_metadata(metadata, payload)
        agent_response["metadata"] = metadata
        target_payload["agent_response"] = agent_response
        target.message = json.dumps(target_payload)
        trans.sa_session.add(target)
        trans.sa_session.commit()

    def _extract_task_id(self, metadata: dict[str, Any]) -> Optional[str]:
        if not isinstance(metadata, dict):
            return None
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

    def _merge_execution_metadata(self, metadata: dict[str, Any], payload: PyodideResultPayload) -> None:
        metadata["pyodide_status"] = "completed" if payload.success else "error"
        metadata["stdout"] = payload.stdout or ""
        metadata["stderr"] = payload.stderr or ""
        metadata["execution"] = {
            "success": payload.success,
            "stdout": payload.stdout or "",
            "stderr": payload.stderr or "",
            "artifacts": payload.artifacts or [],
            "task_id": payload.task_id,
        }

        executed_task: dict[str, Any] = {}
        if isinstance(metadata.get("executed_task"), dict):
            executed_task.update(metadata.get("executed_task") or {})
        pyodide_task = metadata.get("pyodide_task")
        if isinstance(pyodide_task, dict):
            executed_task.setdefault("code", pyodide_task.get("code"))
            executed_task.setdefault("requirements", pyodide_task.get("packages"))
            executed_task.setdefault("datasets", pyodide_task.get("files"))
            executed_task.setdefault("alias_map", pyodide_task.get("alias_map"))
        if executed_task:
            executed_task["task_id"] = payload.task_id
            metadata["executed_task"] = executed_task
        metadata.pop("pyodide_task", None)

        if payload.artifacts:
            metadata["artifacts"] = payload.artifacts

    def _expire_stale_pyodide_task(self, metadata: dict[str, Any], created_at: Optional[datetime]) -> None:
        timeout = self.pyodide_timeout_seconds
        if timeout <= 0:
            return
        if not metadata or not isinstance(metadata, dict):
            return
        if "pyodide_task" not in metadata:
            return
        status = metadata.get("pyodide_status") or "pending"
        if status not in (None, "pending"):
            return
        reference = metadata.get("pyodide_started_at")
        started_at = self._parse_iso_datetime(reference) if isinstance(reference, str) else None
        if started_at is None and isinstance(created_at, datetime):
            started_at = created_at
        if started_at is None:
            return
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        if (now - started_at).total_seconds() < timeout:
            return
        metadata["pyodide_status"] = "timeout"
        metadata["pyodide_timeout_reason"] = (
            metadata.get("pyodide_timeout_reason") or "Timed out waiting for the browser execution result."
        )
        metadata["pyodide_timeout_seconds"] = timeout
        metadata.pop("pyodide_task", None)

    def _parse_iso_datetime(self, value: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _ensure_pyodide_completion_state(self, metadata: dict[str, Any]) -> None:
        if not isinstance(metadata, dict):
            return
        status = metadata.get("pyodide_status")
        if status in ("completed", "error", "timeout"):
            return
        execution = metadata.get("execution")
        if isinstance(execution, dict):
            success = bool(execution.get("success", False))
            metadata["pyodide_status"] = "completed" if success else "error"
            metadata.pop("pyodide_task", None)
            return
        if metadata.get("artifacts") and not metadata.get("pyodide_task"):
            metadata["pyodide_status"] = "completed"

    def _ensure_ai_configured(self):
        """Ensure AI is configured"""
        if self.config.ai_api_key is None:
            raise ConfigurationError("AI API key is not configured for this instance.")

    def _get_ai_response(self, query: str, trans: ProvidesUserContext, context_type: Optional[str] = None) -> str:
        """Get response from AI using pydantic-ai Agent"""
        system_prompt = self._get_system_prompt()
        username = trans.user.username if trans.user else "Anonymous User"

        try:
            # Use pydantic-ai Agent for the response
            model_name = f"openai:{self.config.ai_model}"
            full_system_prompt = f"{system_prompt}\n\nYou will address the user as {username}"
            agent: Agent[None, str] = Agent(model_name, system_prompt=full_system_prompt)

            # Get response from the agent
            result = agent.run_sync(query)
            return result.output
        except UnexpectedModelBehavior as e:
            log.error(f"Unexpected model behavior: {e}")
            return "Sorry, there was an unexpected response from the AI model. Please try again."
        except Exception as e:
            log.error(f"Error using pydantic-ai Agent: {e}")
            # Try fallback to direct OpenAI if available
            if openai is not None:
                return self._call_openai_directly(query, system_prompt, username)
            raise

    def _call_openai_directly(self, query: str, system_prompt: str, username: str) -> str:
        """Direct OpenAI API call as fallback"""
        try:
            messages: list[dict[str, str]] = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "system",
                    "content": f"You will address the user as {username}",
                },
                {"role": "user", "content": query},
            ]
            response = openai.chat.completions.create(
                model=self.config.ai_model,
                messages=messages,  # type: ignore[arg-type]
            )
            return response.choices[0].message.content or ""
        except openai.APIConnectionError:
            log.exception("OpenAI API Connection Error")
            raise ConfigurationError("An error occurred while connecting to OpenAI.")
        except openai.RateLimitError as e:
            # Rate limit exceeded
            log.exception(f"A 429 status code was received; OpenAI rate limit exceeded.: {e}")
            raise
        except Exception as e:
            log.error(f"Error calling OpenAI: {e}")
            raise ConfigurationError("An error occurred while communicating with the AI service.")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the AI"""
        return self.config.chat_prompts.get("tool_error", DEFAULT_PROMPT)

    async def _get_agent_response(
        self,
        query: str,
        agent_type: str,
        trans: ProvidesUserContext,
        user: User,
        job=None,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Get response using the new agent system (legacy method for compatibility)."""
        result = await self._get_agent_response_full(query, agent_type, trans, user, job, context)
        return result.content

    async def _get_agent_response_full(
        self,
        query: str,
        agent_type: str,
        trans: ProvidesHistoryContext,
        user: User,
        job=None,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Get full agent response with metadata and suggestions."""
        # Prepare context - merge passed context with job context
        if context is None:
            context = {}
        if job:
            context["job_id"] = job.id
            context["tool_id"] = job.tool_id
            context["state"] = job.state

        # Use agent service for routing and execution
        return await self.agent_service.route_and_execute(
            query=query,
            trans=trans,
            user=user,
            context=context,
            agent_type=agent_type,
        )
