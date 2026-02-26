"""
Tool recommendation agent for suggesting appropriate Galaxy tools.
"""

import logging
import re
from pathlib import Path
from typing import (
    Any,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
)
from pydantic_ai import Agent
from pydantic_ai.tools import RunContext

from galaxy.schema.agents import ConfidenceLevel
from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    extract_result_content,
    extract_structured_output,
    GalaxyAgentDependencies,
    normalize_llm_text,
)

log = logging.getLogger(__name__)

# Type alias for confidence levels - using Literal inlines the enum values
# in the JSON schema, avoiding $defs references that vLLM can't handle
ConfidenceLiteral = Literal["low", "medium", "high"]


class SimplifiedToolRecommendationResult(BaseModel):
    """Simplified result for local LLMs - avoids nested models and enums."""

    # Instead of nested ToolMatch objects, we'll use simple dictionaries
    primary_tools: list[dict[str, Any]]  # Each dict has tool_id, tool_name, description, etc.
    alternative_tools: list[dict[str, Any]] = []
    workflow_suggestion: Optional[str] = None
    parameter_guidance: dict[str, Any] = {}
    confidence: ConfidenceLiteral
    reasoning: str
    search_keywords: list[str] = []


class ToolRecommendationAgent(BaseGalaxyAgent):
    """
    Agent for recommending appropriate Galaxy tools based on user requirements.

    This agent helps users discover tools, understand tool capabilities,
    and provides guidance on tool selection and parameter configuration.
    """

    agent_type = AgentType.TOOL_RECOMMENDATION

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        """Create the tool recommendation agent with conditional structured output."""
        if self._supports_structured_output():
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                output_type=SimplifiedToolRecommendationResult,
                system_prompt=self.get_system_prompt(),
            )
        else:
            # DeepSeek and other models without structured output
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                system_prompt=self._get_simple_system_prompt(),
            )

        # Add tools for tool discovery and analysis
        @agent.tool
        async def search_galaxy_tools(ctx: RunContext[GalaxyAgentDependencies], query: str) -> str:
            """Search Galaxy's toolbox for tools matching a query.

            Use this to find real tool IDs for tools you want to recommend.
            Returns tool id, name, description, and category for matching tools.
            """
            results = await self.search_tools(query)
            if not results:
                return f"No tools found matching '{query}'"

            formatted = []
            for tool in results[:10]:
                formatted.append(
                    f"- ID: {tool['id']}, Name: {tool['name']}, Description: {tool['description'][:100]}..."
                )
            return f"Found {len(results)} tools:\n" + "\n".join(formatted)

        @agent.tool
        async def get_galaxy_tool_details(ctx: RunContext[GalaxyAgentDependencies], tool_id: str) -> str:
            """Get detailed information about a specific Galaxy tool.

            Use this after searching to get more details about a tool you want to recommend,
            including input/output formats, version, and requirements.
            """
            details = await self.get_tool_details(tool_id)
            if "error" in details:
                return f"Error: {details['error']}"

            lines = [
                f"Tool: {details['name']} (ID: {details['id']})",
                f"Version: {details.get('version', 'unknown')}",
                f"Description: {details.get('description', 'No description')}",
                f"Category: {details.get('category', 'Uncategorized')}",
            ]
            if details.get("requirements"):
                lines.append(f"Requirements: {', '.join(details['requirements'])}")
            if details.get("inputs"):
                input_strs = [f"{i['name']} ({i['type']})" for i in details["inputs"][:5]]
                lines.append(f"Inputs: {', '.join(input_strs)}")
            if details.get("outputs"):
                output_strs = [f"{o['name']} ({o['format']})" for o in details["outputs"][:5]]
                lines.append(f"Outputs: {', '.join(output_strs)}")
            return "\n".join(lines)

        @agent.tool
        async def get_galaxy_tool_categories(ctx: RunContext[GalaxyAgentDependencies]) -> str:
            """Get list of tool categories available on this Galaxy server.

            Use this to understand what kinds of tools are available before searching.
            """
            categories = await self.get_tool_categories()
            if not categories:
                return "No tool categories found"
            return "Available tool categories:\n" + "\n".join(f"- {cat}" for cat in categories)

        return agent

    def get_system_prompt(self) -> str:
        """Get the system prompt for tool recommendation."""
        prompt_path = Path(__file__).parent / "prompts" / "tool_recommendation.md"
        return prompt_path.read_text()

    async def search_tools(self, query: str) -> list[dict[str, Any]]:
        """Search for tools in the Galaxy toolbox."""
        if not self.deps.toolbox:
            log.warning("Toolbox not available in agent dependencies")
            return []

        try:
            # Get the default panel view (usually 'default')
            panel_view = self.deps.config.default_panel_view or "default"

            # Use Galaxy's built-in tool search via the app's toolbox_search
            toolbox_search = self.deps.trans.app.toolbox_search  # type: ignore[attr-defined]
            tool_ids = toolbox_search.search(query, panel_view, self.deps.config)

            # Get tool details for found tools
            tools = []
            for tool_id in tool_ids[:20]:  # Limit to top 20 results
                tool = self.deps.toolbox.get_tool(tool_id)
                if tool and not tool.hidden:
                    tools.append(
                        {
                            "id": tool.id,
                            "name": tool.name,
                            "description": tool.description or "",
                            "category": tool.get_panel_section()[1] or "",
                        }
                    )

            return tools

        except (AttributeError, KeyError, TypeError) as e:
            log.warning(f"Error searching tools: {e}")
            return []

    async def get_tool_details(self, tool_id: str) -> dict[str, Any]:
        """Get detailed information about a specific tool."""
        if not self.deps.toolbox:
            return {"id": tool_id, "error": "Toolbox not available"}

        try:
            tool = self.deps.toolbox.get_tool(tool_id)
            if not tool:
                return {"id": tool_id, "error": "Tool not found"}

            # Build tool details
            details: dict[str, Any] = {
                "id": tool.id,
                "name": tool.name,
                "version": tool.version,
                "description": tool.description or "",
                "category": tool.get_panel_section()[1] or "",
                "requirements": [str(r) for r in tool.requirements] if hasattr(tool, "requirements") else [],
            }

            # Add input information
            if hasattr(tool, "inputs"):
                details["inputs"] = []
                for input_name, input_param in tool.inputs.items():
                    if hasattr(input_param, "type"):
                        details["inputs"].append(
                            {
                                "name": input_name,
                                "type": input_param.type,
                                "label": getattr(input_param, "label", input_name),
                            }
                        )

            # Add output information
            if hasattr(tool, "outputs"):
                details["outputs"] = []
                for output_name, output_param in tool.outputs.items():
                    details["outputs"].append(
                        {
                            "name": output_name,
                            "format": getattr(output_param, "format", "unknown"),
                        }
                    )

            return details

        except (AttributeError, KeyError, TypeError) as e:
            log.warning(f"Error getting tool details for {tool_id}: {e}")
            return {"id": tool_id, "error": str(e)}

    async def get_tool_categories(self) -> list[str]:
        """Get list of tool categories/sections from the toolbox."""
        if not self.deps.toolbox:
            log.warning("Toolbox not available in agent dependencies")
            return []

        try:
            categories: set[str] = set()
            # Iterate through all tools and collect unique panel sections
            for _tool_id, tool in self.deps.toolbox.tools():
                if tool and not tool.hidden:
                    section_name = tool.get_panel_section()[1]
                    if section_name:
                        categories.add(section_name)
            return sorted(categories)
        except (AttributeError, KeyError, TypeError) as e:
            log.warning(f"Error getting tool categories: {e}")
            return []

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        """
        Process a tool recommendation request.

        Args:
            query: User's task description or tool request
            context: Additional context like data formats

        Returns:
            Structured tool recommendation response
        """
        # Fast path for direct tool name queries to prevent LLM hallucination
        try:
            # Search for tools matching the query exactly, trimming whitespace
            trimmed_query = query.strip()
            search_results = await self.search_tools(trimmed_query)
            exact_match = None
            for tool in search_results:
                if tool.get("name", "").lower() == trimmed_query.lower():
                    exact_match = tool
                    break

            if exact_match:
                # Found an exact match, bypass LLM and respond directly
                log.info(f"Found exact tool match for query '{trimmed_query}', bypassing LLM.")

                recommendation = SimplifiedToolRecommendationResult(
                    primary_tools=[exact_match],
                    confidence=ConfidenceLevel.HIGH,
                    reasoning="This is the tool with the exact name you requested.",
                    search_keywords=[trimmed_query],
                )

                content = self._format_recommendation_response(recommendation)
                suggestions = self._create_suggestions(recommendation)

                return self._build_response(
                    content=content,
                    confidence=ConfidenceLevel.HIGH,
                    method="fast_path_exact_match",
                    query=query,
                    suggestions=suggestions,
                    reasoning=f"Directly matched tool name '{exact_match['name']}'.",
                )
        except (AttributeError, KeyError, TypeError) as e:
            log.warning(f"Fast path tool search failed: {e}. Proceeding with LLM.")

        try:
            # Add context information to query
            enhanced_query = query
            if context:
                if context.get("input_format"):
                    enhanced_query += f"\nInput format: {context['input_format']}"
                if context.get("output_format"):
                    enhanced_query += f"\nDesired output: {context['output_format']}"
                if context.get("task_type"):
                    enhanced_query += f"\nTask type: {context['task_type']}"

            # Run the recommendation agent with retry logic
            result = await self._run_with_retry(enhanced_query)
            # Handle different response formats based on model capabilities
            if self._supports_structured_output():
                # Try to extract structured output
                recommendation = extract_structured_output(result, SimplifiedToolRecommendationResult, log)

                if recommendation is None:
                    # Model returned text instead of structured output (e.g., clarifying question)
                    # Return the text response directly
                    content = extract_result_content(result)
                    return self._build_response(
                        content=content,
                        confidence=ConfidenceLevel.MEDIUM,
                        method="text_fallback",
                        result=result,
                        query=query,
                    )

                log.info(f"Tool recommendation result: primary_tools={recommendation.primary_tools}")
                content = self._format_recommendation_response(recommendation)
                suggestions = self._create_suggestions(recommendation)

                confidence = ConfidenceLevel(
                    recommendation.confidence.lower() if recommendation.confidence else "medium"
                )

                return self._build_response(
                    content=content,
                    confidence=confidence,
                    method="structured",
                    result=result,
                    query=query,
                    suggestions=suggestions,
                    agent_data={
                        "num_tools_found": len(recommendation.primary_tools),
                        "has_alternatives": bool(recommendation.alternative_tools),
                        "has_workflow": bool(recommendation.workflow_suggestion),
                        "search_keywords": recommendation.search_keywords,
                    },
                    reasoning=recommendation.reasoning,
                )
            else:
                # Handle simple text output from DeepSeek
                response_text = extract_result_content(result)
                parsed_result = self._parse_simple_response(response_text)

                return self._build_response(
                    content=parsed_result.get("content", response_text),
                    confidence=parsed_result.get("confidence", ConfidenceLevel.MEDIUM),
                    method="simple_text",
                    result=result,
                    query=query,
                    suggestions=parsed_result.get("suggestions", []),
                    agent_data={
                        "has_alternatives": parsed_result.get("has_alternatives", False),
                    },
                )

        except OSError as e:
            log.warning(f"Tool recommendation network error: {e}")
            return self._get_fallback_response(query, str(e))
        except ValueError as e:
            log.warning(f"Tool recommendation value error: {e}")
            return self._get_fallback_response(query, str(e))

    def _format_recommendation_response(self, recommendation: SimplifiedToolRecommendationResult) -> str:
        """Format the recommendation into user-friendly content."""
        parts = []

        # Primary recommendations
        if recommendation.primary_tools:
            parts.append("**Recommended Tools:**")
            for i, tool in enumerate(recommendation.primary_tools[:3], 1):
                tool_name = tool.get("name", tool.get("tool_name", "Unknown"))
                tool_id = tool.get("id", tool.get("tool_id", "unknown"))

                # Check if tool is actually installed
                is_installed = self._verify_tool_exists(tool_id)

                parts.append(f"\n{i}. **{tool_name}** (ID: `{tool_id}`)")
                if not is_installed:
                    parts.append(
                        "   - *This tool does not appear to be installed on this Galaxy server. "
                        "Contact your administrator to request installation.*"
                    )
                parts.append(f"   - {tool.get('description', 'No description available')}")
                if "relevance_score" in tool:
                    parts.append(f"   - Relevance: {tool['relevance_score']:.0%}")
                if tool.get("input_formats"):
                    parts.append(f"   - Accepts: {', '.join(tool['input_formats'])}")
                if tool.get("output_formats"):
                    parts.append(f"   - Produces: {', '.join(tool['output_formats'])}")

        # Alternative tools
        if recommendation.alternative_tools:
            parts.append("\n**Alternative Options:**")
            for tool in recommendation.alternative_tools[:2]:
                tool_name = tool.get("name", tool.get("tool_name", "Unknown"))
                parts.append(f"- **{tool_name}**: {tool.get('description', 'No description')}")

        # Workflow suggestion
        if recommendation.workflow_suggestion:
            parts.append(f"\n**Workflow Suggestion:**\n{recommendation.workflow_suggestion}")

        # Parameter guidance
        if recommendation.parameter_guidance:
            parts.append("\n**Parameter Recommendations:**")
            for param, value in recommendation.parameter_guidance.items():
                parts.append(f"- {param}: {value}")

        # Reasoning
        if recommendation.reasoning:
            parts.append(f"\n**Why these tools?**\n{recommendation.reasoning}")

        return "\n".join(parts)

    def _create_suggestions(self, recommendation: SimplifiedToolRecommendationResult) -> list[ActionSuggestion]:
        """Create action suggestions from recommendation."""
        suggestions = []

        # Suggest running the top tool - but only if it's actually installed
        if recommendation.primary_tools:
            top_tool = recommendation.primary_tools[0]
            log.debug(f"Creating suggestion for top_tool: {top_tool}")
            tool_name = top_tool.get("name", top_tool.get("tool_name", "Unknown tool"))
            tool_id = top_tool.get("id", top_tool.get("tool_id", ""))
            log.debug(f"Extracted tool_name={tool_name}, tool_id={tool_id}")

            # Only add suggestions if we have a valid tool_id AND the tool exists
            if tool_id and self._verify_tool_exists(tool_id):
                action_confidence = ConfidenceLevel(recommendation.confidence.lower())
                suggestions.append(
                    ActionSuggestion(
                        action_type=ActionType.TOOL_RUN,
                        description=f"Open {tool_name}",
                        parameters={"tool_id": tool_id, "tool_name": tool_name},
                        confidence=action_confidence,
                        priority=1,
                    )
                )
            elif tool_id:
                log.warning(f"Tool '{tool_id}' recommended but not found in toolbox - skipping suggestion")

        return suggestions

    def _verify_tool_exists(self, tool_id: str) -> bool:
        """Verify that a tool ID actually exists in the Galaxy toolbox."""
        if not self.deps.toolbox:
            log.warning("Toolbox not available for tool verification")
            return False

        try:
            tool = self.deps.toolbox.get_tool(tool_id)
            return tool is not None and not tool.hidden
        except (AttributeError, KeyError, TypeError) as e:
            log.debug(f"Error verifying tool {tool_id}: {e}")
            return False

    def _get_fallback_content(self) -> str:
        """Get fallback content for recommendation failures."""
        return "Unable to generate tool recommendations at this time."

    def _get_simple_system_prompt(self) -> str:
        """Simple system prompt for models without structured output."""
        return """
        You are a Galaxy tool recommendation expert. Analyze the user's request and recommend tools.

        Respond in this exact format:
        TOOL: [primary tool name]
        TOOL_ID: [tool identifier]
        REASON: [why this tool is recommended]
        ALTERNATIVES: [alternative tools, comma-separated]
        CONFIDENCE: [high/medium/low]

        Example:
        TOOL: BWA-MEM
        TOOL_ID: bwa_mem
        REASON: Best for mapping paired-end reads to reference genome
        ALTERNATIVES: Bowtie2, HISAT2
        CONFIDENCE: high
        """

    def _parse_simple_response(self, response_text: str) -> dict[str, Any]:
        """Parse simple text response into structured format."""
        # Normalize text for consistent parsing
        normalized_text = normalize_llm_text(response_text)

        # Extract structured information from text
        tool = re.search(r"TOOL:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        tool_id = re.search(r"TOOL_ID:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        reason = re.search(r"REASON:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        alternatives = re.search(r"ALTERNATIVES:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        confidence_match = re.search(r"CONFIDENCE:\s*(\w+)", normalized_text, re.IGNORECASE)

        # Parse confidence level
        confidence_level = ConfidenceLevel.MEDIUM
        if confidence_match:
            conf_str = confidence_match.group(1).lower()
            if conf_str == "high":
                confidence_level = ConfidenceLevel.HIGH
            elif conf_str == "low":
                confidence_level = ConfidenceLevel.LOW

        # Build content
        content_parts = []
        if tool and tool.group(1).strip():
            tool_name = tool.group(1).strip()
            tool_id_value = tool_id.group(1).strip() if tool_id else tool_name.lower().replace(" ", "_")
            content_parts.append(f"**Recommended Tool:** {tool_name}")
            content_parts.append(f"Tool ID: `{tool_id_value}`")

        if reason and reason.group(1).strip():
            content_parts.append(f"**Why:** {reason.group(1).strip()}")

        if alternatives and alternatives.group(1).strip():
            alt_list = alternatives.group(1).strip()
            content_parts.append(f"**Alternatives:** {alt_list}")

        if not content_parts:
            content_parts = [normalized_text]  # Fallback to full response

        # Create suggestions - only if tool actually exists in toolbox
        suggestions = []
        if tool and tool.group(1).strip():
            tool_name = tool.group(1).strip()
            tool_id_value = tool_id.group(1).strip() if tool_id else tool_name.lower().replace(" ", "_")
            if self._verify_tool_exists(tool_id_value):
                suggestions.append(
                    ActionSuggestion(
                        action_type=ActionType.TOOL_RUN,
                        description=f"Run {tool_name}",
                        parameters={"tool_id": tool_id_value, "tool_name": tool_name},
                        confidence=confidence_level,
                        priority=1,
                    )
                )
            else:
                log.warning(f"Tool '{tool_id_value}' from simple response not found in toolbox - skipping suggestion")

        return {
            "content": "\n\n".join(content_parts),
            "confidence": confidence_level,
            "has_alternatives": bool(alternatives and alternatives.group(1).strip()),
            "suggestions": suggestions,
        }
