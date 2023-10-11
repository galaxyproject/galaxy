import os.path
import tempfile

import pytest

from galaxy.tool_util.deps import DependencyManager
from galaxy.tool_util.deps.conda_util import (
    best_search_result,
    CondaContext,
    CondaTarget,
    install_conda,
    installed_conda_targets,
)
from galaxy.tool_util.deps.requirements import (
    ToolRequirement,
    ToolRequirements,
)
from galaxy.tool_util.deps.resolvers import NullDependency
from galaxy.tool_util.deps.resolvers.conda import (
    CondaDependency,
    CondaDependencyResolver,
    DEFAULT_ENSURE_CHANNELS,
    MergedCondaDependency,
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


@pytest.fixture(scope="module")
def resolver(tmp_path_factory):
    dependency_manager = DependencyManager(tmp_path_factory.mktemp("dependencies"))
    return CondaDependencyResolver(
        dependency_manager,
        auto_init=True,
        auto_install=True,
        use_path_exec=False,  # For the test ensure this is always a clean install
    )


@external_dependency_management
def test_single_package_resolution(resolver: CondaDependencyResolver) -> None:
    # Test that a read-only resolver returns a NullDependency
    resolver.read_only = True
    package_name = "eXpress"
    req = ToolRequirement(name=package_name, version=None, type="package")
    dependency = resolver.resolve(req)
    assert isinstance(dependency, NullDependency)
    assert dependency.shell_commands() is None

    # Test that a (fake) environment generated from a non-lowercase package name
    # is still accepted by the resolver
    env_path = resolver.conda_context.env_path(f"__{package_name}@_uv_")
    os.mkdir(env_path)
    dependency = resolver.resolve(req)
    assert isinstance(dependency, CondaDependency)
    assert dependency.name == package_name
    assert dependency.version is None
    assert dependency.exact
    assert dependency.environment_path == env_path
    os.rmdir(env_path)

    # Test that a non-read-only resolver creates a conda environment (with a
    # lowercase package name) and returns a CondaDependency
    resolver.read_only = False
    dependency = resolver.resolve(req)
    assert isinstance(dependency, CondaDependency)
    assert dependency.name == package_name
    assert dependency.version is None
    assert dependency.exact
    assert dependency.environment_path == resolver.conda_context.env_path(f"__{package_name.lower()}@_uv_")
    assert dependency.shell_commands() is not None


@external_dependency_management
def test_multi_package_resolution(resolver: CondaDependencyResolver) -> None:
    # Test that a read-only resolver returns an empty list
    resolver.read_only = True
    reqs = ToolRequirements(
        [
            ToolRequirement(name="samtools", version=None, type="package"),
            ToolRequirement(name="eXpress", version=None, type="package"),
        ]
    )
    dependency_list = resolver.resolve_all(reqs)
    assert dependency_list == []

    # Test that a (fake) mulled environment generated from non-lowercase package
    # names is still accepted by the resolver
    env_path = resolver.conda_context.env_path(
        "mulled-v1-37955d8b3667efa38f1fe42bc37b4c9a03e67a90f0055d1db9d388b2f98fe3a1"
    )
    os.mkdir(env_path)
    dependency_list = resolver.resolve_all(reqs)
    assert len(dependency_list) == 2
    for dependency in dependency_list:
        assert isinstance(dependency, MergedCondaDependency)
        assert dependency.version is None
        assert dependency.exact
        assert dependency.environment_path == env_path
    os.rmdir(env_path)

    # Test that a non-read-only resolver creates a mulled conda environment
    # (with a hash from lowercase package names) and returns a list of
    # MergedCondaDependency
    resolver.read_only = False
    dependency_list = resolver.resolve_all(reqs)
    assert len(dependency_list) == 2
    for dependency in dependency_list:
        assert isinstance(dependency, MergedCondaDependency)
        assert dependency.version is None
        assert dependency.exact
        assert dependency.environment_path == resolver.conda_context.env_path(
            "mulled-v1-f36491d362c22cdb24f7de3e1ff978a5ee02cadc8c12a12ae06bce57bbf0765c"
        )


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


@external_dependency_management
def test_best_search_result(tmp_path) -> None:
    conda_context = CondaContext(
        conda_prefix=os.path.join(tmp_path, "_conda"),
        ensure_channels=DEFAULT_ENSURE_CHANNELS,
        condarc_override=os.path.join(tmp_path, "_condarc"),
    )
    install_conda(conda_context)
    (hit, exact) = best_search_result(CondaTarget("samtools"), conda_context)
    assert hit is not None
    assert hit["name"] == "samtools"
    assert exact is True
    (hit, exact) = best_search_result(CondaTarget("samtools", version="1.3.1", build="h0cf4675_11"), conda_context)
    assert hit is not None
    assert hit["name"] == "samtools"
    assert hit["version"] == "1.3.1"
    assert hit["build"] == "h0cf4675_11"
    assert exact is True
    # Search non-existent version
    (hit, exact) = best_search_result(CondaTarget("samtools", version="1.16"), conda_context)
    assert hit is not None
    assert hit["name"] == "samtools"
    assert exact is False
