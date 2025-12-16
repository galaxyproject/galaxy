"""API endpoints for AI agents."""

import logging
import time
from typing import (
    Any,
    Dict,
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
    ConfidenceLevel,
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
    agent_registry = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

router = Router(tags=["ai"])


@router.cbv
class AgentAPI:
    """AI agent endpoints under /api/ai/agents/."""

    agent_service: AgentService = depends(AgentService)
    chat_manager: ChatManager = depends(ChatManager)
    job_manager: JobManager = depends(JobManager)

    @router.get("/api/ai/agents")
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

    @router.post("/api/ai/agents/query")
    async def query_agent(
        self,
        request: AgentQueryRequest,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> AgentQueryResponse:
        """Query an AI agent. Use agent_type='auto' for automatic routing."""
        if not HAS_AGENTS:
            raise ConfigurationError("Agent system is not available")

        start_time = time.time()

        try:
            # Get full agent response with all metadata and routing info
            result = await self.agent_service.route_and_execute(
                query=request.query,
                trans=trans,
                user=user,
                context=request.context or {},
                agent_type=request.agent_type,
            )

            # Create agent response object
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
            log.exception(f"Error in agent query: {e}")
            raise ConfigurationError(f"Agent query failed: {str(e)}")

    @router.post("/api/ai/agents/error-analysis")
    async def analyze_error(
        self,
        query: str = Body(..., description="Description of the error or problem"),
        job_id: Optional[DecodedDatabaseIdField] = Body(None, description="Job ID for context"),
        error_details: Optional[Dict[str, Any]] = Body(None, description="Additional error details"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Dict[str, Any]:
        """Analyze job errors and provide debugging assistance."""
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

            # Save chat exchange for job-based error analysis (enables feedback)
            if job_id:
                job = self.job_manager.get_accessible_job(trans, job_id)
                if job:
                    # Check if exchange already exists
                    existing = self.chat_manager.get(trans, job.id)
                    if not existing:
                        # Create new exchange for feedback tracking
                        exchange = self.chat_manager.create(trans, job.id, response["content"])
                        response["exchange_id"] = exchange.id

            return response

        except Exception as e:
            log.exception(f"Error in error analysis: {e}")
            raise ConfigurationError(f"Error analysis failed: {str(e)}")

    @router.post("/api/ai/agents/tool-recommendation")
    async def recommend_tools(
        self,
        query: str = Body(..., description="Description of the analysis task"),
        input_format: Optional[str] = Body(None, description="Input data format"),
        output_format: Optional[str] = Body(None, description="Desired output format"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Dict[str, Any]:
        """Get tool recommendations for a specific analysis task."""
        try:
            # Build context
            context = {}
            if input_format:
                context["input_format"] = input_format
            if output_format:
                context["output_format"] = output_format

            response = await self.agent_service.execute_agent(
                agent_type="tool_recommendation",
                query=query,
                trans=trans,
                user=user,
                context=context,
            )

            return response

        except Exception as e:
            log.exception(f"Error in tool recommendation: {e}")
            raise ConfigurationError(f"Tool recommendation failed: {str(e)}")

    @router.post("/api/ai/agents/custom-tool")
    async def create_custom_tool(
        self,
        query: str = Body(..., description="Description of the tool to create"),
        context: Optional[Dict[str, Any]] = Body(None, description="Additional context for tool creation"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Dict[str, Any]:
        """Create a custom Galaxy tool."""
        try:
            response = await self.agent_service.execute_agent(
                agent_type="custom_tool",
                query=query,
                trans=trans,
                user=user,
                context=context or {},
            )

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
            "tool_recommendation": [
                "Tool selection",
                "Parameter guidance",
                "Tool discovery",
            ],
            "gtn_training": ["Tutorials", "Learning materials", "Training resources"],
        }
        return specialties_map.get(agent_type, [])
