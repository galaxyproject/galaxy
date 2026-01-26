"""
Base classes for Galaxy AI agents.
"""

import asyncio
import logging
from abc import (
    ABC,
    abstractmethod,
)
from collections.abc import Callable
from dataclasses import dataclass
from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
    Union,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.model import User
from galaxy.schema.agents import (
    ActionSuggestion,
    ActionType,
    ConfidenceLevel,
)

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration
    from galaxy.managers.datasets import DatasetManager
    from galaxy.managers.jobs import JobManager
    from galaxy.managers.workflows import WorkflowsManager
    from galaxy.tools import ToolBox
    from galaxy.tools.cache import ToolCache

# Import pydantic-ai components (required dependency)
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

# Try to import Anthropic support (optional)
try:
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.providers.anthropic import AnthropicProvider

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    AnthropicModel = None  # type: ignore[assignment,misc]
    AnthropicProvider = None  # type: ignore[assignment,misc]

# Try to import Google/Gemini support (optional)
try:
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False
    GoogleModel = None  # type: ignore[assignment,misc]
    GoogleProvider = None  # type: ignore[assignment,misc]

log = logging.getLogger(__name__)

# Re-export common types for convenience
__all__ = [
    "ActionSuggestion",
    "ActionType",
    "AgentResponse",
    "AgentType",
    "BaseGalaxyAgent",
    "ConfidenceLevel",
    "GalaxyAgentDependencies",
    "SimpleGalaxyAgent",
]


# Agent type constants
class AgentType:
    """Constants for registered agent types."""

    ROUTER = "router"
    ERROR_ANALYSIS = "error_analysis"
    CUSTOM_TOOL = "custom_tool"
    ORCHESTRATOR = "orchestrator"


# Internal agent response model (simplified for internal use)
# For API responses, use galaxy.schema.agents.AgentResponse
class AgentResponse:
    """Internal agent response structure."""

    def __init__(
        self,
        content: str,
        confidence: Union[str, ConfidenceLevel],
        agent_type: str,
        suggestions: Optional[list[ActionSuggestion]] = None,
        metadata: Optional[dict[str, Any]] = None,
        reasoning: Optional[str] = None,
    ):
        self.content = content
        # Normalize confidence to ConfidenceLevel enum
        if isinstance(confidence, ConfidenceLevel):
            self.confidence = confidence
        else:
            self.confidence = ConfidenceLevel(confidence.lower())
        self.agent_type = agent_type
        self.suggestions = suggestions or []
        self.metadata = metadata or {}
        self.reasoning = reasoning


@dataclass
class GalaxyAgentDependencies:
    """Dependencies passed to Galaxy agents via dependency injection."""

    trans: ProvidesUserContext
    user: User
    config: "GalaxyAppConfiguration"
    job_manager: Optional["JobManager"] = None
    dataset_manager: Optional["DatasetManager"] = None
    workflow_manager: Optional["WorkflowsManager"] = None
    tool_cache: Optional["ToolCache"] = None
    toolbox: Optional["ToolBox"] = None
    # Callable to get agent instances, avoids circular import in base.py
    get_agent: Optional[Callable[[str, "GalaxyAgentDependencies"], "BaseGalaxyAgent"]] = None
    # Optional factory for creating model instances (useful for testing)
    model_factory: Optional[Callable[[], Any]] = None


class BaseGalaxyAgent(ABC):
    """Base class for all Galaxy AI agents."""

    # Subclasses must define their agent type explicitly
    agent_type: str
    agent: Agent[GalaxyAgentDependencies, Any]

    def __init__(self, deps: GalaxyAgentDependencies):
        """Initialize the agent with dependencies."""
        self.deps = deps

        if not hasattr(self, "agent_type") or not self.agent_type:
            raise NotImplementedError(f"{self.__class__.__name__} must define 'agent_type' class attribute")

        self.agent = self._create_agent()

    @abstractmethod
    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        """Create the pydantic-ai Agent instance."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    def _validate_query(self, query: str) -> Optional[str]:
        """
        Validate query input for security and safety.

        Returns:
            None if valid, error message if invalid
        """
        if not query or not isinstance(query, str):
            return "Query must be a non-empty string"

        # Get max query length from config (default 10000 chars)
        max_length = self._get_agent_config("max_query_length", 10000)

        if len(query) > max_length:
            return f"Query too long ({len(query)} chars). Maximum is {max_length} characters."

        # Check for obvious prompt injection patterns
        suspicious_patterns = [
            "ignore previous instructions",
            "ignore all previous",
            "disregard all previous",
            "forget all previous",
            "new instructions:",
            "system:",
            "assistant:",
        ]

        query_lower = query.lower()
        for pattern in suspicious_patterns:
            if pattern in query_lower:
                log.warning(f"Potential prompt injection detected in {self.agent_type} query: {pattern}")
                # Don't reject, just log - could be legitimate

        return None

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        """
        Process a query and return structured response.

        Args:
            query: The user's query/request
            context: Optional additional context for the query

        Returns:
            AgentResponse with structured output
        """
        # Validate input
        validation_error = self._validate_query(query)
        if validation_error:
            return AgentResponse(
                content=validation_error,
                confidence="low",
                agent_type=self.agent_type,
                suggestions=[],
                metadata={"validation_error": True},
            )

        try:
            # Prepare the full prompt with context
            full_prompt = self._prepare_prompt(query, context or {})

            # Run the agent with retry logic
            result = await self._run_with_retry(full_prompt)

            # Format the response
            return self._format_response(result, query, context or {})

        except UnexpectedModelBehavior as e:
            log.exception(f"Unexpected model behavior in {self.agent_type} agent")
            return self._get_fallback_response(query, f"Unexpected model behavior: {str(e)}")

        except OSError as e:
            log.warning(f"Network error in {self.agent_type} agent: {e}")
            return self._get_fallback_response(query, str(e))

        except ValueError as e:
            log.exception(f"Value error in {self.agent_type} agent")
            return self._get_fallback_response(query, str(e))

    async def _run_with_retry(self, prompt: str, max_retries: int = 3, base_delay: float = 1.0):
        """Run the agent, with exponential backoff for retries."""
        last_exception = None

        # Get model settings from config
        model_settings: ModelSettings = {
            "temperature": self._get_temperature(),
            "max_tokens": self._get_max_tokens(),
        }

        for attempt in range(max_retries + 1):
            try:
                return await self.agent.run(prompt, deps=self.deps, model_settings=model_settings)

            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

                # Generic retry indicators for network errors across providers.
                is_retryable = any(
                    indicator in error_msg
                    for indicator in [
                        "timeout",
                        "connection",
                        "rate limit",
                        "502",
                        "503",
                        "504",
                        "server error",
                        "temporary",
                        "overloaded",
                        "network",
                        "ssl",
                    ]
                )

                if not is_retryable or attempt == max_retries:
                    raise e

                # Calculate exponential backoff delay
                delay = base_delay * (2**attempt)

                log.warning(
                    f"Retryable error in {self.agent_type} agent (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )

                # Wait before retrying
                await asyncio.sleep(delay)

        # This should never be reached, but just in case
        raise last_exception or Exception("Max retries exhausted")

    def _prepare_prompt(self, query: str, context: dict[str, Any]) -> str:
        """Prepare the full prompt including context."""
        prompt_parts = [query]

        if context:
            # Work with a copy to avoid mutating the caller's context
            context = context.copy()

            # Handle visualizations specially
            visualizations = context.pop("visualizations", None)

            # Add remaining context
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items() if v])
            if context_str:
                prompt_parts.insert(0, f"Context:\n{context_str}\n")

            # Add visualization context
            if visualizations:
                from galaxy.agents.visualization_context import format_visualization_context

                viz_context = format_visualization_context(visualizations)
                if viz_context:
                    prompt_parts.insert(0, viz_context)

        return "\n".join(prompt_parts)

    def _format_response(self, result: Any, query: str, context: dict[str, Any]) -> AgentResponse:
        """Convert pydantic-ai result to AgentResponse."""
        # Default implementation - subclasses can override
        content = str(result.data) if hasattr(result, "data") else str(result)

        return AgentResponse(
            content=content,
            confidence="medium",
            agent_type=self.agent_type,
            suggestions=[],
            metadata={
                "model": getattr(self.agent, "model_name", "unknown"),
                "query_length": len(query),
                "has_context": bool(context),
            },
        )

    def _get_fallback_response(self, query: str, error_msg: str) -> AgentResponse:
        """Return a fallback response when agent processing fails."""
        # Check for common service connectivity issues to provide a better message.
        is_service_error = any(
            indicator in error_msg.lower()
            for indicator in [
                "connection",
                "timeout",
                "api",
                "401",
                "403",
                "500",
                "502",
                "503",
                "rate limit",
            ]
        )

        if is_service_error:
            content = "Unable to access the AI inference service. Please try again later."
        else:
            content = f"I'm having trouble processing your request right now. {self._get_fallback_content()}"

        return AgentResponse(
            content=content,
            confidence="low",
            agent_type=self.agent_type,
            suggestions=[
                ActionSuggestion(
                    action_type=ActionType.CONTACT_SUPPORT,
                    description="Contact Galaxy support for assistance",
                    confidence="high",
                    priority=1,
                )
            ],
            metadata={
                "fallback": True,
                "error": error_msg,
                "service_unavailable": is_service_error,
            },
        )

    def _get_fallback_content(self) -> str:
        """Get fallback content specific to this agent type."""
        return "Please try again later or contact support if the issue persists."

    def _supports_structured_output(self) -> bool:
        """Check if current model supports structured output (tool calling/JSON mode).

        Note: This checks basic structured output capability, not complex nested schemas.
        Models via local endpoints (vLLM, LiteLLM) may support simple structured output
        but fail on complex schemas with $defs. Agents requiring complex schemas should
        handle those runtime failures gracefully.
        """
        model_name = self._get_agent_config("model", "").lower()

        # DeepSeek models don't support structured output at all
        if "deepseek" in model_name:
            return False

        # Models with known structured output support (native APIs or compatible proxies)
        # llama-4-scout works for basic structured output via LiteLLM
        # gpt-oss models support json_object but not strict json_schema mode
        if any(m in model_name for m in ["gpt-4", "gpt-3", "claude", "llama-4-scout"]):
            return True

        # Default to not using structured output for unknown models (safer)
        return False

    def _requires_structured_output(self) -> bool:
        """
        Override in agents that require structured output to function.

        When True, the agent will return a graceful error response if the
        configured model doesn't support structured output, rather than
        attempting a fallback that may produce poor results.
        """
        return False

    def _validate_model_capabilities(self) -> Optional[str]:
        """
        Validate that the configured model meets this agent's requirements.

        Called by subclasses (e.g., CustomToolAgent) before attempting operations
        that require specific model capabilities like structured output.

        Returns:
            None if valid, error message string if invalid.
        """
        if self._requires_structured_output() and not self._supports_structured_output():
            model = self._get_agent_config("model", "unknown")
            return (
                f"The model '{model}' failed to generate a tool definition due to JSON schema limitations. "
                f"This typically happens with local inference backends (vLLM, LiteLLM proxies) that don't "
                f"support complex nested JSON schemas.\n\n"
                f"To resolve this, configure a model that fully supports structured output "
                f"(e.g., gpt-4o, claude-3-sonnet) via their native APIs."
            )
        return None

    def _get_agent_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value for this agent with fallback logic.

        Precedence:
        1. Agent-specific config (e.g., inference_services.custom_tool.model)
        2. Default inference config (inference_services.default.model)
        3. Global config (ai_model for 'model' key)
        4. Provided default value
        """
        inference_config = getattr(self.deps.config, "inference_services", {})

        # 1. Check agent-specific config
        if isinstance(inference_config, dict):
            agent_specific = inference_config.get(self.agent_type, {})
            if isinstance(agent_specific, dict) and key in agent_specific:
                return agent_specific[key]

            # 2. Check default inference config
            default_config = inference_config.get("default", {})
            if isinstance(default_config, dict) and key in default_config:
                return default_config[key]

        # 3. Check global config for specific keys
        if key == "model":
            if hasattr(self.deps.config, "ai_model") and self.deps.config.ai_model:
                return self.deps.config.ai_model
        elif key == "api_key":
            if hasattr(self.deps.config, "ai_api_key") and self.deps.config.ai_api_key:
                return self.deps.config.ai_api_key
        elif key == "api_base_url":
            if hasattr(self.deps.config, "ai_api_base_url") and self.deps.config.ai_api_base_url:
                return self.deps.config.ai_api_base_url
        # 4. Return provided default
        return default

    def _get_model_name(self) -> str:
        """Get the model name for this agent from configuration."""
        return self._get_agent_config("model", "gpt-4o-mini")

    def _get_model(self):
        """
        Get the configured model with explicit provider setup.

        Supported providers (via model prefix):
        - 'anthropic:claude-sonnet-4-5' → Anthropic
        - 'google:gemini-2.5-pro' → Google/Gemini
        - 'openai:gpt-4o' or 'gpt-4o' → OpenAI
        - Any model + base_url → OpenAI-compatible (TACC, vLLM, Ollama, etc.)

        All credentials come from Galaxy config, never from environment variables.
        If deps.model_factory is set, uses that instead (for testing).
        """
        # Allow injection of model factory (useful for testing)
        if self.deps.model_factory:
            return self.deps.model_factory()

        model_spec = self._get_model_name()
        api_key = self._get_agent_config("api_key")
        base_url = self._get_agent_config("api_base_url")

        # Check for Anthropic models
        if model_spec.startswith("anthropic:"):
            if not HAS_ANTHROPIC:
                raise ImportError("Anthropic support requires pydantic-ai[anthropic] to be installed")
            model_name = model_spec[10:]  # Strip 'anthropic:' prefix
            anthropic_provider = AnthropicProvider(api_key=api_key)
            return AnthropicModel(model_name, provider=anthropic_provider)

        # Check for Google/Gemini models
        if model_spec.startswith("google:"):
            if not HAS_GOOGLE:
                raise ImportError("Google support requires pydantic-ai[google] to be installed")
            model_name = model_spec[7:]  # Strip 'google:' prefix
            google_provider = GoogleProvider(api_key=api_key)
            return GoogleModel(model_name, provider=google_provider)

        # Strip 'openai:' prefix if present
        if model_spec.startswith("openai:"):
            model_name = model_spec[7:]
        else:
            model_name = model_spec

        # OpenAI or OpenAI-compatible (TACC, vLLM, Ollama, etc.)
        openai_provider = OpenAIProvider(api_key=api_key, base_url=base_url)
        return OpenAIChatModel(model_name, provider=openai_provider)

    def _get_temperature(self) -> float:
        """Get the temperature setting for this agent."""
        return self._get_agent_config("temperature", 0.7)

    def _get_max_tokens(self) -> int:
        """Get the max tokens setting for this agent."""
        return self._get_agent_config("max_tokens", 2000)

    async def _call_agent_from_tool(
        self,
        agent_type: str,
        query: str,
        ctx,
        usage=None,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Centralized helper method for calling other agents from within tool functions.

        This method standardizes agent-to-agent communication within @agent.tool decorated functions,
        reducing code duplication and providing consistent error handling.

        Args:
            agent_type: Type of agent to call (e.g., "error_analysis", "custom_tool")
            query: Query to send to the target agent
            ctx: RunContext from the calling tool function
            usage: Optional usage tracking object (defaults to ctx.usage)
            context: Optional context dict with conversation history, metadata, etc.

        Returns:
            String response from the target agent

        Raises:
            Exception: If the target agent cannot be called

        Example usage in @agent.tool functions:
            response = await self._call_agent_from_tool(
                "error_analysis",
                f"Analyze this issue: {task}",
                ctx,
                context={"conversation_history": history}
            )
        """
        try:
            if ctx.deps.get_agent is None:
                raise RuntimeError("get_agent not configured in dependencies")

            # Get the target agent using the injected callable
            target_agent = ctx.deps.get_agent(agent_type, ctx.deps)

            # Prepare query with context if available
            full_query = query
            if context and "conversation_history" in context:
                history = context["conversation_history"]
                if history and len(history) > 0:
                    # Add conversation history to query for better context
                    history_text = "Previous conversation:\n"
                    for msg in history[-4:]:  # Last 4 messages for context
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")[:200]  # Truncate long messages
                        history_text += f"{role}: {content}\n"
                    full_query = f"{history_text}\nCurrent request: {query}"

            # Get model settings for the target agent
            target_model_settings = {
                "temperature": target_agent._get_temperature(),
                "max_tokens": target_agent._get_max_tokens(),
            }

            # Call the agent with proper usage tracking and model settings
            result = await target_agent.agent.run(
                full_query,
                deps=ctx.deps,
                usage=usage or ctx.usage,  # Use provided usage or fall back to ctx.usage
                model_settings=target_model_settings,
            )

            # Extract response data
            response_data = result.data if hasattr(result, "data") else str(result)

            log.debug(f"Agent {self.agent_type} called {agent_type} via tool: '{query[:50]}...'")

            return str(response_data)

        except ValueError as e:
            # Unknown agent type
            error_msg = f"Unknown agent type '{agent_type}': {e}"
            log.warning(f"Agent-to-agent call failed: {error_msg}")
            return error_msg
        except UnexpectedModelBehavior as e:
            # LLM returned unexpected response
            error_msg = f"Model behavior error calling {agent_type}: {e}"
            log.warning(f"Agent-to-agent call failed: {error_msg}")
            return error_msg
        except (ConnectionError, TimeoutError) as e:
            # Network-related errors
            error_msg = f"Network error calling {agent_type} agent: {e}"
            log.warning(f"Agent-to-agent call failed: {error_msg}")
            return error_msg


class SimpleGalaxyAgent(BaseGalaxyAgent):
    """
    Simple agent that uses basic text completion without structured output.
    Useful for agents that don't need complex response schemas.
    """

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, str]:
        """Create a simple agent with text output."""
        return Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            system_prompt=self.get_system_prompt(),
        )

    def _format_response(self, result: Any, query: str, context: dict[str, Any]) -> AgentResponse:
        """Format simple text response."""
        content = str(result.data) if hasattr(result, "data") else str(result)

        # Try to extract confidence from the response
        confidence = self._extract_confidence(content)

        return AgentResponse(
            content=content,
            confidence=confidence,
            agent_type=self.agent_type,
            suggestions=self._extract_suggestions(content),
            metadata={
                "model": self._get_model_name(),
                "query_length": len(query),
                "has_context": bool(context),
                "response_length": len(content),
            },
        )

    def _extract_confidence(self, content: str) -> ConfidenceLevel:
        """Extract confidence level from response content."""
        content_lower = content.lower()

        if any(word in content_lower for word in ["uncertain", "might", "possibly", "unclear"]):
            return ConfidenceLevel.LOW
        elif any(word in content_lower for word in ["likely", "probably", "confident"]):
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.MEDIUM

    def _extract_suggestions(self, content: str) -> list[ActionSuggestion]:
        """Extract action suggestions from response content."""
        suggestions = []

        # Simple heuristics to extract suggestions
        if "try" in content.lower() or "recommend" in content.lower():
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.TOOL_RUN,
                    description="Follow the suggested approach",
                    confidence=ConfidenceLevel.MEDIUM,
                )
            )

        if "documentation" in content.lower() or "manual" in content.lower():
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.DOCUMENTATION,
                    description="Check the relevant documentation",
                    confidence=ConfidenceLevel.MEDIUM,
                )
            )

        return suggestions
