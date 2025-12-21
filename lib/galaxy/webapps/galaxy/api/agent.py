"""
AI Agent endpoints using pydantic-ai.

This module provides endpoints for running AI agents that can interact with Galaxy
on behalf of the authenticated user. Agents use the same AgentOperationsManager as
the MCP server, but run internally with direct access to Galaxy managers.
"""

import logging
from typing import Any

from fastapi import Body
from pydantic import BaseModel

from galaxy.managers.agent_operations import AgentOperationsManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["agent"])


class AgentQueryRequest(BaseModel):
    """Request model for agent queries."""

    query: str
    """The user's query or instruction for the agent"""

    model: str = "openai:gpt-4"
    """The AI model to use (default: openai:gpt-4)"""


class AgentQueryResponse(BaseModel):
    """Response model for agent queries."""

    result: str
    """The agent's response"""

    operations_used: list[str]
    """List of Galaxy operations the agent performed"""

    success: bool
    """Whether the query was successful"""


@router.cbv
class FastAPIAgent:
    """
    AI Agent endpoints.

    Example usage with pydantic-ai integration.
    """

    @router.post(
        "/api/agent/query",
        summary="Query AI agent",
        response_model=AgentQueryResponse,
    )
    def query_agent(
        self,
        request: AgentQueryRequest = Body(...),
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> AgentQueryResponse:
        """
        Run an AI agent query with access to Galaxy operations.

        The agent runs as the authenticated user and can perform Galaxy operations
        like searching tools, listing histories, and running tools on their behalf.

        **NOTE**: This is an example endpoint. To use it, you need to:
        1. Install pydantic-ai: `pip install pydantic-ai`
        2. Configure your AI model credentials (e.g., OPENAI_API_KEY)
        3. Uncomment the pydantic-ai code below

        Args:
            request: Agent query request
            trans: User session context
        """
        # Create AgentOperationsManager in internal mode
        # This gives the agent direct access to Galaxy managers
        ops_manager = AgentOperationsManager(app=trans.app, trans=trans)

        # Example: Direct call to operations (without pydantic-ai)
        # This demonstrates how the agent would use the operations
        operations_used = []

        try:
            # Example operations the agent might perform
            if "search" in request.query.lower() and "tool" in request.query.lower():
                # Extract search query from user request
                # In real implementation, the LLM would do this
                search_term = request.query.split("tool")[-1].strip()
                if search_term:
                    result = ops_manager.search_tools(search_term)
                    operations_used.append("search_tools")
                    return AgentQueryResponse(
                        result=f"Found {result['count']} tools matching '{search_term}'",
                        operations_used=operations_used,
                        success=True,
                    )

            elif "list" in request.query.lower() and "histor" in request.query.lower():
                result = ops_manager.list_histories(limit=10)
                operations_used.append("list_histories")
                return AgentQueryResponse(
                    result=f"Found {result['count']} histories",
                    operations_used=operations_used,
                    success=True,
                )

            elif "connect" in request.query.lower() or "server" in request.query.lower():
                result = ops_manager.connect()
                operations_used.append("connect")
                return AgentQueryResponse(
                    result=f"Connected to {result['server']['brand']} version {result['server']['version']}",
                    operations_used=operations_used,
                    success=True,
                )

            else:
                return AgentQueryResponse(
                    result="I can help you search tools, list histories, or get server information. "
                    "Try asking: 'search for RNA-seq tools' or 'list my histories'",
                    operations_used=[],
                    success=True,
                )

        except Exception as e:
            log.error(f"Agent query failed: {str(e)}")
            return AgentQueryResponse(
                result=f"Error: {str(e)}", operations_used=operations_used, success=False
            )

        # ============================================================================
        # PYDANTIC-AI INTEGRATION EXAMPLE (commented out - requires pydantic-ai)
        # ============================================================================
        #
        # Uncomment this section to use pydantic-ai for more sophisticated agents
        #
        # from pydantic_ai import Agent, RunContext
        #
        # # Define Galaxy operations as tools for the agent
        # galaxy_agent = Agent(
        #     request.model,
        #     system_prompt=(
        #         "You are a helpful assistant that helps users interact with Galaxy, "
        #         "a platform for bioinformatics analysis. You can search for tools, "
        #         "list histories, get tool details, and run tools."
        #     ),
        # )
        #
        # # Register operations as agent tools
        # @galaxy_agent.tool
        # async def connect() -> dict[str, Any]:
        #     """Get Galaxy server information and verify connection."""
        #     return ops_manager.connect()
        #
        # @galaxy_agent.tool
        # async def search_tools(query: str) -> dict[str, Any]:
        #     """
        #     Search for Galaxy tools.
        #
        #     Args:
        #         query: Search term for tool name or description
        #     """
        #     return ops_manager.search_tools(query)
        #
        # @galaxy_agent.tool
        # async def get_tool_details(tool_id: str, io_details: bool = False) -> dict[str, Any]:
        #     """
        #     Get detailed information about a specific tool.
        #
        #     Args:
        #         tool_id: The tool ID
        #         io_details: Whether to include input/output details
        #     """
        #     return ops_manager.get_tool_details(tool_id, io_details)
        #
        # @galaxy_agent.tool
        # async def list_histories(limit: int = 50) -> dict[str, Any]:
        #     """
        #     List user's Galaxy histories.
        #
        #     Args:
        #         limit: Maximum number of histories to return
        #     """
        #     return ops_manager.list_histories(limit=limit)
        #
        # @galaxy_agent.tool
        # async def run_tool(
        #     history_id: str, tool_id: str, inputs: dict[str, Any]
        # ) -> dict[str, Any]:
        #     """
        #     Execute a Galaxy tool.
        #
        #     Args:
        #         history_id: ID of the history to run in
        #         tool_id: ID of the tool to run
        #         inputs: Tool input parameters
        #     """
        #     return ops_manager.run_tool(history_id, tool_id, inputs)
        #
        # # Run the agent
        # result = galaxy_agent.run_sync(request.query)
        #
        # return AgentQueryResponse(
        #     result=result.data,
        #     operations_used=result.all_messages(),  # Track which tools were called
        #     success=True,
        # )

    @router.post(
        "/api/agent/analyze-history/{history_id}",
        summary="Analyze a Galaxy history",
    )
    async def analyze_history(
        self,
        history_id: str,
        focus: str = "summary",
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> dict[str, Any]:
        """
        Analyze a Galaxy history and generate a summary or methods section.

        This endpoint uses the HistoryAnalyzerAgent to examine all datasets and tools
        used in a history, then generates a comprehensive analysis including:
        - Summary of what was done
        - Tools used and their versions
        - Input and output data descriptions
        - Publication-ready methods section (when focus="methods")

        Args:
            history_id: The Galaxy history ID to analyze
            focus: Analysis focus - "summary" (default), "methods", or "detailed"
            trans: User session context

        Returns:
            Analysis results including title, summary, tools used, citations, etc.
        """
        try:
            from galaxy.agents import (
                GalaxyAgentDependencies,
                HistoryAnalyzerAgent,
            )
            from galaxy.managers.jobs import JobManager

            # Build agent dependencies
            deps = GalaxyAgentDependencies(
                trans=trans,
                user=trans.user,
                config=trans.app.config,
                job_manager=trans.app.job_manager if hasattr(trans.app, "job_manager") else JobManager(trans.app),
                toolbox=trans.app.toolbox,
            )

            agent = HistoryAnalyzerAgent(deps)
            result = await agent.analyze_history(history_id, focus)

            return {
                "success": True,
                "title": result.title,
                "summary": result.summary,
                "workflow_description": result.workflow_description,
                "tools_used": result.tools_used,
                "tool_versions": result.tool_versions,
                "citations": result.citations,
                "input_data": result.input_data,
                "output_data": result.output_data,
                "methods_text": result.methods_text,
                "confidence": result.confidence,
            }

        except ImportError as e:
            log.error(f"Agent dependencies not available: {e}")
            return {
                "success": False,
                "error": "pydantic-ai is required for this feature but is not installed",
            }
        except Exception as e:
            log.exception(f"History analysis failed for {history_id}")
            return {
                "success": False,
                "error": str(e),
            }
