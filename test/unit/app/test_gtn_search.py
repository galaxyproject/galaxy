"""Unit tests for the GTN search library (lib/galaxy/agents/gtn).

These exercise the SQLite-backed search interface and the FAQ/tutorial
result types against tiny in-memory fixture databases built via
GTNDatabaseBuilder.
"""

import gzip
import os
import sqlite3
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

import pytest
import responses

from galaxy.agents.gtn import (
    FAQResult,
    GTNSearchDB,
)
from galaxy.agents.gtn.build_database import (
    FAQ,
    GTNDatabaseBuilder,
    Tutorial,
)
from galaxy.agents.gtn.search import (
    GTN_FAQ_BASE_URL,
    sanitize_fts5_query,
)


@pytest.fixture
def fixture_db(tmp_path: Path) -> Path:
    """Build a tiny GTN search database with a couple of tutorials and FAQs."""
    db_path = tmp_path / "fixture_gtn.db"
    builder = GTNDatabaseBuilder(gtn_path=tmp_path, output_path=db_path)
    builder.tutorials = [
        Tutorial(
            topic="transcriptomics",
            tutorial="rna-seq-intro",
            title="RNA-seq analysis introduction",
            description="Reference-based RNA-seq from reads to counts.",
            url="https://training.galaxyproject.org/training-material/topics/transcriptomics/tutorials/rna-seq-intro/tutorial.html",
            difficulty="introductory",
            hands_on=True,
            time_estimation="3H",
            content="Map RNA-seq reads with HISAT2 and count features with featureCounts.",
            tools=["hisat2", "featurecounts"],
            content_hash="abc123",
        ),
        Tutorial(
            topic="variant-analysis",
            tutorial="dip-and-snp-calling",
            title="Calling variants in diploid systems",
            description="Variant calling tutorial using bwa-mem and bcftools.",
            url="https://training.galaxyproject.org/training-material/topics/variant-analysis/tutorials/dip/tutorial.html",
            difficulty="intermediate",
            hands_on=True,
            time_estimation="2H",
            content="Align reads with BWA-MEM and call variants with bcftools.",
            tools=["bwa-mem", "bcftools"],
            content_hash="def456",
        ),
    ]
    builder.faqs = [
        FAQ(
            category="galaxy",
            filename="archive-a-history",
            title="How do I archive a history?",
            area="histories",
            content="Histories can be archived from the history options menu.",
            content_hash="faq1",
        ),
        FAQ(
            category="gtn",
            filename="contributing-tutorial",
            title="How do I contribute a tutorial to GTN?",
            area="contributing",
            content="Tutorials live in topics/<topic>/tutorials/<name>/tutorial.md.",
            content_hash="faq2",
        ),
    ]
    builder.create_database()
    builder.insert_tutorials()
    builder.insert_faqs()
    builder.add_metadata()
    return db_path


def test_sanitize_fts5_query_strips_operators():
    assert sanitize_fts5_query("climate data, help me analyze (temp)") == "climate data help me analyze temp"


def test_sanitize_fts5_query_preserves_phrases():
    assert sanitize_fts5_query('find "exact phrase" in data', preserve_phrases=True) == 'find "exact phrase" in data'


def test_sanitize_fts5_query_drops_quotes_when_disabled():
    assert sanitize_fts5_query('find "exact phrase" in data', preserve_phrases=False) == "find exact phrase in data"


def test_sanitize_fts5_query_drops_unmatched_quotes():
    # An unmatched quote left in the query would surface to FTS5 as
    # OperationalError: unterminated string, which the search layer
    # silently swallows -- so a user typo becomes a phantom no-results.
    assert sanitize_fts5_query('find "exact phrase') == "find exact phrase"


def test_sanitize_fts5_query_returns_empty_for_blank_input():
    assert sanitize_fts5_query("") == ""
    assert sanitize_fts5_query("    ") == ""


def test_sanitize_fts5_query_handles_only_operators():
    # All characters strip to whitespace, so the cleaned query is empty.
    assert sanitize_fts5_query("()[],;:+-?!") == ""


def test_search_returns_tutorial_hit(fixture_db: Path):
    db = GTNSearchDB(db_path=str(fixture_db))
    results = db.search("RNA-seq")
    assert len(results) >= 1
    titles = [r.title for r in results]
    assert "RNA-seq analysis introduction" in titles


def test_search_filters_by_topic(fixture_db: Path):
    db = GTNSearchDB(db_path=str(fixture_db))
    results = db.search("tutorial", topic="variant-analysis")
    assert all(r.topic == "variant-analysis" for r in results)


def test_search_faqs_returns_hits(fixture_db: Path):
    db = GTNSearchDB(db_path=str(fixture_db))
    results = db.search_faqs("archive")
    assert len(results) == 1
    assert results[0].title == "How do I archive a history?"


def test_search_faqs_falls_back_to_or_for_stopword_heavy_queries(fixture_db: Path):
    # FTS5 ANDs space-separated tokens by default. A user query like
    # "how can I archive my history" misses the archive FAQ because the
    # FAQ doesn't contain "my", even though every other term lines up.
    # The OR fallback should surface it anyway.
    db = GTNSearchDB(db_path=str(fixture_db))
    results = db.search_faqs("how can I archive my history")
    assert len(results) >= 1
    assert results[0].title == "How do I archive a history?"


def test_search_falls_back_to_or_for_stopword_heavy_queries(fixture_db: Path):
    # Same fallback shape for tutorial search.
    db = GTNSearchDB(db_path=str(fixture_db))
    results = db.search("show me a quick RNA-seq tutorial")
    assert len(results) >= 1
    assert "RNA-seq" in results[0].title


def test_search_by_tools_finds_tutorial_using_tool(fixture_db: Path):
    db = GTNSearchDB(db_path=str(fixture_db))
    results = db.search_by_tools(["bwa-mem"])
    assert len(results) == 1
    assert results[0].tutorial == "dip-and-snp-calling"


def test_search_by_tools_escapes_like_metacharacters(fixture_db: Path):
    db = GTNSearchDB(db_path=str(fixture_db))
    # "%" as a tool name should match nothing -- no tutorial uses a tool
    # literally named "%". Without LIKE escaping, "%%%" globs every row.
    assert db.search_by_tools(["%"]) == []
    # Same for "_": it should only match a tool literally containing
    # an underscore, not stand in for any single character.
    assert db.search_by_tools(["hisa_2"]) == []


def test_faq_result_to_dict_points_at_per_faq_page():
    # GTN renders each FAQ as its own .html page rather than as a fragment
    # anchor on the category index, so the URL has to be built from the
    # FAQ's filename, not a title slug. Anchor-style URLs would 200 on the
    # category page but never scroll to the actual FAQ.
    result = FAQResult(
        id=1,
        category="galaxy",
        filename="histories_archive",
        title="Archive a history",
        area="histories",
        content="...",
        snippet="<mark>archive</mark>",
        score=3.5,
    )
    payload = result.to_dict()
    assert payload["url"] == f"{GTN_FAQ_BASE_URL}/galaxy/histories_archive.html"
    assert "<mark>" not in payload["snippet"]


def test_refresh_database_keeps_old_db_when_download_fails(fixture_db: Path, tmp_path: Path):
    target = tmp_path / "live_gtn.db"
    # Seed the target with a valid DB by copying the fixture.
    target.write_bytes(fixture_db.read_bytes())
    original_bytes = target.read_bytes()

    bogus_url = (tmp_path / "does_not_exist.db").as_uri()
    with pytest.raises(FileNotFoundError):
        GTNSearchDB.refresh_database(target, bogus_url)

    # Existing DB must be intact.
    assert target.read_bytes() == original_bytes
    # And the temp file must have been cleaned up.
    assert not (target.parent / "live_gtn.db.tmp").exists()


def test_refresh_database_rejects_invalid_payload(tmp_path: Path):
    target = tmp_path / "live_gtn.db"
    # Pre-existing valid sqlite file (empty schema is fine -- refresh validates against the *new* file)
    sqlite3.connect(target).close()
    bogus_source = tmp_path / "bogus_source.db"
    bogus_source.write_text("not a sqlite database")

    with pytest.raises(FileNotFoundError):
        GTNSearchDB.refresh_database(target, bogus_source.as_uri())

    # Target was not replaced with the bogus payload.
    assert target.read_text(errors="replace") != "not a sqlite database"


def _build_fixture_db(target: Path, marker_title: str) -> None:
    """Build a tiny valid GTN DB whose only tutorial title is ``marker_title``."""
    builder = GTNDatabaseBuilder(gtn_path=target.parent, output_path=target)
    builder.tutorials = [
        Tutorial(
            topic="freshness",
            tutorial="marker",
            title=marker_title,
            description="",
            url="https://example.invalid",
            content="content",
            content_hash="hash",
        )
    ]
    builder.create_database()
    builder.insert_tutorials()
    builder.add_metadata()


def _tutorial_titles(db_path: Path) -> list[str]:
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        return [row[0] for row in conn.execute("SELECT title FROM tutorials")]


def test_refresh_database_if_stale_downloads_when_remote_is_newer(tmp_path: Path):
    remote_path = tmp_path / "remote.db"
    local_path = tmp_path / "local.db"
    _build_fixture_db(remote_path, "REMOTE")
    _build_fixture_db(local_path, "LOCAL")

    # Push local mtime well into the past so remote is unambiguously newer.
    past = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    os.utime(local_path, (past, past))

    metadata = GTNSearchDB.refresh_database_if_stale(local_path, remote_path.as_uri())

    assert metadata is not None
    assert _tutorial_titles(local_path) == ["REMOTE"]


def test_refresh_database_if_stale_skips_when_local_is_current(tmp_path: Path):
    remote_path = tmp_path / "remote.db"
    local_path = tmp_path / "local.db"
    _build_fixture_db(remote_path, "REMOTE")
    _build_fixture_db(local_path, "LOCAL")

    # Push remote into the past so local always looks current.
    past = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
    os.utime(remote_path, (past, past))

    local_mtime_before = local_path.stat().st_mtime
    metadata = GTNSearchDB.refresh_database_if_stale(local_path, remote_path.as_uri())

    assert metadata is None
    assert _tutorial_titles(local_path) == ["LOCAL"]
    assert local_path.stat().st_mtime == local_mtime_before


def test_refresh_database_if_stale_downloads_when_local_is_missing(tmp_path: Path):
    remote_path = tmp_path / "remote.db"
    _build_fixture_db(remote_path, "REMOTE")
    local_path = tmp_path / "cold-start.db"

    metadata = GTNSearchDB.refresh_database_if_stale(local_path, remote_path.as_uri())

    assert metadata is not None
    assert local_path.exists()
    assert _tutorial_titles(local_path) == ["REMOTE"]


def test_download_stamps_local_mtime_to_remote_last_modified(tmp_path: Path):
    remote_path = tmp_path / "remote.db"
    _build_fixture_db(remote_path, "REMOTE")
    # Pin the remote file's mtime to a known past second so we can assert
    # the local copy ends up with the same second after download.
    pinned = (datetime.now(timezone.utc) - timedelta(days=7)).replace(microsecond=0).timestamp()
    os.utime(remote_path, (pinned, pinned))

    local_path = tmp_path / "local.db"
    GTNSearchDB.refresh_database(local_path, remote_path.as_uri())

    assert int(local_path.stat().st_mtime) == int(pinned)


@responses.activate
def test_refresh_database_streams_http_download_and_stamps_timestamp(fixture_db: Path, tmp_path: Path):
    url = "https://example.com/gtn_search.db"
    last_modified = "Wed, 20 Aug 2025 12:00:00 GMT"
    responses.add(
        responses.GET,
        url,
        body=gzip.compress(fixture_db.read_bytes(), mtime=0),
        headers={"Content-Encoding": "gzip", "Last-Modified": last_modified},
    )
    target = tmp_path / "downloaded.db"

    metadata = GTNSearchDB.refresh_database(target, url)

    assert metadata["tutorial_count"] == 2
    assert target.read_bytes() == fixture_db.read_bytes()
    assert datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc) == datetime(
        2025, 8, 20, 12, 0, tzinfo=timezone.utc
    )


@responses.activate
def test_refresh_database_if_stale_uses_http_head(fixture_db: Path, tmp_path: Path):
    url = "https://example.com/gtn_search.db"
    target = tmp_path / "current.db"
    target.write_bytes(fixture_db.read_bytes())
    current = datetime(2025, 8, 21, 12, 0, tzinfo=timezone.utc).timestamp()
    os.utime(target, (current, current))
    responses.add(responses.HEAD, url, headers={"Last-Modified": "Wed, 20 Aug 2025 12:00:00 GMT"})

    assert GTNSearchDB.refresh_database_if_stale(target, url) is None
    assert len(responses.calls) == 1
    assert responses.calls[0].request.method == "HEAD"


TUTORIAL_FRONTMATTER = """---
layout: tutorial_hands_on
title: "Reference-based RNA-Seq data analysis"
level: Introductory
tags:
    - rna-seq
    - collections
questions:
    - What are the steps to process RNA-Seq data?
    - How to identify differentially expressed genes?
objectives:
    - Check a sequence quality report generated by Falco
    - Evaluate the quality of mapping results
key_points:
    - A spliced mapping tool should be used on eukaryotic RNA-Seq data
requirements:
  -
    type: internal
    topic_name: introduction
    tutorials:
      - galaxy-intro-short
---

# Introduction

Map RNA-seq reads with HISAT2.
"""


def _parse_tutorial_text(tmp_path: Path, text: str):
    tutorial_file = tmp_path / "tutorial.md"
    tutorial_file.write_text(text, encoding="utf-8")
    builder = GTNDatabaseBuilder(gtn_path=tmp_path, output_path=tmp_path / "out.db")
    return builder.parse_tutorial(tutorial_file, "transcriptomics", "ref-based")


def test_curriculum_fields_come_from_frontmatter(tmp_path: Path):
    """Authors write questions/objectives/key_points as frontmatter lists."""
    tutorial = _parse_tutorial_text(tmp_path, TUTORIAL_FRONTMATTER)

    assert tutorial is not None
    assert tutorial.objectives.split("\n") == [
        "Check a sequence quality report generated by Falco",
        "Evaluate the quality of mapping results",
    ]
    assert tutorial.questions.split("\n") == [
        "What are the steps to process RNA-Seq data?",
        "How to identify differentially expressed genes?",
    ]
    assert tutorial.key_points == "A spliced mapping tool should be used on eukaryotic RNA-Seq data"


def test_four_space_indented_lists_are_not_dropped(tmp_path: Path):
    tutorial = _parse_tutorial_text(tmp_path, TUTORIAL_FRONTMATTER)

    assert tutorial is not None
    assert tutorial.tags == ["rna-seq", "collections"]


@pytest.mark.parametrize("indent", ["", " ", "  ", "    ", "\t"])
def test_list_items_parse_at_any_indentation(tmp_path: Path, indent: str):
    builder = GTNDatabaseBuilder(gtn_path=tmp_path)

    parsed = builder.parse_yaml_simple(f"objectives:\n{indent}- first\n{indent}- second\n")

    assert parsed["objectives"] == ["first", "second"]


def test_nested_mapping_entries_do_not_leak_into_the_parent_list(tmp_path: Path):
    """A requirement's own `tutorials:` list must not become a requirement."""
    builder = GTNDatabaseBuilder(gtn_path=tmp_path)

    parsed = builder.parse_yaml_simple(
        "requirements:\n  -\n    type: internal\n    tutorials:\n      - galaxy-intro-short\n"
    )

    assert parsed["requirements"] == []


def test_quoted_list_items_lose_their_quotes(tmp_path: Path):
    builder = GTNDatabaseBuilder(gtn_path=tmp_path)

    parsed = builder.parse_yaml_simple("objectives:\n  - \"Learn the basics\"\n  - 'Run the suite'\n")

    assert parsed["objectives"] == ["Learn the basics", "Run the suite"]


def test_curriculum_falls_back_to_the_body_when_frontmatter_omits_it(tmp_path: Path):
    text = "---\ntitle: No curriculum frontmatter\n---\n\n<objectives>\n- Learn the body form\n</objectives>\n"

    tutorial = _parse_tutorial_text(tmp_path, text)

    assert tutorial is not None
    assert "Learn the body form" in tutorial.objectives


def test_empty_frontmatter_key_yields_no_curriculum(tmp_path: Path):
    tutorial = _parse_tutorial_text(tmp_path, "---\ntitle: Empty\nobjectives:\nquestions:\n---\n\nBody.\n")

    assert tutorial is not None
    assert tutorial.objectives == ""
    assert tutorial.questions == ""


def test_long_tutorial_bodies_are_kept_past_the_old_50k_cutoff(tmp_path: Path):
    body = "Section about mapping.\n" * 6000
    tutorial = _parse_tutorial_text(tmp_path, f"---\ntitle: Long\n---\n\n{body}")

    assert tutorial is not None
    assert len(tutorial.content) > 100000
