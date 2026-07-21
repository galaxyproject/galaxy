"""Tests for tool cache infrastructure: index, workflow extraction, CLI."""

import json
import os

import pytest
from gxformat2.normalized import ensure_native
from gxformat2.normalized._native import NormalizedNativeWorkflow

from galaxy.tool_util.workflow_state.scripts.tool_cache import build_parser
from galaxy.tool_util.workflow_state.scripts.workflow_lint_stateful import (
    build_parser as build_lint_stateful_parser,
)
from galaxy.tool_util.workflow_state.scripts.workflow_to_native_stateful import (
    build_parser as build_to_native_parser,
)
from galaxy.tool_util.workflow_state.toolshed_tool_info import (
    _cache_key,
    CacheIndex,
    get_cache_dir,
    parse_toolshed_tool_id,
    ToolShedGetToolInfo,
)

# --- parse_toolshed_tool_id ---


class TestParseToolshedToolId:
    def test_full_id_with_version(self):
        result = parse_toolshed_tool_id("toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0")
        assert result is not None
        url, trs_id, version = result
        assert url == "https://toolshed.g2.bx.psu.edu"
        assert trs_id == "devteam~fastqc~fastqc"
        assert version == "0.74+galaxy0"

    def test_full_id_with_scheme(self):
        result = parse_toolshed_tool_id("https://toolshed.g2.bx.psu.edu/repos/iuc/multiqc/multiqc/1.11+galaxy1")
        assert result is not None
        url, trs_id, version = result
        assert url == "https://toolshed.g2.bx.psu.edu"
        assert trs_id == "iuc~multiqc~multiqc"
        assert version == "1.11+galaxy1"

    def test_id_without_version(self):
        result = parse_toolshed_tool_id("toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc")
        assert result is not None
        url, trs_id, version = result
        assert trs_id == "devteam~fastqc~fastqc"
        assert version is None

    def test_not_a_toolshed_tool(self):
        assert parse_toolshed_tool_id("cat1") is None
        assert parse_toolshed_tool_id("__DATA_FETCH__") is None
        assert parse_toolshed_tool_id("upload1") is None

    def test_too_few_segments(self):
        assert parse_toolshed_tool_id("toolshed.g2.bx.psu.edu/repos/owner/repo") is None


# --- CacheIndex ---


class TestCacheIndex:
    def test_add_and_list(self, tmp_path):
        index = CacheIndex(str(tmp_path))
        index.add("abc123", "devteam/fastqc", "0.74", "api", "https://...")
        entries = index.list_all()
        assert len(entries) == 1
        assert entries[0]["cache_key"] == "abc123"
        assert entries[0]["tool_id"] == "devteam/fastqc"
        assert entries[0]["source"] == "api"

    def test_has(self, tmp_path):
        index = CacheIndex(str(tmp_path))
        assert not index.has("abc123")
        index.add("abc123", "test", "1.0", "api")
        assert index.has("abc123")

    def test_remove(self, tmp_path):
        index = CacheIndex(str(tmp_path))
        index.add("abc123", "test", "1.0", "api")
        index.remove("abc123")
        assert not index.has("abc123")

    def test_clear(self, tmp_path):
        index = CacheIndex(str(tmp_path))
        index.add("a", "t1", "1.0", "api")
        index.add("b", "t2", "2.0", "local")
        index.clear()
        assert len(index.list_all()) == 0

    def test_persistence(self, tmp_path):
        index1 = CacheIndex(str(tmp_path))
        index1.add("abc", "tool", "1.0", "api")

        # New instance reads from disk
        index2 = CacheIndex(str(tmp_path))
        assert index2.has("abc")
        entries = index2.list_all()
        assert len(entries) == 1

    def test_corrupted_index_recovers(self, tmp_path):
        # Write invalid JSON
        index_path = os.path.join(str(tmp_path), "index.json")
        with open(index_path, "w") as f:
            f.write("{bad json")

        index = CacheIndex(str(tmp_path))
        assert len(index.list_all()) == 0
        # Can still add
        index.add("new", "tool", "1.0", "api")
        assert index.has("new")


# --- get_cache_dir ---


class TestGetCacheDir:
    def test_override(self):
        assert get_cache_dir("/custom/path") == "/custom/path"

    def test_env_var(self, monkeypatch):
        monkeypatch.setenv("GALAXY_TOOL_CACHE_DIR", "/env/path")
        assert get_cache_dir() == "/env/path"

    def test_default(self, monkeypatch):
        monkeypatch.delenv("GALAXY_TOOL_CACHE_DIR", raising=False)
        result = get_cache_dir()
        assert result.endswith("tool_info_cache")


# --- ToolShedGetToolInfo cache operations ---


class TestToolShedGetToolInfoCache:
    def _make_fake_parsed_tool(self):
        """Create a minimal ParsedTool for testing."""
        from galaxy.tool_util_models import ParsedTool

        return ParsedTool(
            id="fastqc",
            version="0.74+galaxy0",
            name="FastQC",
            description="Read Quality reports",
            inputs=[],
            outputs=[],
            citations=[],
            license=None,
            profile=None,
            edam_operations=[],
            edam_topics=[],
            xrefs=[],
            help=None,
        )

    def test_populate_and_retrieve(self, tmp_path):
        tool_info = ToolShedGetToolInfo(cache_dir=str(tmp_path))
        pt = self._make_fake_parsed_tool()

        tool_id = "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0"
        tool_info.populate_from_parsed_tool(tool_id, "0.74+galaxy0", pt, source="test")

        assert tool_info.has_cached(tool_id, "0.74+galaxy0")

        # Retrieve it
        result = tool_info.get_tool_info(tool_id, "0.74+galaxy0")
        assert result is not None
        assert result.name == "FastQC"

    def test_list_cached(self, tmp_path):
        tool_info = ToolShedGetToolInfo(cache_dir=str(tmp_path))
        pt = self._make_fake_parsed_tool()

        tool_info.populate_from_parsed_tool(
            "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0", "0.74+galaxy0", pt, source="api"
        )

        entries = tool_info.list_cached()
        assert len(entries) == 1
        assert entries[0]["source"] == "api"

    def test_clear_all(self, tmp_path):
        tool_info = ToolShedGetToolInfo(cache_dir=str(tmp_path))
        pt = self._make_fake_parsed_tool()

        tool_info.populate_from_parsed_tool(
            "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0", "0.74+galaxy0", pt, source="api"
        )
        tool_info.clear_cache()

        assert len(tool_info.list_cached()) == 0
        assert not tool_info.has_cached(
            "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0", "0.74+galaxy0"
        )

    def test_backfill_index_on_load(self, tmp_path):
        """Cache files without index entries get backfilled on load."""
        ToolShedGetToolInfo(cache_dir=str(tmp_path))
        pt = self._make_fake_parsed_tool()

        # Write cache file directly (no index entry)
        key = _cache_key("https://toolshed.g2.bx.psu.edu", "devteam~fastqc~fastqc", "0.74+galaxy0")
        cache_path = os.path.join(str(tmp_path), f"{key}.json")
        os.makedirs(str(tmp_path), exist_ok=True)
        with open(cache_path, "w") as f:
            f.write(pt.model_dump_json(indent=2))

        # New instance — load should backfill index
        tool_info2 = ToolShedGetToolInfo(cache_dir=str(tmp_path))
        result = tool_info2.get_tool_info(
            "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0", "0.74+galaxy0"
        )
        assert result is not None
        assert result.name == "FastQC"
        assert tool_info2.index.has(key)


# --- unique_tools (via NormalizedNativeWorkflow) ---

IWC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "workflows", "iwc")


def _toolshed_tools(workflow: NormalizedNativeWorkflow):
    return [t for t in workflow.unique_tools if parse_toolshed_tool_id(t.tool_id)]


class TestUniqueToolshedTools:
    def test_native_workflow(self):
        workflow = NormalizedNativeWorkflow.model_validate(
            {
                "steps": {
                    "0": {"id": 0, "type": "data_input"},
                    "1": {
                        "id": 1,
                        "tool_id": "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0",
                        "tool_version": "0.74+galaxy0",
                    },
                    "2": {"id": 2, "tool_id": "cat1", "tool_version": "1.0.0"},
                }
            }
        )
        tools = _toolshed_tools(workflow)
        assert len(tools) == 1
        assert tools[0].tool_id == "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0"

    def test_subworkflow_recursion(self):
        workflow = NormalizedNativeWorkflow.model_validate(
            {
                "steps": {
                    "0": {
                        "id": 0,
                        "type": "subworkflow",
                        "subworkflow": {
                            "steps": {
                                "0": {
                                    "id": 0,
                                    "tool_id": "toolshed.g2.bx.psu.edu/repos/iuc/bwa/bwa/0.7.17",
                                    "tool_version": "0.7.17",
                                }
                            }
                        },
                    },
                }
            }
        )
        tools = _toolshed_tools(workflow)
        assert len(tools) == 1
        assert "bwa" in tools[0].tool_id

    def test_deduplication(self):
        workflow = NormalizedNativeWorkflow.model_validate(
            {
                "steps": {
                    "0": {
                        "id": 0,
                        "tool_id": "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0",
                        "tool_version": "0.74+galaxy0",
                    },
                    "1": {
                        "id": 1,
                        "tool_id": "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0",
                        "tool_version": "0.74+galaxy0",
                    },
                }
            }
        )
        tools = _toolshed_tools(workflow)
        assert len(tools) == 1

    def test_no_toolshed_tools(self):
        workflow = NormalizedNativeWorkflow.model_validate(
            {"steps": {"0": {"id": 0, "tool_id": "cat1", "tool_version": "1.0.0"}}}
        )
        tools = _toolshed_tools(workflow)
        assert len(tools) == 0

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(IWC_DIR, "RepeatMasking-Workflow.ga")),
        reason="IWC test workflows not available",
    )
    def test_iwc_repeat_masking(self):
        workflow = ensure_native(os.path.join(IWC_DIR, "RepeatMasking-Workflow.ga"))
        tools = _toolshed_tools(workflow)
        assert len(tools) == 2
        tool_ids = [t.tool_id for t in tools]
        assert any("repeatmodeler" in tid for tid in tool_ids)
        assert any("repeatmasker" in tid for tid in tool_ids)


# --- CLI parser ---


class TestCLIParser:
    def test_populate_workflow(self):
        parser = build_parser()
        args = parser.parse_args(["populate-workflow", "test.ga"])
        assert args.command == "populate-workflow"
        assert args.workflow_path == "test.ga"
        assert args.tool_source == "shed"

    def test_populate_workflow_with_source(self):
        parser = build_parser()
        args = parser.parse_args(["populate-workflow", "test.ga", "--tool-source", "galaxy"])
        assert args.tool_source == "galaxy"

    def test_add(self):
        parser = build_parser()
        args = parser.parse_args(["add", "devteam~fastqc~fastqc", "--version", "0.74+galaxy0"])
        assert args.command == "add"
        assert args.tool_id == "devteam~fastqc~fastqc"
        assert args.version == "0.74+galaxy0"

    def test_add_local(self):
        parser = build_parser()
        args = parser.parse_args(["add-local", "/path/to/tool.xml", "--tool-id", "toolshed.../fastqc/0.74"])
        assert args.xml_path == "/path/to/tool.xml"

    def test_list(self):
        parser = build_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_list_json(self):
        parser = build_parser()
        args = parser.parse_args(["list", "--json"])
        assert args.json is True

    def test_clear(self):
        parser = build_parser()
        args = parser.parse_args(["clear"])
        assert args.command == "clear"

    def test_clear_with_prefix(self):
        parser = build_parser()
        args = parser.parse_args(["clear", "devteam~fastqc~*"])
        assert args.tool_id_prefix == "devteam~fastqc~*"


class TestGalaxySource:
    def test_fetch_from_galaxy(self, tmp_path, monkeypatch):
        """fetch_from_galaxy calls the /parsed endpoint and returns ParsedTool."""
        import requests

        fake_parsed = {
            "id": "param_value_from_file",
            "version": "0.1.0",
            "name": "Parse parameter value",
            "description": None,
            "inputs": [],
            "outputs": [],
            "citations": [],
            "license": None,
            "profile": None,
            "edam_operations": [],
            "edam_topics": [],
            "xrefs": [],
            "help": None,
        }

        class MockResponse:
            status_code = 200

            def json(self):
                return fake_parsed

        def mock_get(url, **kwargs):
            assert "/api/tools/param_value_from_file/parsed" in url
            return MockResponse()

        monkeypatch.setattr(requests, "get", mock_get)
        tool_info = ToolShedGetToolInfo(cache_dir=str(tmp_path), galaxy_url="http://localhost:8080")
        result = tool_info.fetch_from_galaxy("http://localhost:8080", "param_value_from_file")
        assert result.id == "param_value_from_file"
        assert result.name == "Parse parameter value"

    def test_add_tool_galaxy_source(self, tmp_path, monkeypatch):
        """add_tool with source='galaxy' fetches and caches."""
        import requests

        from galaxy.tool_util.workflow_state.cache import add_tool as _add_tool

        fake_parsed = {
            "id": "param_value_from_file",
            "version": "0.1.0",
            "name": "Parse parameter value",
            "description": None,
            "inputs": [],
            "outputs": [],
            "citations": [],
            "license": None,
            "profile": None,
            "edam_operations": [],
            "edam_topics": [],
            "xrefs": [],
            "help": None,
        }

        class MockResponse:
            status_code = 200

            def json(self):
                return fake_parsed

        monkeypatch.setattr(requests, "get", lambda url, **kw: MockResponse())
        tool_info = ToolShedGetToolInfo(cache_dir=str(tmp_path), galaxy_url="http://localhost:8080")
        result = _add_tool(tool_info, "param_value_from_file", "0.1.0", source="galaxy")
        assert result is True
        assert tool_info.has_cached("param_value_from_file", "0.1.0")


# --- gxwf-to-native-stateful CLI parser ---


class TestToNativeStatefulCLIParser:
    def test_basic(self):
        parser = build_to_native_parser()
        args = parser.parse_args(["test.gxwf.yml"])
        assert args.workflow_path == "test.gxwf.yml"

    def test_output(self):
        parser = build_to_native_parser()
        args = parser.parse_args(["test.gxwf.yml", "-o", "output.ga"])
        assert args.output == "output.ga"

    def test_strict(self):
        parser = build_to_native_parser()
        args = parser.parse_args(["test.gxwf.yml", "--strict"])
        assert args.strict is True

    def test_populate_cache(self):
        parser = build_to_native_parser()
        args = parser.parse_args(["test.gxwf.yml", "--populate-cache", "--tool-source", "galaxy"])
        assert args.populate_cache is True
        assert args.tool_source == "galaxy"

    def test_verbose(self):
        parser = build_to_native_parser()
        args = parser.parse_args(["-v", "test.gxwf.yml"])
        assert args.verbose is True


# --- gxwf-lint-stateful CLI parser ---


class TestLintStatefulCLIParser:
    def test_basic(self):
        parser = build_lint_stateful_parser()
        args = parser.parse_args(["test.ga"])
        assert args.workflow_path == "test.ga"

    def test_strict(self):
        parser = build_lint_stateful_parser()
        args = parser.parse_args(["test.ga", "--strict"])
        assert args.strict is True

    def test_skip_best_practices(self):
        parser = build_lint_stateful_parser()
        args = parser.parse_args(["test.ga", "--skip-best-practices"])
        assert args.skip_best_practices is True

    def test_training_topic(self):
        parser = build_lint_stateful_parser()
        args = parser.parse_args(["test.ga", "--training-topic", "assembly"])
        assert args.training_topic == "assembly"

    def test_connections(self):
        parser = build_lint_stateful_parser()
        args = parser.parse_args(["test.ga", "--connections"])
        assert args.connections is True

    def test_report_json(self):
        parser = build_lint_stateful_parser()
        args = parser.parse_args(["test.ga", "--report-json", "out.json"])
        assert args.report_json == "out.json"

    def test_report_markdown_stdout(self):
        parser = build_lint_stateful_parser()
        args = parser.parse_args(["test.ga", "--report-markdown"])
        assert args.report_markdown == "-"

    def test_stale_key_policy(self):
        parser = build_lint_stateful_parser()
        args = parser.parse_args(["test.ga", "--allow", "bookkeeping", "--deny", "stale-root-keys"])
        assert args.allow == ["bookkeeping"]
        assert args.deny == ["stale-root-keys"]

    def test_populate_cache(self):
        parser = build_lint_stateful_parser()
        args = parser.parse_args(["test.ga", "--populate-cache", "--tool-source", "galaxy"])
        assert args.populate_cache is True
        assert args.tool_source == "galaxy"


# --- --output-schema CLI flag ---


class TestOutputSchema:
    """Test --output-schema across all workflow_state CLIs."""

    @pytest.mark.parametrize(
        "main_fn,expected_title",
        [
            ("galaxy.tool_util.workflow_state.scripts.workflow_validate:main", "SingleValidationReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_validate_tree:main", "TreeValidationReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_clean_stale_state:main", "SingleCleanReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_clean_stale_state_tree:main", "TreeCleanReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_to_format2_stateful:main", "SingleExportReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_to_format2_stateful_tree:main", "ExportTreeReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_to_native_stateful:main", "SingleToNativeReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_to_native_stateful_tree:main", "ToNativeTreeReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_lint_stateful:main", "SingleLintReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_lint_stateful_tree:main", "LintTreeReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_roundtrip_validate:main", "SingleRoundTripReport"),
            ("galaxy.tool_util.workflow_state.scripts.workflow_roundtrip_validate_tree:main", "RoundTripTreeReport"),
        ],
    )
    def test_output_schema(self, main_fn, expected_title, capsys):
        module_path, fn_name = main_fn.rsplit(":", 1)
        from importlib import import_module

        mod = import_module(module_path)
        main = getattr(mod, fn_name)
        with pytest.raises(SystemExit) as exc_info:
            main(["--output-schema"])
        assert exc_info.value.code == 0
        schema = json.loads(capsys.readouterr().out)
        assert schema["title"] == expected_title
        assert "properties" in schema
