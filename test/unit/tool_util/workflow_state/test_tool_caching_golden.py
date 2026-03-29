"""Golden-file tests for cache interop contract.

Reads cache_golden.yaml manifest, exercises the full pipeline
(parse_toolshed_tool_id -> _cache_key -> cache load -> ParsedTool assertions)
against the golden cache_golden/ directory.

This manifest + golden directory is the cross-language contract for the
Node.js tool cache proxy package.
"""

import json
import os

import pytest
import yaml

from galaxy.tool_util_models import ParsedTool
from galaxy.tool_util.workflow_state.toolshed_tool_info import (
    _cache_key,
    parse_toolshed_tool_id,
    ToolShedGetToolInfo,
)

FIXTURES_DIR = os.path.dirname(__file__)
MANIFEST_PATH = os.path.join(FIXTURES_DIR, "cache_golden.yaml")
GOLDEN_CACHE_DIR = os.path.join(FIXTURES_DIR, "cache_golden")


def _assert_tool_matches(result, expected):
    """Assert ParsedTool fields match manifest expected_tool section."""
    assert result.name == expected["name"]
    assert result.id == expected["id"]
    if "description" in expected:
        assert result.description == expected["description"]
    if "input_count" in expected:
        assert len(result.inputs) == expected["input_count"]
    if "input_names" in expected:
        assert [i.name for i in result.inputs] == expected["input_names"]
    if "input_types" in expected:
        assert [i.parameter_type for i in result.inputs] == expected["input_types"]
    if "output_count" in expected:
        assert len(result.outputs) == expected["output_count"]
    if "output_names" in expected:
        assert [o.name for o in result.outputs] == expected["output_names"]
    if "citation_count" in expected:
        assert len(result.citations) == expected["citation_count"]
    if "edam_operations" in expected:
        assert result.edam_operations == expected["edam_operations"]


@pytest.fixture(scope="module")
def manifest():
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def tool_info():
    """ToolShedGetToolInfo pointed at the golden cache directory."""
    return ToolShedGetToolInfo(
        cache_dir=GOLDEN_CACHE_DIR,
        default_toolshed_url="https://toolshed.g2.bx.psu.edu",
    )


# --- Toolshed tools: full pipeline ---


class TestToolshedTools:
    def test_parse_and_cache_key(self, manifest):
        for entry in manifest["toolshed_tools"]:
            result = parse_toolshed_tool_id(entry["tool_id"])
            assert result is not None, f"Failed to parse: {entry['tool_id']}"
            url, trs_id, version = result
            assert url == entry["expected_url"]
            assert trs_id == entry["expected_trs_id"]
            assert version == entry["expected_version"]
            key = _cache_key(url, trs_id, version)
            assert (
                key == entry["expected_cache_key"]
            ), f"Cache key mismatch for {entry['tool_id']}: {key} != {entry['expected_cache_key']}"

    def test_cache_load(self, manifest, tool_info):
        for entry in manifest["toolshed_tools"]:
            result = tool_info.get_tool_info(entry["tool_id"], entry["expected_version"])
            assert result is not None, f"Cache miss: {entry['tool_id']}"
            _assert_tool_matches(result, entry["expected_tool"])


# --- Stock tools ---


class TestStockTools:
    def test_cache_key(self, manifest):
        for entry in manifest["stock_tools"]:
            key = _cache_key(
                entry["default_toolshed_url"],
                entry["expected_trs_id"],
                entry["expected_version"],
            )
            assert key == entry["expected_cache_key"]

    def test_cache_load(self, manifest, tool_info):
        for entry in manifest["stock_tools"]:
            result = tool_info.get_tool_info(entry["tool_id"], entry["tool_version"])
            assert result is not None
            _assert_tool_matches(result, entry["expected_tool"])


# --- Unparseable tool IDs ---


class TestUnparseableToolIds:
    def test_returns_none(self, manifest):
        for entry in manifest["unparseable_tool_ids"]:
            assert parse_toolshed_tool_id(entry["tool_id"]) is None, f"Should not parse: {entry['tool_id']}"


# --- Version from separate arg ---


class TestVersionFromSeparateArg:
    def test_parse_yields_no_version(self, manifest):
        """tool_id without version parses with None version."""
        for entry in manifest["version_from_separate_arg"]:
            result = parse_toolshed_tool_id(entry["tool_id"])
            assert result is not None
            url, trs_id, parsed_version = result
            assert parsed_version is None
            assert url == entry["expected_url"]
            assert trs_id == entry["expected_trs_id"]

    def test_same_cache_key_as_embedded(self, manifest):
        """tool_id without version + explicit version = same key as embedded version."""
        for entry in manifest["version_from_separate_arg"]:
            result = parse_toolshed_tool_id(entry["tool_id"])
            assert result is not None
            url, trs_id, _ = result
            key = _cache_key(url, trs_id, entry["tool_version"])
            assert key == entry["expected_cache_key"]

    def test_cache_load_with_explicit_version(self, manifest, tool_info):
        """Full pipeline: versionless tool_id + explicit version resolves to same ParsedTool."""
        for entry in manifest["version_from_separate_arg"]:
            result = tool_info.get_tool_info(entry["tool_id"], entry["tool_version"])
            assert result is not None, f"Cache miss: {entry['tool_id']} @ {entry['tool_version']}"
            expected = entry["expected_tool"]
            assert result.name == expected["name"]
            assert result.id == expected["id"]


# --- Round-trip integrity ---


class TestGoldenIntegrity:
    """Verify golden cache files are valid and consistent with manifest."""

    def test_all_json_files_are_valid_parsed_tools(self):
        """Every .json in cache_golden/ (except index.json) validates as ParsedTool."""
        for fname in os.listdir(GOLDEN_CACHE_DIR):
            if fname == "index.json" or not fname.endswith(".json"):
                continue
            path = os.path.join(GOLDEN_CACHE_DIR, fname)
            with open(path) as f:
                data = json.load(f)
            ParsedTool.model_validate(data)

    def test_manifest_keys_match_golden_files(self, manifest):
        """Every expected_cache_key in manifest has a corresponding .json file."""
        expected_keys = set()
        for entry in manifest.get("toolshed_tools", []):
            expected_keys.add(entry["expected_cache_key"])
        for entry in manifest.get("stock_tools", []):
            expected_keys.add(entry["expected_cache_key"])

        actual_files = {
            f.replace(".json", "") for f in os.listdir(GOLDEN_CACHE_DIR) if f.endswith(".json") and f != "index.json"
        }
        assert expected_keys == actual_files, (
            f"Manifest/golden mismatch.\n"
            f"  In manifest but not golden: {expected_keys - actual_files}\n"
            f"  In golden but not manifest: {actual_files - expected_keys}"
        )

    def test_index_entries_match_golden_files(self):
        """index.json entries match the .json files on disk."""
        index_path = os.path.join(GOLDEN_CACHE_DIR, "index.json")
        with open(index_path) as f:
            index_data = json.load(f)
        index_keys = set(index_data.get("entries", {}).keys())

        actual_files = {
            f.replace(".json", "") for f in os.listdir(GOLDEN_CACHE_DIR) if f.endswith(".json") and f != "index.json"
        }
        assert index_keys == actual_files
