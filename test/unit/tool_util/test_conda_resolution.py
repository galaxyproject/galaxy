import os.path
import tempfile

from galaxy.tool_util.deps import DependencyManager
from galaxy.tool_util.deps.conda_util import (
    CondaContext,
    install_conda,
    installed_conda_targets,
)
from galaxy.tool_util.deps.requirements import ToolRequirement
from galaxy.tool_util.deps.resolvers.conda import (
    CondaDependencyResolver,
    DEFAULT_ENSURE_CHANNELS,
)
from .util import external_dependency_management


@external_dependency_management
def test_install_conda_build(tmp_path) -> None:
    conda_prefix = os.path.join(tmp_path, "miniconda3")
    cc = CondaContext(conda_prefix=conda_prefix, ensure_channels=DEFAULT_ENSURE_CHANNELS)
    assert not cc.is_conda_installed()
    assert install_conda(cc, force_conda_build=True) == 0
    assert cc.is_conda_installed()
    assert cc.conda_build_available


@external_dependency_management
def test_conda_resolution(tmp_path) -> None:
    job_dir = os.path.join(tmp_path, "000")
    dependency_manager = DependencyManager(tmp_path)
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


@external_dependency_management
def test_against_conda_prefix_regression() -> None:
    """Test that would fail if https://github.com/rtfd/readthedocs.org/issues/1902 regressed."""
    with tempfile.TemporaryDirectory(prefix="x" * 80) as base_path:  # a ridiculously long prefix
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
