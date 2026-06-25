"""Tests for the InlineResolver per-walk cache (Phase E follow-up).

Locks the behaviour that walks sharing one InlineResolver re-use a single
``parse_tool(YamlToolSource(...))`` call per inline UDT step, even when
multiple validation phases (validate + connections, clean + validate, the
two ``resolve_for_step`` calls in ``_validate_format2``) all touch the
same step instance.
"""

from unittest.mock import patch

from galaxy.tool_util.workflow_state import (
    ensure_inline_resolver,
    InlineResolver,
    resolve_for_step,
    validate_single,
)
from galaxy.tool_util.workflow_state._inline_tool import _parse_inline_tool
from galaxy.tool_util_models import ParsedTool

from .inline_udt_fixtures import (
    load_format2_inline_udt as _format2_with_inline_udt,
    load_native_inline_udt as _native_with_inline_udt,
)
from .test_inline_udt_workflows import _EmptyGetToolInfo


class _CountingGetToolInfo:
    """Records every (tool_id, version) lookup for cache assertions."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def get_tool_info(self, tool_id: str, tool_version: str | None) -> ParsedTool | None:
        self.calls.append((tool_id, tool_version))
        return None


def test_ensure_inline_resolver_is_idempotent():
    inner = _EmptyGetToolInfo()
    first = ensure_inline_resolver(inner)
    second = ensure_inline_resolver(first)
    assert first is second
    assert first.inner is inner


def test_inline_resolver_satisfies_get_tool_info_protocol():
    inner = _CountingGetToolInfo()
    resolver = InlineResolver(inner)
    resolver.get_tool_info("foo", "1.0")
    assert inner.calls == [("foo", "1.0")]


def test_resolve_for_step_routes_through_resolver_cache():
    """Repeated resolve_for_step on the same step instance parses once."""
    wf = _native_with_inline_udt()
    step = wf["steps"]["1"]
    resolver = ensure_inline_resolver(_EmptyGetToolInfo())

    with patch(
        "galaxy.tool_util.workflow_state._inline_tool._parse_inline_tool",
        wraps=_parse_inline_tool,
    ) as parse_spy:
        first = resolve_for_step(resolver, step)
        second = resolve_for_step(resolver, step)
        third = resolve_for_step(resolver, step)

    assert first is not None
    assert first is second is third
    assert parse_spy.call_count == 1


def test_uncached_path_parses_each_call():
    """Without InlineResolver, every resolve_for_step re-parses (baseline)."""
    wf = _native_with_inline_udt()
    step = wf["steps"]["1"]
    bare = _EmptyGetToolInfo()

    with patch(
        "galaxy.tool_util.workflow_state._inline_tool._parse_inline_tool",
        wraps=_parse_inline_tool,
    ) as parse_spy:
        resolve_for_step(bare, step)
        resolve_for_step(bare, step)

    assert parse_spy.call_count == 2


def test_native_validate_with_connections_parses_inline_step_twice(tmp_path):
    """precheck + _validate_native share the raw step dict and collapse to
    one parse via the resolver cache. The connections walk goes through
    ``normalized_native(workflow_dict)`` which builds fresh step instances,
    so id() doesn't match and the cache doesn't extend across — a second
    parse happens for the connection graph. Total = 2 (was 3 pre-cache).

    Lifting this to 1 requires content-hash dedupe (plan §5.3, deferred).
    """
    import json

    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(_native_with_inline_udt()))

    with patch(
        "galaxy.tool_util.workflow_state._inline_tool._parse_inline_tool",
        wraps=_parse_inline_tool,
    ) as parse_spy:
        report = validate_single(
            str(wf_path),
            _EmptyGetToolInfo(),
            connections=True,
        )

    assert report.results, "expected at least one validation result"
    assert (
        parse_spy.call_count == 2
    ), f"expected one parse per id-stable walk (validate + connections), got {parse_spy.call_count}"


def test_native_validate_without_connections_parses_inline_step_once(tmp_path):
    """precheck and _validate_native share the same dict — one parse total
    when connections is off. Locks the dominant native-walk cache win."""
    import json

    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(_native_with_inline_udt()))

    with patch(
        "galaxy.tool_util.workflow_state._inline_tool._parse_inline_tool",
        wraps=_parse_inline_tool,
    ) as parse_spy:
        report = validate_single(str(wf_path), _EmptyGetToolInfo())

    assert report.results
    assert (
        parse_spy.call_count == 1
    ), f"expected one parse across precheck + _validate_native, got {parse_spy.call_count}"


def test_format2_validate_collapses_double_resolve(tmp_path):
    """_validate_format2 resolves each inline step twice (once inside
    validate_step_format2, once at the labelling fallback). Both calls hit
    the same nf2.steps[i] instance, so the cache keeps it to one parse."""
    import yaml

    wf_path = tmp_path / "wf.gxwf.yml"
    wf_path.write_text(yaml.safe_dump(_format2_with_inline_udt()))

    with patch(
        "galaxy.tool_util.workflow_state._inline_tool._parse_inline_tool",
        wraps=_parse_inline_tool,
    ) as parse_spy:
        report = validate_single(str(wf_path), _EmptyGetToolInfo())

    assert report.results
    assert parse_spy.call_count == 1, f"expected one parse for the format2 inline step, got {parse_spy.call_count}"


def test_inline_resolver_cache_isolated_per_step_identity():
    """Two distinct step dicts (even with identical content) each get their
    own parse — keying is step-identity, not content. Locks the current
    semantics so a future content-hash variant is a deliberate change."""
    wf = _native_with_inline_udt()
    wf2 = _native_with_inline_udt()
    step_a = wf["steps"]["1"]
    step_b = wf2["steps"]["1"]
    resolver = ensure_inline_resolver(_EmptyGetToolInfo())

    with patch(
        "galaxy.tool_util.workflow_state._inline_tool._parse_inline_tool",
        wraps=_parse_inline_tool,
    ) as parse_spy:
        resolve_for_step(resolver, step_a)
        resolve_for_step(resolver, step_b)

    assert parse_spy.call_count == 2
