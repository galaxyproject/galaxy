"""Agent service layer for AI agent management."""

import logging
from typing import (
    Any,
    Optional,
)

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigurationError
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.jobs import JobManager
from galaxy.model import User
from galaxy.schema.agents import AgentResponse

# Import agent system (pydantic_ai is optional)
try:
    from galaxy.agents import (
        agent_registry,
        GalaxyAgentDependencies,
    )
    from galaxy.agents.error_analysis import ErrorAnalysisAgent
    from galaxy.agents.router import QueryRouterAgent

    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False
    agent_registry = None  # type: ignore[assignment,misc,unused-ignore]
    GalaxyAgentDependencies = None  # type: ignore[assignment,misc,unused-ignore]
    QueryRouterAgent = None  # type: ignore[assignment,misc,unused-ignore]
    ErrorAnalysisAgent = None  # type: ignore[assignment,misc,unused-ignore]

log = logging.getLogger(__name__)


class AgentService:
    """Service layer for AI agent execution and routing."""

    def __init__(
        self,
        config: GalaxyAppConfiguration,
        job_manager: JobManager,
    ):
        if not HAS_AGENTS:
            raise ConfigurationError("Agent system is not available")

        self.config = config
        self.job_manager = job_manager

    def create_dependencies(self, trans: ProvidesUserContext, user: User) -> GalaxyAgentDependencies:
        """Create agent dependencies for dependency injection."""
        toolbox = trans.app.toolbox if hasattr(trans, "app") and hasattr(trans.app, "toolbox") else None
        return GalaxyAgentDependencies(
            trans=trans,
            user=user,
            config=self.config,
            job_manager=self.job_manager,
            toolbox=toolbox,
            get_agent=agent_registry.get_agent,
        )

    async def execute_agent(
        self,
        agent_type: str,
        query: str,
        trans: ProvidesUserContext,
        user: User,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentResponse:
        """Execute a specific agent and return response."""
        deps = self.create_dependencies(trans, user)

        if context is None:
            context = {}

        try:
            log.info(f"Executing {agent_type} agent for query: '{query[:100]}...'")
            agent = agent_registry.get_agent(agent_type, deps)
            response = await agent.process(query, context)

            return AgentResponse(
                content=response.content,
                agent_type=response.agent_type,
                confidence=response.confidence,
                suggestions=response.suggestions,
                metadata=response.metadata,
                reasoning=response.reasoning,
            )
        except ValueError as e:
            log.warning(f"Unknown agent type {agent_type}, falling back to error_analysis: {e}")
            # Fallback to error analysis for unknown agents
            agent = ErrorAnalysisAgent(deps)
            response = await agent.process(query, context)
            metadata = response.metadata.copy()
            metadata["fallback"] = True
            return AgentResponse(
                content=response.content,
                agent_type=response.agent_type,
                confidence=response.confidence,
                suggestions=response.suggestions,
                metadata=metadata,
                reasoning=response.reasoning,
            )
        except OSError as e:
            log.error(f"Network error executing agent {agent_type}: {e}")
            raise
        except RuntimeError as e:
            log.exception(f"Runtime error executing agent {agent_type}: {e}")
            raise

    async def route_and_execute(
        self,
        query: str,
        trans: ProvidesUserContext,
        user: User,
        context: Optional[dict[str, Any]] = None,
        agent_type: str = "auto",
    ) -> AgentResponse:
        """Route query to appropriate agent and execute. Uses router if agent_type is 'auto'."""
        deps = self.create_dependencies(trans, user)

        if context is None:
            context = {}

        # Inject visualization context if not already present
        if "visualizations" not in context:
            from galaxy.agents.visualization_context import get_visualization_summaries

            context["visualizations"] = get_visualization_summaries(trans)

        # Route to appropriate agent
        actual_agent_type = agent_type
        routing_reasoning = None

        if agent_type == "auto":
            # Use router agent to determine best agent
            log.info(f"Router: Analyzing query for intent classification: '{query[:100]}...'")
            router = QueryRouterAgent(deps)
            routing_decision = await router.route_query(query, context)

            if routing_decision.direct_response:
                log.info("Router: Handling with direct response (no agent needed)")
                return AgentResponse(
                    content=routing_decision.direct_response,
                    agent_type="router",
                    confidence=routing_decision.confidence,
                    suggestions=[],
                    metadata={"handled_directly": True},
                )

            # Use the primary agent recommended by router
            actual_agent_type = routing_decision.primary_agent
            routing_reasoning = routing_decision.reasoning
            log.info(f"Router: Selected agent '{actual_agent_type}' - Reason: {routing_reasoning}")
            if routing_decision.secondary_agents:
                log.info(f"Router: Secondary agents that could help: {routing_decision.secondary_agents}")
        else:
            log.info(f"User explicitly requested agent: {actual_agent_type}")

        # Execute the agent
        result = await self.execute_agent(actual_agent_type, query, trans, user, context)

        # Add routing information if we used the router
        if routing_reasoning:
            result.metadata["routing_info"] = {
                "selected_agent": actual_agent_type,
                "reasoning": routing_reasoning,
            }

        return result
