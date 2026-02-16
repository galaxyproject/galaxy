"""
Page assistant agent for Galaxy History Pages.

Reads history contents via tools, proposes markdown edits with structured output
(FullReplacementEdit or SectionPatchEdit), and supports conversational responses.
"""

import logging
from pathlib import Path
from typing import (
    Any,
    Literal,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
)
from pydantic_ai import (
    Agent,
    RunContext,
    ToolOutput,
)

from galaxy.schema.agents import ConfidenceLevel
from .base import (
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    extract_result_content,
    GalaxyAgentDependencies,
)
from .history_tools import (
    get_collection_structure as _get_collection_structure,
    get_dataset_info as _get_dataset_info,
    get_dataset_peek as _get_dataset_peek,
    list_history_items as _list_history_items,
    resolve_hid as _resolve_hid,
)

log = logging.getLogger(__name__)


def _djb2_hash(s: str) -> str:
    """DJB2 string hash — matches the frontend implementation."""
    h = 5381
    for c in s:
        h = ((h * 33) + ord(c)) & 0xFFFFFFFF
    return format(h, "08x")


def _build_directive_reference() -> str:
    """Generate directive reference from the authoritative source in markdown_parse.py.

    Keeps the prompt in sync with the actual set of valid directives automatically.
    """
    from galaxy.managers.markdown_parse import (
        DynamicArguments,
        EMBED_CAPABLE_DIRECTIVES,
        VALID_ARGUMENTS,
    )

    # Addressing args hidden from display — they're the primary key shown in the signature
    DATASET_ADDRESSING = {
        "history_dataset_id",
        "history_dataset_collection_id",
        "input",
        "output",
        "invocation_id",
    }

    def _primary_and_hidden(name):
        if name.startswith("history_dataset_"):
            return "history_dataset_id", DATASET_ADDRESSING
        if name.startswith("workflow_"):
            return "workflow_id", {"workflow_id"}
        if name.startswith("invocation_"):
            return "invocation_id", {"invocation_id"}
        if name == "history_link":
            return "history_id", {"history_id"}
        if name.startswith(("job_", "tool_")):
            return "job_id", {"job_id"}
        return None, set()

    def _format(name, args, show_collapse=True):
        primary, hidden = _primary_and_hidden(name)
        sig = f"{name}({primary}=N)" if primary else f"{name}()"
        visible = sorted(a for a in args if a not in hidden)
        if show_collapse:
            visible.append("collapse")
        tag = "  [inline-capable]" if name in EMBED_CAPABLE_DIRECTIVES else ""
        if visible:
            return f"- {sig} — args: {', '.join(visible)}{tag}"
        return f"- {sig}{tag}"

    def _matching(pred):
        return [n for n in sorted(VALID_ARGUMENTS) if pred(n) and not isinstance(VALID_ARGUMENTS[n], DynamicArguments)]

    categories = [
        (
            "Dataset Directives (use history_dataset_id=ID to reference history items)",
            lambda n: n.startswith("history_dataset_"),
            True,
            False,
        ),
        (
            "Workflow & Invocation Directives",
            lambda n: n.startswith(("workflow_", "invocation_")) or n == "history_link",
            True,
            False,
        ),
        ("Job Directives", lambda n: n.startswith(("job_", "tool_")), True, False),
        ("Utility Directives (no arguments)", lambda n: n.startswith("generate_"), False, False),
        (
            "Instance Link Directives (no arguments, all inline-capable)",
            lambda n: n.startswith("instance_"),
            False,
            True,
        ),
    ]

    sections = []
    for title, pred, show_collapse, grouped in categories:
        names = _matching(pred)
        if not names:
            continue
        if grouped:
            sections.append(f"### {title}\n- " + ", ".join(f"{n}()" for n in names))
        else:
            lines = [_format(n, VALID_ARGUMENTS[n], show_collapse) for n in names]
            sections.append(f"### {title}\n" + "\n".join(lines))

    return "\n\n".join(sections)


# --- Structured output types ---
# Using Literal discriminators (not Enum) to avoid $defs in JSON schema (vLLM compat).


class FullReplacementEdit(BaseModel):
    """Complete rewrite of the page document."""

    mode: Literal["full_replacement"] = "full_replacement"
    reasoning: str = Field(description="Why full replacement was chosen over section patch.")
    content: str = Field(description="The complete new document content in markdown.")


class SectionPatchEdit(BaseModel):
    """Targeted edit to a specific section of the page."""

    mode: Literal["section_patch"] = "section_patch"
    reasoning: str = Field(description="Why this section was targeted.")
    target_section_heading: str = Field(
        description="The exact heading text of the section to replace (e.g. '## Methods')."
    )
    new_section_content: str = Field(description="The new content for this section, including the heading line.")


class PageAssistantAgent(BaseGalaxyAgent):
    """Agent for editing Galaxy History Pages via chat.

    Discovers history data via tools, proposes markdown edits using structured
    output (full replacement or section patch), and supports conversational
    responses for questions about the history.
    """

    agent_type = AgentType.PAGE_ASSISTANT

    def __init__(self, deps: GalaxyAgentDependencies, history_id: Optional[int] = None, page_content: str = ""):
        self.history_id: Optional[int] = history_id
        self.history_is_session: bool = False
        self.page_content: str = page_content
        super().__init__(deps)

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        """Create agent with history tools and edit output types."""
        agent_self = self
        if self._supports_structured_output():
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                output_type=[
                    ToolOutput(
                        FullReplacementEdit,
                        name="replace_entire_document",
                        description="Rewrite the entire page. Use for major rewrites, restructuring, or when >50% of content changes.",
                    ),
                    ToolOutput(
                        SectionPatchEdit,
                        name="patch_section",
                        description="Modify a specific section. PREFER THIS when in doubt — it preserves user work on other sections.",
                    ),
                    str,  # Conversational response (no edit)
                ],
            )
        else:
            agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
            )

        # Dynamic system prompt — reads self.page_content at call time
        @agent.system_prompt
        def _system_prompt() -> str:
            if agent_self._supports_structured_output():
                return agent_self.get_system_prompt()
            return agent_self._get_simple_system_prompt()

        # Tools reference agent_self.history_id — set in process() from context before each run.
        # When editing standalone pages (no history), tools return a helpful message.
        _NO_HISTORY_MSG = "This page is not associated with a history. History browsing tools are not available."

        @agent.tool
        async def list_history_datasets(
            ctx: RunContext[GalaxyAgentDependencies],
            include_deleted: bool = False,
            include_hidden: bool = False,
            offset: int = 0,
            limit: int = 50,
        ) -> str:
            """List datasets and collections in the current history.

            Returns HID, name, type, format, state, and size for each item.
            Call this first to understand what data is available before referencing
            specific items by HID.
            """
            if not agent_self.history_id:
                return _NO_HISTORY_MSG
            return await _list_history_items(
                ctx.deps.trans.sa_session,
                agent_self.history_id,
                offset=offset,
                limit=limit,
                include_deleted=include_deleted,
                include_hidden=include_hidden,
                encode_id=ctx.deps.trans.security.encode_id,
            )

        @agent.tool
        async def get_dataset_info(
            ctx: RunContext[GalaxyAgentDependencies],
            hid: int,
        ) -> str:
            """Get detailed information about a specific dataset or collection.

            Returns name, format, state, size, metadata, creation time, and the
            tool that created it. Works for both datasets and collections.
            """
            if not agent_self.history_id:
                return _NO_HISTORY_MSG
            return await _get_dataset_info(
                ctx.deps.trans.sa_session, agent_self.history_id, hid, encode_id=ctx.deps.trans.security.encode_id
            )

        @agent.tool
        async def get_dataset_peek(
            ctx: RunContext[GalaxyAgentDependencies],
            hid: int,
        ) -> str:
            """Get a preview of a dataset's contents (first few rows/lines).

            For tabular data shows column headers and sample rows. For text data
            shows the first lines. Not available for binary formats.
            """
            if not agent_self.history_id:
                return _NO_HISTORY_MSG
            return await _get_dataset_peek(ctx.deps.trans.sa_session, agent_self.history_id, hid)

        @agent.tool
        async def get_collection_structure(
            ctx: RunContext[GalaxyAgentDependencies],
            hid: int,
            max_elements: int = 50,
        ) -> str:
            """Get the structure and element listing of a dataset collection.

            Shows collection type, element count, and lists elements with names,
            formats, and states.
            """
            if not agent_self.history_id:
                return _NO_HISTORY_MSG
            return await _get_collection_structure(
                ctx.deps.trans.sa_session,
                agent_self.history_id,
                hid,
                max_elements=max_elements,
            )

        @agent.tool
        async def resolve_hid(
            ctx: RunContext[GalaxyAgentDependencies],
            hid: int,
        ) -> str:
            """Resolve a HID to the directive argument for Galaxy markdown.

            Use this when you know a dataset's HID number and need the
            history_dataset_id or history_dataset_collection_id for a directive.
            Also returns the job_id if the item was created by a tool.
            """
            if not agent_self.history_id:
                return _NO_HISTORY_MSG
            return await _resolve_hid(
                ctx.deps.trans.sa_session, agent_self.history_id, hid, encode_id=ctx.deps.trans.security.encode_id
            )

        return agent

    def get_system_prompt(self) -> str:
        """Load system prompt and inject page content and directive reference."""
        prompt_path = Path(__file__).parent / "prompts" / "page_assistant.md"
        template = prompt_path.read_text()
        content = self.page_content or "(empty document)"
        directive_ref = _build_directive_reference()
        prompt = template.replace("{page_content}", content).replace("{directive_reference}", directive_ref)
        if not self.history_id:
            prompt = (
                "**NOTE: This is a standalone page with no history available. "
                "The history browsing tools (list_history_datasets, get_dataset_info, etc.) "
                "are not available. Focus on editing the page content directly.**\n\n" + prompt
            )
        elif self.history_is_session:
            prompt = (
                "**NOTE: This is a standalone page. You have access to the user's "
                "current active history for reference, but this page is not attached "
                "to it. You can use history tools to browse datasets, but be aware "
                "the user may switch histories during their session.**\n\n" + prompt
            )
        return prompt

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        """Process a page editing or history question."""
        ctx = context or {}
        self.history_id = ctx.get("history_id") or None
        self.history_is_session = ctx.get("history_is_session", False)
        self.page_content = ctx.get("page_content", "")
        try:
            enhanced_query = self._prepare_prompt(query, ctx)
            result = await self._run_with_retry(enhanced_query)

            # Extract the result data
            result_data = result.output if hasattr(result, "output") else result.data

            content_hash = _djb2_hash(self.page_content)

            if isinstance(result_data, FullReplacementEdit):
                return self._build_response(
                    content=f"I've prepared a full document rewrite.\n\n**Reasoning:** {result_data.reasoning}",
                    confidence=ConfidenceLevel.HIGH,
                    method="structured",
                    result=result,
                    query=query,
                    agent_data={
                        "edit_mode": "full_replacement",
                        "reasoning": result_data.reasoning,
                        "content": result_data.content,
                        "original_content_hash": content_hash,
                    },
                )
            elif isinstance(result_data, SectionPatchEdit):
                return self._build_response(
                    content=(
                        f"I've prepared an edit to section **{result_data.target_section_heading}**."
                        f"\n\n**Reasoning:** {result_data.reasoning}"
                    ),
                    confidence=ConfidenceLevel.HIGH,
                    method="structured",
                    result=result,
                    query=query,
                    agent_data={
                        "edit_mode": "section_patch",
                        "reasoning": result_data.reasoning,
                        "target_section_heading": result_data.target_section_heading,
                        "new_section_content": result_data.new_section_content,
                        "original_content_hash": content_hash,
                    },
                )
            else:
                # Conversational response (str)
                content = extract_result_content(result)
                return self._build_response(
                    content=content,
                    confidence=ConfidenceLevel.MEDIUM,
                    method="text",
                    result=result,
                    query=query,
                )

        except OSError as e:
            log.warning(f"Page assistant network error: {e}")
            return self._get_fallback_response(query, str(e))
        except ValueError as e:
            log.warning(f"Page assistant value error: {e}")
            return self._get_fallback_response(query, str(e))

    def _get_simple_system_prompt(self) -> str:
        """Fallback prompt for models without structured output."""
        content = self.page_content or "(empty document)"
        directive_ref = _build_directive_reference()
        if self.history_id and not self.history_is_session:
            intro = (
                "You are a Galaxy History Page editing assistant. Help users edit their\n"
                "markdown pages that document scientific analysis workflows."
            )
            history_tools_note = (
                "For questions about the history data, use the available tools to look up datasets.\n"
                "Users refer to items by HID (the number in the history panel). Use resolve_hid(hid)\n"
                "to get the encoded history_dataset_id or history_dataset_collection_id for directives.\n"
                "All tool outputs return encoded IDs — copy them directly into directives.\n"
                "The resolve_hid and get_dataset_info tools also return job_id for job directives."
            )
        elif self.history_id and self.history_is_session:
            intro = (
                "You are a Galaxy Page editing assistant. This is a standalone page, but you\n"
                "have access to the user's current active history for reference. The page is not\n"
                "attached to this history — the user may switch histories during their session."
            )
            history_tools_note = (
                "You can use history tools to browse datasets in the user's current session history.\n"
                "Users refer to items by HID (the number in the history panel). Use resolve_hid(hid)\n"
                "to get the encoded history_dataset_id or history_dataset_collection_id for directives.\n"
                "All tool outputs return encoded IDs — copy them directly into directives.\n"
                "The resolve_hid and get_dataset_info tools also return job_id for job directives."
            )
        else:
            intro = (
                "You are a Galaxy Page editing assistant. Help users edit their\n"
                "markdown pages. This page is not associated with a history, so history\n"
                "browsing tools are not available. Focus on editing the page content directly."
            )
            history_tools_note = ""
        return f"""{intro}

When proposing edits, clearly indicate whether you're rewriting the entire document
or patching a specific section by starting your response with:
EDIT_MODE: full_replacement
or
EDIT_MODE: section_patch
TARGET_SECTION: ## Section Name

Then provide the new content after a blank line.

{history_tools_note}

Galaxy markdown uses block directives (```galaxy fenced blocks with one directive each)
and inline directives (${{galaxy directive_name(args)}}) for embed-capable directives.
Dataset directives use history_dataset_id=ENCODED_ID, collection directives use
history_dataset_collection_id=ENCODED_ID, job directives use job_id=ENCODED_ID.

{directive_ref}

Current page content:
{content}"""
