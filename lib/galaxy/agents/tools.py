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

# Literal inlines enum values in JSON schema, avoiding $defs that vLLM can't handle
ConfidenceLiteral = Literal["low", "medium", "high"]


class SimplifiedToolRecommendationResult(BaseModel):
    """Tool recommendation result using simple types for local LLM compatibility."""

    primary_tools: list[dict[str, Any]]
    alternative_tools: list[dict[str, Any]] = []
    workflow_suggestion: Optional[str] = None
    parameter_guidance: dict[str, Any] = {}
    confidence: ConfidenceLiteral
    reasoning: str
    search_keywords: list[str] = []


class ToolRecommendationAgent(BaseGalaxyAgent):
    """Agent for recommending Galaxy tools based on user requirements."""

    agent_type = AgentType.TOOL_RECOMMENDATION

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        """Create the tool recommendation agent."""
        if self._supports_structured_output():
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                output_type=SimplifiedToolRecommendationResult,
                system_prompt=self.get_system_prompt(),
            )
        else:
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                system_prompt=self._get_simple_system_prompt(),
            )

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
        """Search for tools in Galaxy toolbox or remote source."""
        # Check if remote tool source is configured
        remote_url = getattr(self.deps.config, "agent_eval_tool_source_url", None)

        if remote_url:
            return await self._search_remote(query, remote_url)
        else:
            return await self._search_local(query)

    async def _search_local(self, query: str) -> list[dict[str, Any]]:
        """Search for tools in the local Galaxy toolbox."""
        if not self.deps.toolbox:
            log.warning("Toolbox not available in agent dependencies")
            return []

        try:
            panel_view = self.deps.config.default_panel_view or "default"
            toolbox_search = self.deps.trans.app.toolbox_search  # type: ignore[attr-defined]
            tool_ids = toolbox_search.search(query, panel_view, self.deps.config)

            tools = []
            for tool_id in tool_ids[:20]:
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

    async def _search_remote(self, query: str, base_url: str) -> list[dict[str, Any]]:
        """Search remote Galaxy instance via API."""
        try:
            import httpx
        except ImportError:
            log.warning("httpx not available for remote tool search, falling back to local")
            return await self._search_local(query)

        try:
            async with httpx.AsyncClient() as client:
                # First, search for tool IDs matching the query
                search_response = await client.get(
                    f"{base_url.rstrip('/')}/api/tools",
                    params={"q": query},
                    timeout=10.0
                )
                search_response.raise_for_status()
                tool_ids = search_response.json()

                # If no results, return empty list
                if not tool_ids:
                    log.info(f"No tools found for query '{query}' on {base_url}")
                    return []

                # Fetch full tool list to get details
                all_tools_response = await client.get(
                    f"{base_url.rstrip('/')}/api/tools",
                    timeout=15.0
                )
                all_tools_response.raise_for_status()
                all_tools_data = all_tools_response.json()

                # Extract tools from sections
                tools_with_details = []
                for item in all_tools_data:
                    if item.get("model_class") == "ToolSection":
                        for tool in item.get("elems", []):
                            if tool.get("model_class") == "Tool":
                                tools_with_details.append(tool)
                    elif item.get("model_class") == "Tool":
                        tools_with_details.append(item)

                # Filter to only the tools that matched our search
                matching_tools = [
                    {
                        "id": t["id"],
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "category": t.get("panel_section_name", ""),
                    }
                    for t in tools_with_details
                    if t["id"] in tool_ids[:50]  # Limit to top 50 search results
                ]

                log.info(f"Found {len(matching_tools)} tools for query '{query}' on {base_url}")
                return matching_tools[:20]  # Return top 20

        except Exception as e:
            log.warning(f"Remote tool search failed ({base_url}): {e}, falling back to local")
            return await self._search_local(query)

    async def get_tool_details(self, tool_id: str) -> dict[str, Any]:
        """Get detailed information about a specific tool."""
        if not self.deps.toolbox:
            return {"id": tool_id, "error": "Toolbox not available"}

        try:
            tool = self.deps.toolbox.get_tool(tool_id)
            if not tool:
                return {"id": tool_id, "error": "Tool not found"}

            details: dict[str, Any] = {
                "id": tool.id,
                "name": tool.name,
                "version": tool.version,
                "description": tool.description or "",
                "category": tool.get_panel_section()[1] or "",
                "requirements": [str(r) for r in tool.requirements] if hasattr(tool, "requirements") else [],
            }

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
        """Get tool categories/sections from the toolbox."""
        if not self.deps.toolbox:
            log.warning("Toolbox not available in agent dependencies")
            return []

        try:
            categories: set[str] = set()
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
        """Process a tool recommendation request."""
        # Fast path: bypass LLM for exact tool name matches
        try:
            trimmed_query = query.strip()
            search_results = await self.search_tools(trimmed_query)
            exact_match = None
            for tool in search_results:
                if tool.get("name", "").lower() == trimmed_query.lower():
                    exact_match = tool
                    break

            if exact_match:
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
            enhanced_query = query
            if context:
                if context.get("input_format"):
                    enhanced_query += f"\nInput format: {context['input_format']}"
                if context.get("output_format"):
                    enhanced_query += f"\nDesired output: {context['output_format']}"
                if context.get("task_type"):
                    enhanced_query += f"\nTask type: {context['task_type']}"

            result = await self._run_with_retry(enhanced_query)

            if self._supports_structured_output():
                recommendation = extract_structured_output(result, SimplifiedToolRecommendationResult, log)

                if recommendation is None:
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

        except (OSError, ValueError) as e:
            log.warning(f"Tool recommendation failed: {e}")
            return self._get_fallback_response(query, str(e))

    def _format_recommendation_response(self, recommendation: SimplifiedToolRecommendationResult) -> str:
        """Format the recommendation into user-friendly content."""
        parts = []

        if recommendation.primary_tools:
            parts.append("**Recommended Tools:**")
            for i, tool in enumerate(recommendation.primary_tools[:3], 1):
                tool_name = tool.get("name", tool.get("tool_name", "Unknown"))
                tool_id = tool.get("id", tool.get("tool_id", "unknown"))

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

        if recommendation.alternative_tools:
            parts.append("\n**Alternative Options:**")
            for tool in recommendation.alternative_tools[:2]:
                tool_name = tool.get("name", tool.get("tool_name", "Unknown"))
                parts.append(f"- **{tool_name}**: {tool.get('description', 'No description')}")

        if recommendation.workflow_suggestion:
            parts.append(f"\n**Workflow Suggestion:**\n{recommendation.workflow_suggestion}")

        if recommendation.parameter_guidance:
            parts.append("\n**Parameter Recommendations:**")
            for param, value in recommendation.parameter_guidance.items():
                parts.append(f"- {param}: {value}")

        if recommendation.reasoning:
            parts.append(f"\n**Why these tools?**\n{recommendation.reasoning}")

        return "\n".join(parts)

    def _create_suggestions(self, recommendation: SimplifiedToolRecommendationResult) -> list[ActionSuggestion]:
        """Create action suggestions from recommendation."""
        suggestions = []

        if recommendation.primary_tools:
            top_tool = recommendation.primary_tools[0]
            log.debug(f"Creating suggestion for top_tool: {top_tool}")
            tool_name = top_tool.get("name", top_tool.get("tool_name", "Unknown tool"))
            tool_id = top_tool.get("id", top_tool.get("tool_id", ""))
            log.debug(f"Extracted tool_name={tool_name}, tool_id={tool_id}")

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
        """Check if a tool ID exists in the Galaxy toolbox."""
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
        normalized_text = normalize_llm_text(response_text)

        tool = re.search(r"TOOL:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        tool_id = re.search(r"TOOL_ID:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        reason = re.search(r"REASON:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        alternatives = re.search(r"ALTERNATIVES:\s*([^\n]+)", normalized_text, re.IGNORECASE)
        confidence_match = re.search(r"CONFIDENCE:\s*(\w+)", normalized_text, re.IGNORECASE)

        confidence_level = ConfidenceLevel.MEDIUM
        if confidence_match:
            conf_str = confidence_match.group(1).lower()
            if conf_str == "high":
                confidence_level = ConfidenceLevel.HIGH
            elif conf_str == "low":
                confidence_level = ConfidenceLevel.LOW

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
            content_parts = [normalized_text]

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
