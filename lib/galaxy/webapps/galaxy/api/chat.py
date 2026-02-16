"""
API Controller providing Chat functionality
"""

import json
import logging
import time
from functools import partial
from typing import (
    Annotated,
    Any,
    Optional,
    Union,
)

import anyio
from fastapi import (
    Body,
    Path,
    Query,
)
from pydantic import Field

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigurationError
from galaxy.managers.agents import AgentService
from galaxy.managers.chat import ChatManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.jobs import JobManager
from galaxy.model import User
from galaxy.schema.agents import AgentResponse
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    ChatExchangeBatchDeletePayload,
    ChatHistoryItemResponse,
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
    from openai import AsyncOpenAI
except ImportError:
    openai = None  # type: ignore[assignment]
    AsyncOpenAI = None  # type: ignore[assignment,misc]

log = logging.getLogger(__name__)


router = Router(tags=["chat"])

DEFAULT_PROMPT = """
Please only say that something went wrong when configuring the ai prompt in your response.
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


@router.cbv
class ChatAPI:
    """Chat interface for AI agents.

    **BETA**: This API is experimental and may change without notice.
    """

    config: GalaxyAppConfiguration = depends(GalaxyAppConfiguration)
    chat_manager: ChatManager = depends(ChatManager)
    job_manager: JobManager = depends(JobManager)
    agent_service: AgentService = depends(AgentService)

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

        # Determine query source - either from payload (job-based) or query param (general)
        regenerate = False
        if payload and payload.query:
            # Old format: payload body with query and context string
            query_text = payload.query
            # Context from payload is a string (e.g., "tool_error"), convert to dict for agent system
            context_str = payload.context if hasattr(payload, "context") else None
            query_context = {"context_type": context_str} if context_str else {}
            regenerate = bool(payload.regenerate) if hasattr(payload, "regenerate") else False
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
            job = await anyio.to_thread.run_sync(partial(self.job_manager.get_accessible_job, trans, job_id))
            if job and not regenerate:
                existing_response = await anyio.to_thread.run_sync(partial(self.chat_manager.get, trans, job.id))
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

        # Check for page scope and populate agent context
        page_id = None
        page_obj = None
        if payload is not None and hasattr(payload, "page_id") and payload.page_id:
            page_id = payload.page_id
            # Access-check outside the try below so 403s propagate instead of
            # being masked as 500.
            page_obj = self.chat_manager.get_accessible_page(trans, page_id)

        # Use new agent system if available, otherwise fallback to legacy
        try:
            if HAS_AGENTS:
                # Build context with conversation history
                full_context: dict[str, Any] = query_context.copy() if query_context else {}

                # If page-scoped, look up history_id + content for agent.
                # Content is exported (IDs encoded) so the agent sees the same
                # text the editor has — hashes and proposals match the client.
                if page_id:
                    if page_obj:
                        full_context["history_id"] = page_obj.history_id
                        # Fallback to session history for standalone pages
                        if not full_context.get("history_id"):
                            session_history = getattr(trans, "history", None)
                            if session_history:
                                full_context["history_id"] = session_history.id
                                full_context["history_is_session"] = True
                        if page_obj.latest_revision_id:
                            from galaxy.managers.markdown_util import ready_galaxy_markdown_for_export

                            rev = page_obj.latest_revision
                            if rev and rev.content:
                                exported, _, _ = ready_galaxy_markdown_for_export(trans, rev.content)
                                full_context["page_content"] = exported
                            else:
                                full_context["page_content"] = ""
                        else:
                            full_context["page_content"] = ""

                # If we have an exchange_id, ALWAYS load conversation history from database (source of truth)
                if exchange_id:
                    db_history = await anyio.to_thread.run_sync(
                        partial(self.chat_manager.get_chat_history, trans, exchange_id, format_for_pydantic_ai=False)
                    )
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
            else:
                # Fallback to legacy implementation
                self._ensure_ai_configured()
                # For legacy, use context_type from query_context if it exists
                context_type = query_context.get("context_type") if isinstance(query_context, dict) else None
                answer = await self._get_ai_response(query_text, trans, context_type)
                result["response"] = answer

            # Save chat exchange to database
            if job:
                # Job-based chat
                exchange = await anyio.to_thread.run_sync(
                    partial(self.chat_manager.create, trans, job.id, str(result["response"]))
                )
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
                    }
                    message_content = json.dumps(conversation_data)
                    await anyio.to_thread.run_sync(
                        partial(self.chat_manager.add_message, trans, exchange_id, message_content)
                    )
                    result["exchange_id"] = exchange_id
                elif page_id:
                    # Page-scoped chat
                    agent_resp = result.get("agent_response")
                    storable_result = {
                        "response": result.get("response", ""),
                        "agent_response": agent_resp.model_dump() if agent_resp else None,
                    }
                    exchange = self.chat_manager.create_page_chat(
                        trans, page_id, query_text, storable_result, agent_type
                    )
                    result["exchange_id"] = exchange.id
                else:
                    # Create new exchange for first message
                    # Serialize agent_response for JSON storage
                    agent_resp = result.get("agent_response")
                    storable_result = {
                        "response": result.get("response", ""),
                        "agent_response": agent_resp.model_dump() if agent_resp else None,
                    }
                    exchange = await anyio.to_thread.run_sync(
                        partial(self.chat_manager.create_general_chat, trans, query_text, storable_result, agent_type)
                    )
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
    ) -> list[ChatHistoryItemResponse]:
        """Get user's chat history."""
        exchanges = self.chat_manager.get_user_chat_history(trans, limit=limit, include_job_chats=False)
        return self._format_exchange_history(exchanges)

    @router.get("/api/chat/page/{page_id}/history", unstable=True)
    def get_page_chat_history(
        self,
        page_id: DecodedDatabaseIdField,
        limit: int = Query(default=50, description="Maximum number of chats to return"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> list[ChatHistoryItemResponse]:
        """Get chat history scoped to a page."""
        if not user:
            return []

        exchanges = self.chat_manager.get_page_chat_history(trans, page_id, limit=limit)
        return self._format_exchange_history(exchanges)

    @router.delete("/api/chat/history", unstable=True)
    def clear_chat_history(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> dict[str, str]:
        """Clear user's chat history (non-job chats only)."""
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

    @router.delete("/api/chat/exchange/{exchange_id}", unstable=True)
    def delete_exchange(
        self,
        exchange_id: DecodedDatabaseIdField,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> dict[str, str]:
        """Delete a single chat exchange."""
        self.chat_manager.delete_exchange(trans, exchange_id)
        return {"message": "Deleted"}

    @router.put("/api/chat/exchanges/batch/delete", unstable=True)
    def batch_delete_exchanges(
        self,
        payload: ChatExchangeBatchDeletePayload,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> dict[str, str]:
        """Delete multiple chat exchanges."""
        count = self.chat_manager.delete_exchanges(trans, payload.ids)
        return {"message": f"Deleted {count} exchanges"}

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
        exchange_id: DecodedDatabaseIdField,
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
        exchange_id: DecodedDatabaseIdField,
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
                        }
                    )
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

    def _format_exchange_history(self, exchanges) -> list[ChatHistoryItemResponse]:
        """Convert a list of ChatExchange ORM objects into API response models."""
        history: list[ChatHistoryItemResponse] = []
        for exchange in exchanges:
            if not exchange.messages:
                continue
            message = exchange.messages[0]
            try:
                data = json.loads(message.message)
                agent_response_raw = data.get("agent_response")
                agent_response = AgentResponse(**agent_response_raw) if agent_response_raw else None
                history.append(
                    ChatHistoryItemResponse(
                        id=exchange.id,
                        query=data.get("query", ""),
                        response=data.get("response", ""),
                        agent_type=data.get("agent_type", "unknown"),
                        agent_response=agent_response,
                        timestamp=message.create_time.isoformat() if message.create_time else None,
                        feedback=message.feedback,
                        message_count=len(exchange.messages),
                    )
                )
            except (json.JSONDecodeError, AttributeError):
                log.debug("Skipping malformed chat exchange %s", exchange.id)
        return history

    def _ensure_ai_configured(self):
        """Ensure AI is configured"""
        if self.config.ai_api_key is None:
            raise ConfigurationError("AI API key is not configured for this instance.")

    async def _get_ai_response(self, query: str, trans: ProvidesUserContext, context_type: Optional[str] = None) -> str:
        """Get response from AI using pydantic-ai Agent"""
        system_prompt = self._get_system_prompt()
        username = trans.user.username if trans.user else "Anonymous User"

        try:
            # Use pydantic-ai Agent for the response
            model_name = f"openai:{self.config.ai_model}"
            full_system_prompt = f"{system_prompt}\n\nYou will address the user as {username}"
            agent: Agent[None, str] = Agent(model_name, system_prompt=full_system_prompt)

            # Get response from the agent (async)
            result = await agent.run(query)
            return result.output
        except UnexpectedModelBehavior as e:
            log.error(f"Unexpected model behavior: {e}")
            return "Sorry, there was an unexpected response from the AI model. Please try again."
        except Exception as e:
            log.error(f"Error using pydantic-ai Agent: {e}")
            # Try fallback to direct OpenAI if available
            if openai is not None:
                return await self._call_openai_directly(query, system_prompt, username)
            raise

    async def _call_openai_directly(self, query: str, system_prompt: str, username: str) -> str:
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
            client = AsyncOpenAI()
            response = await client.chat.completions.create(
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
        trans: ProvidesUserContext,
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
