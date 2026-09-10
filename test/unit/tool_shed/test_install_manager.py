"""Unit tests for install-time data table registration gating."""

from typing import (
    Any,
)
from unittest import mock

from galaxy.tool_shed.galaxy_install import install_manager

INSTALL_MANAGER_MODULE = "galaxy.tool_shed.galaxy_install.install_manager"


def _make_install_repository_manager():
    app = mock.MagicMock(name="app")
    app.install_model.context = mock.MagicMock(name="session")
    register_mock = mock.MagicMock(name="add_new_entries_from_config_file")
    app.tool_data_tables.add_new_entries_from_config_file = register_mock
    irm = install_manager.InstallRepositoryManager.__new__(install_manager.InstallRepositoryManager)
    irm.app = app
    irm.install_model = app.install_model
    irm.tpm = mock.MagicMock(name="tpm")
    return irm, register_mock


def _invoke_handle(irm, metadata_dict: dict[str, Any], repository_tools_tups: list[Any]):
    irmm_instance = mock.MagicMock(name="irmm_instance")
    irmm_instance.get_metadata_dict.return_value = metadata_dict
    irmm_instance.get_repository_tools_tups.return_value = repository_tools_tups

    stdtm_instance = mock.MagicMock(name="stdtm_instance")
    stdtm_instance.get_tool_index_sample_files.return_value = []
    stdtm_instance.install_tool_data_tables.return_value = (
        "/dev/null/tool_data_table_conf.xml",
        [object()],
    )
    stdtm_instance.handle_missing_data_table_entry.side_effect = lambda *_a, **_k: repository_tools_tups

    patches = [
        mock.patch(f"{INSTALL_MANAGER_MODULE}.InstalledRepositoryMetadataManager", return_value=irmm_instance),
        mock.patch(f"{INSTALL_MANAGER_MODULE}.ShedToolDataTableManager", return_value=stdtm_instance),
        mock.patch(
            f"{INSTALL_MANAGER_MODULE}.repository_util.get_tool_shed_status_for_installed_repository", return_value=None
        ),
        mock.patch(f"{INSTALL_MANAGER_MODULE}.tool_util.copy_sample_files"),
        mock.patch(
            f"{INSTALL_MANAGER_MODULE}.tool_util.handle_missing_index_file",
            side_effect=lambda *_a, **_k: (repository_tools_tups, []),
        ),
        mock.patch(f"{INSTALL_MANAGER_MODULE}.data_manager.DataManagerHandler"),
    ]
    for p in patches:
        p.start()
    try:
        repo = mock.MagicMock(name="tool_shed_repository")
        repo.changeset_revision = "abc"
        repo.installed_changeset_revision = "abc"
        irm._InstallRepositoryManager__handle_repository_contents(
            tool_shed_repository=repo,
            tool_path="/tmp/tool_path",
            repository_clone_url="http://tool-shed/repos/owner/name",
            relative_install_dir="owner/name/abc",
            tool_shed="tool-shed",
            tool_section=None,
            shed_tool_conf=None,
        )
    finally:
        for p in patches:
            p.stop()
    return stdtm_instance


def test_non_data_manager_repo_registers_sample_files():
    irm, register_mock = _make_install_repository_manager()
    stdtm_instance = _invoke_handle(irm, {"sample_files": ["foo.loc.sample"]}, [])
    stdtm_instance.install_tool_data_tables.assert_called_once()
    register_mock.assert_called_once()


def test_data_manager_repo_registers_sample_files():
    irm, register_mock = _make_install_repository_manager()
    metadata = {
        "sample_files": ["foo.loc.sample"],
        "tools": [{"id": "t"}],
        "data_manager": {"data_managers": {}},
    }
    fake_tup = (mock.MagicMock(), "guid", mock.MagicMock())
    stdtm_instance = _invoke_handle(irm, metadata, [fake_tup])
    stdtm_instance.install_tool_data_tables.assert_called_once()
    register_mock.assert_called_once()


def test_non_data_manager_repo_skips_handle_missing_data_table_entry():
    irm, _ = _make_install_repository_manager()
    metadata = {"tools": [{"id": "t"}], "sample_files": []}
    fake_tup = (mock.MagicMock(), "guid", mock.MagicMock())
    stdtm_instance = _invoke_handle(irm, metadata, [fake_tup])
    stdtm_instance.handle_missing_data_table_entry.assert_not_called()


def test_data_manager_repo_invokes_handle_missing_data_table_entry():
    irm, _ = _make_install_repository_manager()
    metadata = {
        "tools": [{"id": "t"}],
        "sample_files": [],
        "data_manager": {"data_managers": {}},
    }
    fake_tup = (mock.MagicMock(), "guid", mock.MagicMock())
    stdtm_instance = _invoke_handle(irm, metadata, [fake_tup])
    stdtm_instance.handle_missing_data_table_entry.assert_called_once()
