"""``populate_store`` run statistics, which the CLI turns into its exit code."""

import tempfile

from galaxy.tools.source_store.populator import populate_store
from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore

_TOOL_XML = """<tool id="{id}" name="Tool" version="1.0">
  <command>echo</command>
  <inputs/>
  <outputs/>
</tool>
"""

# Parses, but without an id there is nothing to index the tool under.
_TOOL_XML_WITHOUT_ID = """<tool name="No Id" version="1.0">
  <command>echo</command>
  <inputs/>
  <outputs/>
</tool>
"""


def test_tool_left_out_of_the_index_counts_as_error(tmp_path, monkeypatch):
    # Loading the Galaxy config points tempfile.tempdir into its data_dir.
    monkeypatch.setattr(tempfile, "tempdir", tempfile.tempdir)
    (tmp_path / "good.xml").write_text(_TOOL_XML.format(id="good"))
    (tmp_path / "no_id.xml").write_text(_TOOL_XML_WITHOUT_ID)
    tool_conf = tmp_path / "tool_conf.xml"
    tool_conf.write_text(
        f'<toolbox store="bundle" tool_path="{tmp_path}"><section id="s" name="S">'
        '<tool file="good.xml"/><tool file="no_id.xml"/>'
        "</section></toolbox>"
    )
    store_url = f"sqlite:///{tmp_path / 'bundle.sqlite'}"
    galaxy_yml = tmp_path / "galaxy.yml"
    galaxy_yml.write_text(
        "galaxy:\n"
        f"  data_dir: {tmp_path / 'data'}\n"
        f"  tool_config_file: {tool_conf}\n"
        f"  tool_source_database_connection: sqlite:///{tmp_path / 'default.sqlite'}\n"
        f"  tool_source_stores:\n    bundle:\n      url: {store_url}\n"
    )

    stats = populate_store(config_file=str(galaxy_yml), parallel=1, target="bundle")

    index = SqlAlchemyToolSourceStore(url=store_url).load_index()
    assert index is not None
    assert set(index.entries) == {"good"}
    assert stats["errors"] == 1
