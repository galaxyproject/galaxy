"""
Query router agent that answers directly or hands off to specialists.

Uses pydantic-ai output functions to either:
- Answer general Galaxy questions directly (returns str)
- Hand off to error_analysis for job debugging
- Hand off to custom_tool for explicit tool creation requests
- Hand off to tool_recommendation for tool discovery
"""

import json
import logging
from pathlib import Path
from typing import (
    Any,
    Optional,
)

from pydantic import ValidationError
from pydantic_ai import (
    Agent,
    RunContext,
)

from galaxy.schema.agents import ConfidenceLevel
from .base import (
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    extract_result_content,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)


class QueryRouterAgent(BaseGalaxyAgent):
    """Router that answers queries directly or delegates to specialist agents."""

    agent_type = AgentType.ROUTER

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, str]:
        model_name = self._get_agent_config("model", "")

        if "deepseek" in model_name.lower():
            return Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                system_prompt=self._get_simple_system_prompt(),
            )

        error_handoff = self._create_error_analysis_handoff()
        tool_handoff = self._create_custom_tool_handoff()
        tool_rec_handoff = self._create_tool_recommendation_handoff()
        history_handoff = self._create_history_handoff()
        next_step_handoff = self._create_next_step_advisor_handoff()
        orchestrator_handoff = self._create_orchestrator_handoff()

        return Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            output_type=[
                error_handoff,
                tool_handoff,
                tool_rec_handoff,
                history_handoff,
                next_step_handoff,
                orchestrator_handoff,
                str,  # Default: answer directly
            ],
            system_prompt=self.get_system_prompt(),
        )

    def get_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "router.md"
        return prompt_path.read_text()

    def _serialize_handoff(self, response: AgentResponse, target_agent: str) -> str:
        """Wrap a delegated agent's response in JSON to pass through the router's output function."""
        return json.dumps(
            {
                "__handoff__": True,
                "content": response.content,
                "agent_type": response.agent_type,
                "confidence": (
                    response.confidence.value if hasattr(response.confidence, "value") else response.confidence
                ),
                "metadata": response.metadata,
                "suggestions": [
                    s.model_dump() if hasattr(s, "model_dump") else s for s in (response.suggestions or [])
                ],
                "handoff_info": {
                    "source_agent": self.agent_type,
                    "target_agent": target_agent,
                },
            }
        )

    async def _execute_handoff(
        self,
        ctx: RunContext[GalaxyAgentDependencies],
        agent_type: str,
        input_text: str,
        target_agent: str | None = None,
    ) -> str:
        """Execute a handoff to a specialist agent."""
        handoff_target = target_agent or agent_type
        log.info(f"Router handing off to {handoff_target}: '{input_text[:100]}...'")
        try:
            agent = ctx.deps.get_agent(agent_type, ctx.deps)
            response = await agent.process(input_text)
            return self._serialize_handoff(response, handoff_target)
        except ValueError as e:
            log.warning(f"{handoff_target} handoff unavailable: {e}")
            return (
                f"The '{handoff_target}' agent is not available in this Galaxy configuration. "
                "Please try a different request or contact your administrator."
            )
        except OSError as e:
            log.error(f"{handoff_target} handoff failed: {e}")
            return f"I encountered an issue ({type(e).__name__}). Please try again or contact support."

    def _create_error_analysis_handoff(self):
        async def hand_off_to_error_analysis(
            ctx: RunContext[GalaxyAgentDependencies],
            task: str,
        ) -> str:
            """Route to error analysis agent for debugging job failures, tool errors, and crash analysis.

            Use this when the user:
            - Has a failed job with error messages or exit codes
            - Is asking about stderr/stdout from a tool run
            - Needs help understanding why a tool crashed
            - Shows error logs they want explained

            Args:
                task: Description of the error or debugging task to analyze
            """
            return await self._execute_handoff(ctx, AgentType.ERROR_ANALYSIS, task)

        return hand_off_to_error_analysis

    def _create_custom_tool_handoff(self):
        async def hand_off_to_custom_tool(
            ctx: RunContext[GalaxyAgentDependencies],
            request: str,
        ) -> str:
            """Route to custom tool agent for explicit Galaxy tool creation requests.

            Use this ONLY when the user explicitly:
            - Asks to CREATE, BUILD, or MAKE a new Galaxy tool
            - Wants to WRAP a command-line tool for Galaxy
            - Requests generating a tool definition (XML/YAML)

            Do NOT use for:
            - Tool discovery ("what tool does X?")
            - Tool usage help ("how do I run BWA?")

            Args:
                request: Description of the tool to create
            """
            return await self._execute_handoff(ctx, AgentType.CUSTOM_TOOL, request)

        return hand_off_to_custom_tool

    def _create_tool_recommendation_handoff(self):
        async def hand_off_to_tool_recommendation(
            ctx: RunContext[GalaxyAgentDependencies],
            query: str,
        ) -> str:
            """Route to tool recommendation agent for finding Galaxy tools.

            Use this when the user:
            - Asks what tool to use for a task ("what tool aligns reads?")
            - Wants to find tools for a specific analysis type
            - Needs help discovering available tools
            - Asks "is there a tool that does X?"

            Do NOT use for:
            - How to USE a specific tool (answer directly)
            - Creating NEW tools (use hand_off_to_custom_tool)
            - Job errors (use hand_off_to_error_analysis)

            Args:
                query: The tool discovery question
            """
            return await self._execute_handoff(ctx, AgentType.TOOL_RECOMMENDATION, query)

        return hand_off_to_tool_recommendation

    def _create_history_handoff(self):
        async def hand_off_to_history_agent(
            ctx: RunContext[GalaxyAgentDependencies],
            request: str,
        ) -> str:
            """Route to history agent for questions about Galaxy histories, datasets, and results.

            Use this when the user:
            - Asks to summarize or describe their history or analysis
            - Wants to know what they did in their analysis
            - Asks for a methods section for publication
            - Wants to understand the workflow or steps in a history
            - Asks about tools used, inputs, or outputs in their analysis
            - Mentions "my history", "my analysis", or similar
            - Asks about specific datasets or outputs ("is this result good?", "what does this dataset mean?")
            - Wants to know what's in their history
            - Asks about data quality or result interpretation

            Examples:
            - "Summarize my history"
            - "What analysis did I do?"
            - "Generate a methods section"
            - "What tools did I use?"
            - "Describe my RNA-seq analysis"
            - "Is the last dataset in my history a good result?"
            - "What does this output mean?"
            - "What's in my history?"

            Args:
                request: The user's request about their history/analysis
            """
            return await self._execute_handoff(ctx, AgentType.HISTORY, request)

        return hand_off_to_history_agent

    def _create_next_step_advisor_handoff(self):
        async def hand_off_to_next_step_advisor(
            ctx: RunContext[GalaxyAgentDependencies],
            request: str,
        ) -> str:
            """Orchestrate multiple agents to provide next-step advice and recommendations.

            Use this when the user:
            - Asks "what should I do next?" or "what's a good next step?"
            - Says "given my history/analysis, what should I..."
            - Wants suggestions or recommendations based on their current work
            - Asks for tutorials or learning resources related to their analysis
            - Needs guidance on continuing their workflow

            Args:
                request: The user's request about next steps or recommendations
            """
            return await self._execute_handoff(ctx, AgentType.ORCHESTRATOR, request, "next_step_advisor")

        return hand_off_to_next_step_advisor

    def _create_orchestrator_handoff(self):
        async def hand_off_to_orchestrator(
            ctx: RunContext[GalaxyAgentDependencies],
            request: str,
        ) -> str:
            """Route to orchestrator for queries requiring multiple agents to work together.

            Use this when the user's query explicitly requires multiple capabilities:
            - "Summarize my history AND suggest what tool to use next" (history + tool_recommendation)
            - "Debug this error AND suggest what to try next" (error_analysis + history)
            - "Analyze my workflow AND suggest improvements" (multiple agents)
            - Any request with "and" connecting distinct capabilities

            Do NOT use for single-capability queries - use the specific handoff instead.

            Args:
                request: The user's multi-faceted request
            """
            return await self._execute_handoff(ctx, AgentType.ORCHESTRATOR, request)

        return hand_off_to_orchestrator

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        validation_error = self._validate_query(query)
        if validation_error:
            return self._validation_error_response(validation_error)

        try:
            if context and context.get("conversation_history"):
                log.info(f"Router: Conversation has {len(context['conversation_history'])} messages")
            else:
                log.info("Router: Processing query with no conversation history")

            full_query = self._build_query_with_context(query, context)
            log.info(f"Router: Full query length={len(full_query)} (original={len(query)})")

            result = await self._run_with_retry(full_query)
            content = extract_result_content(result)

            try:
                handoff_data = json.loads(content)
                if handoff_data.get("__handoff__"):
                    metadata = handoff_data.get("metadata", {})
                    if handoff_data.get("handoff_info"):
                        metadata["handoff_info"] = handoff_data["handoff_info"]
                    return AgentResponse(
                        content=handoff_data["content"],
                        confidence=ConfidenceLevel(handoff_data.get("confidence", "medium")),
                        agent_type=handoff_data.get("agent_type", self.agent_type),
                        suggestions=handoff_data.get("suggestions", []),
                        metadata=metadata,
                    )
            except (json.JSONDecodeError, TypeError, KeyError, ValidationError) as e:
                log.debug(f"Router: Response not a handoff (parse failed: {e}), treating as direct response")

            return self._build_response(
                content=content,
                confidence=ConfidenceLevel.HIGH,
                method="output_function",
                result=result,
                query=query,
            )

        except (OSError, ValueError) as e:
            log.warning(f"Router agent error, using fallback: {e}")
            return self._handle_fallback(query, context, str(e))

    def _build_query_with_context(self, query: str, context: Optional[dict[str, Any]]) -> str:
        parts: list[str] = []

        if context:
            interface_ctx = context.get("interface_context")
            if interface_ctx and isinstance(interface_ctx, dict):
                description = self._format_interface_context(interface_ctx)
                if description:
                    parts.append(f"[Active interface context: {description}]")

            history = context.get("conversation_history")
            if history:
                history_text = "Previous conversation:\n"
                for msg in history[-6:]:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    history_text += f"{role}: {content}\n"
                parts.append(history_text)

        parts.append(f"Current query: {query}" if parts else query)
        return "\n".join(parts)

    def _handle_fallback(self, query: str, context: Optional[dict[str, Any]], error_msg: str) -> AgentResponse:
        query_lower = query.lower()

        # Citation requests can be answered without AI
        if any(phrase in query_lower for phrase in ["cite galaxy", "citation", "reference"]):
            return self._build_response(
                content="""To cite Galaxy, please use: Nekrutenko, A., et al. (2024). The Galaxy platform for accessible, reproducible, and collaborative data analyses: 2024 update. Nucleic Acids Research. https://doi.org/10.1093/nar/gkae410

For specific tools, please also cite the individual tool publications.""",
                confidence=ConfidenceLevel.HIGH,
                method="fallback",
                query=query,
                fallback=True,
                agent_data={"reason": "citation_request"},
            )

        return self._build_response(
            content="The AI service is currently unavailable. Please try again in a moment. "
            "In the meantime, you can browse the Galaxy Training Network "
            "(https://training.galaxyproject.org/) for tutorials and documentation.",
            confidence=ConfidenceLevel.LOW,
            method="fallback",
            query=query,
            fallback=True,
            error=error_msg,
        )

    def _get_simple_system_prompt(self) -> str:
        return """You are Galaxy's AI assistant. You ONLY answer questions about the Galaxy platform, Galaxy tools, and scientific data analysis (genomics, proteomics, bioinformatics, etc.).

CRITICAL: Never guess or make up information. If you don't know something, say so. Never fabricate tool names, parameters, or scientific claims. It's better to admit uncertainty than provide incorrect information.

For general Galaxy questions: Answer directly and helpfully.

For job failures or errors: Explain what might have gone wrong and suggest solutions.

For tool creation requests: Explain that you can help design Galaxy tools and provide guidance.

For history analysis requests: Explain that you can help summarize their analysis, generate methods sections, or describe what was done in a history.

For off-topic questions: Politely explain you can only help with Galaxy and scientific analysis.

When uncertain, suggest the user check Galaxy documentation or the Galaxy Training Network (https://training.galaxyproject.org/)."""

    def _get_fallback_content(self) -> str:
        return (
            "I'm having trouble processing your request. Please try again or check the Galaxy documentation for help."
        )
