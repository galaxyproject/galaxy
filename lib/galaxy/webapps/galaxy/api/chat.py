"""
API Controller providing Chat functionality
"""

import json
import logging
import time
from typing import (
    Annotated,
    Any,
    Dict,
    List,
    Optional,
    Union,
)

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
from galaxy.schema.agents import (
    AgentListResponse,
    AgentQueryRequest,
    AgentQueryResponse,
    AgentResponse,
    AvailableAgent,
    ConfidenceLevel,
)
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
    from galaxy.agents import (
        agent_registry,
        BaseGalaxyAgent,
        GalaxyAgentDependencies,
    )
    from galaxy.agents.error_analysis import ErrorAnalysisAgent
    from galaxy.agents.router import QueryRouterAgent

    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False
    agent_registry = None
    GalaxyAgentDependencies = None
    BaseGalaxyAgent = None
    QueryRouterAgent = None
    ErrorAnalysisAgent = None

# Import pydantic-ai components
try:
    from pydantic_ai import Agent
    from pydantic_ai.exceptions import UnexpectedModelBehavior

    HAS_PYDANTIC_AI = True
except ImportError:
    HAS_PYDANTIC_AI = False
    Agent = None
    UnexpectedModelBehavior = Exception

# Keep OpenAI as a fallback option
try:
    import openai
except ImportError:
    openai = None

log = logging.getLogger(__name__)


router = Router(tags=["chat"])

DEFAULT_PROMPT = """
Please only say that something went wrong when configuing the ai prompt in your response.
"""

JobIdQueryParam = Annotated[
    Optional[DecodedDatabaseIdField],
    Field(default=None, title="Job ID", description="The Job ID the chat exchange is linked to."),
]
JobIdPathParam = Annotated[
    DecodedDatabaseIdField,
    Path(title="Job ID", description="The Job ID the chat exchange is linked to."),
]


@router.cbv
class ChatAPI:
    config: GalaxyAppConfiguration = depends(GalaxyAppConfiguration)
    chat_manager: ChatManager = depends(ChatManager)
    job_manager: JobManager = depends(JobManager)
    agent_service: AgentService = depends(AgentService)

    @router.post("/api/chat")
    async def query(
        self,
        job_id: Optional[
            Annotated[
                DecodedDatabaseIdField, Query(title="Job ID", description="The Job ID for backwards compatibility")
            ]
        ] = None,
        payload: Optional[ChatPayload] = None,
        query: Optional[str] = Query(default=None, description="Query string for general chat"),
        agent_type: str = Query(default="auto", description="Agent type to use for the query"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Dict[str, Any]:
        """ChatGXY endpoint - handles both job-based and general chat queries

        Backwards compatible with both formats:
        1. Old format: job_id in query params + payload body with query/context
        2. New format: query and agent_type in query params for general chat

        Returns enhanced response with agent metadata and action suggestions.
        """
        # Initialize response structure
        result = {"response": "", "error_code": 0, "error_message": "", "agent_response": None}

        # Determine query source - either from payload (job-based) or query param (general)
        if payload and payload.query:
            # Old format: payload body with query and context string
            query_text = payload.query
            # Context from payload is a string (e.g., "tool_error"), convert to dict for agent system
            context_str = payload.context if hasattr(payload, "context") else None
            query_context = {"context_type": context_str} if context_str else {}
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
            # Job-based chat - check for existing responses
            job = self.job_manager.get_accessible_job(trans, job_id)
            if job:
                # If there's an existing response for this job, just return that one for now.
                # TODO: Support regenerating the response as a new message, and
                # asking follow-up questions.
                existing_response = self.chat_manager.get(trans, job.id)
                if existing_response and existing_response.messages[0]:
                    return ChatResponse(
                        response=existing_response.messages[0].message,
                        error_code=0,
                        error_message="",
                    )

        # Check if we're continuing an existing conversation (do this ONCE at the beginning)
        exchange_id = None
        if hasattr(payload, "exchange_id") and payload.exchange_id:
            exchange_id = payload.exchange_id

        # Use new agent system if available, otherwise fallback to legacy
        try:
            if HAS_AGENTS and HAS_PYDANTIC_AI:
                # Build context with conversation history
                full_context = query_context.copy() if query_context else {}

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
                result["response"] = agent_response["content"]
                result["agent_response"] = agent_response
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
                exchange = self.chat_manager.create(trans, job.id, result["response"])
                result["exchange_id"] = exchange.id
            elif trans.user:
                # Use the exchange_id we already extracted at the beginning
                if exchange_id:
                    # Add to existing conversation
                    conversation_data = {
                        "query": query_text,
                        "response": result.get("response", ""),
                        "agent_type": agent_type,
                        "agent_response": result.get("agent_response"),
                    }
                    message_content = json.dumps(conversation_data)
                    self.chat_manager.add_message(trans, exchange_id, message_content)
                    result["exchange_id"] = exchange_id
                else:
                    # Create new exchange for first message
                    exchange = self.chat_manager.create_general_chat(trans, query_text, result, agent_type)
                    result["exchange_id"] = exchange.id

        except Exception as e:
            log.error(f"Error getting AI response: {e}")
            result["response"] = f"Sorry, there was an error processing your query. Error: {str(e)}"
            result["error_code"] = 500
            result["error_message"] = str(e)

        # Return the enhanced response structure
        return result

    @router.get("/api/chat/history")
    def get_chat_history(
        self,
        limit: int = Query(default=50, description="Maximum number of chats to return"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> List[Dict[str, Any]]:
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

    @router.delete("/api/chat/history")
    def clear_chat_history(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Dict[str, str]:
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
        except Exception as e:
            trans.sa_session.rollback()
            log.error(f"Error clearing chat history: {e}", exc_info=True)
            return {"message": f"Error clearing history: {str(e)}"}

    @router.put("/api/chat/{job_id}/feedback")
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

    @router.put("/api/chat/exchange/{exchange_id}/feedback")
    def set_exchange_feedback(
        self,
        exchange_id: int,
        feedback: int = Body(..., description="Feedback value: 0 for negative, 1 for positive"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Dict[str, Any]:
        """Set feedback for a general chat exchange."""
        chat_exchange = self.chat_manager.set_feedback_for_exchange(trans, exchange_id, feedback)
        return {"message": "Feedback saved", "feedback": chat_exchange.messages[0].feedback}

    @router.get("/api/chat/exchange/{exchange_id}/messages")
    def get_exchange_messages(
        self,
        exchange_id: int,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> List[Dict[str, Any]]:
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

    def _ensure_ai_configured(self):
        """Ensure AI libraries are available and configured"""
        if HAS_PYDANTIC_AI:
            # Check if OpenAI API key is configured for pydantic-ai
            if self.config.ai_api_key is None:
                raise ConfigurationError("OpenAI API key is not configured for this instance.")
        elif openai is not None:
            # Fall back to direct OpenAI integration
            if self.config.ai_api_key is None:
                raise ConfigurationError("OpenAI API key is not configured for this instance.")
            openai.api_key = self.config.ai_api_key
            if self.config.ai_api_base_url is not None:
                openai.base_url = self.config.ai_api_base_url
        else:
            raise ConfigurationError(
                "Neither pydantic-ai nor OpenAI is installed. Please install one of these packages to use this feature."
            )

    def _get_ai_response(self, query: str, trans: ProvidesUserContext, context_type: Optional[str] = None) -> str:
        """Get response from AI using pydantic-ai Agent or falling back to OpenAI"""
        system_prompt = self._get_system_prompt()
        username = trans.user.username if trans.user else "Anonymous User"

        if HAS_PYDANTIC_AI:
            try:
                # Use pydantic-ai Agent for the response
                model_name = f"openai:{self.config.ai_model}"
                agent = Agent(model_name)

                # Add system prompt and user info
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": f"You will address the user as {username}"},
                    {"role": "user", "content": query},
                ]

                # Get response from the agent
                result = agent.chat(messages)
                return result.content
            except UnexpectedModelBehavior as e:
                log.error(f"Unexpected model behavior: {e}")
                return f"Sorry, there was an unexpected response from the AI model. Error: {str(e)}"
            except Exception as e:
                log.error(f"Error using pydantic-ai Agent: {e}")
                # Try fallback to direct OpenAI if available
                if openai is not None:
                    return self._call_openai_directly(query, system_prompt, username)
                raise
        elif openai is not None:
            # Use direct OpenAI integration as fallback
            return self._call_openai_directly(query, system_prompt, username)
        else:
            raise ConfigurationError("No AI provider available")

    def _call_openai_directly(self, query: str, system_prompt: str, username: str) -> str:
        """Direct OpenAI API call as fallback"""
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": f"You will address the user as {username}"},
                {"role": "user", "content": query},
            ]
            response = openai.chat.completions.create(
                model=self.config.ai_model,
                messages=messages,
            )
            return response.choices[0].message.content
        except openai.APIConnectionError:
            log.exception("OpenAI API Connection Error")
            raise ConfigurationError("An error occurred while connecting to OpenAI.")
        except openai.RateLimitError as e:
            # Rate limit exceeded
            log.exception(f"A 429 status code was received; OpenAI rate limit exceeded.: {e}")
            raise
        except Exception as e:
            log.error(f"Error calling OpenAI: {e}")
            raise ConfigurationError(f"An error occurred while communicating with OpenAI: {str(e)}")

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
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get response using the new agent system (legacy method for compatibility)."""
        result = await self._get_agent_response_full(query, agent_type, trans, user, job, context)
        return result["content"]

    async def _get_agent_response_full(
        self,
        query: str,
        agent_type: str,
        trans: ProvidesUserContext,
        user: User,
        job=None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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

    @router.get("/api/ai/agents")
    def list_agents(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> AgentListResponse:
        """List available AI agents."""
        if not HAS_AGENTS:
            raise ConfigurationError("Agent system is not available")

        agents = []
        for agent_type in agent_registry.list_agents():
            agent_info = agent_registry.get_agent_info(agent_type)

            # Check if agent is enabled in config
            agent_config = getattr(self.config, "agents", {}).get(agent_type, {})
            enabled = agent_config.get("enabled", True)

            agents.append(
                AvailableAgent(
                    agent_type=agent_type,
                    name=agent_info["class_name"].replace("Agent", "").replace("_", " ").title(),
                    description=agent_info.get("description", "No description available"),
                    enabled=enabled,
                    model=agent_config.get("model"),
                    specialties=self._get_agent_specialties(agent_type),
                )
            )

        return AgentListResponse(agents=agents, total_count=len(agents))

    @router.post("/api/ai/query")
    async def query_agent(
        self,
        request: AgentQueryRequest,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> AgentQueryResponse:
        """Query a specific AI agent."""
        if not HAS_AGENTS:
            raise ConfigurationError("Agent system is not available")

        start_time = time.time()

        try:
            # Get full agent response with all metadata and routing info
            result = await self._get_agent_response_full(request.query, request.agent_type, trans, user)

            # Create agent response object using schema version
            agent_response = AgentResponse(
                content=result["content"],
                confidence=result.get("confidence", ConfidenceLevel.MEDIUM),
                agent_type=result.get("agent_type", request.agent_type),
                suggestions=result.get("suggestions", []),
                metadata=result.get("metadata", {}),
                reasoning=result.get("reasoning"),
            )

            processing_time = time.time() - start_time

            return AgentQueryResponse(
                response=agent_response,
                routing_info=result.get("routing_info"),
                processing_time=processing_time,
            )

        except Exception as e:
            log.error(f"Error in agent query: {e}")
            raise ConfigurationError(f"Agent query failed: {str(e)}")

    def _get_agent_specialties(self, agent_type: str) -> list:
        """Get specialties for an agent type."""
        specialties_map = {
            "router": ["Query routing", "Agent selection", "Task classification"],
            "error_analysis": ["Tool errors", "Job failures", "Debugging", "Error diagnosis"],
            "custom_tool": ["Custom tool creation", "Tool wrapper development", "Parameter configuration"],
            "dataset_analyzer": ["Dataset analysis", "Data validation", "Quality assessment", "Preprocessing"],
            "tool_recommendation": ["Tool selection", "Parameter guidance", "Tool discovery"],
        }
        return specialties_map.get(agent_type, [])

    @router.post("/api/ai/tools/recommend")
    async def recommend_tools(
        self,
        query: str,
        input_format: Optional[str] = None,
        output_format: Optional[str] = None,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Dict[str, Any]:
        """Get tool recommendations for a specific task."""
        if not HAS_AGENTS:
            raise ConfigurationError("Agent system is not available")

        # Build context
        context = {}
        if input_format:
            context["input_format"] = input_format
        if output_format:
            context["output_format"] = output_format

        try:
            response = await self.agent_service.execute_agent(
                agent_type="tool_recommendation",
                query=query,
                trans=trans,
                user=user,
                context=context,
            )

            # Return structured response
            return {
                "recommendations": response["content"],
                "confidence": response["confidence"],
                "suggestions": response["suggestions"],
                "metadata": response.get("metadata", {}),
            }
        except Exception as e:
            log.error(f"Tool recommendation failed: {e}")
            raise ConfigurationError(f"Tool recommendation failed: {str(e)}")
