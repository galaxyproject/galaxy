import os
import shutil
import unittest
from tempfile import mkdtemp

from galaxy.tools.deps import (
    conda_util,
    DependencyManager
)
from galaxy.tools.deps.resolvers.conda import CondaDependencyResolver


def skip_unless_environ(var):
    if var in os.environ:
        return lambda func: func
    template = "Environment variable %s not found, dependent test skipped."
    return unittest.skip(template % var)


@skip_unless_environ("GALAXY_TEST_INCLUDE_SLOW")
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
        conda_context = resolver.conda_context
        assert len(list(conda_util.installed_conda_targets(conda_context))) == 0
        dependency = resolver.resolve(name="samtools", version=None, type="package", job_directory=job_dir)
        assert dependency.shell_commands(None) is not None
        installed_targets = list(conda_util.installed_conda_targets(conda_context))
        assert len(installed_targets) == 1
        samtools_target = installed_targets[0]
        assert samtools_target.package == "samtools"
        assert samtools_target.version is None
    finally:
        shutil.rmtree(base_path)


@skip_unless_environ("GALAXY_TEST_INCLUDE_SLOW")
def test_conda_resolution_failure():
    """This test is specifically designed to trigger https://github.com/rtfd/readthedocs.org/issues/1902
    and thus it expects the install to fail. If this test fails it is a sign that the upstream
    conda issue has been fixed.
    """

    base_path = mkdtemp(prefix='x' * 80)  # a ridiculously long prefix
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
        assert len(list(conda_util.installed_conda_targets(conda_context))) == 0
        dependency = resolver.resolve(name="samtools", version=None, type="package", job_directory=job_dir)
        assert dependency.shell_commands(None) is None  # install should fail
        installed_targets = list(conda_util.installed_conda_targets(conda_context))
        assert len(installed_targets) == 0
    finally:
        shutil.rmtree(base_path)
