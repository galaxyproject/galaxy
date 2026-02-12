"""
Custom tool creation agent for Galaxy.
"""

import logging
from pathlib import Path
from typing import (
    Any,
    Optional,
)

import yaml
from pydantic_ai import Agent
from pydantic_ai.exceptions import (
    ModelHTTPError,
    UnexpectedModelBehavior,
)

from galaxy.schema.agents import ConfidenceLevel
from galaxy.tool_util_models import UserToolSource
from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    extract_result_content,
    extract_structured_output,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)


class CustomToolAgent(BaseGalaxyAgent):
    """Agent that creates custom Galaxy tools using UserToolSource schema.

    Requires a model with structured output support. If the configured model
    doesn't support structured output, returns an error guiding the operator
    to configure an appropriate model.
    """

    agent_type = AgentType.CUSTOM_TOOL

    def _requires_structured_output(self) -> bool:
        return True

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        """Create agent with UserToolSource as the output type."""
        return Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            output_type=UserToolSource,
            system_prompt=self.get_system_prompt(),
        )

    def get_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "custom_tool_structured.md"
        return prompt_path.read_text()

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        """Process tool creation request."""
        capability_error = self._validate_model_capabilities()
        if capability_error:
            return self._build_response(
                content=capability_error,
                confidence=ConfidenceLevel.LOW,
                method="capability_check",
                query=query,
                suggestions=[
                    ActionSuggestion(
                        action_type=ActionType.CONTACT_SUPPORT,
                        description="Contact your Galaxy administrator to configure AI tool generation",
                        parameters={},
                        confidence=ConfidenceLevel.HIGH,
                        priority=1,
                    )
                ],
                error="model_capability",
                agent_data={"requires": "structured_output"},
            )

        try:
            result = await self._run_with_retry(query)
            tool = extract_structured_output(result, UserToolSource, log)

            if tool is None:
                content = extract_result_content(result)
                return self._build_response(
                    content=f"The model did not generate a valid tool definition. Response:\n\n{content}",
                    confidence=ConfidenceLevel.LOW,
                    method="text_fallback",
                    result=result,
                    query=query,
                    error="invalid_structured_output",
                )

            tool_dict = tool.model_dump(by_alias=True, exclude_none=True)
            tool_yaml = yaml.dump(tool_dict, default_flow_style=False, sort_keys=False)

            response_content = f"""I've created a custom Galaxy tool:

```yaml
{tool_yaml}
```

**Tool ID**: {tool.id}
**Name**: {tool.name}
**Version**: {tool.version}
**Container**: {tool.container}

The tool is ready to be saved and used in Galaxy."""

            suggestions = [
                ActionSuggestion(
                    action_type=ActionType.SAVE_TOOL,
                    description="Save this tool to Galaxy",
                    parameters={"tool_yaml": tool_yaml, "tool_id": tool.id},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                ),
            ]

            return self._build_response(
                content=response_content,
                confidence=ConfidenceLevel.HIGH,
                method="structured",
                result=result,
                query=query,
                suggestions=suggestions,
                agent_data={
                    "tool_id": tool.id,
                    "tool_name": tool.name,
                    "tool_yaml": tool_yaml,
                },
            )

        except (OSError, ValueError) as e:
            log.error(f"Tool creation error: {e}")
            return self._build_response(
                content=f"Failed to create tool: {str(e)}\n\nPlease try again with clear requirements.",
                confidence=ConfidenceLevel.LOW,
                method="error",
                query=query,
                error=str(e),
            )
        except ModelHTTPError as e:
            # Schema/grammar errors from model backends (vLLM, LiteLLM, etc.)
            error_str = str(e).lower()
            if "grammar" in error_str or "$defs" in error_str or "pointer" in error_str:
                log.warning(f"Tool creation schema error (model may not support complex JSON schemas): {e}")
                model = self._get_agent_config("model", "unknown")
                return self._build_response(
                    content=(
                        f"The model '{model}' failed to generate a tool definition due to JSON schema limitations. "
                        "This typically happens with local inference backends (vLLM, LiteLLM proxies) that don't "
                        "support complex nested JSON schemas.\n\n"
                        "To resolve this, configure a model that fully supports structured output "
                        "(e.g., gpt-4o, claude-3-sonnet) via their native APIs."
                    ),
                    confidence=ConfidenceLevel.LOW,
                    method="error",
                    query=query,
                    suggestions=[
                        ActionSuggestion(
                            action_type=ActionType.CONTACT_SUPPORT,
                            description="Contact support for help configuring a compatible model",
                            parameters={},
                            confidence=ConfidenceLevel.HIGH,
                            priority=1,
                        )
                    ],
                    error="schema_limitation",
                    agent_data={"model": model},
                )
            raise
        except UnexpectedModelBehavior as e:
            log.warning(f"Model failed to produce valid tool definition: {e}")
            model = self._get_agent_config("model", "unknown")
            return self._build_response(
                content=(
                    f"The model '{model}' was unable to generate a valid tool definition after multiple attempts. "
                    "This may indicate the model doesn't fully support the required structured output format.\n\n"
                    "Try using a model with better structured output support (e.g., gpt-4o, claude-3-sonnet)."
                ),
                confidence=ConfidenceLevel.LOW,
                method="error",
                query=query,
                suggestions=[
                    ActionSuggestion(
                        action_type=ActionType.CONTACT_SUPPORT,
                        description="Contact support for help configuring a compatible model",
                        parameters={},
                        confidence=ConfidenceLevel.HIGH,
                        priority=1,
                    )
                ],
                error="validation_failure",
                agent_data={"model": model},
            )
