"""Tests for parallel tool loading feature."""

import os
import string

from galaxy.app_unittest_utils.toolbox_support import BaseToolBoxTestCase

TOOL_TEMPLATE = string.Template("""<tool id="${tool_id}" name="Test Tool ${tool_id}" version="1.0" profile="16.01">
    <command>echo "test"</command>
    <inputs>
        <param type="text" name="param1" value="" />
    </inputs>
    <outputs>
        <data name="out1" format="data" />
    </outputs>
</tool>
""")


class TestParallelToolLoading(BaseToolBoxTestCase):
    """Test that parallel and serial tool loading produce identical results."""

    def _create_tool_file(self, tool_id):
        """Create a tool XML file and return its filename."""
        tool_contents = TOOL_TEMPLATE.safe_substitute(tool_id=tool_id)
        tool_path = os.path.join(self.test_directory, f"{tool_id}.xml")
        with open(tool_path, "w") as f:
            f.write(tool_contents)
        return f"{tool_id}.xml"

    def _reset_toolbox(self):
        """Reset toolbox state for fresh load."""
        self._toolbox = None
        self.app._toolbox = None  # type: ignore[assignment]
        self.app.tool_cache.cleanup()

    def _load_tools_serial(self):
        """Load tools with serial loading and return tool IDs."""
        self.app.config.parallel_tool_loading = False  # type: ignore[attr-defined]
        return set(self.toolbox._tools_by_id.keys())

    def _load_tools_parallel(self, workers=2):
        """Load tools with parallel loading and return tool IDs."""
        self.app.config.parallel_tool_loading = True  # type: ignore[attr-defined]
        self.app.config.parallel_tool_loading_workers = workers  # type: ignore[attr-defined]
        return set(self.toolbox._tools_by_id.keys())

    def test_parallel_loading_produces_same_tools(self):
        """Verify parallel and serial loading produce identical tool sets."""
        tool_ids = [f"test_tool_{i}" for i in range(5)]
        for tool_id in tool_ids:
            self._create_tool_file(tool_id)

        tool_refs = "\n".join(f'<tool file="{tool_id}.xml" />' for tool_id in tool_ids)
        self._add_config(f"""<toolbox tool_path="{self.test_directory}">
    {tool_refs}
</toolbox>""")

        serial_tool_ids = self._load_tools_serial()
        self._reset_toolbox()
        parallel_tool_ids = self._load_tools_parallel()

        assert serial_tool_ids == parallel_tool_ids
        for tool_id in tool_ids:
            assert tool_id in parallel_tool_ids

    def test_parallel_loading_with_sections(self):
        """Verify parallel loading works with tools in sections."""
        tool_ids = ["section_tool_1", "section_tool_2", "top_level_tool"]
        for tool_id in tool_ids:
            self._create_tool_file(tool_id)

        self._add_config(f"""<toolbox tool_path="{self.test_directory}">
    <section id="test_section" name="Test Section">
        <tool file="section_tool_1.xml" />
        <tool file="section_tool_2.xml" />
    </section>
    <tool file="top_level_tool.xml" />
</toolbox>""")

        serial_tool_ids = self._load_tools_serial()
        self._reset_toolbox()
        parallel_tool_ids = self._load_tools_parallel()

        assert serial_tool_ids == parallel_tool_ids
        for tool_id in tool_ids:
            assert tool_id in parallel_tool_ids

    def test_parallel_loading_handles_invalid_tool(self):
        """Verify parallel loading handles invalid tools gracefully."""
        self._create_tool_file("valid_tool")

        invalid_path = os.path.join(self.test_directory, "invalid_tool.xml")
        with open(invalid_path, "w") as f:
            f.write("not valid xml <><><<")

        self._add_config(f"""<toolbox tool_path="{self.test_directory}">
    <tool file="valid_tool.xml" />
    <tool file="invalid_tool.xml" />
</toolbox>""")

        parallel_tool_ids = self._load_tools_parallel()
        assert "valid_tool" in parallel_tool_ids

    def test_parallel_loading_clears_cache(self):
        """Verify pre-loaded tool sources cache is cleared after loading completes."""
        tool_ids = [f"cache_tool_{i}" for i in range(3)]
        for tool_id in tool_ids:
            self._create_tool_file(tool_id)

        tool_refs = "\n".join(f'<tool file="{tool_id}.xml" />' for tool_id in tool_ids)
        self._add_config(f"""<toolbox tool_path="{self.test_directory}">
    {tool_refs}
</toolbox>""")

        self.app.config.parallel_tool_loading = True  # type: ignore[attr-defined]
        self.app.config.parallel_tool_loading_workers = 2  # type: ignore[attr-defined]
        toolbox = self.toolbox

        # Cache should be empty after loading completes
        assert len(toolbox._preloaded_tool_sources) == 0

    def test_parallel_loading_with_nested_sections(self):
        """Verify tools in nested sections load correctly (via on-demand parsing)."""
        tool_ids = ["nested_tool_1", "nested_tool_2", "outer_tool"]
        for tool_id in tool_ids:
            self._create_tool_file(tool_id)

        # Nested sections are not traversed by pre-loading, but tools should still load
        self._add_config(f"""<toolbox tool_path="{self.test_directory}">
    <section id="outer" name="Outer Section">
        <section id="inner" name="Inner Section">
            <tool file="nested_tool_1.xml" />
            <tool file="nested_tool_2.xml" />
        </section>
    </section>
    <tool file="outer_tool.xml" />
</toolbox>""")

        serial_tool_ids = self._load_tools_serial()
        self._reset_toolbox()
        parallel_tool_ids = self._load_tools_parallel()

        # All tools should load regardless of nesting depth
        assert serial_tool_ids == parallel_tool_ids
        for tool_id in tool_ids:
            assert tool_id in parallel_tool_ids
