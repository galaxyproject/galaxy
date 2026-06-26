"""
Teaching Assistant agent for AI-guided cognitive tutoring.

Wraps existing specialist agents with a pedagogical layer that
uses Socratic questioning, scaffolded guidance, and training
material integration to help users learn computational biology.
"""

import json
import logging
from pathlib import Path
from typing import (
    Any,
    Optional,
)

from pydantic_ai import Agent

from galaxy.managers.learning_state import LearningStateManager
from galaxy.schema.agents import (
    ActionSuggestion,
    ActionType,
    ConfidenceLevel,
)
from .base import (
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    extract_result_content,
    GalaxyAgentDependencies,
)
from .gtn import GTNSearchDB
from .operations import AgentOperationsManager

log = logging.getLogger(__name__)


class TeachingAssistantAgent(BaseGalaxyAgent):
    """
    Pedagogical orchestrator that guides users through learning
    rather than providing direct answers.

    Delegates to specialist agents (error analysis, tool recommendation,
    GTN training) and reframes their responses as learning opportunities.
    """

    agent_type = AgentType.TEACHING_ASSISTANT

    def __init__(self, deps: GalaxyAgentDependencies):
        self.learning_state_manager = LearningStateManager()
        self.ops = AgentOperationsManager(app=deps.trans.app, trans=deps.trans)

        # GTN training material search is an optional capability; the tutor
        # degrades to coaching-only if the database can't be loaded.
        db_path = getattr(deps.config, "gtn_database_path", None)
        download_url = getattr(deps.config, "gtn_database_url", None)
        self.gtn_db: Optional[GTNSearchDB] = None
        try:
            self.gtn_db = GTNSearchDB(db_path=db_path, download_url=download_url)
        except Exception as e:
            log.warning(f"GTN database not available: {e}")
            self.gtn_db = None

        super().__init__(deps)

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, str]:
        """Create the teaching assistant agent with tools."""
        agent = Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            system_prompt=self.get_system_prompt(),
        )

        teaching_assistant = self

        @agent.tool
        async def search_training_materials(ctx, query: str) -> str:
            """Search GTN training materials for relevant tutorials."""
            if teaching_assistant.gtn_db is None:
                return "Training material search is not available right now."
            results = teaching_assistant.gtn_db.search(query, limit=5)
            if not results:
                return "No matching training materials found."
            formatted = []
            for r in results:
                d = r.to_dict()
                formatted.append(
                    f"- **{d['title']}** ({d.get('topic', 'general')})\n"
                    f"  {d.get('snippet') or d.get('description', '')}\n"
                    f"  URL: {d.get('url', 'N/A')}"
                )
            return f"Found {len(results)} relevant tutorials:\n\n" + "\n".join(formatted)

        @agent.tool
        async def get_learning_pathway(ctx, topic: str) -> str:
            """Suggest an ordered set of tutorials for a topic, easiest first."""
            if teaching_assistant.gtn_db is None:
                return "Learning pathway lookup is not available right now."
            results = teaching_assistant.gtn_db.search(topic, limit=8)
            if not results:
                return f"No learning pathway found for '{topic}'."
            difficulty_order = {"introductory": 0, "beginner": 0, "intermediate": 1, "advanced": 2}
            ordered = sorted(results, key=lambda r: difficulty_order.get((r.difficulty or "").lower(), 1))
            formatted = []
            for i, r in enumerate(ordered, start=1):
                formatted.append(f"Step {i}: **{r.title}** (difficulty: {r.difficulty or 'unknown'})\n  URL: {r.url}")
            return f"A suggested learning pathway for '{topic}':\n\n" + "\n".join(formatted)

        @agent.tool
        async def check_user_context(ctx) -> str:
            """Inspect the user's current history to understand their work context."""
            history = teaching_assistant.deps.trans.get_history()
            if history is None:
                return "The user has no active history."
            history_id = teaching_assistant.deps.trans.security.encode_id(history.id)
            result = teaching_assistant.ops.get_history_contents(history_id, limit=100, order="hid-asc")
            datasets = result.get("contents", [])
            if not datasets:
                return "The user's current history is empty."
            summary_lines = []
            for ds in datasets[:15]:
                state_indicator = ds.get("state", "?")
                summary_lines.append(
                    f"- [{state_indicator}] HID {ds.get('hid', '?')}: "
                    f"{ds.get('name', 'unnamed')} ({ds.get('extension', '?')})"
                )
            total = result.get("pagination", {}).get("total_items", len(datasets))
            shown = min(len(datasets), 15)
            header = f"User's current history has {total} datasets"
            if total > shown:
                header += f" (showing first {shown})"
            return header + ":\n" + "\n".join(summary_lines)

        @agent.tool
        async def analyze_error(ctx, job_id: str) -> str:
            """Get error details for a failed job. Returns raw analysis for pedagogical reframing."""
            try:
                status = teaching_assistant.ops.get_job_status(job_id)
            except Exception as e:
                return f"Could not retrieve job info: {e}"
            job_info = status.get("job", {})

            # Also try to get analysis from the error analysis agent
            analysis = ""
            try:
                analysis = await teaching_assistant._call_agent_from_tool(
                    AgentType.ERROR_ANALYSIS,
                    f"Analyze job failure: tool={job_info.get('tool_id')}, "
                    f"exit_code={job_info.get('exit_code')}, "
                    f"stderr={str(job_info.get('stderr', ''))[:300]}",
                    ctx,
                )
            except Exception as e:
                log.warning(f"Error analysis delegation failed: {e}")
                analysis = "Error analysis agent unavailable."

            return (
                f"Job {job_id} details:\n"
                f"- Tool: {job_info.get('tool_id', 'unknown')}\n"
                f"- State: {job_info.get('state', 'unknown')}\n"
                f"- Exit code: {job_info.get('exit_code', 'N/A')}\n"
                f"- Stderr: {str(job_info.get('stderr', 'none'))[:300]}\n\n"
                f"Analysis: {analysis}"
            )

        @agent.tool
        async def recommend_tools(ctx, task_description: str) -> str:
            """Get tool recommendations for a task. Returns results for guided discovery."""
            try:
                response = await teaching_assistant._call_agent_from_tool(
                    AgentType.TOOL_RECOMMENDATION,
                    task_description,
                    ctx,
                )
                return response
            except Exception as e:
                log.warning(f"Tool recommendation delegation failed: {e}")
                # Fall back to direct toolbox search
                result = teaching_assistant.ops.search_tools(task_description)
                tools = result.get("tools", [])
                if not tools:
                    return "No matching tools found for that task."
                formatted = [f"- **{t['name']}** ({t['id']}): {t.get('description', '')}" for t in tools[:5]]
                return "Available tools:\n" + "\n".join(formatted)

        @agent.tool
        async def demonstrate_concept(ctx, tool_id: str, inputs_json: str) -> str:
            """Run a tool to demonstrate a concept. Use sparingly -- prefer coaching over showing."""
            try:
                inputs = json.loads(inputs_json) if inputs_json else {}
            except json.JSONDecodeError:
                return f"Invalid inputs JSON: {inputs_json}"

            history = teaching_assistant.deps.trans.get_history()
            if history is None:
                return "No active history available for demonstration."
            history_id = teaching_assistant.deps.trans.security.encode_id(history.id)

            try:
                result = teaching_assistant.ops.run_tool(history_id, tool_id, inputs)
            except Exception as e:
                return f"Could not run tool '{tool_id}': {e}"
            return f"Demonstration: Ran tool '{tool_id}' in history.\nResult: {json.dumps(result, default=str)[:500]}"

        @agent.tool
        async def save_learning_note(ctx, content: str) -> str:
            """Save a learning note to the user's history notebook if available."""
            # Notebook integration -- gracefully no-op if not available
            log.info(f"Learning note requested (notebook integration pending): {content[:100]}")
            return (
                "Learning note recorded. (History Notebook integration will save these "
                "directly to your analysis history once available.)"
            )

        return agent

    def get_system_prompt(self) -> str:
        """Get system prompt with dynamic learning context injected."""
        prompt_path = Path(__file__).parent / "prompts" / "teaching_assistant.md"
        template = prompt_path.read_text()

        # Build learning context from user state
        learning_context = self._build_learning_context()
        return template.replace("{learning_context}", learning_context)

    def _build_learning_context(self) -> str:
        """Build dynamic context string from user's learning state."""
        try:
            state = self.learning_state_manager.get_learning_state(self.deps.trans)
        except Exception:
            return "No learning state available."

        lines = [
            f"**User expertise level:** {state.get('expertise_level', 'beginner')}",
            f"**Scaffolding level:** {state.get('scaffolding_level', 3)} (1=max support, 5=minimal)",
            f"**Interaction count:** {state.get('interaction_count', 0)}",
        ]

        completed = state.get("completed_tutorials", [])
        if completed:
            lines.append(f"**Completed tutorials:** {', '.join(completed[-5:])}")

        pathway = state.get("current_pathway")
        if pathway:
            progress = state.get("pathway_progress", {}).get(pathway, 0)
            lines.append(f"**Current pathway:** {pathway} (step {progress})")

        topics = state.get("topics_explored", [])
        if topics:
            lines.append(f"**Topics explored:** {', '.join(topics[-5:])}")

        return "\n".join(lines)

    def _prepare_prompt(self, query: str, context: dict[str, Any]) -> str:
        """Prepare prompt with learning context included."""
        # Record the interaction
        try:
            self.learning_state_manager.record_interaction(self.deps.trans)
        except Exception as e:
            log.warning(f"Failed to record interaction: {e}")

        prompt_parts = [query]
        if context:
            # Filter out conversation_history from context display (it's handled separately)
            display_context = {k: v for k, v in context.items() if k != "conversation_history" and v}
            if display_context:
                context_str = "\n".join([f"{k}: {v}" for k, v in display_context.items()])
                prompt_parts.insert(0, f"Context:\n{context_str}\n")

        return "\n".join(prompt_parts)

    def _format_response(self, result: Any, query: str, context: dict[str, Any]) -> AgentResponse:
        """Format response with tutor-specific metadata and suggestions."""
        content = extract_result_content(result)

        # Build suggestions based on content
        suggestions = self._build_tutor_suggestions(content, query)

        # Include learning state in metadata
        try:
            learning_state = self.learning_state_manager.get_learning_state(self.deps.trans)
        except Exception:
            learning_state = {}

        return self._build_response(
            content=content,
            confidence=ConfidenceLevel.HIGH,
            method="teaching_assistant",
            result=result,
            query=query,
            suggestions=suggestions,
            agent_data={
                "learning_state": learning_state,
                "tutor_mode": True,
            },
        )

    def _build_tutor_suggestions(self, content: str, query: str) -> list[ActionSuggestion]:
        """Build action suggestions appropriate for learning context."""
        suggestions: list[ActionSuggestion] = []
        content_lower = content.lower()

        # Suggest tutorials if training content was referenced
        if "training.galaxyproject.org" in content or "tutorial" in content_lower:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.START_TUTORIAL,
                    description="Open the recommended tutorial",
                    parameters={"source": "gtn"},
                    confidence=ConfidenceLevel.MEDIUM,
                    priority=1,
                )
            )

        # Suggest next pathway step if on a learning path
        if "pathway" in content_lower or "next step" in content_lower:
            suggestions.append(
                ActionSuggestion(
                    action_type=ActionType.NEXT_PATHWAY_STEP,
                    description="Continue to the next step in your learning pathway",
                    parameters={},
                    confidence=ConfidenceLevel.MEDIUM,
                    priority=2,
                )
            )

        return suggestions

    def _get_fallback_content(self) -> str:
        """Tutor-specific fallback message."""
        return (
            "I'm having trouble connecting to the AI service right now. "
            "In the meantime, you can explore tutorials at "
            "https://training.galaxyproject.org/ or ask your question "
            "in task mode for a direct answer."
        )
