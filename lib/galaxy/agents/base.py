"""
Base classes for Galaxy AI agents.
"""

import asyncio
import fnmatch
import logging
import os
import random
from abc import (
    ABC,
    abstractmethod,
)
from collections.abc import (
    Callable,
    Sequence,
)
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
    Literal,
    Optional,
    TYPE_CHECKING,
    Union,
)

import yaml

from galaxy.exceptions import ConfigurationError
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

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings

try:
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.providers.anthropic import AnthropicProvider

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    AnthropicModel = None  # type: ignore[assignment,misc]
    AnthropicProvider = None  # type: ignore[assignment,misc]

try:
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False
    GoogleModel = None  # type: ignore[assignment,misc]
    GoogleProvider = None  # type: ignore[assignment,misc]

log = logging.getLogger(__name__)

# Literal inlines enum values in JSON schema, avoiding $defs that vLLM can't handle
ConfidenceLiteral = Literal["low", "medium", "high"]

MAX_HISTORY_MESSAGES = 40
"""Cap on prior messages passed as pydantic-ai ``message_history`` to bound token load."""

TOOL_HELPER_HISTORY_MESSAGES = 8
"""Tighter history cap for sub-agents invoked from inside a ``@agent.tool`` call."""

# Hardcoded fallback if the capability YAML can't be located. Mirrors the
# previous behaviour (deepseek -> no structured output, everything else yes).
_DEFAULT_MODEL_CAPABILITIES: dict[str, Any] = {
    "model_capabilities": [
        {"pattern": "deepseek*", "structured_output": False},
    ],
    "default": {"structured_output": True},
}

_model_capabilities_cache: dict[str, dict[str, Any]] = {}


def _load_model_capabilities(path: Optional[str], force_reload: bool = False) -> dict[str, Any]:
    """Return the parsed model-capabilities table for ``path``, falling back to defaults on any failure."""
    if not isinstance(path, str) or not path:
        return _DEFAULT_MODEL_CAPABILITIES

    if not force_reload and path in _model_capabilities_cache:
        return _model_capabilities_cache[path]

    if not os.path.exists(path):
        log.warning("Model capabilities file not found at %s; using built-in defaults.", path)
        _model_capabilities_cache[path] = _DEFAULT_MODEL_CAPABILITIES
        return _DEFAULT_MODEL_CAPABILITIES

    try:
        with open(path) as fh:
            parsed = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError) as exc:
        log.warning("Could not parse model capabilities at %s: %s; using built-in defaults.", path, exc)
        _model_capabilities_cache[path] = _DEFAULT_MODEL_CAPABILITIES
        return _DEFAULT_MODEL_CAPABILITIES

    if not isinstance(parsed, dict):
        log.warning("Ignoring model capabilities at %s: not a mapping; using built-in defaults.", path)
        _model_capabilities_cache[path] = _DEFAULT_MODEL_CAPABILITIES
        return _DEFAULT_MODEL_CAPABILITIES

    _model_capabilities_cache[path] = parsed
    return parsed


def _capability_for_model(model_name: str, capability: str, table: dict[str, Any]) -> Optional[bool]:
    """Look up `capability` for `model_name` against the parsed table.

    Strips any `provider:` prefix before matching. Returns None when neither
    a pattern nor a default entry covers the capability -- callers decide
    what to do with that.
    """
    if not model_name:
        return None

    bare_name = model_name.split(":", 1)[1] if ":" in model_name else model_name
    bare_name = bare_name.lower()

    for entry in table.get("model_capabilities", []) or []:
        if not isinstance(entry, dict):
            continue
        pattern = entry.get("pattern")
        if not pattern:
            continue
        if fnmatch.fnmatch(bare_name, pattern.lower()):
            if capability in entry:
                return bool(entry[capability])

    default_block = table.get("default") or {}
    if isinstance(default_block, dict) and capability in default_block:
        return bool(default_block[capability])
    return None


__all__ = [
    "ActionSuggestion",
    "ActionType",
    "AgentResponse",
    "AgentRunState",
    "AgentType",
    "BaseGalaxyAgent",
    "ConfidenceLevel",
    "ConfidenceLiteral",
    "extract_result_content",
    "extract_structured_output",
    "extract_usage_info",
    "GalaxyAgentDependencies",
    "MAX_HISTORY_MESSAGES",
    "normalize_llm_text",
    "SimpleGalaxyAgent",
    "TOOL_HELPER_HISTORY_MESSAGES",
    "truncate_message_history",
]


def truncate_message_history(history: list[ModelMessage], limit: int = MAX_HISTORY_MESSAGES) -> list[ModelMessage]:
    """Cap conversation history at ``limit`` recent messages, preserving the first one.

    Keeps ``history[0]`` -- typically the user's original request, which anchors
    intent across long conversations -- and the most recent ``limit`` messages.
    """
    if len(history) <= limit:
        return history
    log.info(
        "Truncating conversation history from %d to %d messages (first + last %d)",
        len(history),
        limit + 1,
        limit,
    )
    return [history[0]] + history[-limit:]


def _coerce_message_history(history: Sequence[Any]) -> list[ModelMessage]:
    """Normalize API-formatted and legacy role/content chat history."""
    messages: list[ModelMessage] = []
    skipped = 0

    for item in history:
        if isinstance(item, (ModelRequest, ModelResponse)):
            messages.append(item)
            continue

        if not isinstance(item, dict):
            skipped += 1
            continue

        role = str(item.get("role", "")).lower()
        content = item.get("content")
        if content is None:
            skipped += 1
            continue

        if role == "assistant":
            messages.append(ModelResponse(parts=[TextPart(content=str(content))]))
        elif role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=str(content))]))
        elif role == "system":
            messages.append(ModelRequest(parts=[SystemPromptPart(content=str(content))]))
        else:
            skipped += 1

    if skipped:
        log.warning("Ignored %d unsupported conversation_history message(s)", skipped)

    return messages


def extract_result_content(result: Any) -> str:
    """Extract text content from a pydantic-ai result (.output or .data)."""
    if hasattr(result, "output"):
        return str(result.output)
    elif hasattr(result, "data"):
        return str(result.data)
    return str(result)


def extract_usage_info(result: Any) -> dict[str, int]:
    """Extract token usage from a pydantic-ai result, or empty dict."""
    if not hasattr(result, "usage"):
        return {}
    try:
        usage = result.usage()
        return {
            "input_tokens": getattr(usage, "input_tokens", 0),
            "output_tokens": getattr(usage, "output_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        }
    except Exception:
        return {}


def extract_structured_output(result: Any, expected_type: type, logger: Optional[logging.Logger] = None) -> Any:
    """Extract structured output from a pydantic-ai result, or None if extraction fails."""
    _log = logger or log

    if hasattr(result, "data") and isinstance(result.data, expected_type):
        _log.debug(f"Extracted {expected_type.__name__} from result.data")
        return result.data

    if hasattr(result, "output") and isinstance(result.output, expected_type):
        _log.debug(f"Extracted {expected_type.__name__} from result.output")
        return result.output

    _log.warning(
        f"Could not extract {expected_type.__name__} from result. "
        f"Result type: {type(result).__name__}, "
        f"data type: {type(getattr(result, 'data', None)).__name__}, "
        f"output type: {type(getattr(result, 'output', None)).__name__}"
    )

    if hasattr(result, "data") and result.data is not None:
        _log.debug(f"result.data value: {str(result.data)[:500]}")
    if hasattr(result, "output") and result.output is not None:
        _log.debug(f"result.output value: {str(result.output)[:500]}")

    return None


def normalize_llm_text(text: str) -> str:
    """Normalize LLM text: convert literal \\n/\\t, strip whitespace."""
    normalized = text.replace("\\n", "\n")
    normalized = normalized.replace("\\t", "\t")
    normalized = normalized.strip()
    return normalized


class AgentType:
    """Constants for registered agent types."""

    ROUTER = "router"
    ERROR_ANALYSIS = "error_analysis"
    CUSTOM_TOOL = "custom_tool"
    ORCHESTRATOR = "orchestrator"
    TOOL_RECOMMENDATION = "tool_recommendation"
    HISTORY = "history"
    GTN_TRAINING = "gtn_training"
    PAGE_ASSISTANT = "page_assistant"
    WORKFLOW_REPORT = "workflow_report"


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
        if isinstance(confidence, ConfidenceLevel):
            self.confidence = confidence
        else:
            self.confidence = ConfidenceLevel(confidence.lower())
        self.agent_type = agent_type
        self.suggestions = suggestions or []
        self.metadata = metadata or {}
        self.reasoning = reasoning


@dataclass
class AgentRunState:
    """Per-invocation state shared across sequential multi-agent flows.

    The orchestrator creates a fresh instance per user query and attaches it
    to each agent's context. Sequential agents read prior agents' responses
    from here instead of parsing them out of a text-concatenated prompt.
    """

    prior_responses: dict[str, "AgentResponse"] = field(default_factory=dict)

    def get_prior(self, agent_type: str) -> Optional["AgentResponse"]:
        return self.prior_responses.get(agent_type)

    def record(self, agent_type: str, response: "AgentResponse") -> None:
        self.prior_responses[agent_type] = response


@dataclass
class GalaxyAgentDependencies:
    """Dependencies passed to Galaxy agents via dependency injection."""

    trans: ProvidesUserContext
    user: User
    config: "GalaxyAppConfiguration"
    # Callable to get agent instances, avoids circular import in base.py
    get_agent: Callable[[str, "GalaxyAgentDependencies"], "BaseGalaxyAgent"]
    # Callable returning an agent's user-facing capability blurb, or None when that agent
    # is not enabled in this deployment. Lets the router advertise only real capabilities.
    get_capability_blurb: Optional[Callable[[str], Optional[str]]] = None
    job_manager: Optional["JobManager"] = None
    dataset_manager: Optional["DatasetManager"] = None
    workflow_manager: Optional["WorkflowsManager"] = None
    tool_cache: Optional["ToolCache"] = None
    toolbox: Optional["ToolBox"] = None
    model_factory: Optional[Callable[[], Any]] = None


class BaseGalaxyAgent(ABC):
    """Base class for all Galaxy AI agents."""

    agent_type: str
    # One-line, user-facing description of what this agent lets the user do. The router
    # composes its "what can you do" answer from the blurbs of the agents enabled in this
    # deployment. None means the agent is not advertised there (e.g. the router itself, or
    # surfaces like the notebook page assistant that users reach a different way).
    capability_blurb: Optional[str] = None
    agent: Agent[GalaxyAgentDependencies, Any]
    _INTERNAL_CONTEXT_KEYS = frozenset({"run_state", "responding_to_clarification"})

    # Fallback when no max_tokens is configured. 8k leaves headroom on every
    # backend we currently support (smallest is Qwen3-32B at 32k context).
    DEFAULT_MAX_TOKENS = 8192

    # Retry budget passed to Agent(retries=...) (tool calls and output validation).
    # pydantic-ai defaults to 1; 3 gives a flaky model a couple more chances to
    # produce conforming output before the run fails.
    DEFAULT_AGENT_RETRIES = 3

    def __init__(self, deps: GalaxyAgentDependencies):
        self.deps = deps

        if not hasattr(self, "agent_type") or not self.agent_type:
            raise NotImplementedError(f"{self.__class__.__name__} must define 'agent_type' class attribute")

        self.agent = self._create_agent()

    @abstractmethod
    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def _validate_query(self, query: str) -> Optional[str]:
        """Validate query input. Returns None if valid, error message if not."""
        if not query or not isinstance(query, str):
            return "Query must be a non-empty string"

        max_length = self._get_agent_config("max_query_length", 10000)

        if len(query) > max_length:
            return f"Query too long ({len(query)} chars). Maximum is {max_length} characters."

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
                return "I'm not able to process that query. Please rephrase your question."

        return None

    def _validation_error_response(self, validation_error: str) -> AgentResponse:
        return AgentResponse(
            content=validation_error,
            confidence=ConfidenceLevel.LOW,
            agent_type=self.agent_type,
            suggestions=[],
            metadata={"validation_error": True},
        )

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        validation_error = self._validate_query(query)
        if validation_error:
            return self._validation_error_response(validation_error)

        try:
            ctx = context or {}
            message_history = self._extract_message_history(ctx)
            full_prompt = self._prepare_prompt(query, self._strip_history_from_context(ctx))
            result = await self._run_with_retry(full_prompt, message_history=message_history)
            return self._format_response(result, query, ctx)

        except (UnexpectedModelBehavior, OSError, ValueError) as e:
            log.warning(f"Error in {self.agent_type} agent: {e}")
            return self._get_fallback_response(query, str(e))

    @staticmethod
    def _extract_message_history(
        context: Optional[dict[str, Any]],
        limit: int = MAX_HISTORY_MESSAGES,
    ) -> Optional[list[ModelMessage]]:
        """Pull ``conversation_history`` out of context, normalize it, and truncate it.

        Returns None when history is missing/empty so callers can pass it
        straight to ``agent.run(..., message_history=...)`` without branching.
        """
        if not context:
            return None
        history = context.get("conversation_history")
        if not history:
            return None
        if isinstance(history, (str, bytes)) or not isinstance(history, Sequence):
            log.warning("Ignoring unsupported conversation_history value of type %s", type(history).__name__)
            return None
        messages = _coerce_message_history(history)
        if not messages:
            return None
        return truncate_message_history(messages, limit=limit)

    @staticmethod
    def _strip_history_from_context(context: dict[str, Any]) -> dict[str, Any]:
        """Drop ``conversation_history`` before rendering context as text.

        ``_prepare_prompt`` stringifies whatever's in the context dict; the raw
        ``ModelMessage`` repr is noise once we're passing the history through
        the structured ``message_history`` channel.
        """
        return {k: v for k, v in context.items() if k != "conversation_history"}

    async def _run_with_retry(
        self,
        prompt: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
        message_history: Optional[list[ModelMessage]] = None,
    ):
        """Run the agent with exponential backoff for retryable errors."""
        last_exception = None

        model_settings: ModelSettings = {
            "temperature": self._get_temperature(),
            "max_tokens": self._get_max_tokens(),
        }

        for attempt in range(max_retries + 1):
            try:
                return await self.agent.run(
                    prompt,
                    deps=self.deps,
                    model_settings=model_settings,
                    message_history=message_history,
                )

            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()

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
                    raise

                delay = base_delay * (2**attempt) + random.uniform(0, 0.5)

                log.warning(
                    f"Retryable error in {self.agent_type} agent (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )

                await asyncio.sleep(delay)

        raise last_exception or Exception("Max retries exhausted")

    @staticmethod
    def _sanitize_context_value(value: Any, max_length: int = 200) -> str:
        """Sanitize a user-supplied context field value for safe prompt inclusion."""
        s = str(value).replace("\n", " ").replace("\r", " ").strip()
        if len(s) > max_length:
            s = s[:max_length]
        return s

    def _format_interface_context(self, ctx: dict[str, Any]) -> str:
        ctx_type = ctx.get("contextType")
        if not ctx_type:
            return ""

        _s = self._sanitize_context_value

        if ctx_type == "tool":
            name = _s(ctx.get("toolName", ctx.get("toolId", "unknown")))
            tool_id = _s(ctx.get("toolId", ""))
            version = ctx.get("toolVersion")
            version_str = f", version {_s(version)}" if version else ""
            return f'The user is viewing the tool form for "{name}" ({tool_id}{version_str}).'

        if ctx_type == "dataset":
            dataset_id = _s(ctx.get("datasetId", "unknown"))
            name = _s(ctx.get("datasetName", dataset_id))
            ext = ctx.get("extension")
            ext_str = f" ({_s(ext)} format)" if ext else ""
            return f'The user is viewing dataset "{name}"{ext_str}.'

        if ctx_type == "workflow_editor":
            wf_id = _s(ctx.get("workflowId", "unknown"))
            name = _s(ctx.get("workflowName", wf_id))
            return f'The user is editing workflow "{name}".'

        if ctx_type == "workflow_run":
            wf_id = _s(ctx.get("workflowId", "unknown"))
            name = _s(ctx.get("workflowName", wf_id))
            return f'The user is running workflow "{name}".'

        if ctx_type == "job":
            job_id = _s(ctx.get("jobId", "unknown"))
            job_tool_id = ctx.get("toolId")
            tool_str = f" (tool: {_s(job_tool_id)})" if job_tool_id else ""
            return f"The user is viewing job {job_id}{tool_str}."

        return f"The user is viewing: {_s(ctx_type)}"

    def _prepare_prompt(self, query: str, context: dict[str, Any]) -> str:
        prompt_parts = [query]

        if context:
            interface_ctx = context.get("interface_context")
            if interface_ctx and isinstance(interface_ctx, dict):
                description = self._format_interface_context(interface_ctx)
                if description:
                    prompt_parts.insert(0, f"[Active interface context: {description}]\n")

            entities = context.get("entities")
            if entities and isinstance(entities, dict):
                entity_desc = self._format_entity_context(entities)
                if entity_desc:
                    prompt_parts.insert(0, f"{entity_desc}\n")

            skip_keys = self._INTERNAL_CONTEXT_KEYS | {"interface_context", "conversation_history", "entities"}
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items() if v and k not in skip_keys])
            if context_str:
                prompt_parts.insert(0, f"Context:\n{context_str}\n")

        return "\n".join(prompt_parts)

    @staticmethod
    def _format_entity_context(entities: dict[str, Any]) -> str:
        """Format entity references from @mentions into readable text."""
        _s = BaseGalaxyAgent._sanitize_context_value
        lines: list[str] = []
        for ds in entities.get("datasets", []):
            parts = [f"Dataset #{_s(ds.get('hid', '?'))}"]
            name = ds.get("name")
            if name:
                parts.append(f'"{_s(name)}"')
            details = []
            if ds.get("extension"):
                details.append(_s(ds["extension"]))
            if ds.get("state"):
                details.append(_s(ds["state"]))
            if details:
                parts.append(f"({', '.join(details)})")
            lines.append(f"- {' '.join(parts)}")
        for hist in entities.get("histories", []):
            label = "Current history" if hist.get("identifier") == "current" else "History"
            name = _s(hist.get("name", ""))
            lines.append(f'- {label}: "{name}"')
        if not lines:
            return ""
        return "Referenced entities:\n" + "\n".join(lines)

    def _format_response(self, result: Any, query: str, context: dict[str, Any]) -> AgentResponse:
        """Convert pydantic-ai result to AgentResponse. Subclasses can override."""
        content = extract_result_content(result)

        return self._build_response(
            content=content,
            confidence=ConfidenceLevel.MEDIUM,
            method="default",
            result=result,
            query=query,
            agent_data={"has_context": bool(context)} if context else None,
        )

    def _get_fallback_response(self, query: str, error_msg: str) -> AgentResponse:
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

        return self._build_response(
            content=content,
            confidence=ConfidenceLevel.LOW,
            method="fallback",
            query=query,
            suggestions=[
                ActionSuggestion(
                    action_type=ActionType.CONTACT_SUPPORT,
                    description="Contact Galaxy support for assistance",
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                )
            ],
            fallback=True,
            error=error_msg,
            agent_data={"service_unavailable": is_service_error},
        )

    def _get_fallback_content(self) -> str:
        """Override to provide agent-specific fallback text."""
        return "Please try again later or contact support if the issue persists."

    def _build_metadata(
        self,
        method: str,
        result: Any = None,
        query: Optional[str] = None,
        agent_data: Optional[dict[str, Any]] = None,
        fallback: bool = False,
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        """Build consistent metadata for agent responses.

        agent_data gets added both flat (backwards compat) and under 'agent_data' key.
        """
        metadata: dict[str, Any] = {
            "model": self._get_model_name(),
            "method": method,
        }

        if result:
            usage = extract_usage_info(result)
            if usage:
                metadata.update(usage)

        if query is not None:
            metadata["query_length"] = len(query)

        if fallback:
            metadata["fallback"] = True
        if error:
            metadata["error"] = error

        if agent_data:
            metadata.update(agent_data)
            metadata["agent_data"] = agent_data

        return metadata

    def _build_response(
        self,
        content: str,
        confidence: ConfidenceLevel,
        method: str,
        result: Any = None,
        query: Optional[str] = None,
        suggestions: Optional[list[ActionSuggestion]] = None,
        agent_data: Optional[dict[str, Any]] = None,
        fallback: bool = False,
        error: Optional[str] = None,
        reasoning: Optional[str] = None,
    ) -> AgentResponse:
        return AgentResponse(
            content=content,
            confidence=confidence,
            agent_type=self.agent_type,
            suggestions=suggestions or [],
            metadata=self._build_metadata(method, result, query, agent_data, fallback, error),
            reasoning=reasoning,
        )

    def _supports_structured_output(self) -> bool:
        """Check if current model supports structured output (tool calling/JSON mode).

        Resolution order:
          1. Agent-specific ``structured_output_override`` in inference_services
          2. Global ``default.structured_output_override`` in inference_services
          3. Glob match in the capability table at ``config.agent_model_capabilities_file``
             (Galaxy resolves this to the admin override in ``config_dir`` if present,
             otherwise the shipped sample under ``sample_config_dir``)
          4. The capability table's ``default`` block (true if absent)
        """
        override = self._get_agent_config("structured_output_override")
        if override is not None:
            return bool(override)

        model_name = self._get_agent_config("model", "")
        capabilities_path = getattr(self.deps.config, "agent_model_capabilities_file", None)
        capability = _capability_for_model(model_name, "structured_output", _load_model_capabilities(capabilities_path))
        if capability is None:
            return True
        return capability

    def _requires_structured_output(self) -> bool:
        """Override in agents that require structured output to function."""
        return False

    def _validate_model_capabilities(self) -> Optional[str]:
        """Check that the model meets this agent's requirements. Returns error message or None."""
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
        """Get config value with precedence: agent-specific > default inference > global > default."""
        inference_config = getattr(self.deps.config, "inference_services", {})

        if isinstance(inference_config, dict):
            agent_specific = inference_config.get(self.agent_type, {})
            if isinstance(agent_specific, dict) and key in agent_specific:
                return agent_specific[key]

            default_config = inference_config.get("default", {})
            if isinstance(default_config, dict) and key in default_config:
                return default_config[key]

        if key == "model":
            if hasattr(self.deps.config, "ai_model") and self.deps.config.ai_model:
                return self.deps.config.ai_model
        elif key == "api_key":
            if hasattr(self.deps.config, "ai_api_key") and self.deps.config.ai_api_key:
                return self.deps.config.ai_api_key
        elif key == "api_base_url":
            if hasattr(self.deps.config, "ai_api_base_url") and self.deps.config.ai_api_base_url:
                return self.deps.config.ai_api_base_url
        return default

    def _get_agent_specific_config(self, key: str, default: Any = None) -> Any:
        """Read a value only from this agent's own ``inference_services`` block.

        Unlike :meth:`_get_agent_config`, this skips the shared ``default`` block so a
        caller-pinned builtin is overridden only by an explicit per-agent entry.
        """
        inference_config = getattr(self.deps.config, "inference_services", {})
        if isinstance(inference_config, dict):
            agent_specific = inference_config.get(self.agent_type, {})
            if isinstance(agent_specific, dict) and key in agent_specific:
                return agent_specific[key]
        return default

    def _get_model_name(self) -> str:
        return self._get_agent_config("model", "gpt-4o-mini")

    def _get_model(self):
        """Get the configured model with explicit provider setup.

        Supported prefixes: 'anthropic:', 'google:', 'openai:' (or no prefix for OpenAI-compatible).
        All credentials come from Galaxy config, never from environment variables.
        """
        if self.deps.model_factory:
            return self.deps.model_factory()

        model_spec = self._get_model_name()
        api_key = self._get_agent_config("api_key")
        base_url = self._get_agent_config("api_base_url")

        if model_spec.startswith("anthropic:"):
            if not HAS_ANTHROPIC:
                raise ImportError("Anthropic support requires pydantic-ai[anthropic] to be installed")
            model_name = model_spec[10:]
            anthropic_provider = AnthropicProvider(api_key=api_key)
            return AnthropicModel(model_name, provider=anthropic_provider)

        if model_spec.startswith("google:"):
            if not HAS_GOOGLE:
                raise ImportError("Google support requires pydantic-ai[google] to be installed")
            model_name = model_spec[7:]
            google_provider = GoogleProvider(api_key=api_key)
            return GoogleModel(model_name, provider=google_provider)

        if model_spec.startswith("openai:"):
            model_name = model_spec[7:]
        else:
            model_name = model_spec

        openai_provider = OpenAIProvider(api_key=api_key, base_url=base_url)
        return OpenAIChatModel(model_name, provider=openai_provider)

    def _get_temperature(self) -> float:
        return self._get_agent_config("temperature", 0.7)

    def _get_max_tokens(self) -> int:
        return self._get_agent_config("max_tokens", self.DEFAULT_MAX_TOKENS)

    def _get_retries(self, default: Optional[int] = None) -> int:
        """Retry budget for the agent's pydantic-ai ``Agent(retries=...)``.

        With no ``default``, the budget resolves per-agent > ``default`` block >
        builtin (:attr:`DEFAULT_AGENT_RETRIES`). A caller-pinned ``default`` (e.g.
        custom_tool's producer keeps 0 so its own reflection loop owns the retry) is
        a correctness requirement, not a tunable: only an explicit per-agent
        ``retries`` overrides it -- a shared ``default`` block must not silently
        re-enable pydantic-ai retries there.
        """
        if default is None:
            raw = self._get_agent_config("retries", self.DEFAULT_AGENT_RETRIES)
        else:
            raw = self._get_agent_specific_config("retries", default)
        try:
            retries = int(raw)
        except (TypeError, ValueError):
            retries = None
        if retries is None or retries < 0:
            raise ConfigurationError(
                f"inference_services 'retries' for agent '{self.agent_type}' must be a non-negative integer, got {raw!r}"
            )
        return retries

    async def _call_agent_from_tool(
        self,
        agent_type: str,
        query: str,
        ctx,
        usage=None,
        context: Optional[dict[str, Any]] = None,
    ) -> str:
        """Call another agent from within a @agent.tool function."""
        try:
            if ctx.deps.get_agent is None:
                raise RuntimeError("get_agent not configured in dependencies")

            target_agent = ctx.deps.get_agent(agent_type, ctx.deps)

            message_history = self._extract_message_history(context, limit=TOOL_HELPER_HISTORY_MESSAGES)

            target_model_settings = {
                "temperature": target_agent._get_temperature(),
                "max_tokens": target_agent._get_max_tokens(),
            }

            result = await target_agent.agent.run(
                query,
                deps=ctx.deps,
                usage=usage or ctx.usage,
                model_settings=target_model_settings,
                message_history=message_history,
            )

            response_data = extract_result_content(result)

            log.debug(f"Agent {self.agent_type} called {agent_type} via tool: '{query[:50]}...'")

            return response_data

        except (ValueError, UnexpectedModelBehavior, ConnectionError, TimeoutError) as e:
            error_msg = f"Error calling {agent_type}: {e}"
            log.warning(f"Agent-to-agent call failed: {error_msg}")
            return error_msg


class SimpleGalaxyAgent(BaseGalaxyAgent):
    """Agent using basic text completion without structured output."""

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, str]:
        return Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            system_prompt=self.get_system_prompt(),
            retries=self._get_retries(),
        )

    def _format_response(self, result: Any, query: str, context: dict[str, Any]) -> AgentResponse:
        content = extract_result_content(result)
        confidence = self._extract_confidence(content)

        return self._build_response(
            content=content,
            confidence=confidence,
            method="simple",
            result=result,
            query=query,
            suggestions=self._extract_suggestions(content),
            agent_data={
                "has_context": bool(context),
                "response_length": len(content),
            },
        )

    def _extract_confidence(self, content: str) -> ConfidenceLevel:
        content_lower = content.lower()

        if any(word in content_lower for word in ["uncertain", "might", "possibly", "unclear"]):
            return ConfidenceLevel.LOW
        elif any(word in content_lower for word in ["likely", "probably", "confident"]):
            return ConfidenceLevel.HIGH
        else:
            return ConfidenceLevel.MEDIUM

    def _extract_suggestions(self, content: str) -> list[ActionSuggestion]:
        """Override to provide actionable suggestions. Returns empty list by default."""
        return []
