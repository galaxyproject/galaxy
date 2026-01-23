"""
History Analyzer agent for understanding and summarizing Galaxy histories.

This agent analyzes a Galaxy history, gathers information about all datasets
and tools used, and can generate summaries, methods sections, or answer
questions about what was done in the analysis.
"""

import logging
from pathlib import Path
from typing import (
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
)
from pydantic_ai import Agent
from pydantic_ai.tools import RunContext

from galaxy.exceptions import MalformedId
from galaxy.managers.agent_operations import AgentOperationsManager
from .base import (
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    extract_structured_output,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)

ConfidenceLiteral = Literal["low", "medium", "high"]


class HistoryAnalysis(BaseModel):
    """Structured output for history analysis."""

    title: str = Field(description="A concise title summarizing the analysis")
    summary: str = Field(description="Brief summary of what was done in the history")
    workflow_description: str = Field(description="Description of the analysis workflow and steps")
    tools_used: list[str] = Field(description="List of tool names used in the analysis")
    tool_versions: dict[str, str] = Field(default_factory=dict, description="Tool versions used")
    citations: list[str] = Field(default_factory=list, description="Formatted citations for tools used")
    input_data: list[str] = Field(default_factory=list, description="Description of input datasets")
    output_data: list[str] = Field(default_factory=list, description="Description of output datasets")
    methods_text: str = Field(default="", description="Publication-ready methods section text")
    confidence: ConfidenceLiteral = Field(default="medium", description="Confidence in the analysis")


class HistoryAnalyzerAgent(BaseGalaxyAgent):
    """
    Agent for analyzing and summarizing Galaxy histories.

    This agent uses AgentOperationsManager to access history contents, dataset details,
    job information, and tool citations. It can generate summaries, publication-ready
    methods sections, or answer questions about what was done in the analysis.
    """

    agent_type = AgentType.HISTORY_ANALYZER

    def __init__(self, deps: GalaxyAgentDependencies):
        """Initialize the agent with dependencies."""
        super().__init__(deps)
        self.ops = AgentOperationsManager(app=deps.trans.app, trans=deps.trans)

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        """Create the pydantic-ai agent with tools for Galaxy data access."""
        agent = Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            output_type=HistoryAnalysis,
            system_prompt=self.get_system_prompt(),
        )

        @agent.tool
        async def list_user_histories(ctx: RunContext[GalaxyAgentDependencies], limit: int = 20) -> dict[str, Any]:
            """List the user's Galaxy histories to find which one to analyze.

            Call this first to discover available histories before analyzing one.
            Returns histories sorted by most recently updated.
            """
            return self.ops.list_histories(limit=limit)

        @agent.tool
        async def get_history_info(ctx: RunContext[GalaxyAgentDependencies], history_id: str) -> dict[str, Any]:
            """Get metadata about a Galaxy history including name, annotation, and tags."""
            try:
                return self.ops.get_history_details(history_id)
            except MalformedId:
                return {"error": f"Invalid history_id '{history_id}'. Please use an exact ID from list_user_histories."}

        @agent.tool
        async def list_datasets(ctx: RunContext[GalaxyAgentDependencies], history_id: str) -> dict[str, Any]:
            """List all datasets in a history with their basic info."""
            try:
                return self.ops.get_history_contents(history_id, limit=500, order="hid-asc")
            except MalformedId:
                return {"error": f"Invalid history_id '{history_id}'. Please use an exact ID from list_user_histories."}

        @agent.tool
        async def get_dataset_info(ctx: RunContext[GalaxyAgentDependencies], dataset_id: str) -> dict[str, Any]:
            """Get detailed information about a specific dataset."""
            try:
                return self.ops.get_dataset_details(dataset_id)
            except MalformedId:
                return {"error": f"Invalid dataset_id '{dataset_id}'. Please use an exact ID from list_datasets."}

        @agent.tool
        async def get_job_for_dataset(
            ctx: RunContext[GalaxyAgentDependencies], dataset_id: str, history_id: str
        ) -> dict[str, Any]:
            """Get the job that created a dataset, including tool info and parameters."""
            try:
                return self.ops.get_job_details(dataset_id, history_id)
            except MalformedId as e:
                return {"error": f"Invalid ID provided: {e}. Please use exact IDs from list_datasets."}

        @agent.tool
        async def get_tool_citations(ctx: RunContext[GalaxyAgentDependencies], tool_id: str) -> dict[str, Any]:
            """Get citation information for a tool."""
            return self.ops.get_tool_citations(tool_id)

        @agent.tool
        async def get_tool_info(ctx: RunContext[GalaxyAgentDependencies], tool_id: str) -> dict[str, Any]:
            """Get detailed information about a tool including description and version."""
            return self.ops.get_tool_details(tool_id)

        return agent

    def get_system_prompt(self) -> str:
        """Get the system prompt for history analysis."""
        prompt_path = Path(__file__).parent / "prompts" / "history_analyzer.md"
        if prompt_path.exists():
            return prompt_path.read_text()

        return """You are an expert bioinformatics analyst who specializes in understanding and summarizing Galaxy analysis workflows.

Your task is to analyze a Galaxy history and provide a comprehensive understanding of what was done.

## Finding the Right History

If no specific history is mentioned:
1. Call list_user_histories to see the user's available histories
2. Pick the most recently updated history (first in the list) unless the user's query suggests a different one
3. If the user mentions a specific analysis type (e.g., "RNA-seq analysis"), look for a history with a matching name

## Analyzing a History

Once you have identified which history to analyze:
1. Call get_history_info to get the history metadata (name, annotation, tags)
2. Call list_datasets to see all datasets in the history
3. For key output datasets, call get_job_for_dataset to understand what tool created them
4. Call get_tool_citations for the main tools used
5. Use get_tool_info if you need more details about a specific tool
6. Synthesize this into a comprehensive analysis

## Output Guidelines

- Be thorough but concise
- Use scientific terminology appropriately
- Note tool versions when available
- Organize information logically by analysis stage
- Include citations in standard format when generating methods sections
- For the methods_text field, write in third person past tense suitable for a publication

## What You Can Do

- Summarize what analysis was performed
- Identify the input data and final outputs
- Describe the tools used and their purpose
- Generate publication-ready methods sections
- Answer specific questions about the analysis workflow
"""

    async def analyze_history(self, history_id: str, focus: str = "summary") -> HistoryAnalysis:
        """
        Analyze a Galaxy history.

        Args:
            history_id: The Galaxy history ID to analyze
            focus: What to focus on - "summary", "methods", or "detailed"

        Returns:
            HistoryAnalysis with comprehensive analysis results
        """
        focus_instructions = {
            "summary": "Provide a concise summary of what was done in this analysis.",
            "methods": "Generate a publication-ready methods section with citations.",
            "detailed": "Provide a detailed breakdown of every step in the analysis workflow.",
        }

        instruction = focus_instructions.get(focus, focus_instructions["summary"])

        prompt = f"""Analyze Galaxy history {history_id}.

{instruction}

Use the available tools to gather information:
1. Call get_history_info to get the history metadata
2. Call list_datasets to see all datasets in the history
3. For key output datasets, call get_job_for_dataset to see what tool created them
4. Call get_tool_citations for the main tools used
5. Use get_tool_info if you need more details about a specific tool

Then synthesize this information into a comprehensive analysis."""

        result = await self._run_with_retry(prompt)

        extracted = extract_structured_output(result, HistoryAnalysis, log)
        if extracted:
            return extracted

        # Extraction failed - log details and raise an error
        self._log_result_debug_info(result, "analyze_history")
        raise ValueError(
            "The AI model did not return a properly formatted response. "
            "This may indicate the model doesn't support structured output. "
            "Check the logs for details about what was returned."
        )

    async def analyze_with_discovery(self, query: str, focus: str = "summary") -> HistoryAnalysis:
        """
        Analyze a history by first discovering which history to use.

        The agent will list the user's histories and select the most appropriate
        one based on the query, then analyze it.

        Args:
            query: User's request (e.g., "summarize my history", "what RNA-seq analysis did I do?")
            focus: What to focus on - "summary", "methods", or "detailed"

        Returns:
            HistoryAnalysis with comprehensive analysis results
        """
        focus_instructions = {
            "summary": "Provide a concise summary of what was done in this analysis.",
            "methods": "Generate a publication-ready methods section with citations.",
            "detailed": "Provide a detailed breakdown of every step in the analysis workflow.",
        }

        instruction = focus_instructions.get(focus, focus_instructions["summary"])

        prompt = f"""The user asked: "{query}"

{instruction}

First, call list_user_histories to see the user's available histories.
Then select the most appropriate history based on the user's request:
- If they mention a specific analysis type or name, look for a matching history
- Otherwise, use the most recently updated history (first in the list)

Once you've identified the history, analyze it using:
1. get_history_info to get the history metadata
2. list_datasets to see all datasets
3. get_job_for_dataset for key output datasets
4. get_tool_citations for the main tools
5. get_tool_info for additional tool details

Synthesize this into a comprehensive analysis."""

        result = await self._run_with_retry(prompt)

        extracted = extract_structured_output(result, HistoryAnalysis, log)
        if extracted:
            return extracted

        # Extraction failed - log details and raise an error
        self._log_result_debug_info(result, "analyze_with_discovery")
        raise ValueError(
            "The AI model did not return a properly formatted response. "
            "This may indicate the model doesn't support structured output. "
            "Check the logs for details about what was returned."
        )

    def _log_result_debug_info(self, result: Any, method_name: str) -> None:
        """Log detailed debug information about an agent result for troubleshooting."""
        log.warning(f"HistoryAnalyzer.{method_name} did not return structured HistoryAnalysis")
        log.warning(f"  Result type: {type(result).__name__}")

        if result is None:
            log.warning("  Result is None")
            return

        # Log available attributes
        attrs = [attr for attr in dir(result) if not attr.startswith("_")]
        log.debug(f"  Available attributes: {attrs}")

        # Log .data if present
        if hasattr(result, "data"):
            data = result.data
            log.warning(f"  result.data type: {type(data).__name__ if data is not None else 'None'}")
            if data is not None:
                log.debug(f"  result.data value: {str(data)[:500]}")

        # Log .output if present (common in pydantic-ai)
        if hasattr(result, "output"):
            output = result.output
            log.warning(f"  result.output type: {type(output).__name__ if output is not None else 'None'}")
            if output is not None:
                log.debug(f"  result.output value: {str(output)[:500]}")

        # Log messages/tool calls if present
        if hasattr(result, "all_messages"):
            messages = result.all_messages()
            log.debug(f"  Message count: {len(messages) if messages else 0}")
            for i, msg in enumerate(messages or []):
                log.debug(f"    Message {i}: {type(msg).__name__} - {str(msg)[:200]}")

        if hasattr(result, "new_messages"):
            new_msgs = result.new_messages()
            log.debug(f"  New message count: {len(new_msgs) if new_msgs else 0}")

    async def process(self, query: str, context: dict[str, Any] | None = None) -> AgentResponse:
        """
        Process a history analysis request.

        Args:
            query: User's request or question about the history
            context: Optionally contains 'history_id' and/or 'focus'

        Returns:
            AgentResponse with the analysis
        """
        history_id = None
        focus = "summary"

        if context:
            history_id = context.get("history_id")
            focus = context.get("focus", "summary")

        try:
            if history_id:
                # Direct analysis of a specific history
                result = await self.analyze_history(history_id, focus)
            else:
                # Discovery mode - let the agent find the right history
                result = await self.analyze_with_discovery(query, focus)

            # Choose primary content based on focus
            if focus == "methods":
                content = result.methods_text or result.workflow_description
            else:
                content = result.summary + "\n\n" + result.workflow_description

            return AgentResponse(
                content=content,
                confidence=result.confidence,
                agent_type=self.agent_type,
                suggestions=[],
                metadata={
                    "title": result.title,
                    "summary": result.summary,
                    "tools_used": result.tools_used,
                    "tool_versions": result.tool_versions,
                    "citations": result.citations,
                    "input_data": result.input_data,
                    "output_data": result.output_data,
                    "methods_text": result.methods_text,
                },
            )

        except Exception as e:
            log.exception(f"Error analyzing history: {e}")
            return self._get_fallback_response(query, str(e))

    def _get_fallback_content(self) -> str:
        """Get fallback content for analysis failures."""
        return "Unable to analyze the history at this time. Please try again later."
