"""
Tool recommendation agent for suggesting appropriate Galaxy tools.
"""

import logging
import re
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
)
from pydantic_ai import Agent
from pydantic_ai.tools import RunContext

from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    BaseGalaxyAgent,
    ConfidenceLevel,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)


class SimplifiedToolRecommendationResult(BaseModel):
    """Simplified result for local LLMs - avoids nested models."""

    # Instead of nested ToolMatch objects, we'll use simple dictionaries
    primary_tools: List[Dict[str, Any]]  # Each dict has tool_id, tool_name, description, etc.
    alternative_tools: List[Dict[str, Any]] = []
    workflow_suggestion: Optional[str] = None
    parameter_guidance: Dict[str, Any] = {}
    confidence: Union[str, ConfidenceLevel]  # "low", "medium", or "high"
    reasoning: str
    search_keywords: List[str] = []


class ToolRecommendationAgent(BaseGalaxyAgent):
    """
    Agent for recommending appropriate Galaxy tools based on user requirements.

    This agent helps users discover tools, understand tool capabilities,
    and provides guidance on tool selection and parameter configuration.
    """

    def _create_agent(self) -> Agent:
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
        async def get_training_materials(
            ctx: RunContext[GalaxyAgentDependencies], tool_names: str, analysis_type: str = ""
        ) -> str:
            """Get relevant training materials and tutorials for specified tools or analysis types."""
            query = f"Find tutorials and training materials for {tool_names}"
            if analysis_type:
                query += f" for {analysis_type} analysis"

            return await self._call_agent_from_tool("gtn_training", query, ctx)

        return agent

    def get_system_prompt(self) -> str:
        """Get the system prompt for tool recommendation."""
        prompt_path = Path(__file__).parent / "prompts" / "tool_recommendation.md"
        return prompt_path.read_text()

    async def search_tools(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for tools in the Galaxy toolbox."""
        if not self.deps.toolbox:
            log.warning("Toolbox not available in agent dependencies")
            return []

        try:
            # Get the default panel view (usually 'default')
            panel_view = self.deps.config.default_panel_view or "default"

            # Use Galaxy's built-in tool search via the app's toolbox_search
            toolbox_search = self.deps.trans.app.toolbox_search
            tool_ids = toolbox_search.search(query, panel_view, self.deps.config)

            # Get tool details for found tools
            tools = []
            for tool_id in tool_ids[:20]:  # Limit to top 20 results
                tool = self.deps.toolbox.get_tool(tool_id)
                if tool and not tool.hidden:
                    tools.append({
                        "id": tool.id,
                        "name": tool.name,
                        "description": tool.description or "",
                        "category": tool.get_panel_section()[1] or "",
                    })

            return tools

        except Exception as e:
            log.error(f"Error searching tools: {e}")
            return []

    async def get_tool_details(self, tool_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific tool."""
        if not self.deps.toolbox:
            return {"id": tool_id, "error": "Toolbox not available"}

        try:
            tool = self.deps.toolbox.get_tool(tool_id)
            if not tool:
                return {"id": tool_id, "error": "Tool not found"}

            # Build comprehensive tool details
            details = {
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
                        details["inputs"].append({
                            "name": input_name,
                            "type": input_param.type,
                            "label": getattr(input_param, "label", input_name),
                        })

            # Add output information
            if hasattr(tool, "outputs"):
                details["outputs"] = []
                for output_name, output_param in tool.outputs.items():
                    details["outputs"].append({
                        "name": output_name,
                        "format": getattr(output_param, "format", "unknown"),
                    })

            return details

        except Exception as e:
            log.error(f"Error getting tool details for {tool_id}: {e}")
            return {"id": tool_id, "error": str(e)}

    async def check_tool_compatibility(self, tool_id: str, input_format: str) -> bool:
        """
        Check if a tool is compatible with a given input format.

        Args:
            tool_id: Galaxy tool identifier
            input_format: Input data format

        Returns:
            True if compatible, False otherwise
        """
        try:
            tool_details = await self.get_tool_details(tool_id)
            if "inputs" in tool_details:
                for input_spec in tool_details["inputs"]:
                    if "format" in input_spec:
                        formats = input_spec["format"].split(",")
                        if input_format in formats or "any" in formats:
                            return True
            return False
        except Exception as e:
            log.error(f"Error checking compatibility: {e}")
            return False

    async def get_tool_categories(self) -> List[str]:
        """
        Get available tool categories in Galaxy.

        Returns:
            List of tool categories
        """
        return [
            "Text Manipulation",
            "NGS: Mapping",
            "NGS: QC",
            "NGS: Assembly",
            "Variant Calling",
            "RNA-seq",
            "ChIP-seq",
            "Genome Annotation",
            "Phylogenetics",
            "Proteomics",
            "Visualization",
            "File Conversion",
            "Statistics",
            "Utilities",
        ]

    async def process(self, query: str, context: Dict[str, Any] = None) -> AgentResponse:
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
                    confidence="high",
                    reasoning=f"This is the tool with the exact name you requested.",
                    search_keywords=[trimmed_query],
                )

                content = self._format_recommendation_response(recommendation)
                suggestions = self._create_suggestions(recommendation)

                return AgentResponse(
                    content=content,
                    confidence="high",
                    agent_type=self.agent_type,
                    suggestions=suggestions,
                    metadata={"method": "fast_path_exact_match"},
                    reasoning=f"Directly matched tool name '{exact_match['name']}'.",
                )
        except Exception as e:
            log.warning(f"Fast path tool search failed: {e}. Proceeding with LLM.")

        try:
            # Extract keywords from query
            keywords = self._extract_keywords(query)

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
                # Handle structured output
                if hasattr(result, "output"):
                    recommendation = result.output
                elif hasattr(result, "data"):
                    recommendation = result.data
                else:
                    recommendation = result

                content = self._format_recommendation_response(recommendation)
                suggestions = self._create_suggestions(recommendation)

                return AgentResponse(
                    content=content,
                    confidence=recommendation.confidence,
                    agent_type=self.agent_type,
                    suggestions=suggestions,
                    metadata={
                        "num_tools_found": len(recommendation.primary_tools),
                        "has_alternatives": bool(recommendation.alternative_tools),
                        "has_workflow": bool(recommendation.workflow_suggestion),
                        "search_keywords": recommendation.search_keywords,
                        "method": "structured",
                    },
                    reasoning=recommendation.reasoning,
                )
            else:
                # Handle simple text output from DeepSeek
                response_text = str(result.data) if hasattr(result, "data") else str(result)
                parsed_result = self._parse_simple_response(response_text)

                return AgentResponse(
                    content=parsed_result.get("content", response_text),
                    confidence=parsed_result.get("confidence", "medium"),
                    agent_type=self.agent_type,
                    suggestions=parsed_result.get("suggestions", []),
                    metadata={
                        "method": "simple_text",
                        "has_alternatives": parsed_result.get("has_alternatives", False),
                    },
                )

        except Exception as e:
            log.error(f"Tool recommendation failed: {e}")
            return self._get_fallback_response(query, str(e))

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract relevant keywords from user query."""
        # Remove common words
        stop_words = {
            "i",
            "want",
            "to",
            "need",
            "help",
            "with",
            "for",
            "a",
            "an",
            "the",
            "my",
            "data",
            "file",
            "files",
            "how",
            "do",
            "can",
        }

        # Extract words
        words = re.findall(r"\b\w+\b", query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Add task-specific keywords
        task_keywords = {
            "align": ["alignment", "mapping", "reference"],
            "quality": ["qc", "quality", "control", "check"],
            "variant": ["snp", "indel", "variant", "calling", "vcf"],
            "expression": ["rna", "rnaseq", "differential", "expression", "counts"],
            "assembly": ["assemble", "assembly", "contigs", "scaffolds"],
            "annotation": ["annotate", "annotation", "genes", "features"],
        }

        for task, related in task_keywords.items():
            if task in query.lower():
                keywords.extend(related)

        return list(set(keywords))

    def _format_recommendation_response(self, recommendation: SimplifiedToolRecommendationResult) -> str:
        """Format the recommendation into user-friendly content."""
        parts = []

        # Primary recommendations
        if recommendation.primary_tools:
            parts.append("**Recommended Tools:**")
            for i, tool in enumerate(recommendation.primary_tools[:3], 1):
                tool_name = tool.get("name", tool.get("tool_name", "Unknown"))
                tool_id = tool.get("id", tool.get("tool_id", "unknown"))
                parts.append(f"\n{i}. **{tool_name}** (ID: `{tool_id}`)")
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

    def _create_suggestions(self, recommendation: SimplifiedToolRecommendationResult) -> List[ActionSuggestion]:
        """Create action suggestions from recommendation."""
        suggestions = []

        # Suggest running the top tool
        if recommendation.primary_tools:
            top_tool = recommendation.primary_tools[0]
            tool_name = top_tool.get("name", top_tool.get("tool_name", "Unknown tool"))
            tool_id = top_tool.get("id", top_tool.get("tool_id", ""))
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.TOOL_RUN,
                    description=f"Run {tool_name}",
                    parameters={"tool_id": tool_id, "tool_name": tool_name},
                    confidence="medium" if recommendation.confidence == "medium" else "high",
                    priority=1,
                )
            )

        # Suggest workflow if applicable
        if recommendation.workflow_suggestion:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.WORKFLOW_STEP,
                    description="Follow recommended workflow",
                    confidence="medium",
                    priority=2,
                )
            )

        # Suggest documentation review
        if recommendation.primary_tools:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.DOCUMENTATION,
                    description="Review tool documentation",
                    confidence="high",
                    priority=3,
                )
            )

        # Parameter changes if recommended
        if recommendation.parameter_guidance:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.PARAMETER_CHANGE,
                    description="Apply recommended parameters",
                    parameters=recommendation.parameter_guidance,
                    confidence="medium",
                    priority=2,
                )
            )

        return suggestions

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

    def _parse_simple_response(self, response_text: str) -> Dict[str, Any]:
        """Parse simple text response into structured format."""
        import re

        # Extract structured information from text
        tool = re.search(r"TOOL:\s*([^\n]+)", response_text, re.IGNORECASE)
        tool_id = re.search(r"TOOL_ID:\s*([^\n]+)", response_text, re.IGNORECASE)
        reason = re.search(r"REASON:\s*([^\n]+)", response_text, re.IGNORECASE)
        alternatives = re.search(r"ALTERNATIVES:\s*([^\n]+)", response_text, re.IGNORECASE)
        confidence = re.search(r"CONFIDENCE:\s*(\w+)", response_text, re.IGNORECASE)

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
            content_parts = [response_text]  # Fallback to full response

        # Create suggestions
        suggestions = []
        if tool and tool.group(1).strip():
            suggestions.append(
                {
                    "action_type": "TOOL_RUN",
                    "description": f"Run {tool.group(1).strip()}",
                    "confidence": confidence.group(1).lower() if confidence else "medium",
                    "priority": 1,
                }
            )

        return {
            "content": "\n\n".join(content_parts),
            "confidence": confidence.group(1).lower() if confidence else "medium",
            "has_alternatives": bool(alternatives and alternatives.group(1).strip()),
            "suggestions": suggestions,
        }

