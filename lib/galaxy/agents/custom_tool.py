"""
Custom tool creation agent for Galaxy - uses UserToolSource for proper tool definitions.
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
    """
    Agent that creates custom Galaxy tools using UserToolSource schema.

    This agent requires a model with structured output support to generate
    valid Galaxy tool definitions. If the configured model doesn't support
    structured output, it returns a helpful error message guiding the
    operator to configure an appropriate model.
    """

    agent_type = AgentType.CUSTOM_TOOL

    def _requires_structured_output(self) -> bool:
        """CustomToolAgent requires structured output for proper tool generation."""
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
        """System prompt for structured output."""
        prompt_path = Path(__file__).parent / "prompts" / "custom_tool_structured.md"
        return prompt_path.read_text()

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        """Process tool creation request."""
        # Check model capabilities first
        capability_error = self._validate_model_capabilities()
        if capability_error:
            return AgentResponse(
                content=capability_error,
                confidence=ConfidenceLevel.LOW,
                agent_type=self.agent_type,
                suggestions=[
                    ActionSuggestion(
                        action_type=ActionType.CONTACT_SUPPORT,
                        description="Contact your Galaxy administrator to configure AI tool generation",
                        parameters={},
                        confidence=ConfidenceLevel.HIGH,
                        priority=1,
                    )
                ],
                metadata={"error": "model_capability", "requires": "structured_output"},
            )

        try:
            # Run the agent to generate a UserToolSource
            result = await self._run_with_retry(query)
            tool = extract_structured_output(result, UserToolSource, log)

            if tool is None:
                # Model returned text instead of structured output
                content = extract_result_content(result)
                return AgentResponse(
                    content=f"The model did not generate a valid tool definition. Response:\n\n{content}",
                    confidence=ConfidenceLevel.LOW,
                    agent_type=self.agent_type,
                    suggestions=[],
                    metadata={"method": "text_fallback", "error": "invalid_structured_output"},
                )

            # Convert UserToolSource to YAML
            tool_dict = tool.model_dump(by_alias=True, exclude_none=True)
            tool_yaml = yaml.dump(tool_dict, default_flow_style=False, sort_keys=False)

            metadata = {
                "tool_id": tool.id,
                "tool_name": tool.name,
                "tool_yaml": tool_yaml,
                "method": "structured",
            }

            # Create response content
            response_content = f"""I've created a custom Galaxy tool:

```yaml
{tool_yaml}
```

**Tool ID**: {tool.id}
**Name**: {tool.name}
**Version**: {tool.version}
**Container**: {tool.container}

The tool is ready to be saved and used in Galaxy."""

            # Add action suggestions
            suggestions = [
                ActionSuggestion(
                    action_type=ActionType.SAVE_TOOL,
                    description="Save this tool to Galaxy",
                    parameters={"tool_yaml": tool_yaml, "tool_id": tool.id},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                ),
            ]

            return AgentResponse(
                content=response_content,
                confidence=ConfidenceLevel.HIGH,
                agent_type=self.agent_type,
                suggestions=suggestions,
                metadata=metadata,
            )

        except OSError as e:
            log.error(f"Tool creation network error: {e}")
            return AgentResponse(
                content=f"Failed to create tool due to network issues: {str(e)}\n\nPlease try again.",
                confidence=ConfidenceLevel.LOW,
                agent_type=self.agent_type,
                suggestions=[],
                metadata={"error": str(e)},
            )
        except ValueError as e:
            log.error(f"Tool creation value error: {e}")
            return AgentResponse(
                content=f"Failed to create tool: {str(e)}\n\nPlease provide clear requirements for your tool.",
                confidence=ConfidenceLevel.LOW,
                agent_type=self.agent_type,
                suggestions=[],
                metadata={"error": str(e)},
            )
        except ModelHTTPError as e:
            # Handle schema/grammar errors from model backends (vLLM, LiteLLM, etc.)
            error_str = str(e).lower()
            if "grammar" in error_str or "$defs" in error_str or "pointer" in error_str:
                log.warning(f"Tool creation schema error (model may not support complex JSON schemas): {e}")
                model = self._get_agent_config("model", "unknown")
                return AgentResponse(
                    content=(
                        f"The model '{model}' failed to generate a tool definition due to JSON schema limitations. "
                        "This typically happens with local inference backends (vLLM, LiteLLM proxies) that don't "
                        "support complex nested JSON schemas.\n\n"
                        "To resolve this, configure a model that fully supports structured output "
                        "(e.g., gpt-4o, claude-3-sonnet) via their native APIs."
                    ),
                    confidence=ConfidenceLevel.LOW,
                    agent_type=self.agent_type,
                    suggestions=[
                        ActionSuggestion(
                            action_type=ActionType.CONTACT_SUPPORT,
                            description="Contact support for help configuring a compatible model",
                            parameters={},
                            confidence=ConfidenceLevel.HIGH,
                            priority=1,
                        )
                    ],
                    metadata={"error": "schema_limitation", "model": model},
                )
            raise
        except UnexpectedModelBehavior as e:
            # Handle validation failures when model can't produce valid structured output
            log.warning(f"Model failed to produce valid tool definition: {e}")
            model = self._get_agent_config("model", "unknown")
            return AgentResponse(
                content=(
                    f"The model '{model}' was unable to generate a valid tool definition after multiple attempts. "
                    "This may indicate the model doesn't fully support the required structured output format.\n\n"
                    "Try using a model with better structured output support (e.g., gpt-4o, claude-3-sonnet)."
                ),
                confidence=ConfidenceLevel.LOW,
                agent_type=self.agent_type,
                suggestions=[
                    ActionSuggestion(
                        action_type=ActionType.CONTACT_SUPPORT,
                        description="Contact support for help configuring a compatible model",
                        parameters={},
                        confidence=ConfidenceLevel.HIGH,
                        priority=1,
                    )
                ],
                metadata={"error": "validation_failure", "model": model},
            )
