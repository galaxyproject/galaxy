"""API endpoints for direct agent access."""

import logging
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
    AgentQueryRequest,
    AgentQueryResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    DependsOnUser,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["agents"])


@router.cbv
class DirectAgentAPI:
    """Direct agent access endpoints. Shares logic with chat through AgentService."""

    agent_service: AgentService = depends(AgentService)
    chat_manager: ChatManager = depends(ChatManager)
    job_manager: JobManager = depends(JobManager)

    @router.post("/api/agents/custom-tool")
    async def create_custom_tool(
        self,
        query: str = Body(..., description="Description of the tool to create"),
        context: Optional[Dict[str, Any]] = Body(None, description="Additional context for tool creation"),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> Dict[str, Any]:
        """Create a custom Galaxy tool. Bypasses router for direct tool creation."""
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

    @router.post("/api/agents/tool-recommendation")
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

    @router.post("/api/agents/error-analysis")
    async def analyze_error(
        self,
        query: str = Body(..., description="Description of the error or problem"),
        job_id: Optional[int] = Body(None, description="Job ID for context"),
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

    @router.post("/api/agents/{agent_type}")
    async def query_agent(
        self,
        agent_type: str,
        request: AgentQueryRequest,
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> AgentQueryResponse:
        """Generic endpoint for querying any registered agent directly."""
        try:
            import time

            start_time = time.time()

            response = await self.agent_service.execute_agent(
                agent_type=agent_type,
                query=request.query,
                trans=trans,
                user=user,
                context=request.context or {},
            )

            processing_time = time.time() - start_time

            # Convert to AgentQueryResponse format
            from galaxy.agents.base import AgentResponse

            agent_response = AgentResponse(
                content=response["content"],
                confidence=response["confidence"],
                agent_type=response["agent_type"],
                suggestions=[],  # Already converted to dicts
                metadata=response.get("metadata", {}),
                reasoning=response.get("reasoning"),
            )

            return AgentQueryResponse(response=agent_response, processing_time=processing_time)

        except Exception as e:
            log.exception(f"Error querying agent {agent_type}: {e}")
            raise ConfigurationError(f"Agent query failed: {str(e)}")
