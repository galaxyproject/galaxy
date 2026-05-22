"""
Query router agent that answers directly or hands off to specialists.

Uses pydantic-ai output functions to either:
- Answer general Galaxy questions directly (returns str)
- Hand off to error_analysis for job debugging
- Hand off to custom_tool for explicit tool creation requests
- Hand off to tool_recommendation for tool discovery
- Hand off to gtn_training for tutorial and learning requests

Also exposes a small set of @agent.tool fast-path tools for read-only browsing
queries (list histories/workflows, get user info, get a history summary) so the
router can answer those directly without round-tripping through a specialist.
"""

import json
import logging
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Optional,
)

import anyio
from pydantic import ValidationError
from pydantic_ai import (
    Agent,
    RunContext,
)

from galaxy.agents.operations import AgentOperationsManager
from galaxy.exceptions import MalformedId
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
        gtn_handoff = self._create_gtn_training_handoff()

        agent: Agent[GalaxyAgentDependencies, str] = Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            output_type=[
                error_handoff,
                tool_handoff,
                tool_rec_handoff,
                history_handoff,
                next_step_handoff,
                orchestrator_handoff,
                gtn_handoff,
                str,  # Default: answer directly
            ],
            system_prompt=self.get_system_prompt(),
        )

        self._register_fast_path_tools(agent)
        return agent

    def _register_fast_path_tools(self, agent: Agent[GalaxyAgentDependencies, str]) -> None:
        """Register stateless read-only tools that the router can use directly.

        These are only for low-cost browsing queries that map to a single
        AgentOperationsManager call. Anything that needs domain reasoning,
        multi-step context building, or structured output should still hand
        off to the appropriate specialist.
        """

        def _ops(ctx: RunContext[GalaxyAgentDependencies]) -> AgentOperationsManager:
            return AgentOperationsManager(app=ctx.deps.trans.app, trans=ctx.deps.trans)

        @agent.tool
        async def list_histories(ctx: RunContext[GalaxyAgentDependencies], limit: int = 10) -> dict[str, Any]:
            """List the user's Galaxy histories (most recently updated first).

            Use this for browsing questions like "what histories do I have?" or
            "list my recent histories". Returns id, name, and summary metadata.
            For deeper analysis of a specific history, hand off to the history
            specialist instead.
            """
            ops = _ops(ctx)
            return await anyio.to_thread.run_sync(partial(ops.list_histories, limit=limit))

        @agent.tool
        async def get_history_summary(ctx: RunContext[GalaxyAgentDependencies], history_id: str) -> dict[str, Any]:
            """Get summary metadata for a single history (name, annotation, tags, counts).

            Use this for direct lookups when the user already has a history id.
            For interpretation of contents, methods sections, or workflow
            reconstruction, hand off to the history specialist.
            """
            ops = _ops(ctx)
            try:
                return await anyio.to_thread.run_sync(partial(ops.get_history_details, history_id))
            except MalformedId:
                return {"error": f"Invalid history_id '{history_id}'. Use list_histories to find a valid id."}

        @agent.tool
        async def list_workflows(ctx: RunContext[GalaxyAgentDependencies], filter: str = "") -> dict[str, Any]:
            """List the user's stored workflows, optionally filtered by a search string.

            Use this for "what workflows do I have?" style questions. The
            ``filter`` argument is passed to the workflow index search.
            """
            ops = _ops(ctx)
            search = filter or None
            return await anyio.to_thread.run_sync(partial(ops.list_workflows, search=search))

        @agent.tool
        async def search_workflows(
            ctx: RunContext[GalaxyAgentDependencies], query: str, limit: int = 10
        ) -> dict[str, Any]:
            """Search the user's local/shared Galaxy workflows by name or description.

            Use this for availability questions like "do I have an RNA-seq
            workflow?" or "find workflows for variant calling". Searches only
            local/shared workflows, not the public IWC catalog. For
            recommendations ("which workflow should I use?"), hand off to the
            tool/recommendation specialist instead.
            """
            ops = _ops(ctx)
            return await anyio.to_thread.run_sync(partial(ops.list_workflows, search=query, limit=limit))

        @agent.tool
        async def search_tools(ctx: RunContext[GalaxyAgentDependencies], query: str, limit: int = 10) -> dict[str, Any]:
            """Search the installed Galaxy toolbox by name/description for availability.

            Use this for "is FastQC installed?", "do we have BWA?", or "show me
            tools matching 'trim adapters'". Returns matching tools as id, name,
            description, version. For recommendations ("what tool should I use
            for my analysis?"), hand off to the tool_recommendation specialist
            instead.
            """
            ops = _ops(ctx)
            result = await anyio.to_thread.run_sync(partial(ops.search_tools, query))
            tools = result.get("tools", [])
            effective_limit = max(1, min(limit, 50)) if limit and limit > 0 else 10
            if len(tools) > effective_limit:
                result = {
                    **result,
                    "tools": tools[:effective_limit],
                    "count": effective_limit,
                    "truncated": True,
                }
            return result

        @agent.tool
        async def get_user_info(ctx: RunContext[GalaxyAgentDependencies]) -> dict[str, Any]:
            """Return the current authenticated user (id, email, username, admin flag).

            Use this when the user asks "who am I?", "what's my username?", or
            similar account-identity questions.
            """
            ops = _ops(ctx)
            return await anyio.to_thread.run_sync(ops.get_user)

        @agent.tool
        async def get_server_info(ctx: RunContext[GalaxyAgentDependencies]) -> dict[str, Any]:
            """Return Galaxy server metadata (version, brand, URL, capability flags).

            Use this when the user asks "what version of Galaxy is this?",
            "what's the server URL?", or about server-level capabilities like
            quotas / user creation / dataset purging.
            """
            ops = _ops(ctx)
            return await anyio.to_thread.run_sync(ops.get_server_info)

        @agent.tool
        async def list_file_source_templates(ctx: RunContext[GalaxyAgentDependencies]) -> dict[str, Any]:
            """List the catalog of remote data repository plugins Galaxy supports.

            Use this when the user asks about uploading to, exporting to, or
            connecting a remote repository (Omero, Dropbox, S3, Zenodo,
            Invenio, Google Drive, etc.) -- the result confirms whether that
            target is supported and surfaces its template id for the
            configure-then-export flow. Returns plugin templates only; for
            the user's already-configured connections use
            ``list_user_file_sources``.
            """
            ops = _ops(ctx)
            return await anyio.to_thread.run_sync(ops.list_file_source_templates)

        @agent.tool
        async def list_user_file_sources(ctx: RunContext[GalaxyAgentDependencies]) -> dict[str, Any]:
            """List the remote-repository file source instances the user has configured.

            Use this when the user asks "what file sources do I have set up?"
            or needs to reference a specific configured connection (by name or
            uuid) -- e.g. when picking an Omero instance to export to. Returns
            only this user's instances. For the catalog of plugin templates
            available to configure, use ``list_file_source_templates``.
            """
            ops = _ops(ctx)
            return await anyio.to_thread.run_sync(ops.list_user_file_sources)

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

    def _create_gtn_training_handoff(self):
        async def hand_off_to_gtn_training(
            ctx: RunContext[GalaxyAgentDependencies],
            query: str,
        ) -> str:
            """Route to GTN training agent for tutorial searches and learning guidance.

            Use this when the user:
            - Asks how to perform a specific type of analysis (RNA-seq, variant calling, etc.)
            - Wants to learn how to use Galaxy or specific tools
            - Is looking for tutorials, training materials, or learning resources
            - Asks about best practices for an analysis workflow
            - Wants step-by-step guidance for a bioinformatics task

            Args:
                query: The user's question about training, tutorials, or how to do analysis
            """
            return await self._execute_handoff(ctx, AgentType.GTN_TRAINING, query)

        return hand_off_to_gtn_training

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        validation_error = self._validate_query(query)
        if validation_error:
            return self._validation_error_response(validation_error)

        try:
            message_history = self._extract_message_history(context)
            if message_history:
                log.info(f"Router: passing {len(message_history)} prior messages as message_history")
            else:
                log.info("Router: processing query with no conversation history")

            result = await self._run_with_retry(query, message_history=message_history)
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

For training/tutorial requests: Search the Galaxy Training Network for relevant tutorials.

For off-topic questions: Politely explain you can only help with Galaxy and scientific analysis.

When uncertain, suggest the user check Galaxy documentation or the Galaxy Training Network (https://training.galaxyproject.org/)."""

    def _get_fallback_content(self) -> str:
        return (
            "I'm having trouble processing your request. Please try again or check the Galaxy documentation for help."
        )
