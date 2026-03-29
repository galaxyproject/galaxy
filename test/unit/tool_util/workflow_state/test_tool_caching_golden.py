"""Golden-file tests for cache interop contract.

Reads cache_golden.yaml manifest, exercises the full pipeline
(parse_toolshed_tool_id -> _cache_key -> cache load -> ParsedTool assertions)
against the golden cache_golden/ directory.

This manifest + golden directory is the cross-language contract for the
Node.js tool cache proxy package.
"""

import hashlib
import json
import os

import pytest
import yaml

from galaxy.tool_util.workflow_state.toolshed_tool_info import (
    _cache_key,
    parse_toolshed_tool_id,
    ToolShedGetToolInfo,
)
from galaxy.tool_util_models import ParsedTool

FIXTURES_DIR = os.path.dirname(__file__)
MANIFEST_PATH = os.path.join(FIXTURES_DIR, "cache_golden.yaml")
GOLDEN_CACHE_DIR = os.path.join(FIXTURES_DIR, "cache_golden")

SUPPORTED_FORMAT_VERSION = 1


def _resolve_path(inputs, path):
    """Walk a ParsedTool input tree to resolve a dotted path to a parameter type.

    Path segments are interpreted based on the current node type:
    - gx_repeat/gx_section: segment is a child parameter name
    - gx_conditional: first segment after the conditional is the test param name
      OR a when-branch discriminator value, then remaining segments resolve within that branch
    """
    parts = path.split(".")
    current_inputs = inputs

    i = 0
    while i < len(parts):
        segment = parts[i]
        # Find matching parameter in current_inputs
        param = None
        for p in current_inputs:
            if p.name == segment:
                param = p
                break
        if param is None:
            return None

        # Last segment — return its type
        if i == len(parts) - 1:
            return param.parameter_type

        ptype = param.parameter_type
        if ptype == "gx_conditional":
            # Next segment could be the test parameter name or a when-branch discriminator
            next_seg = parts[i + 1]
            if param.test_parameter and param.test_parameter.name == next_seg:
                # Resolving the test parameter itself
                if i + 1 == len(parts) - 1:
                    return param.test_parameter.parameter_type
                # Can't go deeper into a test parameter
                return None
            # Otherwise next_seg is a when-branch discriminator
            when_branch = None
            for w in param.whens:
                if w.discriminator == next_seg:
                    when_branch = w
                    break
            if when_branch is None:
                return None
            current_inputs = when_branch.parameters
            i += 2  # skip conditional name + discriminator
            continue
        elif ptype in ("gx_repeat", "gx_section"):
            current_inputs = param.parameters
            i += 1
            continue
        else:
            return None

    return None


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
        data = yaml.safe_load(f)
    assert "format_version" in data, "cache_golden.yaml missing format_version field"
    assert (
        data["format_version"] == SUPPORTED_FORMAT_VERSION
    ), f"Unsupported manifest format_version {data['format_version']}, expected {SUPPORTED_FORMAT_VERSION}"
    return data


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


# --- Nested structure assertions ---


class TestNestedStructure:
    """Verify deep parameter nesting matches manifest expected_nested_structure."""

    def test_nested_paths(self, manifest, tool_info):
        for section in ("toolshed_tools", "stock_tools"):
            for entry in manifest.get(section, []):
                nested = entry.get("expected_nested_structure")
                if not nested:
                    continue
                version = entry.get("expected_version") or entry.get("tool_version")
                result = tool_info.get_tool_info(entry["tool_id"], version)
                assert result is not None, f"Cache miss: {entry['tool_id']}"
                for path, expected_type in nested.items():
                    actual_type = _resolve_path(result.inputs, path)
                    assert actual_type is not None, f"Path {path!r} not found in {entry['tool_id']}"
                    assert actual_type == expected_type, (
                        f"Type mismatch at {path!r} in {entry['tool_id']}: "
                        f"expected {expected_type}, got {actual_type}"
                    )

    def test_bogus_paths_return_none(self, manifest, tool_info):
        """Invalid paths resolve to None rather than raising."""
        entry = manifest["toolshed_tools"][0]
        version = entry["expected_version"]
        result = tool_info.get_tool_info(entry["tool_id"], version)
        assert result is not None
        for bogus in ("nonexistent", "results.nonexistent", "results.software_cond.fake_when.x"):
            assert _resolve_path(result.inputs, bogus) is None, f"Expected None for {bogus!r}"


# --- Round-trip integrity ---


class TestGoldenIntegrity:
    """Verify golden cache files are valid and consistent with manifest."""

    def test_all_json_files_are_valid_parsed_tools(self):
        """Every .json in cache_golden/ (except index.json/checksums.json) validates as ParsedTool."""
        for fname in os.listdir(GOLDEN_CACHE_DIR):
            if fname in ("index.json", "checksums.json") or not fname.endswith(".json"):
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
            f.replace(".json", "")
            for f in os.listdir(GOLDEN_CACHE_DIR)
            if f.endswith(".json") and f not in ("index.json", "checksums.json")
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
            f.replace(".json", "")
            for f in os.listdir(GOLDEN_CACHE_DIR)
            if f.endswith(".json") and f not in ("index.json", "checksums.json")
        }
        assert index_keys == actual_files

    def test_checksums_valid(self):
        """checksums.json matches actual file hashes."""
        checksums_path = os.path.join(GOLDEN_CACHE_DIR, "checksums.json")
        with open(checksums_path) as f:
            checksums = json.load(f)

        # Verify manifest hash
        with open(MANIFEST_PATH, "rb") as f:
            manifest_hash = hashlib.sha256(f.read()).hexdigest()
        assert checksums["manifest_sha256"] == manifest_hash, (
            f"Manifest checksum stale: expected {manifest_hash}, got {checksums['manifest_sha256']}. "
            "Regenerate with: PYTHONPATH=lib python generate_golden_cache.py"
        )

        # Verify each golden file hash
        for fname, expected_hash in checksums["files"].items():
            fpath = os.path.join(GOLDEN_CACHE_DIR, fname)
            assert os.path.exists(fpath), f"checksums.json references missing file: {fname}"
            with open(fpath, "rb") as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            assert (
                actual_hash == expected_hash
            ), f"Checksum mismatch for {fname}. Regenerate with: PYTHONPATH=lib python generate_golden_cache.py"
