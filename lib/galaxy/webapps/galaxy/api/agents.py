"""API endpoints for AI agents."""

import logging
import time
from functools import partial
from typing import (
    Any,
    Optional,
)

import anyio
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
        config = trans.app.config
        inference_config = getattr(config, "inference_services", {}) or {}

        agents = []
        for agent_type in self.agent_service.list_agents():
            agent_info = self.agent_service.get_agent_info(agent_type)
            agent_config = inference_config.get(agent_type, {})

            # Resolve model: agent-specific -> default -> global
            model = None
            if isinstance(agent_config, dict):
                model = agent_config.get("model")
            if model is None:
                default_config = inference_config.get("default", {})
                if isinstance(default_config, dict):
                    model = default_config.get("model")
            if model is None:
                model = getattr(config, "ai_model", None)

            agents.append(
                AvailableAgent(
                    agent_type=agent_type,
                    name=agent_info["class_name"].replace("Agent", "").replace("_", " ").title(),
                    description=agent_info.get("description", "No description available"),
                    enabled=True,
                    model=model,
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

            return AgentQueryResponse(
                response=result,
                processing_time=processing_time,
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
                    job = await anyio.to_thread.run_sync(partial(self.job_manager.get_accessible_job, trans, job_id))
                    if job:
                        existing = await anyio.to_thread.run_sync(partial(self.chat_manager.get, trans, job.id))
                        if not existing:
                            exchange = await anyio.to_thread.run_sync(
                                partial(self.chat_manager.create, trans, job.id, response.content)
                            )
                            response.metadata["exchange_id"] = exchange.id
                elif trans.user:
                    # Create general chat exchange for non-job error analysis
                    result = {"response": response.content, "agent_response": response.model_dump()}
                    exchange = await anyio.to_thread.run_sync(
                        partial(self.chat_manager.create_general_chat, trans, query, result, "error_analysis")
                    )
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
                exchange = await anyio.to_thread.run_sync(
                    partial(self.chat_manager.create_general_chat, trans, query, result, "custom_tool")
                )
                response.metadata["exchange_id"] = exchange.id

            return response

        except Exception as e:
            log.exception(f"Error in custom tool creation: {e}")
            raise ConfigurationError(f"Custom tool creation failed: {str(e)}")

    @router.post("/api/ai/agents/history-summary", unstable=True)
    async def history_summary(
        self,
        history_id: str = Body(..., embed=True, description="Encoded id of the history to summarize."),
        trans: ProvidesUserContext = DependsOnTrans,
        user: User = DependsOnUser,
    ) -> AgentResponse:
        """Produce a comprehensive markdown report for a history's analysis.

        The history agent fetches the full lineage via ``get_history_graph``
        and synthesizes a multi-section report (Summary, Data Inputs,
        Analysis Pipeline, Tools and Parameters, Outputs, Notes). Suitable
        for inclusion in a history notebook or methods section.
        """
        query = (
            f"Generate a comprehensive analysis report for Galaxy history {history_id}.\n\n"
            f"Call get_history_graph(history_id='{history_id}') with no seed for the "
            "full history overview. If the response's truncated.item_count_capped is "
            "true, note that in the Notes section.\n\n"
            "Produce a markdown report with these sections (use ## headings):\n\n"
            "## Summary\n"
            "Two or three sentences: what kind of analysis, key inputs/outputs, key tools.\n\n"
            "## Data Inputs\n"
            "List input files and collections with their formats.\n\n"
            "## Analysis Pipeline\n"
            "Narrative description of the processing steps in past tense, scientific style.\n\n"
            "## Tools and Parameters\n"
            "For each tool: name, version when known, what it does in this workflow, "
            "and any key parameters or settings.\n\n"
            "## Outputs\n"
            "Final output files and collections with formats.\n\n"
            "## Notes\n"
            "Observations: caveats, truncation, anything notable. Omit if nothing to add.\n\n"
            "Style rules:\n"
            "- Past tense, third person, scientific.\n"
            "- Include tool versions only when available; omit placeholder text otherwise.\n"
            "- Exclude internal Galaxy tools (__DATA_FETCH__, __SET_METADATA__, etc.).\n"
            "- Do not hallucinate tool names, parameters, or versions."
        )
        try:
            return await self.agent_service.execute_agent(
                agent_type="history",
                query=query,
                trans=trans,
                user=user,
                context={"history_id": history_id},
            )
        except Exception as e:
            log.exception(f"Error in history summary: {e}")
            raise ConfigurationError(f"History summary failed: {str(e)}")

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
            "history": ["History summaries", "Analysis interpretation", "Next-step guidance"],
            "tool_recommendation": ["Tool discovery", "Available tools", "Workflow suggestions"],
        }
        return specialties_map.get(agent_type, [])
