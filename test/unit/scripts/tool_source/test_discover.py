import sys
import textwrap
from pathlib import Path

galaxy_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(galaxy_root / "lib"))

from galaxy.tools.source_store.discover import (
    discover_tools,
    discover_tools_from_config,
    DiscoveredTool,
)


def _write_conf(tmp_path: Path, body: str) -> tuple[Path, Path]:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "alpha.xml").write_text("<tool id='alpha' version='1.0'><description/></tool>")
    (tools_dir / "beta.xml").write_text("<tool id='beta' version='1.0'><description/></tool>")
    conf = tmp_path / "tool_conf.xml"
    conf.write_text(textwrap.dedent(body).strip())
    return conf, tools_dir


def test_top_level_tool_has_no_section(tmp_path):
    conf, _ = _write_conf(
        tmp_path,
        f"""
        <toolbox tool_path="{tmp_path}/tools">
          <tool file="alpha.xml"/>
        </toolbox>
        """,
    )
    tools = list(discover_tools_from_config(str(conf)))
    assert len(tools) == 1
    assert tools[0].section_id is None
    assert tools[0].section_name is None
    assert tools[0].labels == []


def test_section_stamps_id_and_name(tmp_path):
    conf, _ = _write_conf(
        tmp_path,
        f"""
        <toolbox tool_path="{tmp_path}/tools">
          <section id="ngs" name="NGS Tools">
            <tool file="alpha.xml"/>
            <tool file="beta.xml"/>
          </section>
        </toolbox>
        """,
    )
    tools = {t.path: t for t in discover_tools_from_config(str(conf))}
    assert len(tools) == 2
    for t in tools.values():
        assert t.section_id == "ngs"
        assert t.section_name == "NGS Tools"


def test_labels_attribute_parsed_into_list(tmp_path):
    conf, _ = _write_conf(
        tmp_path,
        f"""
        <toolbox tool_path="{tmp_path}/tools">
          <tool file="alpha.xml" labels="beta, experimental"/>
        </toolbox>
        """,
    )
    tools = list(discover_tools_from_config(str(conf)))
    assert tools[0].labels == ["beta", "experimental"]


def test_hidden_attribute_still_captured(tmp_path):
    conf, _ = _write_conf(
        tmp_path,
        f"""
        <toolbox tool_path="{tmp_path}/tools">
          <tool file="alpha.xml" hidden="true"/>
          <tool file="beta.xml"/>
        </toolbox>
        """,
    )
    by_name = {Path(t.path).name: t for t in discover_tools_from_config(str(conf))}
    assert by_name["alpha.xml"].hidden is True
    assert by_name["beta.xml"].hidden is False


def test_mixed_top_level_and_section(tmp_path):
    conf, _ = _write_conf(
        tmp_path,
        f"""
        <toolbox tool_path="{tmp_path}/tools">
          <tool file="alpha.xml" labels="featured"/>
          <section id="ngs" name="NGS">
            <tool file="beta.xml"/>
          </section>
        </toolbox>
        """,
    )
    by_name = {Path(t.path).name: t for t in discover_tools_from_config(str(conf))}
    assert by_name["alpha.xml"].section_id is None
    assert by_name["alpha.xml"].labels == ["featured"]
    assert by_name["beta.xml"].section_id == "ngs"
    assert by_name["beta.xml"].section_name == "NGS"
    assert by_name["beta.xml"].labels == []


def test_section_propagates_to_tool_dir_walk(tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    nested = tools_dir / "ngs_pack"
    nested.mkdir()
    (nested / "one.xml").write_text("<tool id='one' version='1'><description/></tool>")
    conf = tmp_path / "tool_conf.xml"
    conf.write_text(textwrap.dedent(f"""
            <toolbox tool_path="{tmp_path}/tools">
              <section id="ngs" name="NGS Tools">
                <tool_dir dir="ngs_pack"/>
              </section>
            </toolbox>
            """).strip())
    tools = list(discover_tools_from_config(str(conf)))
    assert len(tools) == 1
    assert tools[0].section_id == "ngs"
    assert tools[0].section_name == "NGS Tools"


def test_dataclass_defaults_are_independent_lists():
    # Regression guard for the field(default_factory=list) wiring on labels —
    # two instances must not share the same underlying list.
    a = DiscoveredTool(path="/a", tool_conf="/c", tool_path=None)
    b = DiscoveredTool(path="/b", tool_conf="/c", tool_path=None)
    a.labels.append("x")
    assert b.labels == []


def test_only_confs_skips_unlisted_conf_walk(tmp_path):
    conf_bodies = {}
    for name in ("a", "b"):
        tool = tmp_path / f"{name}_tool.xml"
        tool.write_text(f'<tool id="{name}" version="1.0"><command>echo</command></tool>')
        conf = tmp_path / f"{name}_conf.xml"
        conf.write_text(f'<toolbox tool_path="{tmp_path}"><tool file="{tool.name}"/></toolbox>')
        conf_bodies[name] = str(conf)

    class _Cfg:
        root = None
        tool_path = str(tmp_path)
        enable_beta_tool_formats = False
        data_manager_config_file = None
        shed_data_manager_config_file = None

        def all_tool_config_files(self):
            return [conf_bodies["a"], conf_bodies["b"]]

    cfg = _Cfg()
    walked = {
        d.tool_conf
        for d in discover_tools(cfg, include_bundled=False, include_converters=False)  # type: ignore[arg-type]
        if d.tool_conf in conf_bodies.values()
    }
    assert walked == set(conf_bodies.values())

    walked = {
        d.tool_conf
        for d in discover_tools(cfg, include_bundled=False, include_converters=False, only_confs={conf_bodies["a"]})  # type: ignore[arg-type]
        if d.tool_conf in conf_bodies.values()
    }
    assert walked == {conf_bodies["a"]}


def test_bundled_compatibility_alias_is_not_a_second_panel_placement(tmp_path):
    tools_dir = tmp_path / "tools"
    bundled_dir = tmp_path / "lib" / "galaxy" / "tools" / "bundled"
    tools_dir.mkdir()
    bundled_dir.mkdir(parents=True)
    tool_source = "<tool id='alpha' version='1.0'><description/></tool>"
    (tools_dir / "alpha.xml").write_text(tool_source)
    (bundled_dir / "alpha.xml").write_text(tool_source)
    conf = tmp_path / "tool_conf.xml"
    conf.write_text(
        f'<toolbox tool_path="{tools_dir}"><section id="section"><tool file="alpha.xml"/></section></toolbox>'
    )

    class _Cfg:
        root = str(tmp_path)
        tool_path = str(tools_dir)
        enable_beta_tool_formats = False
        data_manager_config_file = None
        shed_data_manager_config_file = None

        def all_tool_config_files(self):
            return [str(conf)]

    discoveries = [
        discovered
        for discovered in discover_tools(_Cfg(), include_converters=False)  # type: ignore[arg-type]
        if Path(discovered.path).name == "alpha.xml"
    ]

    assert len(discoveries) == 1
    assert discoveries[0].section_id == "section"
