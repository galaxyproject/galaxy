"""
AI Agent endpoints using pydantic-ai.
"""

import logging
from typing import Any

from fastapi import Body
from pydantic import BaseModel

from galaxy.managers.agent_operations import AgentOperationsManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.webapps.galaxy.api import (
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
    """AI Agent endpoints."""

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
        """Run an AI agent query with access to Galaxy operations."""
        ops_manager = AgentOperationsManager(app=trans.app, trans=trans)
        operations_used = []

        try:
            if "search" in request.query.lower() and "tool" in request.query.lower():
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
            return AgentQueryResponse(result=f"Error: {str(e)}", operations_used=operations_used, success=False)

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
        """Analyze a Galaxy history and generate a summary or methods section."""
        try:
            from galaxy.agents import (
                GalaxyAgentDependencies,
                HistoryAnalyzerAgent,
            )
            from galaxy.managers.jobs import JobManager

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
