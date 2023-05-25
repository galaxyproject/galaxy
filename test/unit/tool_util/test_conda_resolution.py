import os
import shutil
from tempfile import mkdtemp

from galaxy.tool_util.deps import DependencyManager
from galaxy.tool_util.deps.conda_util import (
    best_search_result,
    CondaContext,
    CondaTarget,
    install_conda,
    installed_conda_targets,
)
from galaxy.tool_util.deps.requirements import ToolRequirement
from galaxy.tool_util.deps.resolvers.conda import CondaDependencyResolver
from .util import external_dependency_management


@external_dependency_management
def test_conda_resolution():
    base_path = mkdtemp()
    try:
        job_dir = os.path.join(base_path, "000")
        dependency_manager = DependencyManager(base_path)
        resolver = CondaDependencyResolver(
            dependency_manager,
            auto_init=True,
            auto_install=True,
            use_path_exec=False,  # For the test ensure this is always a clean install
        )
        resolver.read_only = True
        req = ToolRequirement(name="samtools", version=None, type="package")
        dependency = resolver.resolve(req, job_directory=job_dir)
        assert dependency.shell_commands() is None

        resolver.read_only = False
        req = ToolRequirement(name="samtools", version=None, type="package")
        dependency = resolver.resolve(req, job_directory=job_dir)
        assert dependency.shell_commands() is not None
    finally:
        shutil.rmtree(base_path)


@external_dependency_management
def test_against_conda_prefix_regression():
    """Test that would fail if https://github.com/rtfd/readthedocs.org/issues/1902 regressed."""

    base_path = mkdtemp(prefix="x" * 80)  # a ridiculously long prefix
    try:
        job_dir = os.path.join(base_path, "000")
        dependency_manager = DependencyManager(base_path)
        resolver = CondaDependencyResolver(
            dependency_manager,
            auto_init=True,
            auto_install=True,
            use_path_exec=False,  # For the test ensure this is always a clean install
        )
        conda_context = resolver.conda_context
        assert len(list(installed_conda_targets(conda_context))) == 0
        req = ToolRequirement(name="samtools", version="0.1.16", type="package")
        dependency = resolver.resolve(req, job_directory=job_dir)
        assert dependency.shell_commands() is not None  # install should not fail anymore
        installed_targets = list(installed_conda_targets(conda_context))
        assert len(installed_targets) > 0
    finally:
        shutil.rmtree(base_path)


@external_dependency_management
def test_best_search_result(tmp_path) -> None:
    conda_context = CondaContext(
        conda_prefix=os.path.join(tmp_path, "_conda"), condarc_override=os.path.join(tmp_path, "_condarc")
    )
    install_conda(conda_context)
    (hit, exact) = best_search_result(CondaTarget("samtools"), conda_context)
    assert hit["name"] == "samtools"
    assert exact is True
    (hit, exact) = best_search_result(CondaTarget("samtools", version="1.3.1"), conda_context)
    assert hit["name"] == "samtools"
    assert hit["version"] == "1.3.1"
    assert exact is True
    # Search non-existent version
    (hit, exact) = best_search_result(CondaTarget("samtools", version="1.16"), conda_context)
    assert hit["name"] == "samtools"
    assert exact is False
