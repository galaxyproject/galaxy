"""Unit tests for Tool Shed repository installation."""

import logging
from typing import (
    Any,
)
from unittest import mock

import pytest

from galaxy.tool_shed.galaxy_install import install_manager
from galaxy.tool_util.deps.requirements import (
    ToolRequirement,
    ToolRequirements,
)
from galaxy.tool_util.deps.resolvers import DependencyException

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


def _requirements(name: str) -> ToolRequirements:
    return ToolRequirements([ToolRequirement(name=name, type="package", version="1.0")])


def test_dependency_cache_failure_is_isolated_to_requirement_set(caplog):
    irm, _ = _make_install_repository_manager()
    first_requirements = _requirements("first")
    second_requirements = _requirements("second")
    first_tool = mock.MagicMock()
    first_tool.requirements.packages = first_requirements
    duplicate_tool = mock.MagicMock()
    duplicate_tool.requirements.packages = first_requirements
    second_tool = mock.MagicMock()
    second_tool.requirements.packages = second_requirements
    irm.app.toolbox._tools_by_id = {
        "first/tool": first_tool,
        "duplicate/tool": duplicate_tool,
        "second/tool": second_tool,
    }
    irm._view = mock.MagicMock()
    dependency_manager = irm.app.toolbox.dependency_manager
    dependency_manager.cached = True
    dependency_manager.build_cache.side_effect = [DependencyException("cache failed"), None]
    metadata = {"tools": [{"guid": tool_id} for tool_id in irm.app.toolbox._tools_by_id]}

    with caplog.at_level(logging.ERROR, logger=INSTALL_MANAGER_MODULE):
        irm._install_tool_dependencies(metadata)

    assert irm._view.install_dependencies.call_args_list == [
        mock.call(first_requirements),
        mock.call(second_requirements),
    ]
    assert dependency_manager.build_cache.call_args_list == [
        mock.call(first_requirements),
        mock.call(second_requirements),
    ]
    assert "first/tool, duplicate/tool" in caplog.text
    assert "repository installation will continue" in caplog.text


def test_unexpected_dependency_cache_failure_is_not_suppressed():
    irm, _ = _make_install_repository_manager()
    requirements = _requirements("package")
    tool = mock.MagicMock()
    tool.requirements.packages = requirements
    irm.app.toolbox._tools_by_id = {"example/tool": tool}
    irm._view = mock.MagicMock()
    dependency_manager = irm.app.toolbox.dependency_manager
    dependency_manager.cached = True
    dependency_manager.build_cache.side_effect = RuntimeError("unexpected")

    with pytest.raises(RuntimeError, match="unexpected"):
        irm._install_tool_dependencies({"tools": [{"guid": "example/tool"}]})
