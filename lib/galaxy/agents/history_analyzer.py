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
    Dict,
    List,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
)
from pydantic_ai import Agent
from pydantic_ai.tools import RunContext

from galaxy.managers.agent_operations import AgentOperationsManager
from .base import (
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    ConfidenceLevel,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)

ConfidenceLiteral = Literal["low", "medium", "high"]


class HistoryAnalysis(BaseModel):
    """Structured output for history analysis."""

    title: str = Field(description="A concise title summarizing the analysis")
    summary: str = Field(description="Brief summary of what was done in the history")
    workflow_description: str = Field(description="Description of the analysis workflow and steps")
    tools_used: List[str] = Field(description="List of tool names used in the analysis")
    tool_versions: Dict[str, str] = Field(default_factory=dict, description="Tool versions used")
    citations: List[str] = Field(default_factory=list, description="Formatted citations for tools used")
    input_data: List[str] = Field(default_factory=list, description="Description of input datasets")
    output_data: List[str] = Field(default_factory=list, description="Description of output datasets")
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
        async def get_history_info(ctx: RunContext[GalaxyAgentDependencies], history_id: str) -> Dict[str, Any]:
            """Get metadata about a Galaxy history including name, annotation, and tags."""
            return self.ops.get_history_details(history_id)

        @agent.tool
        async def list_datasets(ctx: RunContext[GalaxyAgentDependencies], history_id: str) -> Dict[str, Any]:
            """List all datasets in a history with their basic info."""
            return self.ops.get_history_contents(history_id, limit=500, order="hid-asc")

        @agent.tool
        async def get_dataset_info(ctx: RunContext[GalaxyAgentDependencies], dataset_id: str) -> Dict[str, Any]:
            """Get detailed information about a specific dataset."""
            return self.ops.get_dataset_details(dataset_id)

        @agent.tool
        async def get_job_for_dataset(
            ctx: RunContext[GalaxyAgentDependencies], dataset_id: str, history_id: str
        ) -> Dict[str, Any]:
            """Get the job that created a dataset, including tool info and parameters."""
            return self.ops.get_job_details(dataset_id, history_id)

        @agent.tool
        async def get_tool_citations(ctx: RunContext[GalaxyAgentDependencies], tool_id: str) -> Dict[str, Any]:
            """Get citation information for a tool."""
            return self.ops.get_tool_citations(tool_id)

        @agent.tool
        async def get_tool_info(ctx: RunContext[GalaxyAgentDependencies], tool_id: str) -> Dict[str, Any]:
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

When analyzing a history:
1. First get the history info to understand the overall context
2. List all datasets to see the workflow of inputs and outputs
3. For output datasets, get the job that created them to understand the tools and parameters used
4. Get tool information and citations when relevant
5. Synthesize this into a clear understanding of the analysis

You should be able to:
- Summarize what analysis was performed
- Identify the input data and final outputs
- Describe the tools used and their purpose
- Generate publication-ready methods sections when requested
- Answer specific questions about the analysis workflow

Guidelines:
- Be thorough but concise
- Use scientific terminology appropriately
- Note tool versions when available
- Organize information logically by analysis stage
- Include citations in standard format when generating methods sections
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

        if hasattr(result, "data"):
            return result.data
        return result

    async def process(self, query: str, context: Dict[str, Any] | None = None) -> AgentResponse:
        """
        Process a history analysis request.

        Args:
            query: User's request or question about the history
            context: Should contain 'history_id' key, optionally 'focus'

        Returns:
            AgentResponse with the analysis
        """
        history_id = None
        focus = "summary"

        if context:
            history_id = context.get("history_id")
            focus = context.get("focus", "summary")

        if not history_id:
            return AgentResponse(
                content="Please provide a history_id to analyze.",
                confidence=ConfidenceLevel.LOW,
                agent_type=self.agent_type,
                suggestions=[],
                metadata={"error": "missing_history_id"},
            )

        try:
            result = await self.analyze_history(history_id, focus)

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
            log.exception(f"Error analyzing history {history_id}")
            return self._get_fallback_response(query, str(e))

    def _get_fallback_content(self) -> str:
        """Get fallback content for analysis failures."""
        return "Unable to analyze the history at this time. Please try again later."
