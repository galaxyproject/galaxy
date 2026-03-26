"""Stale key classification for Galaxy workflow tool_state.

Classifies undeclared keys in tool_state into categories:
- BOOKKEEPING: framework-managed keys (__current_case__, __page__, etc.)
- RUNTIME_LEAK: execution artifacts (__workflow_invocation_uuid__, *|__identifier__)
- STALE_ROOT: conditional params leaked to parent level
- STALE_BRANCH: data from inactive conditional branch
- UNKNOWN: catch-all (often tool upgrade residue)

See STALE_KEY_TAXONOMY.md for full category descriptions.
"""

import json
from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
from typing import (
    Any,
    cast,
)

from galaxy.tool_util.parameters import (
    ConditionalParameterModel,
    RepeatParameterModel,
    ToolParameterT,
    validate_explicit_conditional_test_value,
)
from galaxy.tool_util_models.parameters import SectionParameterModel
from ._types import (
    NativeStepDict,
    ToolInputs,
)
from ._util import decode_double_encoded_values
from ._walker import (
    _NATIVE_BOOKKEEPING_KEYS,
    _test_value_matches_discriminator,
    as_dict,
    as_list,
)


class StaleKeyCategory(Enum):
    BOOKKEEPING = "bookkeeping"
    STALE_ROOT = "stale-root-keys"
    STALE_BRANCH = "stale-branch-data"
    UNKNOWN = "unknown"
    RUNTIME_LEAK = "runtime-leak"


ALL_CATEGORIES = frozenset(StaleKeyCategory)

CATEGORY_NAMES = {c.value: c for c in StaleKeyCategory}

_RUNTIME_LEAK_EXACT = frozenset({"__workflow_invocation_uuid__"})
_RUNTIME_LEAK_SUFFIX = "|__identifier__"


class InvalidCategoryError(ValueError):
    pass


class ConflictingCategoryError(ValueError):
    pass


@dataclass
class StaleKey:
    key_path: str
    category: StaleKeyCategory
    value: Any = field(repr=False, default=None)
    detail: str | None = None


# -- Classification --


def classify_stale_keys(
    step: NativeStepDict,
    parsed_tool: ToolInputs,
) -> list[StaleKey]:
    """Walk tool_state against tool definition, classify every undeclared key."""
    tool_state_raw = step.get("tool_state")
    if not tool_state_raw:
        return []
    if isinstance(tool_state_raw, str):
        try:
            tool_state = json.loads(tool_state_raw)
        except (json.JSONDecodeError, TypeError):
            return []
        decode_double_encoded_values(tool_state)
    elif isinstance(tool_state_raw, dict):
        tool_state = tool_state_raw
    else:
        return []
    result: list[StaleKey] = []
    _classify_recursive(tool_state, list(parsed_tool.inputs), result, prefix="")
    return result


def _classify_recursive(
    state: dict[str, Any],
    tool_inputs: list[ToolParameterT],
    result: list[StaleKey],
    prefix: str,
):
    """Walk state dict against tool inputs, classify undeclared keys and recurse into containers."""
    declared = {inp.name for inp in tool_inputs}

    # Collect conditional param names at this level for stale-root detection
    conditional_param_names = _collect_conditional_param_names(tool_inputs)

    for key in state:
        if key in declared:
            continue

        key_path = f"{prefix}{key}" if prefix else key
        value = state[key]

        # Classification waterfall
        if _is_runtime_leak(key):
            result.append(StaleKey(key_path, StaleKeyCategory.RUNTIME_LEAK, value, detail=_runtime_leak_detail(key)))
        elif key in _NATIVE_BOOKKEEPING_KEYS:
            result.append(StaleKey(key_path, StaleKeyCategory.BOOKKEEPING, value))
        elif key in conditional_param_names:
            detail = _stale_root_detail(key, tool_inputs, state)
            result.append(StaleKey(key_path, StaleKeyCategory.STALE_ROOT, value, detail=detail))
        else:
            result.append(StaleKey(key_path, StaleKeyCategory.UNKNOWN, value))

    # Recurse into declared containers
    _recurse_into_containers(state, tool_inputs, result, prefix)


def _recurse_into_containers(
    state: dict[str, Any],
    tool_inputs: list[ToolParameterT],
    result: list[StaleKey],
    prefix: str,
):
    """Recurse into declared conditional/repeat/section containers only."""
    for tool_input in tool_inputs:
        name = tool_input.name
        if name not in state:
            continue

        value = state[name]
        parameter_type = tool_input.parameter_type
        child_prefix = f"{prefix}{name}." if prefix else f"{name}."

        if parameter_type == "gx_conditional":
            _classify_conditional(tool_input, value, result, child_prefix)
        elif parameter_type == "gx_repeat":
            _classify_repeat(tool_input, value, result, prefix, name)
        elif parameter_type == "gx_section":
            _classify_section(tool_input, value, result, child_prefix)


def _classify_conditional(
    tool_input: ToolParameterT,
    value: Any,
    result: list[StaleKey],
    child_prefix: str,
):
    """Classify undeclared keys inside a conditional, with stale-branch detection."""
    conditional = cast(ConditionalParameterModel, tool_input)
    cond_state = as_dict(value)
    if cond_state is None:
        return

    test_param = conditional.test_parameter
    test_value_raw = cond_state.get(test_param.name)
    test_value = validate_explicit_conditional_test_value(test_param.name, test_value_raw)

    # Determine active branch
    active_when = None
    for when in conditional.whens:
        if test_value is None and when.is_default_when:
            active_when = when
        elif test_value is not None and _test_value_matches_discriminator(test_value, when.discriminator):
            active_when = when

    if active_when is None:
        recorded_case = cond_state.get("__current_case__")
        if isinstance(recorded_case, int) and 0 <= recorded_case < len(conditional.whens):
            active_when = conditional.whens[recorded_case]

    if active_when is None:
        return

    # Active branch params
    active_params: list[ToolParameterT] = [test_param] + list(active_when.parameters)
    active_names = {p.name for p in active_params}

    # Collect params from ALL inactive branches for stale-branch detection
    inactive_param_names: dict[str, str] = {}  # param_name -> branch discriminator
    for when in conditional.whens:
        if when is not active_when:
            disc = str(when.discriminator)
            for p in when.parameters:
                inactive_param_names[p.name] = disc

    # Classify undeclared keys inside conditional state (stale-branch aware)
    for key in cond_state:
        if key in active_names or key in _NATIVE_BOOKKEEPING_KEYS:
            continue

        key_path = f"{child_prefix}{key}"
        key_value = cond_state[key]

        if _is_runtime_leak(key):
            result.append(
                StaleKey(key_path, StaleKeyCategory.RUNTIME_LEAK, key_value, detail=_runtime_leak_detail(key))
            )
        elif key in inactive_param_names:
            branch = inactive_param_names[key]
            result.append(
                StaleKey(key_path, StaleKeyCategory.STALE_BRANCH, key_value, detail=f'from inactive branch "{branch}"')
            )
        else:
            result.append(StaleKey(key_path, StaleKeyCategory.UNKNOWN, key_value))

    # Recurse into active branch containers only (no undeclared-key pass — already done above)
    _recurse_into_containers(cond_state, active_params, result, prefix=child_prefix)


def _classify_repeat(
    tool_input: ToolParameterT,
    value: Any,
    result: list[StaleKey],
    prefix: str,
    name: str,
):
    repeat = cast(RepeatParameterModel, tool_input)
    repeat_state = as_list(value)
    for i, instance in enumerate(repeat_state):
        if isinstance(instance, dict):
            instance_prefix = f"{prefix}{name}_{i}."
            _classify_recursive(instance, list(repeat.parameters), result, prefix=instance_prefix)


def _classify_section(
    tool_input: ToolParameterT,
    value: Any,
    result: list[StaleKey],
    child_prefix: str,
):
    section = cast(SectionParameterModel, tool_input)
    section_state = as_dict(value)
    if section_state is None:
        return
    _classify_recursive(section_state, list(section.parameters), result, prefix=child_prefix)


# -- Classification helpers --


def _is_runtime_leak(key: str) -> bool:
    return key in _RUNTIME_LEAK_EXACT or _RUNTIME_LEAK_SUFFIX in key


def _runtime_leak_detail(key: str) -> str:
    if key in _RUNTIME_LEAK_EXACT:
        return "runtime invocation UUID"
    return "collection element identifier"


def _collect_conditional_param_names(tool_inputs: list[ToolParameterT]) -> set[str]:
    """Collect all param names from conditionals at this level (for stale-root detection)."""
    names: set[str] = set()
    for tool_input in tool_inputs:
        if tool_input.parameter_type == "gx_conditional":
            assert isinstance(tool_input, ConditionalParameterModel)
            names.add(tool_input.test_parameter.name)
            for when in tool_input.whens:
                for p in when.parameters:
                    names.add(p.name)
    return names


def _stale_root_detail(key: str, tool_inputs: list[ToolParameterT], state: dict) -> str:
    """Build detail string for a stale root key, including value divergence check."""
    for tool_input in tool_inputs:
        if tool_input.parameter_type != "gx_conditional":
            continue
        assert isinstance(tool_input, ConditionalParameterModel)
        cond_name = tool_input.name

        # Check test param
        if key == tool_input.test_parameter.name:
            cond_state = as_dict(state.get(cond_name))
            if cond_state and key in cond_state:
                root_val = state.get(key)
                nested_val = cond_state.get(key)
                if root_val == nested_val:
                    return f"duplicate of {cond_name}.{key} (values match)"
                else:
                    return f"duplicate of {cond_name}.{key} (VALUE DIVERGED: root={root_val!r}, nested={nested_val!r})"
            return f"duplicate of {cond_name}.{key}"

        # Check branch params
        for when in tool_input.whens:
            for p in when.parameters:
                if p.name == key:
                    cond_state = as_dict(state.get(cond_name))
                    if cond_state and key in cond_state:
                        root_val = state.get(key)
                        nested_val = cond_state.get(key)
                        if root_val == nested_val:
                            return f"duplicate of {cond_name}.{key} (values match)"
                        else:
                            return f"duplicate of {cond_name}.{key} (VALUE DIVERGED: root={root_val!r}, nested={nested_val!r})"
                    return f'leaked from {cond_name} (branch "{when.discriminator}")'

    return "matches conditional parameter"


# -- Policy --


class StaleKeyPolicy:
    """Determines which stale key categories are denied (flagged/stripped)."""

    def __init__(self, denied: set[StaleKeyCategory]):
        self.denied = denied

    def is_denied(self, category: StaleKeyCategory) -> bool:
        return category in self.denied

    def is_allowed(self, category: StaleKeyCategory) -> bool:
        return category not in self.denied

    def filter(self, stale_keys: list[StaleKey]) -> tuple:
        """Split stale keys into (denied, allowed) lists."""
        denied = [k for k in stale_keys if self.is_denied(k.category)]
        allowed = [k for k in stale_keys if self.is_allowed(k.category)]
        return denied, allowed

    @classmethod
    def for_validate(cls, allow: list[str], deny: list[str]) -> "StaleKeyPolicy":
        """Validate defaults: deny all except bookkeeping."""
        defaults = set(ALL_CATEGORIES - {StaleKeyCategory.BOOKKEEPING})
        return cls._build(defaults, allow_args=allow, deny_args=deny)

    @classmethod
    def for_export(cls, allow: list[str], deny: list[str]) -> "StaleKeyPolicy":
        """Export defaults: allow everything."""
        defaults: set[StaleKeyCategory] = set()
        return cls._build(defaults, allow_args=allow, deny_args=deny)

    @classmethod
    def for_clean(cls, preserve: list[str], strip: list[str]) -> "StaleKeyPolicy":
        """Clean defaults: strip all categories including bookkeeping."""
        defaults = set(ALL_CATEGORIES)
        # For clean, "strip" = deny, "preserve" = allow
        return cls._build(defaults, allow_args=preserve, deny_args=strip)

    @classmethod
    def _build(
        cls,
        defaults: set[StaleKeyCategory],
        allow_args: list[str],
        deny_args: list[str],
    ) -> "StaleKeyPolicy":
        denied = set(defaults)

        # Parse args — raises InvalidCategoryError on bad input
        allow_cats = _parse_category_args(allow_args)
        deny_cats = _parse_category_args(deny_args)

        # Check for conflicts — only flag explicit (non-'all') overlaps.
        # 'all' is a shorthand, so --deny all --allow bookkeeping is valid
        # (meaning "deny everything then carve out bookkeeping").
        allow_explicit = _parse_category_args([a for a in allow_args if a.lower() != "all"])
        deny_explicit = _parse_category_args([d for d in deny_args if d.lower() != "all"])
        conflicts = allow_explicit & deny_explicit
        if conflicts:
            conflict_names = ", ".join(c.value for c in conflicts)
            raise ConflictingCategoryError(f"Conflicting categories in --allow and --deny: {conflict_names}")

        # Apply deny first, then allow
        denied |= deny_cats
        denied -= allow_cats

        return cls(denied)


def _parse_category_args(args: list[str]) -> set[StaleKeyCategory]:
    """Parse CLI category arguments, handling 'all' and 'none'.

    Raises InvalidCategoryError on unrecognized category names.
    """
    result: set[StaleKeyCategory] = set()
    for arg in args:
        arg_lower = arg.lower()
        if arg_lower == "all":
            result |= ALL_CATEGORIES
        elif arg_lower == "none":
            pass  # no-op
        elif arg_lower in CATEGORY_NAMES:
            result.add(CATEGORY_NAMES[arg_lower])
        else:
            valid = ", ".join(sorted(CATEGORY_NAMES.keys()))
            raise InvalidCategoryError(f"Unknown category '{arg}'. Valid: {valid}, all, none")
    return result


# -- Formatting helpers --


def format_stale_keys(stale_keys: list[StaleKey], indent: str = "  ") -> list[str]:
    """Format stale keys as human-readable lines."""
    lines = []
    for sk in stale_keys:
        detail = f" ({sk.detail})" if sk.detail else ""
        lines.append(f"{indent}{sk.category.value}: {sk.key_path}{detail}")
    return lines
