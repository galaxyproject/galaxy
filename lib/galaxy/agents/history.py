"""
History agent for understanding and answering questions about Galaxy histories.

Provides tools to explore histories, datasets, jobs, and tool usage. Can answer
general questions about history contents, interpret results, generate methods
sections, and summarize analyses.
"""

import logging
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.tools import RunContext

from galaxy.exceptions import MalformedId
from galaxy.managers.agent_operations import AgentOperationsManager
from .base import (
    AgentType,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)


class HistoryAgent(BaseGalaxyAgent):
    """Agent for understanding and answering questions about Galaxy histories."""

    agent_type = AgentType.HISTORY

    def __init__(self, deps: GalaxyAgentDependencies):
        super().__init__(deps)
        self.ops = AgentOperationsManager(app=deps.trans.app, trans=deps.trans)

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, str]:
        agent = Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
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
        async def get_job_errors(ctx: RunContext[GalaxyAgentDependencies], dataset_id: str) -> dict[str, Any]:
            """Get error details (stderr, stdout, exit code) for a failed job.

            IMPORTANT: For any dataset with state='error', call this to get the actual error message.
            This is required to understand WHY a job failed.
            """
            try:
                return self.ops.get_job_errors(dataset_id)
            except MalformedId:
                return {"error": f"Invalid dataset_id '{dataset_id}'. Please use an exact ID from list_datasets."}

        @agent.tool
        async def get_tool_citations(ctx: RunContext[GalaxyAgentDependencies], tool_id: str) -> dict[str, Any]:
            """Get citation information for a tool."""
            return self.ops.get_tool_citations(tool_id)

        @agent.tool
        async def get_tool_info(ctx: RunContext[GalaxyAgentDependencies], tool_id: str) -> dict[str, Any]:
            """Get detailed information about a tool including description and version."""
            return self.ops.get_tool_details(tool_id)

        @agent.tool
        async def peek_dataset_content(ctx: RunContext[GalaxyAgentDependencies], dataset_id: str) -> dict[str, Any]:
            """Preview the actual content of a dataset.

            Use this when you need to see what's IN a dataset — to interpret results,
            check data quality, or answer questions about specific outputs. Returns a
            short preview (peek) and a longer content preview (up to 1MB for text files).
            Non-text datasets will return metadata only.
            """
            try:
                return self.ops.peek_dataset_content(dataset_id)
            except MalformedId:
                return {"error": f"Invalid dataset_id '{dataset_id}'. Please use an exact ID from list_datasets."}

        return agent

    def get_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "history_analyzer.md"
        if prompt_path.exists():
            return prompt_path.read_text()
        return self._fallback_system_prompt()

    def _fallback_system_prompt(self) -> str:
        return """You are an expert bioinformatics analyst who helps users understand their Galaxy histories.

You can answer questions about what's in a history, interpret results, summarize analyses,
generate methods sections, and help users understand their data.

Use the available tools to explore the history and gather the information you need to answer
the user's question thoroughly and accurately.

CRITICAL: Never invent or guess information. If you don't know something, say so."""

    def _get_fallback_content(self) -> str:
        return "Unable to access the history at this time. Please try again later."
