"""
Query router agent that answers directly or hands off to specialists.

Uses pydantic-ai output functions to either:
- Answer general Galaxy questions directly (returns str)
- Hand off to error_analysis for job debugging
- Hand off to custom_tool for explicit tool creation requests
"""

import logging
from pathlib import Path
from typing import (
    Any,
    Optional,
)

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
    """
    Router agent that answers queries directly or hands off to specialists.

    This agent serves as Galaxy's primary AI assistant, handling most queries
    directly and only delegating to specialist agents when their specific
    expertise is needed (error debugging, tool creation).
    """

    agent_type = AgentType.ROUTER

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, str]:
        """Create the router agent with output functions for specialist handoff."""
        model_name = self._get_agent_config("model", "")

        # DeepSeek and other models without structured output support
        # fall back to simple text-based routing
        if "deepseek" in model_name.lower():
            return Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                system_prompt=self._get_simple_system_prompt(),
            )

        # Create output functions for specialist handoff
        error_handoff = self._create_error_analysis_handoff()
        tool_handoff = self._create_custom_tool_handoff()

        return Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            output_type=[
                error_handoff,
                tool_handoff,
                str,  # Default: answer directly
            ],
            system_prompt=self.get_system_prompt(),
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the router agent."""
        prompt_path = Path(__file__).parent / "prompts" / "router.md"
        return prompt_path.read_text()

    def _create_error_analysis_handoff(self):
        """Create output function for error analysis handoff."""

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
            from .error_analysis import ErrorAnalysisAgent

            log.info(f"Router handing off to error_analysis: '{task[:100]}...'")

            try:
                agent = ErrorAnalysisAgent(ctx.deps)

                # Pass conversation history if available
                message_history = ctx.messages[:-1] if hasattr(ctx, "messages") and ctx.messages else None

                result = await agent.agent.run(
                    task,
                    deps=ctx.deps,
                    usage=ctx.usage,
                    message_history=message_history,
                )

                return extract_result_content(result)
            except Exception as e:
                log.error(f"Error analysis handoff failed: {e}")
                return (
                    f"I encountered an issue while analyzing the error. Please try again or contact support. Error: {e}"
                )

        return hand_off_to_error_analysis

    def _create_custom_tool_handoff(self):
        """Create output function for custom tool handoff."""

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
            from .custom_tool import CustomToolAgent

            log.info(f"Router handing off to custom_tool: '{request[:100]}...'")

            try:
                agent = CustomToolAgent(ctx.deps)

                # Pass conversation history if available
                message_history = ctx.messages[:-1] if hasattr(ctx, "messages") and ctx.messages else None

                result = await agent.agent.run(
                    request,
                    deps=ctx.deps,
                    usage=ctx.usage,
                    message_history=message_history,
                )

                return extract_result_content(result)
            except Exception as e:
                log.error(f"Custom tool handoff failed: {e}")
                return (
                    f"I encountered an issue while creating the tool. Please try again or contact support. Error: {e}"
                )

        return hand_off_to_custom_tool

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        """
        Process a query and return the response.

        The router now handles most queries directly, only handing off to
        specialist agents when their specific expertise is needed.
        """
        try:
            # Build the full query with conversation history if available
            full_query = self._build_query_with_context(query, context)

            # Run the agent - it will either answer directly or use a handoff function
            result = await self._run_with_retry(full_query)
            content = extract_result_content(result)

            return AgentResponse(
                content=content,
                confidence=ConfidenceLevel.HIGH,
                agent_type=self.agent_type,
                suggestions=[],
                metadata={
                    "method": "output_function",
                    "query_length": len(query),
                },
            )

        except OSError as e:
            log.warning(f"Router agent network error, using fallback: {e}")
            return self._handle_fallback(query, context, str(e))
        except ValueError as e:
            log.warning(f"Router agent value error, using fallback: {e}")
            return self._handle_fallback(query, context, str(e))

    def _build_query_with_context(self, query: str, context: Optional[dict[str, Any]]) -> str:
        """Build full query including conversation history if available."""
        if not context or "conversation_history" not in context:
            return query

        history = context["conversation_history"]
        if not history:
            return query

        history_text = "Previous conversation:\n"
        for msg in history[-6:]:  # Last 6 messages for context
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            history_text += f"{role}: {content}\n"
        history_text += f"\nCurrent query: {query}"

        return history_text

    def _handle_fallback(self, query: str, context: Optional[dict[str, Any]], error_msg: str) -> AgentResponse:
        """Handle fallback when the main agent fails."""
        query_lower = query.lower()

        # Check for citation requests
        if any(phrase in query_lower for phrase in ["cite galaxy", "citation", "reference"]):
            return AgentResponse(
                content="""To cite Galaxy, please use: Nekrutenko, A., et al. (2024). The Galaxy platform for accessible, reproducible, and collaborative data analyses: 2024 update. Nucleic Acids Research. https://doi.org/10.1093/nar/gkae410

For specific tools, please also cite the individual tool publications.""",
                confidence=ConfidenceLevel.HIGH,
                agent_type=self.agent_type,
                suggestions=[],
                metadata={"fallback": True, "reason": "citation_request"},
            )

        # Check for error-related keywords
        error_keywords = ["error", "fail", "crash", "not work", "broken", "stderr", "exit code", "died", "killed"]
        if any(kw in query_lower for kw in error_keywords):
            return AgentResponse(
                content="I noticed you're asking about an error or failure. Unfortunately, I'm having trouble connecting to the AI service right now. Please try again in a moment, or check the job details panel for error information.",
                confidence=ConfidenceLevel.LOW,
                agent_type=self.agent_type,
                suggestions=[],
                metadata={"fallback": True, "reason": "error_query_service_unavailable", "error": error_msg},
            )

        # Check for explicit tool creation keywords
        tool_keywords = ["create a tool", "build a tool", "make a tool", "wrap a tool", "tool wrapper"]
        if any(kw in query_lower for kw in tool_keywords):
            return AgentResponse(
                content="I noticed you want to create a Galaxy tool. Unfortunately, I'm having trouble connecting to the AI service right now. Please try again in a moment.",
                confidence=ConfidenceLevel.LOW,
                agent_type=self.agent_type,
                suggestions=[],
                metadata={"fallback": True, "reason": "tool_creation_service_unavailable", "error": error_msg},
            )

        # General fallback
        return AgentResponse(
            content="I'm having trouble connecting to the AI service right now. Please try again in a moment. If you have a question about Galaxy, you can also check the Galaxy Training Network (https://training.galaxyproject.org/) for tutorials and documentation.",
            confidence=ConfidenceLevel.LOW,
            agent_type=self.agent_type,
            suggestions=[],
            metadata={"fallback": True, "reason": "service_unavailable", "error": error_msg},
        )

    def _get_simple_system_prompt(self) -> str:
        """Simple system prompt for models that don't support output functions."""
        return """You are Galaxy's AI assistant. You ONLY answer questions about the Galaxy platform, Galaxy tools, and scientific data analysis (genomics, proteomics, bioinformatics, etc.).

CRITICAL: Never guess or make up information. If you don't know something, say so. Never fabricate tool names, parameters, or scientific claims. It's better to admit uncertainty than provide incorrect information.

For general Galaxy questions: Answer directly and helpfully.

For job failures or errors: Explain what might have gone wrong and suggest solutions.

For tool creation requests: Explain that you can help design Galaxy tools and provide guidance.

For off-topic questions: Politely explain you can only help with Galaxy and scientific analysis.

When uncertain, suggest the user check Galaxy documentation or the Galaxy Training Network (https://training.galaxyproject.org/)."""

    def _get_fallback_content(self) -> str:
        """Get fallback content for router failures."""
        return (
            "I'm having trouble processing your request. Please try again or check the Galaxy documentation for help."
        )
