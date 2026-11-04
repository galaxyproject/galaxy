from galaxy.tool_util.toolbox.lineages.interface import ToolLineage


def test_lineage_orders_galaxy_suffix_numerically():
    lineage = ToolLineage("toolshed.example.org/repos/owner/repo/tool_id/1.4.0+galaxy8")
    for version in ["1.4.0+galaxy8", "1.4.0+galaxy10", "1.4.0+galaxy9"]:
        lineage.register_version(version)
    assert list(lineage.tool_versions) == ["1.4.0+galaxy8", "1.4.0+galaxy9", "1.4.0+galaxy10"]
    assert lineage.get_version_ids() == [
        "toolshed.example.org/repos/owner/repo/tool_id/1.4.0+galaxy8",
        "toolshed.example.org/repos/owner/repo/tool_id/1.4.0+galaxy9",
        "toolshed.example.org/repos/owner/repo/tool_id/1.4.0+galaxy10",
    ]
