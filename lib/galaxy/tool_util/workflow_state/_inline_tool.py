"""Local parse + validate for inline user-defined tool representations.

Galaxy's workflow exporter inlines a step's UDT YAML under
``step.tool_representation`` whenever the originating ``dynamic_tool`` row
resolves on export. The offline ``workflow_state`` stack has no
``DynamicTool`` table to resolve against, so we re-parse the embedded
representation locally and run the same pydantic gate / lint pipeline
Galaxy uses when the user creates the tool through the editor.

This module is the Phase A foundation for the resolver swap (Phase B)
described in ``USER_DEFINED_TOOL_STEP_VALIDATION.md``. Only
``InlineToolSourceResult`` is public; the parse/validate helpers stay
underscore-prefixed until Phase B settles the resolver call site.
"""

from typing import (
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    computed_field,
    Field,
    ValidationError,
)

from galaxy.tool_util.lint import lint_user_tool_source_structured
from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.parser.yaml import YamlToolSource
from galaxy.tool_util_models import (
    format_validation_errors,
    ParsedTool,
    UserToolSource,
)

from ._types import GetToolInfo
from ._util import (
    inline_class_from_run,
    step_inline_tool_class,
    step_is_inline_tool,
    step_tool_id,
    step_tool_representation,
    step_tool_version,
    StepLike,
)


class InlineToolSourceResult(BaseModel):
    """Report bundle for one inline ``tool_representation`` validation pass.

    Serializes through the same Pydantic surface as the rest of the
    workflow_state report models so JSON / Markdown rendering picks it up
    without bespoke code.
    """

    ok: bool = Field(description="True iff pydantic validation succeeded and no lint errors were emitted.")
    inline_class: Optional[str] = Field(
        default=None,
        description="The ``class`` value found on the representation (e.g. ``GalaxyUserTool``).",
    )
    supported: bool = Field(
        default=True,
        description="False for inline classes outside this plan's scope (e.g. ``GalaxyTool``).",
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="Pydantic errors against ``UserToolSource``, formatted as ``<dotted.loc>: <msg>``.",
    )
    lint_errors: List[str] = Field(default_factory=list)
    lint_warnings: List[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_issues(self) -> bool:
        return bool(self.validation_errors or self.lint_errors or self.lint_warnings or not self.supported)


def _parse_inline_tool(tool_representation: dict) -> ParsedTool:
    """Parse an inline ``tool_representation`` into a :class:`ParsedTool`.

    Mirrors Galaxy's own ``tools/__init__.py`` path: wrap the dict in a
    :class:`YamlToolSource` and run :func:`parse_tool`. Caller is responsible
    for validating against :class:`UserToolSource` first — this helper does
    not gate.
    """
    return parse_tool(YamlToolSource(tool_representation))


def validate_inline_tool_source_for_step(step: StepLike, *, offline: bool = False) -> Optional[InlineToolSourceResult]:
    """Return inline-source diagnostics for *step*, or ``None`` if not inline.

    Single entry point for the diagnostics surface: callers walk steps and
    attach the returned :class:`InlineToolSourceResult` to their per-step
    report row when non-None.
    """
    if not step_is_inline_tool(step):
        return None
    representation = step_tool_representation(step)
    if representation is None:
        return None
    return _validate_inline_tool_source(representation, offline=offline)


def _validate_inline_tool_source(tool_representation: dict, *, offline: bool = False) -> InlineToolSourceResult:
    """Validate an inline ``tool_representation`` against the pydantic schema + linter.

    ``offline=True`` skips network-touching linters (EDAM, bio.tools);
    matches the ``--offline`` CLI flag plumbed in Phase C.
    """
    class_ = tool_representation.get("class") if isinstance(tool_representation, dict) else None

    if class_ != "GalaxyUserTool":
        # Admin dynamic tools (class: GalaxyTool) and unknown classes are
        # out of scope per §3 — surface as ``supported=False`` so the
        # caller can emit an ``inline_source_unsupported`` warning.
        return InlineToolSourceResult(
            ok=False,
            inline_class=class_ if isinstance(class_, str) else None,
            supported=False,
        )

    try:
        user_tool_source = UserToolSource.model_validate(tool_representation)
    except ValidationError as exc:
        return InlineToolSourceResult(
            ok=False,
            inline_class="GalaxyUserTool",
            validation_errors=format_validation_errors(exc),
        )

    lint_errors, lint_warnings = lint_user_tool_source_structured(user_tool_source, skip_network=offline)
    return InlineToolSourceResult(
        ok=not lint_errors,
        inline_class="GalaxyUserTool",
        lint_errors=lint_errors,
        lint_warnings=lint_warnings,
    )


def resolve_for_step(
    get_tool_info: GetToolInfo,
    step: StepLike,
    *,
    offline: bool = False,
) -> Optional[ParsedTool]:
    """Resolve a step's :class:`ParsedTool`, preferring an inline representation.

    Order:

    1. If the step carries an inline ``GalaxyUserTool`` representation,
       parse it locally and return immediately — no network.
    2. If the inline class is anything else (``GalaxyTool`` admin dynamic
       tools, unknown classes), return ``None`` so callers can surface an
       ``inline_source_unsupported`` diagnostic.
    3. Otherwise fall back to the injected :class:`GetToolInfo` resolver.

    ``offline`` is accepted for forward compatibility with the Phase C
    ``--offline`` plumbing; it does not affect parsing itself (the lint
    pipeline is the only network consumer and runs in
    :func:`_validate_inline_tool_source`).
    """
    if step_is_inline_tool(step):
        if step_inline_tool_class(step) != "GalaxyUserTool":
            return None
        representation = step_tool_representation(step)
        if representation is None:
            return None
        return _parse_inline_tool(representation)
    tool_id = step_tool_id(step)
    if not tool_id:
        return None
    return get_tool_info.get_tool_info(tool_id, step_tool_version(step))


class InlineToolInventoryEntry(BaseModel):
    """One inline-tool entry surfaced by ``walk_inline_tools``.

    Phase D consumer: ``galaxy-tool-cache populate-workflow`` /
    ``list-inline-tools`` / ``embedded-schema``. ``step_path`` follows the
    dotted prefix convention used by ``_validate_native`` / ``_validate_format2``
    (e.g. ``"2.1"`` for a step inside a subworkflow).
    """

    step_path: str
    workflow_path: Optional[str] = None
    inline_class: str
    tool_id: Optional[str] = Field(
        default=None,
        description="The tool id declared inside the inline representation (``id`` field).",
    )
    tool_version: Optional[str] = None


def walk_inline_tools(workflow_dict: dict, *, workflow_path: Optional[str] = None) -> List[InlineToolInventoryEntry]:
    """Walk a native or format2 workflow dict and return inline-tool entries.

    Subworkflow steps are recursed into; ``step_path`` is dotted (e.g. ``"3.0"``).
    Detection mirrors :func:`step_is_inline_tool` (works on raw dicts).
    """
    workflow_class = workflow_dict.get("class")
    if workflow_class == "GalaxyWorkflow":
        return _walk_inline_tools_format2(workflow_dict, prefix="", workflow_path=workflow_path)
    return _walk_inline_tools_native(workflow_dict, prefix="", workflow_path=workflow_path)


def _entry_from_representation(
    representation: dict, step_path: str, workflow_path: Optional[str]
) -> InlineToolInventoryEntry:
    return InlineToolInventoryEntry(
        step_path=step_path,
        workflow_path=workflow_path,
        inline_class=str(representation.get("class") or ""),
        tool_id=representation.get("id"),
        tool_version=representation.get("version"),
    )


def _walk_inline_tools_native(
    workflow_dict: dict, *, prefix: str, workflow_path: Optional[str]
) -> List[InlineToolInventoryEntry]:
    entries: List[InlineToolInventoryEntry] = []
    steps = workflow_dict.get("steps", {})
    for step_index, step_def in sorted(steps.items(), key=lambda x: int(x[0])):
        step_label = f"{prefix}{step_index}" if prefix else str(step_index)
        if step_def.get("type") == "subworkflow" and "subworkflow" in step_def:
            entries.extend(
                _walk_inline_tools_native(step_def["subworkflow"], prefix=f"{step_label}.", workflow_path=workflow_path)
            )
            continue
        rep = step_def.get("tool_representation")
        if inline_class_from_run(rep) is not None:
            entries.append(_entry_from_representation(rep, step_label, workflow_path))
    return entries


def _walk_inline_tools_format2(
    workflow_dict: dict, *, prefix: str, workflow_path: Optional[str]
) -> List[InlineToolInventoryEntry]:
    entries: List[InlineToolInventoryEntry] = []
    steps = workflow_dict.get("steps", {})
    if isinstance(steps, dict):
        step_items = list(steps.items())
    elif isinstance(steps, list):
        step_items = [(str(i), step) for i, step in enumerate(steps)]
    else:
        return entries

    for step_key, step_def in step_items:
        step_label = f"{prefix}{step_key}" if prefix else str(step_key)
        if not isinstance(step_def, dict):
            continue
        run = step_def.get("run")
        # Inline subworkflow: recurse with the nested dict.
        if isinstance(run, dict) and run.get("class") == "GalaxyWorkflow":
            entries.extend(_walk_inline_tools_format2(run, prefix=f"{step_label}.", workflow_path=workflow_path))
            continue
        if inline_class_from_run(run) is not None:
            entries.append(_entry_from_representation(run, step_label, workflow_path))
    return entries


class _ResolveCache:
    """Per-invocation memoization layered over :func:`resolve_for_step`.

    Keyed by step identity (``id(step)``) — content-hash dedupe deferred
    until profiling says it matters. Lifetime is bound to a single CLI
    invocation; the original step objects are kept alive by the workflow
    document the cache was built from.
    """

    def __init__(self, get_tool_info: GetToolInfo, *, offline: bool = False) -> None:
        self._get_tool_info = get_tool_info
        self._offline = offline
        self._cache: dict = {}

    def resolve(self, step: StepLike) -> Optional[ParsedTool]:
        key = id(step)
        if key in self._cache:
            return self._cache[key]
        parsed = resolve_for_step(self._get_tool_info, step, offline=self._offline)
        self._cache[key] = parsed
        return parsed
