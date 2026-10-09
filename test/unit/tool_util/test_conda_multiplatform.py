"""Tests for multi-platform conda environments, using a fake conda executable."""

import json
import os
import stat
import sys
import textwrap
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pytest

from galaxy.tool_util.deps import DependencyManager
from galaxy.tool_util.deps.conda_util import (
    CondaContext,
    CondaTarget,
    install_conda_target,
    install_conda_targets,
    PLATFORM_OK_MARKER,
)
from galaxy.tool_util.deps.requirements import (
    ToolRequirement,
    ToolRequirements,
)
from galaxy.tool_util.deps.resolvers import NullDependency
from galaxy.tool_util.deps.resolvers.conda import (
    CONDA_SOURCE_CMD,
    CondaDependencyResolver,
    MergedCondaDependency,
)

FAKE_CONDA = """\
#!{python}
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
with open(os.path.join(here, "calls.log"), "a") as fh:
    fh.write(json.dumps({{
        "argv": argv,
        "CONDA_SUBDIR": os.environ.get("CONDA_SUBDIR"),
        "CONDA_OVERRIDE_GLIBC": os.environ.get("CONDA_OVERRIDE_GLIBC"),
        "CONDA_OVERRIDE_OSX": os.environ.get("CONDA_OVERRIDE_OSX"),
        "CONDARC": os.environ.get("CONDARC"),
    }}) + "\\n")
if argv[:2] == ["info", "--json"]:
    print(json.dumps({{"platform": "linux-64", "conda_version": "24.1.0", "default_prefix": os.path.dirname(here)}}))
    sys.exit(0)
if argv[:1] == ["list"]:
    print("[]")
    sys.exit(0)
if argv[:1] == ["create"]:
    fail = os.path.join(here, "fail_subdirs")
    subdir = os.environ.get("CONDA_SUBDIR")
    if subdir and os.path.exists(fail) and subdir in open(fail).read().split():
        print("fake solver error for " + subdir)
        sys.exit(1)
    if "-p" in argv:
        prefix = argv[argv.index("-p") + 1]
    else:
        prefix = os.path.join(os.path.dirname(here), "envs", argv[argv.index("--name") + 1])
    os.makedirs(os.path.join(prefix, "conda-meta"), exist_ok=True)
    open(os.path.join(prefix, "conda-meta", "history"), "w").close()
    sys.exit(0)
sys.exit(0)
"""


class FakeConda:
    def __init__(self, base: str) -> None:
        self.prefix = os.path.join(base, "conda")
        bin_dir = os.path.join(self.prefix, "bin")
        os.makedirs(bin_dir)
        self.exec = os.path.join(bin_dir, "conda")
        with open(self.exec, "w") as fh:
            fh.write(FAKE_CONDA.format(python=sys.executable))
        os.chmod(self.exec, os.stat(self.exec).st_mode | stat.S_IEXEC)
        self.log_path = os.path.join(bin_dir, "calls.log")
        self.fail_path = os.path.join(bin_dir, "fail_subdirs")

    def fail_for(self, *subdirs: str) -> None:
        with open(self.fail_path, "w") as fh:
            fh.write("\n".join(subdirs))

    def calls(self, command: Optional[str] = None) -> List[Dict[str, Any]]:
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path) as fh:
            calls = [json.loads(line) for line in fh if line.strip()]
        if command:
            calls = [c for c in calls if c["argv"][0] == command]
        return calls

    def creates(self) -> List[Dict[str, Any]]:
        return [c for c in self.calls("create")]


@pytest.fixture
def fake_conda(tmp_path) -> FakeConda:
    return FakeConda(str(tmp_path))


def make_context(fake: FakeConda, **kwds) -> CondaContext:
    return CondaContext(
        conda_prefix=fake.prefix,
        conda_exec=fake.exec,
        ensure_channels=["conda-forge", "bioconda"],
        condarc_override=os.path.join(fake.prefix, "condarc"),
        **kwds,
    )


def make_dependency_manager(tmp_path, **app_config) -> DependencyManager:
    # An explicit empty resolver list stops DependencyManager from building (and installing) the default resolvers.
    os.makedirs(tmp_path / "deps", exist_ok=True)
    return DependencyManager(str(tmp_path / "deps"), app_config=dict(dependency_resolvers=[], **app_config))


def make_resolver(fake: FakeConda, tmp_path, **kwds) -> CondaDependencyResolver:
    dependency_manager = make_dependency_manager(tmp_path)
    options: Dict[str, Any] = dict(prefix=fake.prefix, exec=fake.exec, auto_init=True, auto_install=False)
    options.update(kwds)
    resolver = CondaDependencyResolver(dependency_manager, **options)
    dependency_manager.dependency_resolvers = [resolver]
    return resolver


def req(name: str, version: Optional[str] = "1.0") -> ToolRequirement:
    return ToolRequirement(name=name, version=version, type="package")


def foreign_marker(fake: FakeConda, subdir: str, env_name: str) -> str:
    return os.path.join(fake.prefix, "platforms", subdir, "envs", env_name, PLATFORM_OK_MARKER)


def test_no_platforms_unchanged(fake_conda: FakeConda) -> None:
    context = make_context(fake_conda)
    target = CondaTarget("samtools", version="1.9")
    assert install_conda_target(target, context) == 0
    creates = fake_conda.creates()
    assert len(creates) == 1
    assert creates[0]["argv"][0] == "create"
    assert "--platform" not in creates[0]["argv"]
    assert creates[0]["CONDA_SUBDIR"] is None
    assert not os.path.exists(os.path.join(fake_conda.prefix, "platforms"))
    assert context.foreign_platforms == []
    assert context.configured_platforms == []


def test_no_platforms_shell_commands_unchanged(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path)
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    activate = os.path.join(fake_conda.prefix, "bin", "activate")
    env_path = os.path.join(fake_conda.prefix, "envs", "__samtools@1.9")
    expected = CONDA_SOURCE_CMD.format(activate_path=activate, environment_path=env_path)
    dependencies = resolver.resolve_all(ToolRequirements([req("samtools", "1.9")]))
    assert [d.shell_commands() for d in dependencies] == [expected]
    # an explicit native platform gives the very same commands
    dependencies = resolver.resolve_all(ToolRequirements([req("samtools", "1.9")]), platform="linux-64")
    assert [d.shell_commands() for d in dependencies] == [expected]
    # nothing platform related is ever created
    assert not os.path.exists(os.path.join(fake_conda.prefix, "platforms"))


def test_platform_paths_and_env_vars(fake_conda: FakeConda) -> None:
    context = make_context(
        fake_conda,
        platforms="linux-aarch64, osx-arm64,linux-64",
        platform_overrides={"osx-arm64": {"CONDA_OVERRIDE_OSX": "12.0"}},
    )
    assert context.native_platform == "linux-64"
    assert context.foreign_platforms == ["linux-aarch64", "osx-arm64"]
    assert context.configured_platforms == ["linux-64", "linux-aarch64", "osx-arm64"]
    assert context.platform_prefix("linux-64") == fake_conda.prefix
    assert context.platform_prefix("linux-aarch64") == os.path.join(fake_conda.prefix, "platforms", "linux-aarch64")
    assert context.platform_env_path("linux-aarch64", "__x@1") == os.path.join(
        fake_conda.prefix, "platforms", "linux-aarch64", "envs", "__x@1"
    )
    assert context.platform_env_vars("linux-aarch64") == {
        "CONDA_SUBDIR": "linux-aarch64",
        "CONDA_OVERRIDE_GLIBC": "2.17",
    }
    assert context.platform_env_vars("osx-arm64") == {"CONDA_SUBDIR": "osx-arm64", "CONDA_OVERRIDE_OSX": "12.0"}
    assert context.platform_env_vars("win-64") == {"CONDA_SUBDIR": "win-64"}
    # native info is cached
    assert len(fake_conda.calls("info")) == 1


def test_invalid_platforms_dropped(fake_conda: FakeConda) -> None:
    context = make_context(fake_conda, platforms=["linux-aarch64", "../etc", "", "linux-aarch64"])
    assert context.platforms == ["linux-aarch64"]


def test_foreign_base_creation(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64")
    assert not resolver.disabled
    creates = fake_conda.creates()
    assert len(creates) == 2
    by_subdir = {c["CONDA_SUBDIR"]: c for c in creates}
    aarch = by_subdir["linux-aarch64"]
    base = os.path.join(fake_conda.prefix, "platforms", "linux-aarch64")
    assert aarch["argv"][:6] == ["create", "--yes", "--platform", "linux-aarch64", "-p", base]
    assert aarch["argv"][-2:] == ["conda", "python"]
    assert "--override-channels" in aarch["argv"]
    assert aarch["CONDA_OVERRIDE_GLIBC"] == "2.17"
    assert aarch["CONDARC"] is not None
    assert by_subdir["osx-arm64"]["CONDA_OVERRIDE_OSX"] == "11.0"
    assert os.path.exists(os.path.join(base, "conda-meta", "history"))
    # a second start does not recreate existing bases
    make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64")
    assert len(fake_conda.creates()) == 2


def test_foreign_base_failure_is_not_fatal(fake_conda: FakeConda, tmp_path) -> None:
    fake_conda.fail_for("linux-aarch64")
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    assert not resolver.disabled
    assert not os.path.exists(os.path.join(fake_conda.prefix, "platforms", "linux-aarch64", "conda-meta", "history"))


def test_environment_creation_per_platform(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64")
    context = resolver.conda_context
    n_before = len(fake_conda.creates())
    targets = [CondaTarget("samtools", version="1.9"), CondaTarget("bwa", version="0.7")]
    assert install_conda_targets(targets, context, env_name="mulled-v1-abc") == 0
    creates = fake_conda.creates()[n_before:]
    assert len(creates) == 3
    native, aarch, osx = creates
    assert native["argv"][:3] == ["create", "-y", "--quiet"] or "--name" in native["argv"]
    assert "--name" in native["argv"] and "--platform" not in native["argv"]
    assert native["CONDA_SUBDIR"] is None
    for call, subdir in ((aarch, "linux-aarch64"), (osx, "osx-arm64")):
        argv = call["argv"]
        env_path = os.path.join(fake_conda.prefix, "platforms", subdir, "envs", "mulled-v1-abc")
        assert argv[argv.index("--platform") + 1] == subdir
        assert argv[argv.index("-p") + 1] == env_path
        assert argv[-2:] == ["samtools=1.9", "bwa=0.7"]
        assert call["CONDA_SUBDIR"] == subdir
        assert os.path.exists(foreign_marker(fake_conda, subdir, "mulled-v1-abc"))
    assert aarch["CONDA_OVERRIDE_GLIBC"] == "2.17" and aarch["CONDA_OVERRIDE_OSX"] is None
    assert osx["CONDA_OVERRIDE_OSX"] == "11.0" and osx["CONDA_OVERRIDE_GLIBC"] is None
    assert os.path.exists(os.path.join(fake_conda.prefix, "envs", "mulled-v1-abc", PLATFORM_OK_MARKER))


def test_single_target_install_covers_platforms(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    assert resolver._install_dependency("samtools", "1.9", "package")
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))


def test_foreign_failure_is_nonfatal_and_leaves_no_marker(fake_conda: FakeConda, tmp_path, caplog) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64")
    fake_conda.fail_for("osx-arm64")
    target = CondaTarget("samtools", version="1.9")
    with caplog.at_level("WARNING"):
        assert install_conda_target(target, resolver.conda_context) == 0
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))
    assert not os.path.exists(foreign_marker(fake_conda, "osx-arm64", "__samtools@1.9"))
    assert os.path.exists(os.path.join(fake_conda.prefix, "envs", "__samtools@1.9", PLATFORM_OK_MARKER))
    assert "fake solver error for osx-arm64" in caplog.text
    assert any(r.levelname == "WARNING" for r in caplog.records)


def test_platform_kwd_changes_activate_line(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    dm = resolver.dependency_manager
    requirements = ToolRequirements([req("samtools", "1.9")])

    foreign_activate = os.path.join(fake_conda.prefix, "platforms", "linux-aarch64", "bin", "activate")
    foreign_env = os.path.join(fake_conda.prefix, "platforms", "linux-aarch64", "envs", "__samtools@1.9")
    commands = dm.dependency_shell_commands(requirements, platform="linux-aarch64")
    assert len(commands) == 1
    assert f". '{foreign_activate}' '{foreign_env}'" in commands[0]

    # native subdir and None resolve exactly like no platform at all
    native_env = os.path.join(fake_conda.prefix, "envs", "__samtools@1.9")
    native_activate = os.path.join(fake_conda.prefix, "bin", "activate")
    with_native = dm.requirements_to_dependencies(requirements, platform="linux-64")
    assert [d.environment_path for d in with_native.values()] == [native_env]
    for platform in (None, "linux-64"):
        dep = resolver.resolve(req("samtools", "1.9"), platform=platform)
        assert dep.activate == native_activate
        assert dep.environment_path == native_env


def test_unconfigured_platform_gives_null_dependency(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    assert isinstance(resolver.resolve(req("samtools", "1.9"), platform="osx-arm64"), NullDependency)
    assert resolver.resolve_all(ToolRequirements([req("a"), req("b")]), platform="osx-arm64") == []
    dm = resolver.dependency_manager
    assert dm.dependency_shell_commands(ToolRequirements([req("samtools", "1.9")]), platform="osx-arm64") == []


def test_missing_marker_gives_null_dependency(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    fake_conda.fail_for("linux-aarch64")
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    assert isinstance(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"), NullDependency)
    # a partially created environment without marker does not count either
    env = os.path.join(fake_conda.prefix, "platforms", "linux-aarch64", "envs", "__samtools@1.9", "bin")
    os.makedirs(env)
    assert isinstance(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"), NullDependency)


def test_merged_environment_per_platform(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    requirements = ToolRequirements([req("samtools", "1.9"), req("bwa", "0.7")])
    deps = resolver.resolve_all(requirements)
    assert len(deps) == 2
    foreign = resolver.resolve_all(requirements, platform="linux-aarch64")
    assert len(foreign) == 2
    assert all("/platforms/linux-aarch64/envs/mulled-v1-" in d.environment_path for d in foreign)
    assert "/platforms/linux-aarch64/bin/activate" in foreign[0].shell_commands()


def test_platforms_for_requirements(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64")
    dm = resolver.dependency_manager
    context = resolver.conda_context
    install_conda_target(CondaTarget("samtools", version="1.9"), context)
    fake_conda.fail_for("osx-arm64")
    install_conda_target(CondaTarget("bwa", version="0.7"), context)
    n_calls = len(fake_conda.calls())

    assert dm.platforms_for_requirements(ToolRequirements([req("samtools", "1.9")])) == [
        "linux-64",
        "linux-aarch64",
        "osx-arm64",
    ]
    assert dm.platforms_for_requirements(ToolRequirements([req("bwa", "0.7")])) == ["linux-64", "linux-aarch64"]
    assert dm.platforms_for_requirements(ToolRequirements([req("samtools", "1.9"), req("bwa", "0.7")])) == [
        "linux-64",
        "linux-aarch64",
    ]
    assert dm.platforms_for_requirements(ToolRequirements([req("nothere", "1")])) == []
    # no package requirements: everything configured
    assert dm.platforms_for_requirements(ToolRequirements([])) == ["linux-64", "linux-aarch64", "osx-arm64"]
    # filesystem only
    assert len(fake_conda.calls()) == n_calls


def test_platforms_from_global_config(fake_conda: FakeConda, tmp_path) -> None:
    dependency_manager = make_dependency_manager(tmp_path, conda_platforms="linux-aarch64")
    resolver = CondaDependencyResolver(dependency_manager, prefix=fake_conda.prefix, exec=fake_conda.exec)
    assert resolver.conda_context.platforms == ["linux-aarch64"]


def test_extra_env_per_call(fake_conda: FakeConda) -> None:
    context = make_context(fake_conda)
    assert context.exec_create(["--name", "x"], extra_env={"CONDA_SUBDIR": "linux-aarch64"}) == 0
    assert fake_conda.creates()[-1]["CONDA_SUBDIR"] == "linux-aarch64"
    assert fake_conda.creates()[-1]["CONDARC"] == context.condarc_override
    assert context.exec_create(["--name", "y"]) == 0
    assert fake_conda.creates()[-1]["CONDA_SUBDIR"] is None
