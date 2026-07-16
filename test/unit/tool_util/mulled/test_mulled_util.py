import pytest

from galaxy.tool_util.deps.mulled import util
from galaxy.tool_util.deps.mulled.util import (
    build_target,
    find_remote_mulled_name,
    select_mulled_v2_tag,
    select_single_package_tag,
    v2_image_name,
    version_sorted,
)


@pytest.mark.parametrize(
    "tags,tag",
    [
        (["2.22--he941832_1", "2.22--he860b03_2", "2.22--hdbcaa40_3"], "2.22--hdbcaa40_3"),
        (["1.1.2--py27_0", "1.1.2--py36_0", "1.1.2--py35_0"], "1.1.2--py36_0"),
        (
            ["6725cda82000b8e514baddcbf8c2dce054e3f797-1", "6725cda82000b8e514baddcbf8c2dce054e3f797-0"],
            "6725cda82000b8e514baddcbf8c2dce054e3f797-1",
        ),
        (["python:3.5", "python:3.7", "python:3.7--2"], "python:3.7--2"),
    ],
)
def test_version_sorted(tags, tag):
    assert version_sorted(tags)[0] == tag


# --- shared tag selectors (pure, no network) --------------------------------


def test_select_single_package_tag_exact():
    tags = ["1.17--h0_0", "1.16--h0_0"]
    assert select_single_package_tag(tags, "1.16") == ("1.16--h0_0", True)


def test_select_single_package_tag_no_exact_no_fallback():
    assert select_single_package_tag(["1.17--h0_0"], "9.9") == (None, False)


def test_select_single_package_tag_no_exact_with_fallback():
    assert select_single_package_tag(["1.17--h0_0"], "9.9", allow_newest_fallback=True) == ("1.17--h0_0", False)


def test_select_single_package_tag_no_version_requires_fallback():
    assert select_single_package_tag(["1.17--h0_0"], None) == (None, False)
    assert select_single_package_tag(["1.17--h0_0"], None, allow_newest_fallback=True) == ("1.17--h0_0", False)


def test_select_single_package_tag_empty():
    assert select_single_package_tag([], "1.0") == (None, False)


def test_select_mulled_v2_tag_exact():
    tags = ["abc123-1", "abc123-0", "def456-0"]
    assert select_mulled_v2_tag(tags, "abc123") == ("abc123-1", True)


def test_select_mulled_v2_tag_no_match_no_fallback():
    assert select_mulled_v2_tag(["def456-0"], "abc123") == (None, False)


def test_select_mulled_v2_tag_no_match_with_fallback():
    assert select_mulled_v2_tag(["def456-0"], "abc123", allow_newest_fallback=True) == ("def456-0", False)


def test_select_mulled_v2_tag_no_version_hash_is_newest_exact():
    # No version-hash (v1 / unversioned): the newest tag is the canonical match.
    assert select_mulled_v2_tag(["def456-0"], None) == ("def456-0", True)


def test_select_mulled_v2_tag_empty():
    assert select_mulled_v2_tag([], "abc123") == (None, False)


# --- find_remote_mulled_name (network faked) --------------------------------


def test_find_remote_single_exact(monkeypatch):
    monkeypatch.setattr(util, "mulled_tags_for", lambda *a, **k: ["1.17--h0_0", "1.16--h0_0"])
    match = find_remote_mulled_name([build_target("samtools", version="1.17")], "biocontainers")
    assert match == ("samtools:1.17--h0_0", True)


def test_find_remote_single_no_fallback_returns_none(monkeypatch):
    monkeypatch.setattr(util, "mulled_tags_for", lambda *a, **k: ["1.17--h0_0"])
    # exact-only (resolver semantics): a missing version yields no match.
    assert find_remote_mulled_name([build_target("samtools", version="9.9")], "biocontainers") is None


def test_find_remote_single_newest_fallback(monkeypatch):
    monkeypatch.setattr(util, "mulled_tags_for", lambda *a, **k: ["1.17--h0_0", "1.16--h0_0"])
    match = find_remote_mulled_name(
        [build_target("samtools", version="9.9")], "biocontainers", allow_newest_fallback=True
    )
    assert match == ("samtools:1.17--h0_0", False)


def test_find_remote_multi_exact(monkeypatch):
    targets = [build_target("bwa", version="0.7.17"), build_target("samtools", version="1.17")]
    repo, version_hash = v2_image_name(targets).split(":", 1)

    def fake_tags(namespace, image, **k):
        return [f"{version_hash}-0"] if image == repo else []

    monkeypatch.setattr(util, "mulled_tags_for", fake_tags)
    match = find_remote_mulled_name(targets, "biocontainers")
    assert match == (f"{repo}:{version_hash}-0", True)


def test_find_remote_multi_no_match_returns_none(monkeypatch):
    targets = [build_target("bwa", version="0.7.17"), build_target("samtools", version="1.17")]
    monkeypatch.setattr(util, "mulled_tags_for", lambda *a, **k: ["unrelated-0"])
    assert find_remote_mulled_name(targets, "biocontainers") is None
    match = find_remote_mulled_name(targets, "biocontainers", allow_newest_fallback=True)
    assert match is not None and match.exact is False
