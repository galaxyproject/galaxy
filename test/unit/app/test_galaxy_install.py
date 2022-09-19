"""Test installation using galaxy.tool_shed package.

It should be able to quickly test installing things from the real tool shed
and from bootstrapped tool sheds.
"""
from pathlib import Path
from typing import (
    Any,
    Dict,
)

from galaxy.model.tool_shed_install import ToolShedRepository
from galaxy.tool_shed.galaxy_install.client import InstallationTarget
from galaxy.tool_shed.galaxy_install.install_manager import InstallRepositoryManager
from galaxy.tool_shed.galaxy_install.installed_repository_manager import InstalledRepositoryManager
from galaxy.tool_shed.unittest_utils import StandaloneInstallationTarget
from galaxy.tool_shed.util.repository_util import check_for_updates
from galaxy.util.tool_shed.tool_shed_registry import DEFAULT_TOOL_SHED_URL


def test_against_production_shed(tmp_path: Path):
    repo_owner = "iuc"
    repo_name = "collection_column_join"
    repo_revision = "dfde09461b1e"

    install_target: InstallationTarget = StandaloneInstallationTarget(tmp_path)
    install_manager = InstallRepositoryManager(install_target)
    install_options: Dict[str, Any] = {}
    install_manager.install(
        DEFAULT_TOOL_SHED_URL,
        repo_name,
        repo_owner,
        repo_revision,  # revision 2, a known installable revision
        install_options,
    )
    with open(tmp_path / "shed_conf.xml", "r") as f:
        assert "toolshed.g2.bx.psu.edu/repos/iuc/collection_column_join/collection_column_join/0.0.2" in f.read()
    repo_path = tmp_path / "tools" / "toolshed.g2.bx.psu.edu" / "repos" / repo_owner / repo_name / repo_revision
    assert repo_path.exists()

    install_model_context = install_target.install_model.context
    query = install_model_context.query(ToolShedRepository).where(ToolShedRepository.name == repo_name)
    tsr = query.first()
    assert tsr
    message, status = check_for_updates(
        install_target.tool_shed_registry,
        install_model_context,
        tsr.id,
    )
    assert status

    irm = InstalledRepositoryManager(install_target)
    errors = irm.uninstall_repository(repository=tsr, remove_from_disk=True)
    assert not errors

    with open(tmp_path / "shed_conf.xml", "r") as f:
        assert "toolshed.g2.bx.psu.edu/repos/iuc/collection_column_join/collection_column_join/0.0.2" not in f.read()

    repo_path = tmp_path / "tools" / "toolshed.g2.bx.psu.edu" / "repos" / repo_owner / repo_name / repo_revision
    assert not repo_path.exists()
