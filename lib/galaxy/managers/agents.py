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
            log.warning(f"Unknown agent type {agent_type}, falling back to router: {e}")
            # Fallback to router for unknown agents - it handles general queries
            router = QueryRouterAgent(deps)
            response = await router.process(query, context)
            metadata = response.metadata.copy()
            metadata["fallback"] = True
            metadata["original_agent_type"] = agent_type
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
        """
        Execute query with automatic routing or specific agent.

        When agent_type is 'auto', the router agent handles the query directly,
        either answering it or using output functions to hand off to specialists.
        """
        if agent_type == "auto":
            # Router handles everything via output functions:
            # - Answers general questions directly
            # - Hands off to error_analysis for debugging
            # - Hands off to custom_tool for tool creation
            log.info(f"Processing query via router: '{query[:100]}...'")
            return await self.execute_agent("router", query, trans, user, context)
        else:
            # Explicit agent request - execute directly
            log.info(f"User explicitly requested agent: {agent_type}")
            return await self.execute_agent(agent_type, query, trans, user, context)
