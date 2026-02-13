"""API endpoints for AI agents."""

import logging
import time
from typing import (
    Any,
    Optional,
)

from fastapi import Body

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
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    DependsOnUser,
    Router,
)

# Import agent system
try:
    from galaxy.agents import agent_registry

    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False
    agent_registry = None  # type: ignore[assignment,unused-ignore]

log = logging.getLogger(__name__)

router = Router(tags=["ai"])


@router.cbv
class AgentAPI:
    """AI agent endpoints under /api/ai/agents/.

    **BETA**: This API is experimental and may change without notice.
    """

    agent_service: AgentService = depends(AgentService)
    chat_manager: ChatManager = depends(ChatManager)
    job_manager: JobManager = depends(JobManager)

    @router.get("/api/ai/agents", unstable=True)
    def list_agents(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> AgentListResponse:
        """List available AI agents."""
        if not HAS_AGENTS:
            raise ConfigurationError("Agent system is not available")

        config = trans.app.config

        agents = []
        for agent_type in agent_registry.list_agents():
            agent_info = agent_registry.get_agent_info(agent_type)

            # Check if agent is enabled in config
            agent_config = getattr(config, "agents", {}).get(agent_type, {})
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

    @router.post("/api/ai/agents/query", unstable=True)
    async def query_agent(
        self,
        request: AgentQueryRequest,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> AgentQueryResponse:
        """Query an AI agent. Use agent_type='auto' for automatic routing.

        DEPRECATED: Use /api/chat for new integrations. This endpoint will be
        removed in a future release.
        """
        log.warning("DEPRECATED: /api/ai/agents/query is deprecated. Use /api/chat instead.")

        if not HAS_AGENTS:
            raise ConfigurationError("Agent system is not available")

        start_time = time.time()

        try:
            result = await self.agent_service.route_and_execute(
                query=request.query,
                trans=trans,
                user=user,
                context=request.context or {},
                agent_type=request.agent_type,
            )

            processing_time = time.time() - start_time

            # Extract usage from metadata if available
            usage = None
            if result.metadata:
                # Check for usage fields in metadata
                if "input_tokens" in result.metadata or "output_tokens" in result.metadata:
                    usage = {
                        "input_tokens": result.metadata.get("input_tokens", 0),
                        "output_tokens": result.metadata.get("output_tokens", 0),
                        "total_tokens": result.metadata.get("total_tokens", 0),
                    }

            return AgentQueryResponse(
                response=result,
                processing_time=processing_time,
                usage=usage,
            )

        except Exception as e:
            log.exception(f"Error in agent query: {e}")
            raise ConfigurationError(f"Agent query failed: {str(e)}")

    @router.post("/api/ai/agents/error-analysis", unstable=True)
    async def analyze_error(
        self,
        query: str = Body(..., description="Description of the error or problem"),
        job_id: Optional[DecodedDatabaseIdField] = Body(None, description="Job ID for context"),
        error_details: Optional[dict[str, Any]] = Body(None, description="Additional error details"),
        save_exchange: Optional[bool] = Body(
            None, description="Save exchange for feedback tracking. Defaults to false."
        ),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> AgentResponse:
        """Analyze job errors and provide debugging assistance.

        Set save_exchange=True to enable feedback tracking on the response.
        """
        try:
            # Build context
            context = error_details or {}
            if job_id:
                context["job_id"] = job_id

            response = await self.agent_service.execute_agent(
                agent_type="error_analysis",
                query=query,
                trans=trans,
                user=user,
                context=context,
            )

            # Save chat exchange for feedback tracking if requested or if job_id provided
            if bool(save_exchange) or job_id:
                if job_id:
                    job = self.job_manager.get_accessible_job(trans, job_id)
                    if job:
                        existing = self.chat_manager.get(trans, job.id)
                        if not existing:
                            exchange = self.chat_manager.create(trans, job.id, response.content)
                            response.metadata["exchange_id"] = exchange.id
                elif trans.user:
                    # Create general chat exchange for non-job error analysis
                    result = {"response": response.content, "agent_response": response.model_dump()}
                    exchange = self.chat_manager.create_general_chat(trans, query, result, "error_analysis")
                    response.metadata["exchange_id"] = exchange.id

            return response

        except Exception as e:
            log.exception(f"Error in error analysis: {e}")
            raise ConfigurationError(f"Error analysis failed: {str(e)}")

    @router.post("/api/ai/agents/custom-tool", unstable=True)
    async def create_custom_tool(
        self,
        query: str = Body(..., description="Description of the tool to create"),
        context: Optional[dict[str, Any]] = Body(None, description="Additional context for tool creation"),
        save_exchange: Optional[bool] = Body(
            None, description="Save exchange for feedback tracking. Defaults to false."
        ),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> AgentResponse:
        """Create a custom Galaxy tool.

        Note: Returns AgentResponse with tool_yaml in metadata.
        Set save_exchange=True to enable feedback tracking on the response.
        """
        try:
            response = await self.agent_service.execute_agent(
                agent_type="custom_tool",
                query=query,
                trans=trans,
                user=user,
                context=context or {},
            )

            # Save chat exchange for feedback tracking if requested
            if bool(save_exchange) and trans.user:
                result = {"response": response.content, "agent_response": response.model_dump()}
                exchange = self.chat_manager.create_general_chat(trans, query, result, "custom_tool")
                response.metadata["exchange_id"] = exchange.id

            return response

        except Exception as e:
            log.exception(f"Error in custom tool creation: {e}")
            raise ConfigurationError(f"Custom tool creation failed: {str(e)}")

    def _get_agent_specialties(self, agent_type: str) -> list:
        """Get specialties for an agent type."""
        specialties_map = {
            "router": ["Query routing", "Agent selection", "Task classification"],
            "error_analysis": [
                "Tool errors",
                "Job failures",
                "Debugging",
                "Error diagnosis",
            ],
            "custom_tool": [
                "Custom tool creation",
                "Tool wrapper development",
                "Parameter configuration",
            ],
            "gtn_training": ["Tutorials", "Learning materials", "Training resources"],
        }
        return specialties_map.get(agent_type, [])
