"""Unit tests for bounded lift-status response headers.

Lift errors scale with stored tool content, and response header blocks are
limited by reverse proxy buffer sizes -- so the header helpers must dedupe,
cap, and summarize rather than emit the raw error list.
"""

import h11

from galaxy.webapps.galaxy.api.common import (
    compact_lift_errors,
    LIFT_HEADER_MAX_BYTES,
    lift_headers,
)


def test_compact_dedupes_preserving_order():
    compact, total = compact_lift_errors(["b", "a", "b", "c", "a"], separator=",")
    assert compact == "b,a,c"
    assert total == 3


def test_compact_empty_list():
    compact, total = compact_lift_errors([], separator=",")
    assert compact == ""
    assert total == 0


def test_compact_caps_item_count():
    errors = [f"inputs.{i}.max" for i in range(50)]
    compact, total = compact_lift_errors(errors, separator=",", max_items=20)
    assert total == 50
    assert compact.endswith(",+30 more")
    assert compact.count(",") == 20  # 20 items joined by 19 separators, plus the suffix


def test_compact_max_bytes_is_a_hard_bound():
    errors = [f"path.{i}." + "x" * 100 for i in range(50)]
    compact, total = compact_lift_errors(errors, separator=",", max_items=50, max_bytes=500)
    assert total == 50
    assert len(compact) <= 500
    assert compact.endswith("more")


def test_compact_single_oversized_error_still_reports_count():
    compact, total = compact_lift_errors(["y" * 5000], separator=",")
    assert total == 1
    assert compact == "+1 more"


def test_compact_honors_degenerate_caps():
    compact, total = compact_lift_errors(["x"], separator=",", max_bytes=3)
    assert total == 1
    assert len(compact) <= 3


def test_compact_neutralizes_header_injection():
    # Stored dict keys reach error paths verbatim; control characters must
    # never make it into a header value.
    compact, total = compact_lift_errors(["inputs.0.bad\r\nX-Evil: yes"], separator=",")
    assert total == 1
    assert "\r" not in compact
    assert "\n" not in compact
    assert compact == "inputs.0.bad??X-Evil: yes"


def test_compact_replaces_non_ascii():
    compact, _ = compact_lift_errors(["inputs.0.名前"], separator=",")
    assert all(0x20 <= ord(char) <= 0x7E for char in compact)


def test_lift_headers_absent_for_ok_status():
    assert lift_headers("ok", []) == {}
    assert lift_headers("ok", ["ignored"]) == {}
    assert lift_headers("lifted", []) == {}


def test_lift_headers_lifted_is_bounded_and_warning_is_short():
    errors = [f"inputs.{i}.{field}" for i in range(40) for field in ("parameter_type", "argument", "hidden")]
    headers = lift_headers("lifted", errors)
    assert set(headers) == {"X-Galaxy-Deprecated-Fields", "Warning"}
    assert len(headers["X-Galaxy-Deprecated-Fields"]) <= LIFT_HEADER_MAX_BYTES
    assert headers["X-Galaxy-Deprecated-Fields"].endswith("more")
    assert len(headers["Warning"]) < 200
    assert "X-Galaxy-Deprecated-Fields" in headers["Warning"]
    assert "inputs.0.parameter_type" not in headers["Warning"]


def test_lift_headers_invalid_uses_schema_errors_header():
    headers = lift_headers("invalid", ["name: field required"])
    assert set(headers) == {"X-Galaxy-Schema-Errors", "Warning"}
    assert headers["X-Galaxy-Schema-Errors"] == "name: field required"
    assert "X-Galaxy-Schema-Errors" in headers["Warning"]


def test_lift_headers_values_are_always_header_safe():
    error_lists = [
        ["inputs.0.名前", "inputs.1.bad\r\nX-Evil: yes"],
        # Stored keys can carry stray whitespace; h11 (uvicorn's parser) rejects
        # header values that start or end with it.
        ["inputs.0.foo "],
        [" top", "inputs.1.bar "],
    ]
    for status in ("lifted", "invalid"):
        for errors in error_lists:
            headers = lift_headers(status, errors)
            for name, value in headers.items():
                assert all(0x20 <= ord(char) <= 0x7E for char in value), value
                h11.Response(status_code=200, headers=[(name.encode(), value.encode())])


def test_compact_counts_errors_that_sanitize_alike():
    # The Warning count should match representation_errors in the body.
    compact, total = compact_lift_errors(["a\tb", "a\nb"], separator=",")
    assert total == 2
    assert compact == "a?b,a?b"


def test_compact_keeps_a_list_that_fits_without_truncation():
    # The truncation-suffix reserve only applies when something is cut.
    error = "y" * (LIFT_HEADER_MAX_BYTES - 4)
    compact, total = compact_lift_errors([error], separator=",")
    assert total == 1
    assert compact == error
