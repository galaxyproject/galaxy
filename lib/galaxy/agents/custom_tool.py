"""
Custom tool creation agent for Galaxy.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
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
from galaxy.tool_util.lint import lint_user_tool_source
from galaxy.tool_util_models import (
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


class CritiqueReport(BaseModel):
    """Structured critique returned by the LLM critic.

    Issues are split between *clarity* (text the user reads -- description,
    labels, help text) and *idiomaticity* (tool shape -- defaults, exposed
    options, container choice). The producer is re-rolled only when
    ``should_refine`` is true, which the critic should reserve for issues
    significant enough to be worth another model call.
    """

    clarity_issues: list[str] = Field(default_factory=list)
    idiomaticity_issues: list[str] = Field(default_factory=list)
    should_refine: bool = False
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

    Both loops are gated on per-deployment config under
    ``inference_services.custom_tool``: ``validator_retry_enabled`` and
    ``quality_critic_enabled``. Default to validator-only behavior --
    operators turn the critic on when they're willing to pay for it.
    """

    agent_type = AgentType.CUSTOM_TOOL
    capability_blurb = (
        "Generate a Galaxy tool definition (XML/YAML) when you explicitly ask to wrap a command-line program."
    )
    DEFAULT_MAX_TOKENS = 16384

    def __init__(self, deps: GalaxyAgentDependencies):
        super().__init__(deps)
        self._critic_agent: Agent[GalaxyAgentDependencies, CritiqueReport] | None = None

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

    def _get_critic_agent(self) -> Agent[GalaxyAgentDependencies, CritiqueReport]:
        """Lazily build the critic agent. Same model as the producer by default;
        operators can override via ``inference_services.custom_tool.critic_model``."""
        if self._critic_agent is None:
            self._critic_agent = Agent(
                self._get_model(),
                deps_type=GalaxyAgentDependencies,
                output_type=CritiqueReport,
                system_prompt=self._get_critic_system_prompt(),
                retries=self._get_retries(),
            )
        return self._critic_agent

    def _validator_retry_enabled(self) -> bool:
        return bool(self._get_agent_config("validator_retry_enabled", True))

    def _quality_critic_enabled(self) -> bool:
        return bool(self._get_agent_config("quality_critic_enabled", False))

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

            # Quality critic: only refine on significant issues, never re-critique.
            if self._quality_critic_enabled():
                critique = await self._run_critic(tool_yaml, query)
                if critique is not None and critique.should_refine:
                    log.info(
                        "CustomTool: critic flagged %d clarity / %d idiomaticity issues; refining once",
                        len(critique.clarity_issues),
                        len(critique.idiomaticity_issues),
                    )
                    refined = await self._produce_tool(query, critique=critique, prior_yaml=tool_yaml)
                    if isinstance(refined, tuple):
                        tool, tool_yaml, result = refined
                    elif isinstance(refined, _ProducerFailure):
                        log.warning(
                            "CustomTool: refinement broke validation (%d issue(s)); keeping pre-refine tool",
                            len(refined.errors),
                        )

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
                tool_dict = tool.model_dump(by_alias=True, exclude_none=True)
                tool_yaml = yaml.dump(tool_dict, default_flow_style=False, sort_keys=False)
                lint_errors = lint_user_tool_source(tool)
                if lint_errors:
                    log.debug("CustomToolAgent lint failure: %s", lint_errors)
                    # The tool validated, so we have its rendered YAML -- carry it so a
                    # retry can show the model exactly what to fix in place.
                    return _ProducerFailure(lint_errors, prior_yaml=tool_yaml)
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
            "Critique this tool for clarity and idiomaticity. Set should_refine "
            "only if the issues are significant enough to be worth another model call."
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
