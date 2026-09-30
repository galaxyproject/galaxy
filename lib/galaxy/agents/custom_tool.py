"""
Custom tool creation agent for Galaxy.
"""

import asyncio
import logging
import re
from collections.abc import (
    Callable,
    Sequence,
)
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Literal,
)

import yaml
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
)
from pydantic_ai import (
    Agent,
    capture_run_messages,
)
from pydantic_ai.exceptions import (
    ModelHTTPError,
    UnexpectedModelBehavior,
)

from galaxy.schema.agents import ConfidenceLevel
from galaxy.tool_util.deps.mulled.recommend import (
    biocontainer_tag_built,
    ContainerRecommendation,
    MatchQuality,
    PackageSpec,
    QUAY_BIOCONTAINERS_PREFIX,
    recommend_container,
)
from galaxy.tool_util.lint import lint_user_tool_source
from galaxy.tool_util_models import (
    CondaPackage,
    format_validation_errors,
    UserToolSource,
    UserToolSourceAuthoringView,
)
from .base import (
    ActionSuggestion,
    ActionType,
    AgentResponse,
    AgentType,
    BaseGalaxyAgent,
    extract_structured_output,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)

# Matches an interpreter invoking a script *file by name* in a shell_command, e.g.
# ``Rscript boxplot.R`` / ``python script.py`` / ``bash run.sh``. Deliberately
# conservative -- the script must immediately follow the interpreter (no flags in
# between), so inline-code forms like ``python -c "..."`` / ``Rscript -e "..."`` do
# NOT match (their flag isn't a filename). Under-matching is safe here (we'd just
# skip a check); over-matching would reject valid tools, so we don't.
_SCRIPT_INVOCATION_RE = re.compile(
    r"\b(?:python3?|Rscript|bash|sh|perl|ruby)\s+['\"]?(?P<script>[\w./-]+\.(?:py|R|r|sh|bash|pl|rb))\b"
)


def _find_validation_error(exc: BaseException) -> ValidationError | None:
    """Walk the exception cause chain looking for a pydantic ValidationError.

    pydantic-ai wraps validation failures inside UnexpectedModelBehavior after
    exhausting retries; the original ValidationError surfaces via __cause__.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, ValidationError):
            return current
        current = current.__cause__ or current.__context__
    return None


def _invalid_attempt_yaml(messages: list[Any]) -> str | None:
    """Best-effort render of the model's last ``final_result`` tool-call arguments
    (the attempt that just failed schema validation) as YAML.

    On a schema-validation failure there's no constructed model to show back, but
    the raw rejected arguments are still in the captured run messages. Recovering
    them lets a validation-failure retry show the model its own output to patch in
    place, instead of regenerating blind. Returns None if the args can't be
    recovered (malformed JSON, no tool call, etc.).
    """
    for message in reversed(messages):
        for part in getattr(message, "parts", None) or []:
            if getattr(part, "part_kind", None) != "tool-call":
                continue
            if getattr(part, "tool_name", None) != "final_result":
                continue
            try:
                args = part.args_as_dict()
            except (ValueError, TypeError):
                return None
            # pydantic-ai returns a {"INVALID_JSON": "<raw>"} sentinel rather than
            # raising when the tool-call args aren't valid JSON; that's not a usable
            # prior attempt, so treat it as unrecoverable.
            if not isinstance(args, dict) or not args or set(args) == {"INVALID_JSON"}:
                return None
            return yaml.dump(args, default_flow_style=False, sort_keys=False)
    return None


class InferredDependencies(BaseModel):
    """Output of the dedicated container critic.

    The container critic reads only a tool's ``shell_command`` and configfiles and
    returns the conda packages needed to run them, so a verified biocontainer can
    be resolved from ``packages`` without the producer guessing an image tag.
    """

    packages: list[CondaPackage] = Field(default_factory=list)


class ToolEdit(BaseModel):
    """A single field-level fix the critic supplies so it can be applied
    deterministically -- no full re-roll of the tool.

    ``target`` selects what to edit; ``name`` identifies the input/output by its
    declared ``name`` (ignored for ``tool``); ``attribute`` is the field to set and
    ``value`` its new (string) text. Only a fixed, safe set of (target, attribute)
    pairs is applied (see ``CustomToolAgent._apply_one_edit``) -- anything else is a
    structural change the critic must route through ``needs_full_refine`` instead.
    """

    target: Literal["tool", "input", "output"]
    name: str | None = None
    attribute: Literal["label", "help", "description", "name", "shell_command"]
    value: str
    reason: str = ""


class CritiqueReport(BaseModel):
    """Structured critique returned by the quality critic.

    Issues are split between *clarity* (text the user reads -- description,
    labels, help text) and *idiomaticity* (tool shape -- defaults, exposed
    options). Container choice is out of scope -- the dedicated container critic
    owns it.

    The critic also supplies the *fixes*, not just the diagnosis:

    - ``edits`` are field-level patches applied deterministically to the validated
      tool, so the common clarity polish (labels, help, description) needs no
      second producer call and cannot regress unflagged fields.
    - ``needs_full_refine`` signals a change that can't be expressed as a field
      edit (adding an input/output, exposing a new parameter, ...); those fall
      back to a full producer re-roll using ``clarity_issues``/``idiomaticity_issues``.
    """

    clarity_issues: list[str] = Field(default_factory=list)
    idiomaticity_issues: list[str] = Field(default_factory=list)
    edits: list[ToolEdit] = Field(default_factory=list)
    needs_full_refine: bool = False
    summary: str = ""


@dataclass
class _ProducerFailure:
    """A failed production attempt.

    Carries the distilled validation/lint ``errors`` and -- when we have it -- the
    rendered ``prior_yaml`` of the attempt. Lint failures validate cleanly first,
    so the YAML exists and can be shown back to the model on retry to anchor the
    error list to a concrete artifact ("fix these problems in the YAML below")
    rather than asking it to regenerate blind. Schema-validation failures don't
    yield a rendered model, so ``prior_yaml`` is None there (addressed separately
    by an in-context continuation retry).
    """

    errors: list[str]
    prior_yaml: str | None = None


class CustomToolAgent(BaseGalaxyAgent):
    """Agent that creates custom Galaxy tools using UserToolSource schema.

    Requires a model with structured output support. If the configured model
    doesn't support structured output, returns an error guiding the operator
    to configure an appropriate model.

    Reflection: ``UserToolSource``'s pydantic validators catch structural
    issues at construction time. Two opt-in loops handle the remainder:

    - **Validator-driven retry** (default on): if the producer's output
      fails validation, the producer is re-called once with the structured
      error list and asked to fix specifically those issues. Cap of one
      retry.
    - **Quality critic + refine** (default off): an LLM critic reviews the
      validated tool for clarity / idiomaticity issues that pydantic can't
      see. If the critic flags significant issues, the producer is
      re-rolled once with the critique. Cap of one refine; if refinement
      breaks validation, the original tool is kept.

    Container resolution is a separate, opt-in concern (default off): the
    producer prompt only asks for a plausible image. When enabled, a dedicated
    **container critic** infers the conda packages from the tool's
    ``shell_command``/configfiles alone, a verified ``quay.io/biocontainers``
    image is resolved from them, and a deterministic gate applies it.

    The loops are gated on per-deployment config under
    ``inference_services.custom_tool``: ``validator_retry_enabled``,
    ``quality_critic_enabled``, and ``container_recommendation_enabled``.
    Default to validator-only behavior -- operators turn the critics on when
    they're willing to pay for the extra model calls.
    """

    agent_type = AgentType.CUSTOM_TOOL
    capability_blurb = (
        "Generate a Galaxy tool definition (XML/YAML) when you explicitly ask to wrap a command-line program."
    )
    DEFAULT_MAX_TOKENS = 16384

    def __init__(
        self,
        deps: GalaxyAgentDependencies,
        recommender: Callable[[Sequence[PackageSpec]], ContainerRecommendation] = recommend_container,
        tag_verifier: Callable[[str], bool | None] = biocontainer_tag_built,
    ):
        super().__init__(deps)
        self._critic_agent: Agent[GalaxyAgentDependencies, CritiqueReport] | None = None
        self._container_critic_agent: Agent[GalaxyAgentDependencies, InferredDependencies] | None = None
        # Injected so tests can supply fakes instead of patching the module globals
        # (and to keep unit tests off the network).
        self._recommender = recommender
        self._tag_verifier = tag_verifier

    def _requires_structured_output(self) -> bool:
        return True

    def _get_temperature(self) -> float:
        # Tool generation is schema-constrained structured output, not creative
        # prose. A low temperature converges faster and produces fewer invalid
        # drafts, which directly cuts the validator-retry round-trips this agent
        # would otherwise pay for. Operators can still override via
        # inference_services.custom_tool.temperature.
        return self._get_agent_config("temperature", 0.2)

    def _create_agent(self) -> Agent[GalaxyAgentDependencies, Any]:
        """Create agent with ``UserToolSourceAuthoringView`` as the output type.

        The authoring view is ``UserToolSource`` minus the ``tests`` block, which
        is ~70% of the full JSON schema. Targeting it shrinks the structured-output
        schema the model must satisfy (~150 KB -> ~33 KB) without weakening any tool
        validation -- a produced view is promoted to a full ``UserToolSource`` in
        ``_produce_tool``.

        Defaults retries to 0 because the agent's explicit reflection loop owns the
        validation retry (to provide a better prompt); operators can still override
        via inference_services.
        """
        return Agent(
            self._get_model(),
            deps_type=GalaxyAgentDependencies,
            output_type=UserToolSourceAuthoringView,
            system_prompt=self.get_system_prompt(),
            retries=self._get_retries(default=0),
        )

    def get_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "custom_tool_structured.md"
        return prompt_path.read_text()

    def _get_critic_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "custom_tool_critic.md"
        return prompt_path.read_text()

    def _get_container_critic_system_prompt(self) -> str:
        prompt_path = Path(__file__).parent / "prompts" / "custom_tool_container_critic.md"
        return prompt_path.read_text()

    def _get_critic_agent(self) -> Agent[GalaxyAgentDependencies, CritiqueReport]:
        """Lazily build the quality critic. Same model as the producer by default;
        operators can override via ``inference_services.custom_tool.critic_model``.

        The critic has no tools and stays single-shot: it reviews clarity /
        idiomaticity only. Container choice is owned by the dedicated container
        critic + deterministic recommender gate, not by this critic.
        """
        if self._critic_agent is None:
            self._critic_agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                output_type=CritiqueReport,
                system_prompt=self._get_critic_system_prompt(),
                retries=self._get_retries(),
            )
        return self._critic_agent

    def _get_container_critic_agent(self) -> Agent[GalaxyAgentDependencies, InferredDependencies]:
        """Lazily build the container critic.

        A focused, single-shot agent: its only input is the tool's
        ``shell_command``/configfiles and its only output is the conda packages
        needed to run them. No tools -- the deterministic recommender does the
        quay.io resolution from its package list.
        """
        if self._container_critic_agent is None:
            self._container_critic_agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                output_type=InferredDependencies,
                system_prompt=self._get_container_critic_system_prompt(),
                retries=self._get_retries(),
            )
        return self._container_critic_agent

    def _validator_retry_enabled(self) -> bool:
        return bool(self._get_agent_config("validator_retry_enabled", True))

    def _quality_critic_enabled(self) -> bool:
        return bool(self._get_agent_config("quality_critic_enabled", False))

    def _container_recommendation_enabled(self) -> bool:
        """Resolve the tool's container against quay.io biocontainers.

        Off by default and independent of the quality critic. When on, the
        dedicated container critic infers the conda packages from the tool's
        ``shell_command``/configfiles, the recommender resolves a verified image,
        and a deterministic gate applies it. Enabling it adds a focused model call
        plus an outbound network call (to quay.io) during the agent turn.
        """
        return bool(self._get_agent_config("container_recommendation_enabled", False))

    async def process(self, query: str, context: dict[str, Any] | None = None) -> AgentResponse:
        validation_error = self._validate_query(query)
        if validation_error:
            return self._validation_error_response(validation_error)

        capability_error = self._validate_model_capabilities()
        if capability_error:
            return self._capability_error_response(capability_error, query)

        try:
            attempts = 1
            produced = await self._produce_tool(query)
            if produced is None:
                return self._invalid_structured_output_response(query)

            if isinstance(produced, _ProducerFailure):
                # _produce_tool returns a _ProducerFailure when the producer hit a
                # pydantic ValidationError or lint failure. Retry once if enabled,
                # otherwise surface the issues to the user.
                if not self._validator_retry_enabled():
                    log.debug("CustomTool: validator retry disabled; failing with issues: %s", produced.errors)
                    return self._validation_failed_response(produced.errors, query, attempts=attempts)
                attempts = 2
                log.info("CustomTool: model failed validation (%d issue(s)); retrying once", len(produced.errors))
                log.debug(
                    "CustomTool: first-attempt issues=%s; prior_yaml_available=%s",
                    produced.errors,
                    produced.prior_yaml is not None,
                )
                if produced.prior_yaml:
                    log.debug("CustomTool: rejected first attempt:\n%s", produced.prior_yaml)
                # Thread the prior attempt (when we have it) so the retry prompt can
                # anchor the error list to the YAML the model actually produced.
                retried = await self._produce_tool(query, retry_errors=produced.errors, prior_yaml=produced.prior_yaml)
                if retried is None:
                    log.warning(
                        "CustomTool: retry produced no usable structured output (issues fed back: %s)",
                        produced.errors,
                    )
                    return self._invalid_structured_output_response(query)
                if isinstance(retried, _ProducerFailure):
                    first, again = set(produced.errors), set(retried.errors)
                    log.warning(
                        "CustomTool: retry still invalid (%d issue(s)). "
                        "resolved=%s; persisted=%s; newly-introduced=%s",
                        len(retried.errors),
                        sorted(first - again) or "none",
                        sorted(first & again) or "none",
                        sorted(again - first) or "none",
                    )
                    return self._validation_failed_response(retried.errors, query, attempts=attempts)
                log.info("CustomTool: retry recovered after %d first-attempt issue(s)", len(produced.errors))
                tool, tool_yaml, result = retried
            else:
                tool, tool_yaml, result = produced

            # Quality critic: clarity/idiomaticity only (container is resolved below).
            # The critic supplies the fixes, not just the diagnosis:
            #   - field-level ``edits`` are applied deterministically -- no second
            #     producer call, and they can't regress fields the critic didn't name.
            #   - a structural change (``needs_full_refine``) or a patch that fails to
            #     apply/validate falls back to a full producer re-roll.
            if self._quality_critic_enabled():
                critique = await self._run_critic(tool_yaml, query)
                if critique is not None and critique.needs_full_refine:
                    log.info(
                        "CustomTool: critic requested full refine (%d clarity / %d idiomaticity issues)",
                        len(critique.clarity_issues),
                        len(critique.idiomaticity_issues),
                    )
                    tool, tool_yaml, result = await self._full_refine(query, critique, tool, tool_yaml, result)
                elif critique is not None and critique.edits:
                    patched = self._apply_edits(tool, critique.edits)
                    if patched is not None:
                        tool, tool_yaml = patched
                        log.info(
                            "CustomTool: applied %d deterministic critic edit(s); no refine call",
                            len(critique.edits),
                        )
                    else:
                        log.info("CustomTool: critic edits not applicable; falling back to full refine")
                        tool, tool_yaml, result = await self._full_refine(query, critique, tool, tool_yaml, result)

            # Container resolution (opt-in, critic-independent). The producer's own
            # image choice is a best guess; a dedicated container critic infers
            # the conda packages from the final tool's shell_command/configfiles, the
            # recommender resolves a verified quay.io image, and the deterministic
            # gate applies it. Run last so it sees the post-refine command.
            tool, tool_yaml = await self._resolve_container(tool, tool_yaml)

            return self._success_response(tool, tool_yaml, result, query, attempts=attempts)

        except (OSError, ValueError) as e:
            log.error(f"Tool creation error: {e}")
            return self._build_response(
                content=f"Failed to create tool: {str(e)}\n\nPlease try again with clear requirements.",
                confidence=ConfidenceLevel.LOW,
                method="error",
                query=query,
                error=str(e),
            )
        except ModelHTTPError as e:
            return self._handle_model_http_error(e, query)
        except UnexpectedModelBehavior as e:
            return self._handle_unexpected_model_behavior(e, query)

    async def _produce_tool(
        self,
        query: str,
        retry_errors: list[str] | None = None,
        critique: CritiqueReport | None = None,
        prior_yaml: str | None = None,
    ) -> tuple[UserToolSource, str, Any] | _ProducerFailure | None:
        """Run the producer agent. Returns (tool, yaml, raw_result), a
        ``_ProducerFailure``, or None.

        ``retry_errors`` and ``critique`` are mutually exclusive: each prepends a
        structured "fix specifically these issues" preamble to the original query.
        """
        prompt = self._build_producer_prompt(query, retry_errors=retry_errors, critique=critique, prior_yaml=prior_yaml)
        # Capture the run messages so that, on a schema-validation failure, we can
        # recover the model's rejected tool-call args and feed them back into the
        # retry (there's no constructed model to render in that case).
        with capture_run_messages() as messages:
            try:
                result = await self._run_with_retry(prompt)
                authored = extract_structured_output(result, UserToolSourceAuthoringView, log)
                if authored is None:
                    return None
                # The model authors against the slim view (no `tests`); promote to the
                # full UserToolSource so linting, serialization, and storage operate on
                # the canonical model. The view is a strict subset, so this never fails.
                tool = UserToolSource.model_validate(authored.model_dump(by_alias=True))
                tool_yaml = self._render_tool_yaml(tool)
                # Lint + an agent-side check that any script the command runs by name
                # is actually materialized by a configfile (a common producer miss the
                # canonical validators don't catch -- e.g. `Rscript boxplot.R` with no
                # configfile, which would fail at runtime).
                issues = lint_user_tool_source(tool) + self._unmaterialized_scripts(tool)
                if issues:
                    log.debug("CustomToolAgent lint/script failure: %s", issues)
                    # The tool validated, so we have its rendered YAML -- carry it so a
                    # retry can show the model exactly what to fix in place.
                    return _ProducerFailure(issues, prior_yaml=tool_yaml)
                return tool, tool_yaml, result
            except UnexpectedModelBehavior as e:
                pydantic_error = _find_validation_error(e)
                if pydantic_error:
                    # No constructed model to show back, but recover the raw rejected
                    # args from the run messages so the retry can patch them in place.
                    return _ProducerFailure(
                        format_validation_errors(pydantic_error),
                        prior_yaml=_invalid_attempt_yaml(messages),
                    )
                raise e

    @staticmethod
    def _build_producer_prompt(
        query: str,
        retry_errors: list[str] | None = None,
        critique: CritiqueReport | None = None,
        prior_yaml: str | None = None,
    ) -> str:
        if not retry_errors and not critique:
            return query

        # On a repair/refine turn, lead with the artifact being fixed so the error
        # list is anchored to something concrete, follow with the prominent,
        # numbered problems, and demote the original request to trailing reference
        # (it's secondary when patching a near-correct draft).
        sections: list[str] = []
        if prior_yaml:
            sections.append(
                "Your previous attempt is below. It is close -- fix it in place, do NOT "
                "rewrite it from scratch:\n\n"
                f"```yaml\n{prior_yaml}```"
            )

        if retry_errors:
            numbered = "\n".join(f"{i}. {e}" for i, e in enumerate(retry_errors, 1))
            target = "the YAML above" if prior_yaml else "your previous attempt"
            sections.append(
                f"That attempt failed validation. Fix every one of these problems in {target} "
                "and return the full corrected tool definition; leave everything else "
                f"unchanged:\n\n{numbered}"
            )
        elif critique:
            issue_lines: list[str] = []
            if critique.clarity_issues:
                issue_lines.append("Clarity issues:")
                issue_lines.extend(f"- {issue}" for issue in critique.clarity_issues)
            if critique.idiomaticity_issues:
                if issue_lines:
                    issue_lines.append("")
                issue_lines.append("Idiomaticity issues:")
                issue_lines.extend(f"- {issue}" for issue in critique.idiomaticity_issues)
            sections.append(
                "The previous attempt is structurally valid but a reviewer flagged "
                "the following quality issues:\n\n" + "\n".join(issue_lines) + "\n\n"
                "Re-generate the tool definition addressing those issues. Don't "
                "change parts the reviewer didn't flag."
            )

        sections.append("Original request (for reference):\n\n" + query)
        return "\n\n".join(sections)

    async def _run_critic(self, tool_yaml: str, query: str) -> CritiqueReport | None:
        """Run the quality critic. Returns None if the critic call fails."""
        critic = self._get_critic_agent()
        critic_prompt = (
            "Original request:\n\n"
            f"{query}\n\n"
            "Tool definition produced (already structurally validated):\n\n"
            f"```yaml\n{tool_yaml}```\n\n"
            "Critique this tool for clarity and idiomaticity, and supply the fixes: "
            "provide an `edits` entry for every field-level issue, or set "
            "`needs_full_refine` if a structural change is required."
        )
        try:
            result = await critic.run(critic_prompt, deps=self.deps)
            output = getattr(result, "output", None)
            if isinstance(output, CritiqueReport):
                return output
            log.warning("CustomTool: critic returned non-CritiqueReport output (%r); skipping refine", type(output))
            return None
        except (OSError, ValueError, ModelHTTPError, UnexpectedModelBehavior) as e:
            log.warning("CustomTool: critic call failed (%s); skipping refine", e)
            return None

    async def _full_refine(
        self, query: str, critique: CritiqueReport, tool: UserToolSource, tool_yaml: str, result: Any
    ) -> tuple[UserToolSource, str, Any]:
        """Re-roll the whole tool to address ``critique``; keep the prior tool on failure.

        The fallback for changes the critic can't express as deterministic field
        edits (structural fixes) or when a patch fails to validate.
        """
        refined = await self._produce_tool(query, critique=critique, prior_yaml=tool_yaml)
        if isinstance(refined, tuple):
            return refined
        if isinstance(refined, _ProducerFailure):
            log.warning(
                "CustomTool: refinement broke validation (%d issue(s)); keeping pre-refine tool",
                len(refined.errors),
            )
        return tool, tool_yaml, result

    def _apply_edits(self, tool: UserToolSource, edits: list[ToolEdit]) -> tuple[UserToolSource, str] | None:
        """Apply the critic's field-level ``edits`` deterministically.

        Mutates a dict copy of ``tool``, re-validates, and returns the patched
        ``(tool, yaml)``. Returns None if no edit applied or the result fails
        validation -- the caller then falls back to a full refine. Because only the
        named fields change, the patch can't regress anything the critic didn't flag.
        """
        data = tool.model_dump(by_alias=True)
        applied = sum(int(self._apply_one_edit(data, edit)) for edit in edits)
        if not applied:
            return None
        try:
            patched = UserToolSource.model_validate(data)
        except ValidationError as e:
            log.warning("CustomTool: critic edits failed validation (%s); falling back", e)
            return None
        return patched, self._render_tool_yaml(patched)

    # (target, attribute) pairs we apply deterministically. All are string-valued;
    # anything outside this set is a structural change the critic must route through
    # needs_full_refine instead.
    _PATCHABLE = {
        ("tool", "description"),
        ("tool", "name"),
        ("tool", "shell_command"),
        ("input", "label"),
        ("input", "help"),
        ("output", "label"),
    }

    @classmethod
    def _apply_one_edit(cls, data: dict[str, Any], edit: ToolEdit) -> bool:
        """Set a single field on the tool dict in place. Returns True if applied."""
        if (edit.target, edit.attribute) not in cls._PATCHABLE:
            return False
        if edit.target == "tool":
            data[edit.attribute] = edit.value
            return True
        # input / output: locate the entry by its declared name.
        collection = data.get("inputs" if edit.target == "input" else "outputs") or []
        for entry in collection:
            if isinstance(entry, dict) and entry.get("name") == edit.name:
                entry[edit.attribute] = edit.value
                return True
        return False

    async def _resolve_container(self, tool: UserToolSource, tool_yaml: str) -> tuple[UserToolSource, str]:
        """Pick a verified biocontainer for ``tool`` and apply it if warranted.

        No-op unless ``container_recommendation_enabled``. Otherwise: the container
        critic infers the conda packages from the command/configfiles, the
        recommender resolves an image, and the deterministic gate
        (``_should_override_container``) decides whether to rewrite. Returns the
        possibly-updated ``(tool, tool_yaml)``; the original pair on any miss.
        """
        if not self._container_recommendation_enabled():
            return tool, tool_yaml

        packages = await self._infer_packages(tool)
        if not packages:
            return tool, tool_yaml

        recommendation = await self._lookup_container(packages)
        if (
            recommendation.image is not None
            and self._container_differs(tool.container, recommendation.image)
            and await self._should_override_container(tool.container, recommendation.match_quality)
        ):
            rewritten = self._rewrite_container(tool, recommendation.image)
            if rewritten is not None:
                log.info("CustomTool: rewrote container to verified biocontainer %s", recommendation.image)
                return rewritten
        return tool, tool_yaml

    async def _infer_packages(self, tool: UserToolSource) -> list[CondaPackage]:
        """Infer the tool's conda packages via the dedicated container critic.

        The critic sees only the ``shell_command`` and configfiles -- nothing else
        about the tool. Returns an empty list on any failure or when the command
        wraps no recognizable package, in which case the container is left as the
        producer wrote it.
        """
        critic = self._get_container_critic_agent()
        sections = [f"shell_command:\n\n{tool.shell_command}"]
        for configfile in tool.configfiles or []:
            name = configfile.filename or configfile.name or "configfile"
            sections.append(f"configfile ({name}):\n\n{configfile.content}")
        prompt = "Infer the conda packages required to run the following.\n\n" + "\n\n".join(sections)
        try:
            result = await critic.run(prompt, deps=self.deps)
            output = getattr(result, "output", None)
            if isinstance(output, InferredDependencies):
                return output.packages
            log.warning("CustomTool: container critic returned %r; skipping container resolution", type(output))
        except (OSError, ValueError, ModelHTTPError, UnexpectedModelBehavior) as e:
            log.warning("CustomTool: container critic failed (%s); skipping container resolution", e)
        return []

    async def _lookup_container(self, packages: Sequence[CondaPackage]) -> ContainerRecommendation:
        """Resolve a verified biocontainer for ``packages`` off the event loop.

        ``recommend_container`` is synchronous (``requests``) and never raises for
        a missing container or transient network error, so it is safe to offload.
        """
        specs = [PackageSpec(p.name, p.version) for p in packages]
        return await asyncio.to_thread(self._recommender, specs)

    async def _should_override_container(self, current: str | None, match_quality: MatchQuality) -> bool:
        """Decide whether to deterministically replace ``current`` with the recommendation.

        An ``EXACT_VERSION`` match always wins. A ``NAME_ONLY`` match wins unless
        ``current`` is a *verified-present* biocontainer (a deliberate, working pin
        we respect). So it overrides both a broken biocontainer tag AND an image
        that isn't a biocontainer at all (``rocker/...``, ``ubuntu``, ...) -- when
        container resolution is on, a verified biocontainer is preferred over an
        arbitrary registry image.
        """
        if match_quality == MatchQuality.EXACT_VERSION:
            return True
        if match_quality == MatchQuality.NAME_ONLY:
            if not self._is_biocontainer_ref(current):
                return True
            return await self._container_tag_missing(current)
        return False

    @staticmethod
    def _is_biocontainer_ref(container: str | None) -> bool:
        """True if ``container`` is a ``quay.io/biocontainers`` image reference."""
        return container is not None and container.strip().startswith(f"{QUAY_BIOCONTAINERS_PREFIX}/")

    async def _container_tag_missing(self, container: str | None) -> bool:
        """True only when ``container`` is positively verified absent from biocontainers.

        Offloads the synchronous ``requests``-based verifier and collapses its
        tri-state result: an unverifiable container (non-biocontainer image or a
        transient lookup failure) yields ``False`` so we never override on a guess.
        """
        if not container:
            return False
        verified = await asyncio.to_thread(self._tag_verifier, container)
        return verified is False

    @staticmethod
    def _container_differs(current: str | None, recommended: str | None) -> bool:
        if not recommended:
            return False
        return (current or "").strip() != recommended.strip()

    def _rewrite_container(self, tool: UserToolSource, image: str) -> tuple[UserToolSource, str] | None:
        """Return ``(tool, yaml)`` with the container replaced, or None if that breaks validation."""
        updated = tool.model_copy(update={"container": image})
        lint_errors = lint_user_tool_source(updated)
        if lint_errors:
            log.warning(
                "CustomTool: recommended container %s failed validation (%d issue(s)); keeping original",
                image,
                len(lint_errors),
            )
            return None
        return updated, self._render_tool_yaml(updated)

    @staticmethod
    def _render_tool_yaml(tool: UserToolSource) -> str:
        """Render a tool as the minimal YAML shown to and saved by the user.

        ``exclude_defaults`` drops fields left at their schema default
        (``optional: false``, ``multiple: false``, ``precreate_directory: false``,
        empty ``requirements``, default ``format``, ...) so the output carries only
        what the author actually chose. The defaults reapply on load, so the
        stripped YAML round-trips to an identical tool -- it's purely cosmetic.
        ``exclude_none`` additionally drops unset optional fields.
        """
        tool_dict = tool.model_dump(by_alias=True, exclude_none=True, exclude_defaults=True)
        return yaml.dump(tool_dict, default_flow_style=False, sort_keys=False)

    @staticmethod
    def _unmaterialized_scripts(tool: UserToolSource) -> list[str]:
        """Flag scripts the command runs by name that no configfile creates.

        ``shell_command: Rscript boxplot.R`` with no ``configfiles`` entry naming
        ``boxplot.R`` is a runtime failure (the file never exists) that the schema
        validators don't catch. Returns one issue per missing script so the retry
        loop makes the producer add the configfile (or inline the script). Scripts
        referenced via ``$(inputs...)`` are real inputs, not missing files.
        """
        command = tool.shell_command or ""
        provided = {
            name.strip().lstrip("./").rsplit("/", 1)[-1]
            for configfile in (tool.configfiles or [])
            for name in (configfile.filename, configfile.name)
            if name
        }
        errors: list[str] = []
        seen: set[str] = set()
        for match in _SCRIPT_INVOCATION_RE.finditer(command):
            token = match.group("script")
            if "$(" in token or "inputs." in token:
                continue
            base = token.lstrip("./").rsplit("/", 1)[-1]
            if base in seen:
                continue
            seen.add(base)
            if base not in provided:
                errors.append(
                    f"shell_command runs '{token}' but no configfile creates it. Add a configfiles "
                    f"entry with filename '{base}' containing the script, or inline the script with an "
                    "interpreter flag (e.g. `python -c` / `Rscript -e`)."
                )
        return errors

    def _capability_error_response(self, message: str, query: str) -> AgentResponse:
        return self._build_response(
            content=message,
            confidence=ConfidenceLevel.LOW,
            method="capability_check",
            query=query,
            suggestions=[
                ActionSuggestion(
                    action_type=ActionType.CONTACT_SUPPORT,
                    description="Contact your Galaxy administrator to configure AI tool generation",
                    parameters={},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                )
            ],
            error="model_capability",
            agent_data={"requires": "structured_output"},
        )

    def _invalid_structured_output_response(self, query: str) -> AgentResponse:
        return self._build_response(
            content="The model did not generate a valid tool definition.",
            confidence=ConfidenceLevel.LOW,
            method="text_fallback",
            query=query,
            error="invalid_structured_output",
        )

    def _validation_failed_response(
        self,
        validation_errors: list[str],
        query: str,
        attempts: int = 1,
    ) -> AgentResponse:
        log.warning(
            "CustomToolAgent produced a UserToolSource that failed validation: %s",
            validation_errors,
        )
        bullet_list = "\n".join(f"- {issue}" for issue in validation_errors)
        content = (
            "The model produced a tool definition, but it has problems "
            "that need to be fixed before it can be saved:\n\n"
            f"{bullet_list}"
        )
        return self._build_response(
            content=content,
            confidence=ConfidenceLevel.LOW,
            method="validation_error",
            query=query,
            error="validation_failed",
            agent_data={
                "validation_errors": validation_errors,
                # Number of producer calls made (1 = first attempt, 2 = a retry was
                # spent). Surfaced for offline benchmarking of schema/model quality.
                "attempts": attempts,
            },
        )

    def _success_response(
        self, tool: UserToolSource, tool_yaml: str, result: Any, query: str, attempts: int = 1
    ) -> AgentResponse:
        response_content = f"""I've created a custom Galaxy tool:

```yaml
{tool_yaml}
```

**Tool ID**: {tool.id}
**Name**: {tool.name}
**Version**: {tool.version}
**Container**: {tool.container}

The tool is ready to be saved and used in Galaxy."""

        suggestions = [
            ActionSuggestion(
                action_type=ActionType.SAVE_TOOL,
                description="Save this tool to Galaxy",
                parameters={"tool_yaml": tool_yaml, "tool_id": tool.id},
                confidence=ConfidenceLevel.HIGH,
                priority=1,
            ),
        ]

        return self._build_response(
            content=response_content,
            confidence=ConfidenceLevel.HIGH,
            method="structured",
            result=result,
            query=query,
            suggestions=suggestions,
            agent_data={
                "tool_id": tool.id,
                "tool_name": tool.name,
                "tool_yaml": tool_yaml,
                # 1 = produced on the first attempt, 2 = a validator retry was needed.
                # Surfaced for offline benchmarking of schema/model quality.
                "attempts": attempts,
            },
        )

    def _handle_model_http_error(self, e: ModelHTTPError, query: str) -> AgentResponse:
        # Schema/grammar errors from model backends (vLLM, LiteLLM, etc.)
        error_str = str(e).lower()
        if "grammar" in error_str or "$defs" in error_str or "pointer" in error_str:
            log.warning(f"Tool creation schema error (model may not support complex JSON schemas): {e}")
            model = self._get_agent_config("model", "unknown")
            return self._build_response(
                content=(
                    f"The model '{model}' failed to generate a tool definition due to JSON schema limitations. "
                    "This typically happens with local inference backends (vLLM, LiteLLM proxies) that don't "
                    "support complex nested JSON schemas.\n\n"
                    "To resolve this, configure a model that fully supports structured output "
                    "(e.g., gpt-4o, claude-3-sonnet) via their native APIs."
                ),
                confidence=ConfidenceLevel.LOW,
                method="error",
                query=query,
                suggestions=[
                    ActionSuggestion(
                        action_type=ActionType.CONTACT_SUPPORT,
                        description="Contact support for help configuring a compatible model",
                        parameters={},
                        confidence=ConfidenceLevel.HIGH,
                        priority=1,
                    )
                ],
                error="schema_limitation",
                agent_data={"model": model},
            )
        raise e

    def _handle_unexpected_model_behavior(self, e: UnexpectedModelBehavior, query: str) -> AgentResponse:
        log.warning(f"Model failed to produce valid tool definition: {e}")
        model = self._get_agent_config("model", "unknown")
        return self._build_response(
            content=(
                f"The model '{model}' was unable to generate a valid tool definition after multiple attempts. "
                "This may indicate the model doesn't fully support the required structured output format.\n\n"
                "Try using a model with better structured output support (e.g., gpt-4o, claude-3-sonnet)."
            ),
            confidence=ConfidenceLevel.LOW,
            method="error",
            query=query,
            suggestions=[
                ActionSuggestion(
                    action_type=ActionType.CONTACT_SUPPORT,
                    description="Contact support for help configuring a compatible model",
                    parameters={},
                    confidence=ConfidenceLevel.HIGH,
                    priority=1,
                )
            ],
            error="validation_failure",
            agent_data={"model": model},
        )
