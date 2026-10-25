from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest
from lxml.etree import XMLSyntaxError

from galaxy.app import (
    GalaxyManagerApplication,
    MinimalGalaxyApplication,
    UniverseApplication,
)
from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.config import GalaxyAppConfiguration
from galaxy.config_watchers import ConfigWatchers
from galaxy.queue_worker import reload_tool_data_tables
from galaxy.tool_util.data import ToolDataTableManager
from galaxy.tools.parameters.dynamic_options import DynamicOptions
from galaxy.tools.parameters.options import ParameterOption
from galaxy.util import XML
from galaxy.util.bunch import Bunch
from galaxy.work.context import WorkRequestContext
from .test_data_manager_reload import _data_manager


def write_config(tmp_path, source, rows="", table_name="references"):
    loc = tmp_path / f"{source}.loc"
    loc.write_text(rows)
    config = tmp_path / f"{source}.xml"
    config.write_text(f"""<tables><table name="{table_name}">
      <columns>value, name, path</columns><file path="{loc}" />
    </table></tables>""")
    return config


def make_app(tmp_path, sources, managed=None, app_type=UniverseApplication):
    kwds = dict(
        override_tempdir=False,
        config_dir=str(tmp_path),
        managed_config_dir=str(tmp_path / "managed"),
        tool_data_path=str(tmp_path),
        tool_data_table_config_path=[str(p) for p in sources],
    )
    if managed is not None:
        kwds["shed_tool_data_table_config"] = str(managed)
    app = Mock(spec=app_type, config=GalaxyAppConfiguration(**kwds), queue_worker=Mock())
    if app_type is UniverseApplication:
        app.watchers = Mock()
    # Bind the application hook as well as exercising the real startup path.
    application = cast(MinimalGalaxyApplication, app)
    app._tool_data_tables_registered = lambda names: MinimalGalaxyApplication._tool_data_tables_registered(
        application, names
    )
    MinimalGalaxyApplication._configure_tool_data_tables(application, from_shed_config=False)
    app.tool_data_tables = app._tool_data_tables
    return app


def paths(app):
    return [row[2] for row in app.tool_data_tables["references"].data]


def test_live_registration_and_peer_reload_follow_source_order(tmp_path):
    local = write_config(tmp_path, "local")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    external = write_config(tmp_path, "external", "hg38\tHuman\t/external\n")
    sources = [local, managed, external]
    app = make_app(tmp_path, sources, managed)
    peer = make_app(tmp_path, sources, managed)
    table = app.tool_data_tables["references"]
    version = table._loaded_content_version
    incoming = write_config(tmp_path, "incoming", "hg38\tHuman\t/managed\n")
    elems, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert not error
    assert elems
    assert paths(app) == ["/managed", "/external"]
    assert app.tool_data_tables["references"] is table
    assert not table.is_current_version(version)
    reload_tool_data_tables(peer, table_name="references")
    assert paths(peer) == paths(app) == paths(make_app(tmp_path, sources, managed))


@pytest.mark.parametrize("managed_first", [False, True])
def test_omitted_managed_legacy_order_and_admin_reordering(tmp_path, managed_first):
    local = write_config(tmp_path, "local", "hg38\tHuman\t/local\n")
    managed = write_config(tmp_path, "managed", "hg38\tHuman\t/managed\n")
    external = write_config(tmp_path, "external", "hg38\tHuman\t/external\n")
    sources = [managed, local, external] if managed_first else [local, external]
    app = make_app(tmp_path, sources, managed)
    expected = ["/managed", "/local", "/external"] if managed_first else ["/local", "/external", "/managed"]
    assert paths(app) == expected
    app.tool_data_tables.reload_tables()
    assert paths(app) == expected
    assert app.tool_data_tables["references"].get_field("hg38")["path"] == expected[0]


@pytest.mark.parametrize("explicit", [False, True])
def test_missing_default_reserves_position_for_registration(tmp_path, explicit):
    managed_dir = tmp_path / "managed"
    managed_dir.mkdir()
    managed = managed_dir / "shed_tool_data_table_conf.xml"
    external = write_config(tmp_path, "external", "hg38\tHuman\t/external\n")
    sources = [managed, external] if explicit else [external]
    app = make_app(tmp_path, sources)
    peer = make_app(tmp_path, sources)
    incoming = write_config(tmp_path, "incoming", "hg38\tHuman\t/managed\n")
    _, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert not error
    assert managed.exists()
    expected = ["/managed", "/external"] if explicit else ["/external", "/managed"]
    assert paths(app) == expected
    reload_tool_data_tables(peer)
    assert paths(peer) == paths(make_app(tmp_path, sources)) == expected


@pytest.mark.parametrize("missing_managed", [False, True])
def test_explicit_missing_configs_are_errors(tmp_path, missing_managed):
    managed = tmp_path / "custom.xml"
    local = write_config(tmp_path, "local")
    if not missing_managed:
        managed.write_text("<tables />")
        local.unlink()
    with pytest.raises(FileNotFoundError):
        make_app(tmp_path, [local, managed], managed)


@pytest.mark.parametrize("write_alias", [False, True])
def test_aliases_preserve_xml_relative_paths_and_different_config_bases(tmp_path, write_alias):
    managed_dir = tmp_path / "managed"
    managed_dir.mkdir()
    managed = managed_dir / "tables.xml"
    managed.write_text("""<tables><table name="references"><columns>value, name, path</columns>
      <file path="${__HERE__}/index.loc" /></table></tables>""")
    (managed_dir / "index.loc").write_text("hg38\tHuman\t/wrong-base\n")
    (tmp_path / "index.loc").write_text("hg38\tHuman\t/alias-base\n")
    alias = tmp_path / "alias.xml"
    alias.symlink_to(managed)
    external = write_config(tmp_path, "external", "hg38\tHuman\t/external\n")
    # The source alias is relative to config_dir, the write destination to managed_config_dir.
    destination = "../alias.xml" if write_alias else "tables.xml"
    app = make_app(tmp_path, ["alias.xml", external, managed], destination)
    assert paths(app) == ["/alias-base", "/external"]
    assert len(app.tool_data_tables["references"]._merged_load_info) == 1
    incoming = write_config(tmp_path, "incoming", "mm10\tMouse\t/new\n")
    _, error = app.tool_data_tables.add_new_entries_from_config_file(
        incoming, None, app.config.shed_tool_data_table_config, persist=True
    )
    assert not error
    assert alias.is_symlink()
    assert paths(app) == ["/alias-base", "/new", "/external"]
    assert paths(make_app(tmp_path, ["alias.xml", external, managed], destination)) == paths(app)


@pytest.mark.parametrize("reload_kind", ["targeted", "all", "path"])
def test_new_table_registration_notifies_peers_and_updates_watchers(tmp_path, reload_kind):
    local = write_config(tmp_path, "local")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    app = make_app(tmp_path, [local, managed], managed)
    peer = make_app(tmp_path, [local, managed], managed)
    incoming = write_config(tmp_path, "incoming", "hg38\tHuman\t/new\n", table_name="new_table")
    _, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert not error
    app.queue_worker.send_control_task.assert_called_once_with(
        "reload_tool_data_tables", noop_self=True, kwargs={"table_name": ["new_table"]}
    )
    app.watchers.update_watch_data_table_paths.assert_called_once()
    kwds = {"table_name": "new_table"} if reload_kind == "targeted" else {}
    if reload_kind == "path":
        kwds = {"path": str(tmp_path / "incoming.loc")}
    reload_tool_data_tables(peer, **kwds)
    assert peer.tool_data_tables["new_table"].data == app.tool_data_tables["new_table"].data
    peer.watchers.update_watch_data_table_paths.assert_called_once()


def test_multi_table_registration_sends_one_peer_reload(tmp_path):
    local = write_config(tmp_path, "local", "hg38\tHuman\t/local\n")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    app = make_app(tmp_path, [local, managed], managed)
    peer = make_app(tmp_path, [local, managed], managed)
    loc = tmp_path / "incoming.loc"
    loc.write_text("mm10\tMouse\t/new\n")
    incoming = tmp_path / "incoming.xml"
    incoming.write_text(f"""<tables>
      <table name="references"><columns>value, name, path</columns><file path="{loc}" /></table>
      <table name="new_table"><columns>value, name, path</columns><file path="{loc}" /></table>
    </tables>""")
    _, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert not error
    app.queue_worker.send_control_task.assert_called_once_with(
        "reload_tool_data_tables", noop_self=True, kwargs={"table_name": ["references", "new_table"]}
    )
    reload_tool_data_tables(peer, **app.queue_worker.send_control_task.call_args.kwargs["kwargs"])
    assert paths(peer) == paths(app) == ["/local", "/new"]
    assert peer.tool_data_tables["new_table"].data == app.tool_data_tables["new_table"].data


def test_registration_preserves_read_only_external_sources_and_data_manager_order(tmp_path):
    local = write_config(tmp_path, "local", "")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    external = write_config(tmp_path, "external", "hg38\tHuman\t/external\n")
    external_loc = tmp_path / "external.loc"
    originals = {p: p.read_bytes() for p in (local, external, external_loc)}
    external.chmod(0o444)
    external_loc.chmod(0o444)
    sources = [local, managed, external]
    app = make_app(tmp_path, sources, managed)
    peer = make_app(tmp_path, sources, managed)
    incoming = write_config(tmp_path, "incoming", "hg38\tHuman\t/managed\n")
    _, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert not error
    table = app.tool_data_tables["references"]
    table.add_entry(["hg38", "Human", "/local"], persist=True, tool_data_file_path=str(tmp_path / "local.loc"))
    data_manager, _ = _data_manager(app.tool_data_tables)
    data_manager._reload(["references"])
    reload_tool_data_tables(peer, table_name="references")
    assert (
        paths(app) == paths(peer) == paths(make_app(tmp_path, sources, managed)) == ["/local", "/managed", "/external"]
    )
    table.reload_from_files()
    assert paths(app) == ["/local", "/managed", "/external"]
    for p, contents in originals.items():
        assert p.read_bytes() == contents
    assert external.stat().st_mode & 0o777 == 0o444
    assert external_loc.stat().st_mode & 0o777 == 0o444


def test_invalid_registration_changes_neither_disk_nor_live_tables(tmp_path):
    local = write_config(tmp_path, "local", "hg38\tHuman\t/local\n")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    app = make_app(tmp_path, [local, managed], managed)
    table = app.tool_data_tables["references"]
    version = table._loaded_content_version
    incoming = tmp_path / "invalid.xml"
    incoming.write_text("""<tables>
      <table name="new_table"><columns>value, name, path</columns></table>
      <table name="references"><columns>value, name, version, path</columns></table>
    </tables>""")
    elems, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert not elems
    assert "conflicting columns" in error
    assert managed.read_text() == "<tables />"
    assert "new_table" not in app.tool_data_tables
    assert table.is_current_version(version)
    assert paths(app) == ["/local"]
    app.queue_worker.send_control_task.assert_not_called()


def test_failed_write_does_not_publish_registration(tmp_path, monkeypatch):
    local = write_config(tmp_path, "local", "hg38\tHuman\t/local\n")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    app = make_app(tmp_path, [managed, local], managed)
    incoming = write_config(tmp_path, "incoming", "hg38\tHuman\t/managed\n")
    monkeypatch.setattr(app.tool_data_tables, "to_xml_file", Mock(side_effect=OSError("write failed")))
    with pytest.raises(OSError, match="write failed"):
        app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert paths(app) == ["/local"]
    app.queue_worker.send_control_task.assert_not_called()


@pytest.mark.parametrize("version", ["1", "2", "3"])
def test_ordered_sources_retain_version_filtered_rows(tmp_path, version):
    configs = []
    for source, index in (("local", "1"), ("managed", "2"), ("external", "3")):
        conf = write_config(tmp_path, source, f"hg38\tHuman\t{index}\t/{source}\n")
        conf.write_text(conf.read_text().replace("value, name, path", "value, name, version, path"))
        configs.append(conf)
    configured = make_app(tmp_path, configs, configs[1])
    app = MockApp()
    app.tool_data_tables = configured.tool_data_tables
    options = DynamicOptions(
        XML(f"""<options from_data_table="references">
          <filter type="static_value" column="version" value="{version}" />
        </options>"""),
        Bunch(tool=Bunch(app=app)),
    )
    trans = WorkRequestContext(app=app)
    expected = {"1": "/local", "2": "/managed", "3": "/external"}[version]
    for _ in range(2):
        assert options.get_options(trans, {}) == [ParameterOption("Human", "hg38", False)]
        assert options.get_field_by_name_for_value("path", "hg38", trans, {}) == [expected]
        app.tool_data_tables.reload_tables("references")


def test_xml_definition_file_and_row_order_survive_reload(tmp_path):
    managed = write_config(tmp_path, "managed", "hg38\tHuman\t/managed\n")
    external = write_config(tmp_path, "external", "hg38\tHuman\t/external\n")
    first = tmp_path / "first.loc"
    second = tmp_path / "second.loc"
    first.write_text("hg38\tHuman\t/first\nmm10\tMouse\t/second\n")
    second.write_text("hg38\tHuman\t/third\nmm10\tMouse\t/second\n")
    local = tmp_path / "local.xml"
    local.write_text(f"""<tables>
      <table name="references"><columns>value, name, path</columns>
        <file path="{first}" /><file path="{second}" /></table>
      <table name="references"><columns>value, name, path</columns>
        <file path="{tmp_path / 'managed.loc'}" /></table>
    </tables>""")
    app = make_app(tmp_path, [local, managed, external], managed)
    expected = ["/first", "/second", "/third", "/second", "/managed", "/external"]
    # The first definition's within-file duplicate policy remains unchanged;
    # identical rows merged from subsequent definitions are skipped.
    assert paths(app) == expected
    app.tool_data_tables.reload_tables()
    assert paths(app) == expected


def test_watchers_discover_new_location_directories_with_reload_callback(tmp_path, tmp_path_factory):
    local = write_config(tmp_path, "local")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    app = make_app(tmp_path, [local, managed], managed)
    watcher = Mock(monitored_dirs={str(tmp_path): True})
    watcher.watch_directory.side_effect = lambda directory, **kwds: watcher.monitored_dirs.update({directory: True})
    watchers = ConfigWatchers.__new__(ConfigWatchers)
    watchers.app = app
    watchers.tool_data_watcher = watcher
    app.watchers = watchers
    outside = tmp_path_factory.mktemp("new_locations")
    nested = tmp_path / "nested"
    nested.mkdir()
    for directory, table_name in ((outside, "outside_table"), (nested, "nested_table")):
        incoming = write_config(directory, "incoming", "hg38\tHuman\t/new\n", table_name=table_name)
        _, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
        assert not error
    watched = [call.args[0] for call in watcher.watch_directory.call_args_list]
    assert str(nested) not in watched
    calls = [call for call in watcher.watch_directory.call_args_list if call.args == (str(outside),)]
    assert len(calls) == 1
    assert calls[0].kwargs["require_extensions"] == (".loc",)
    assert calls[0].kwargs["recursive"] is False
    calls[0].kwargs["callback"](str(outside / "incoming.loc"))
    app.queue_worker.send_control_task.assert_called_with(
        "reload_tool_data_tables", kwargs={"path": str(outside / "incoming.loc")}
    )


def test_nonpersistent_parser_keeps_transient_definitions(tmp_path):
    local = write_config(tmp_path, "local", "hg38\tHuman\t/local\n")
    manager = ToolDataTableManager(str(tmp_path), local)
    incoming = write_config(tmp_path, "incoming", "hg38\tHuman\t/transient\n")
    destination = tmp_path / "unwritten.xml"
    _, error = manager.add_new_entries_from_config_file(incoming, None, destination)
    assert not error
    assert not destination.exists()
    manager.reload_tables()
    assert [row[2] for row in manager["references"].data] == ["/local", "/transient"]


def test_failed_reload_keeps_table_state_and_notifies_after_persist(tmp_path, monkeypatch):
    local = write_config(tmp_path, "local", "hg38\tHuman\t/local\n")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    app = make_app(tmp_path, [local, managed], managed)
    table = app.tool_data_tables["references"]
    version = table._loaded_content_version
    managed.write_text("<broken")
    with pytest.raises(XMLSyntaxError):
        app.tool_data_tables.reload_tables()
    assert table.is_current_version(version)
    assert paths(app) == ["/local"]
    managed.write_text("<tables />")
    incoming = write_config(tmp_path, "incoming", "hg38\tHuman\t/new\n")
    monkeypatch.setattr(app.tool_data_tables, "reload_tables", Mock(side_effect=OSError("reload failed")))
    elems, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert elems
    assert error == "Registered incoming.xml but reloading data tables failed: reload failed"
    assert "incoming.loc" in managed.read_text()
    assert paths(app) == ["/local"]
    app.queue_worker.send_control_task.assert_called_once_with(
        "reload_tool_data_tables", noop_self=True, kwargs={"table_name": ["references"]}
    )


def test_registration_and_reload_without_application_watchers(tmp_path):
    local = write_config(tmp_path, "local", "hg38\tHuman\t/local\n")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    app = make_app(tmp_path, [managed, local], managed, app_type=GalaxyManagerApplication)
    peer = make_app(tmp_path, [managed, local], managed, app_type=GalaxyManagerApplication)
    incoming = write_config(tmp_path, "incoming", "hg38\tHuman\t/managed\n")
    _, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert not error
    app.queue_worker.send_control_task.assert_called_once_with(
        "reload_tool_data_tables", noop_self=True, kwargs={"table_name": ["references"]}
    )
    reload_tool_data_tables(peer, table_name="references")
    assert paths(app) == paths(peer) == ["/managed", "/local"]


def test_path_reload_does_not_download_unrelated_tables(tmp_path, monkeypatch):
    download = Mock(return_value=Mock(text="remote\tRemote\t/remote\n"))
    monkeypatch.setattr("galaxy.tool_util.data.requests.get", download)
    local = write_config(tmp_path, "local", "hg38\tHuman\t/local\n")
    remote = tmp_path / "remote.xml"
    remote.write_text("""<tables><table name="remote"><columns>value, name, path</columns>
      <file url="https://example.org/references.loc" /></table></tables>""")
    app = make_app(tmp_path, [local, remote])
    remote_table = app.tool_data_tables["remote"]
    remote_version = remote_table._loaded_content_version
    (tmp_path / "local.loc").write_text("hg38\tHuman\t/updated\n")
    app.tool_data_tables.reload_tables(path=str(tmp_path / "local.loc"))
    assert paths(app) == ["/updated"]
    download.assert_called_once()
    assert remote_table.is_current_version(remote_version)


def test_url_downloads_are_not_watched_but_missing_location_files_are(tmp_path, monkeypatch):
    monkeypatch.setattr("galaxy.tool_util.data.requests.get", Mock(return_value=Mock(text="remote\tRemote\t/remote\n")))
    location_dir = tmp_path / "locations"
    location_dir.mkdir()
    config = tmp_path / "remote.xml"
    config.write_text(f"""<tables><table name="remote"><columns>value, name, path</columns>
      <file url="https://example.org/references.loc" />
      <file path="{location_dir / 'missing.loc'}" /></table></tables>""")
    app = make_app(tmp_path, [config])
    watchers = ConfigWatchers.__new__(ConfigWatchers)
    watchers.app = app
    temporary_filename = next(iter(app.tool_data_tables["remote"].filenames))
    assert not Path(temporary_filename).exists()
    assert str(Path(temporary_filename).parent) not in watchers.tool_data_paths
    assert str(location_dir) in watchers.tool_data_paths


@pytest.mark.parametrize("reload_existing_first", [False, True])
def test_path_reload_discovers_new_table_using_an_already_known_file(tmp_path, reload_existing_first):
    local = write_config(tmp_path, "local", "hg38\tHuman\t/local\n")
    managed = tmp_path / "managed.xml"
    managed.write_text("<tables />")
    app = make_app(tmp_path, [managed, local], managed)
    peer = make_app(tmp_path, [managed, local], managed)
    incoming = tmp_path / "incoming.xml"
    incoming.write_text(local.read_text().replace('name="references"', 'name="new_table"'))
    _, error = app.tool_data_tables.add_new_entries_from_config_file(incoming, None, managed, persist=True)
    assert not error
    if reload_existing_first:
        reload_tool_data_tables(peer, table_name="references")
        assert "new_table" not in peer.tool_data_tables
    reload_tool_data_tables(peer, path=str(tmp_path / "local.loc"))
    assert peer.tool_data_tables["new_table"].data == app.tool_data_tables["new_table"].data
    assert paths(peer) == paths(app)
