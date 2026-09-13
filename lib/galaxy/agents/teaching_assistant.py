"""
Teaching Assistant agent for AI-guided cognitive tutoring.

Wraps existing specialist agents with a pedagogical layer that
uses Socratic questioning, scaffolded guidance, and training
material integration to help users learn computational biology.
"""

import json
import logging
import re
import string
from html import unescape
from pathlib import Path
from typing import (
    Any,
)
from urllib.parse import (
    unquote,
    urlsplit,
)
from uuid import uuid4

from pydantic_ai import (
    Agent,
    ModelRetry,
    RunContext,
)
from pydantic_ai.messages import ToolReturn

from galaxy.managers.learning_state import LearningStateManager
from galaxy.schema.agents import ConfidenceLevel
from .base import (
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    extract_result_content,
    GalaxyAgentDependencies,
    JOB_LOG_EXCERPT_CHARS,
    truncate_middle,
)
from .gtn import GTNSearchDB
from .operations import AgentOperationsManager

log = logging.getLogger(__name__)
_SEARCH_TOOLS = {"search_training_materials", "suggest_tutorials"}
_REFERENCE = re.compile(r"\[\[tutorial:([a-f0-9]{12})\]\]")
_GTN_LINK = re.compile(r"training\.galaxyproject\.org([^\s<>`\"'\[\]()]*)", re.IGNORECASE)


def _plain_markdown(value: str) -> str:
    return re.sub(f"([{re.escape(string.punctuation)}])", r"\\\1", " ".join(value.split()))


def _render_tutorial_references(ctx: RunContext[GalaxyAgentDependencies], content: str) -> str:
    sources = {}
    for message in ctx.messages:
        # Conversation history and failed transport attempts cannot authorize new citations.
        if not ctx.run_id or message.run_id != ctx.run_id:
            continue
        for part in message.parts:
            if (
                part.part_kind == "tool-return"
                and part.tool_name in _SEARCH_TOOLS
                and getattr(part, "outcome", "success") == "success"
                and isinstance(part.metadata, dict)
            ):
                sources.update((s["id"], s) for s in part.metadata.get("tutor_sources", []))

    ids = _REFERENCE.findall(content)
    link_text = unquote(unescape(re.sub(r"\\([\W_])", r"\1", content)))
    has_link = any(m.group(1).rstrip("/.,;:!?") for m in _GTN_LINK.finditer(link_text))
    has_path = re.search(r"(?:training-material/|topics/[\w-]+/tutorials/)", link_text, re.IGNORECASE)
    remaining = _REFERENCE.sub("", content)
    misplaced = len(re.findall(f"^{_REFERENCE.pattern}[ \t]*$", content, re.MULTILINE)) != len(ids)
    fence = ""
    for line in content.splitlines():
        if match := re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line):
            marker, suffix = match.groups()
            if not fence:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence) and not suffix.strip():
                fence = ""
        elif fence and _REFERENCE.search(line):
            misplaced = True
    if (
        has_link
        or has_path
        or misplaced
        or any(source_id not in sources for source_id in ids)
        or "[[tutorial" in remaining.lower()
    ):
        raise ModelRetry(
            "Use only [[tutorial:ID]] markers returned by a search in this run, each on its own line outside code blocks; "
            "Galaxy renders the references. "
            "Remove authored tutorial URLs, unknown markers, and unsupported tutorial claims. "
            "If no source was retrieved, give useful general guidance and say you cannot verify a specific tutorial."
        )

    def render(match: re.Match) -> str:
        source = sources[match.group(1)]
        title = _plain_markdown(source["title"])
        excerpt = _plain_markdown(source["excerpt"])
        return f"\n\n[{title}](<{source['url']}>)" + (f"\n\n> {excerpt}" if excerpt else "") + "\n\n"

    return _REFERENCE.sub(render, content).strip()


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
        self.gtn_db: GTNSearchDB | None = None
        try:
            self.gtn_db = GTNSearchDB(db_path=db_path, download_url=download_url)
        except Exception as e:
            log.warning(f"GTN database not available: {e}")
            self.gtn_db = None

        super().__init__(deps)

    def _tool_execution_allowed(self) -> bool:
        """Whether the tutor may actually run tools on the user's data.

        Off by default: demonstrate_concept describes tools instead of executing
        them unless a deployment opts in via ``tutor_allow_tool_execution``.
        """
        return bool(getattr(self.deps.config, "tutor_allow_tool_execution", False))

    def _get_temperature(self) -> float:
        return self._get_agent_config("temperature", 0.2)

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, str]:
        """Create the teaching assistant agent with tools."""
        agent = Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            system_prompt=self.get_system_prompt(),
            retries=2,
        )

        teaching_assistant = self

        @agent.instructions
        def runtime_capabilities() -> str:
            return teaching_assistant._build_capability_context()

        agent.output_validator(_render_tutorial_references)

        @agent.tool
        async def search_training_materials(ctx, query: str) -> str | ToolReturn:
            """Search GTN training materials for relevant tutorials."""
            return teaching_assistant._search_tutorials(query, limit=5)

        @agent.tool
        async def suggest_tutorials(ctx, topic: str) -> str | ToolReturn:
            """Suggest an ordered set of tutorials for a topic, easiest first."""
            return teaching_assistant._search_tutorials(topic, limit=8, easiest_first=True)

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
                status = teaching_assistant.ops.get_job_status(job_id, full=True)
            except Exception as e:
                return f"Could not retrieve job info: {e}"
            job_info = status.get("job", {})
            stderr = truncate_middle(str(job_info.get("stderr") or ""), JOB_LOG_EXCERPT_CHARS)

            # Also try to get analysis from the error analysis agent
            analysis = ""
            try:
                analysis = await teaching_assistant._call_agent_from_tool(
                    AgentType.ERROR_ANALYSIS,
                    f"Analyze job failure: tool={job_info.get('tool_id')}, "
                    f"exit_code={job_info.get('exit_code')}, "
                    f"stderr={stderr}",
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
                f"- Stderr: {stderr or 'none'}\n\n"
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
            """Demonstrate a tool. Use sparingly -- prefer coaching over showing.

            Runs the tool only when live execution is enabled for this deployment;
            otherwise it describes the tool and its inputs without touching the
            user's data.
            """
            try:
                inputs = json.loads(inputs_json) if inputs_json else {}
            except json.JSONDecodeError:
                return f"Invalid inputs JSON: {inputs_json}"

            if not teaching_assistant._tool_execution_allowed():
                # Safe default: describe the tool instead of running it (no side effects).
                try:
                    details = teaching_assistant.ops.get_tool_details(tool_id, io_details=True)
                except Exception as e:
                    return f"Could not look up tool '{tool_id}': {e}"
                return (
                    f"(Live tool execution is turned off here, so rather than running it, "
                    f"here's how '{tool_id}' works.)\n"
                    f"{json.dumps(details, default=str)[:800]}\n"
                    f"Proposed inputs: {json.dumps(inputs, default=str)[:300]}"
                )

            history = teaching_assistant.deps.trans.get_history()
            if history is None:
                return "No active history available for demonstration."
            history_id = teaching_assistant.deps.trans.security.encode_id(history.id)

            try:
                result = teaching_assistant.ops.run_tool(history_id, tool_id, inputs)
            except Exception as e:
                return f"Could not run tool '{tool_id}': {e}"

            if not result.get("jobs"):
                return (
                    f"No demonstration jobs were submitted for tool '{tool_id}'.\n"
                    f"Result: {json.dumps(result, default=str)[:500]}"
                )

            # Descriptions and failed submissions must not inflate the execution count.
            try:
                teaching_assistant.learning_state_manager.record_demonstration(teaching_assistant.deps.trans)
            except Exception as e:
                log.warning(f"Failed to record demonstration: {e}")

            return f"Demonstration submitted with tool '{tool_id}'.\nResult: {json.dumps(result, default=str)[:500]}"

        return agent

    def _search_tutorials(self, query: str, limit: int, easiest_first: bool = False) -> str | ToolReturn:
        if self.gtn_db is None:
            return (
                "Training material search is not available right now. No catalog evidence is available. "
                "Do not assert that GTN has or lacks tutorials on this or related topics."
            )
        try:
            results = self.gtn_db.search(query, limit=limit)
            if easiest_first:
                difficulty_order = {"introductory": 0, "beginner": 0, "intermediate": 1, "advanced": 2}
                results = sorted(results, key=lambda r: difficulty_order.get((r.difficulty or "").lower(), 1))
            sources = []
            for result in results:
                record = result.to_dict()
                url = record.get("url", "")
                parsed = urlsplit(url)
                if (
                    parsed.scheme != "https"
                    or parsed.netloc != "training.galaxyproject.org"
                    or re.search(r"[\s<>]", url)
                    or not record.get("title")
                ):
                    continue
                sources.append(
                    {
                        "id": uuid4().hex[:12],
                        "title": record["title"],
                        "url": url,
                        "excerpt": record.get("snippet") or record.get("description", ""),
                        "difficulty": result.difficulty or "unknown",
                    }
                )
        except Exception:
            log.exception("Training material search failed")
            return "Training material search failed. No sources were retrieved; tutorial availability is unknown."
        if not results:
            return (
                "No matching training materials found. This does not establish that no tutorial exists. "
                "No evidence was retrieved for related tutorials either. Do not claim the catalog has or lacks them."
            )
        if not sources:
            return "Search returned no usable tutorial references. Tutorial availability is unknown."
        # URLs stay in application metadata; the model selects records instead of writing links.
        return ToolReturn(
            return_value={"sources": [{k: v for k, v in source.items() if k != "url"} for source in sources]},
            metadata={"tutor_sources": sources},
        )

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

        return f"**Scaffolding level:** {state.get('scaffolding_level', 3)} (1=max support, 5=minimal)"

    def _build_capability_context(self) -> str:
        search = (
            "Available. Search before recommending specific tutorials; a search can still fail or return no matches."
            if self.gtn_db is not None
            else (
                "Unavailable. You cannot determine whether GTN has or lacks a tutorial on any topic. "
                "Say 'I cannot verify whether GTN has a tutorial on that topic here.' "
                "You may suggest search terms, but never claim matching lessons, sections, or related tutorials exist."
            )
        )
        execution = (
            "Enabled. demonstrate_concept can submit a job with valid inputs and an active history; submission is not completion."
            if self._tool_execution_allowed()
            else "Disabled. You can explain tools and inspect available details, but cannot run an analysis or promise to run one."
        )
        return f"Current capabilities:\nGTN search: {search}\nTool execution: {execution}"

    def _prepare_prompt(self, query: str, context: dict[str, Any]) -> str:
        """Prepare prompt with learning context included."""
        # Record the interaction
        try:
            self.learning_state_manager.record_interaction(self.deps.trans)
        except Exception as e:
            log.warning(f"Failed to record interaction: {e}")

        display_context = dict(context)
        if isinstance(display_context.get("job_id"), int):
            # The shared context uses database IDs; tutor operations require encoded IDs.
            display_context["job_id"] = self.deps.trans.security.encode_id(display_context["job_id"])
        return super()._prepare_prompt(query, display_context)

    def _format_response(self, result: Any, query: str, context: dict[str, Any]) -> AgentResponse:
        """Format response with tutor-specific metadata and suggestions."""
        content = extract_result_content(result)

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
            agent_data={
                "learning_state": learning_state,
                "tutor_mode": True,
            },
        )

    def _get_fallback_content(self) -> str:
        """Tutor-specific fallback message."""
        return (
            "I couldn't produce a reliable answer to that request. "
            "In the meantime, you can explore tutorials at "
            "https://training.galaxyproject.org/ or ask your question "
            "in task mode for a direct answer."
        )
