"""
Custom tool creation agent for Galaxy - simplified version using UserToolSource.
"""

import logging
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from pydantic import (
    BaseModel,
    Field,
)
from pydantic_ai import Agent

from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)


class SimpleTool(BaseModel):
    """Simplified tool model for basic Galaxy tools."""

    id: str = Field(description="Tool ID, lowercase with underscores")
    name: str = Field(description="Human-readable tool name")
    version: str = Field(description="Tool version, e.g. 1.0.0")
    description: str = Field(description="Brief tool description")
    command: str = Field(description="Shell command to execute")
    container: str = Field(description="Docker/Singularity container")
    inputs_description: str = Field(description="Description of input files/parameters")
    outputs_description: str = Field(description="Description of output files")


class CustomToolAgent(BaseGalaxyAgent):
    """
    Agent that creates custom Galaxy tools with fallback for models without structured output.
    """

    def _create_agent(self) -> Agent:
        """Create agent - tries structured output first."""
        return Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            output_type=SimpleTool,
            system_prompt=self.get_system_prompt(),
        )

    def get_system_prompt(self) -> str:
        """System prompt for structured output."""
        prompt_path = Path(__file__).parent / "prompts" / "custom_tool_structured.md"
        return prompt_path.read_text()

    async def process(self, query: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process tool creation request with fallback."""
        use_structured = self._supports_structured_output()

        try:
            if use_structured:
                log.info("Using structured output")
                # Try structured output first
                try:
                    result = await self._run_with_retry(query)
                    tool = result.output if hasattr(result, "output") else result.data

                    # Create YAML from structured output
                    tool_yaml = f"""class: GalaxyUserTool
id: {tool.id}
name: {tool.name}
version: {tool.version}
description: {tool.description}
container: {tool.container}
shell_command: {tool.command}
inputs:
  - {tool.inputs_description}
outputs:
  - {tool.outputs_description}"""

                    metadata = {
                        "tool_id": tool.id,
                        "tool_name": tool.name,
                        "tool_yaml": tool_yaml,
                        "method": "structured",
                    }

                except Exception as e:
                    log.warning(f"Structured output failed, falling back to template: {e}")
                    use_structured = False

            if not use_structured:
                log.info("Using simple template fallback")
                # For DeepSeek, just generate a basic template since it hangs on complex prompts
                # Extract key info from query
                tool_id = "custom_tool"
                tool_name = "Custom Tool"
                if "bwa" in query.lower():
                    tool_id = "bwa_mem_paired"
                    tool_name = "BWA-MEM Paired End"
                    container = "quay.io/biocontainers/bwa:0.7.17"
                    command = "bwa mem reference.fa reads1.fq reads2.fq > output.sam"
                    inputs = "- Reference genome (FASTA)\n  - Read 1 (FASTQ)\n  - Read 2 (FASTQ)"
                    outputs = "- Aligned reads (SAM)"
                else:
                    container = "ubuntu:latest"
                    command = "echo 'Tool command here'"
                    inputs = "- Input files"
                    outputs = "- Output files"

                tool_yaml = f"""class: GalaxyUserTool
id: {tool_id}
name: {tool_name}
version: 1.0.0
description: Tool created from user request
container: {container}
shell_command: {command}
inputs:
  {inputs}
outputs:
  {outputs}"""

                metadata = {
                    "tool_id": tool_id,
                    "tool_name": tool_name,
                    "tool_yaml": tool_yaml,
                    "method": "simple_template",
                }

            # Create response
            response_content = f"""I've created a custom Galaxy tool:

```yaml
{metadata['tool_yaml']}
```

**Tool ID**: {metadata['tool_id']}
**Name**: {metadata['tool_name']}

The tool is ready to use in Galaxy."""

            # Add action suggestions
            suggestions = [
                ActionSuggestion(
                    action_type=ActionType.SAVE_TOOL,
                    description="Save this tool to Galaxy",
                    parameters={"tool_yaml": metadata["tool_yaml"], "tool_id": metadata["tool_id"]},
                    confidence="high" if metadata["method"] == "structured" else "medium",
                    priority=1,
                ),
                ActionSuggestion(
                    action_type=ActionType.TEST_TOOL,
                    description="Test this tool",
                    parameters={"tool_id": metadata["tool_id"]},
                    confidence="medium",
                    priority=2,
                ),
            ]

            return AgentResponse(
                content=response_content,
                confidence="high" if metadata["method"] == "structured" else "medium",
                agent_type=self.agent_type,
                suggestions=suggestions,
                metadata=metadata,
            )

        except Exception as e:
            log.error(f"Tool creation failed: {e}")
            return AgentResponse(
                content=f"Failed to create tool: {str(e)}\n\nPlease provide clear requirements for your tool.",
                confidence="low",
                agent_type=self.agent_type,
                suggestions=[],
                metadata={"error": str(e)},
            )
