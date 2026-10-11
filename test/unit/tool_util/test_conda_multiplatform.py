"""Tests for multi-platform conda environments, using a fake conda executable."""

import json
import os
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
from typing import (
    Any,
)

import pytest

from galaxy.tool_util.deps import (
    CachedDependencyManager,
    conda_util,
    DependencyManager,
)
from galaxy.tool_util.deps.conda_util import (
    CondaContext,
    CondaTarget,
    install_conda_target,
    install_conda_targets,
    installed_conda_targets,
    parse_platforms,
    PLATFORM_OK_MARKER,
)
from galaxy.tool_util.deps.requirements import (
    ToolRequirement,
    ToolRequirements,
)
from galaxy.tool_util.deps.resolvers import (
    DependencyResolver,
    NullDependency,
)
from galaxy.tool_util.deps.resolvers.conda import (
    CONDA_SOURCE_CMD,
    CondaDependencyResolver,
)
from galaxy.util.bunch import Bunch

FAKE_CONDA = """\
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[1:]
with open(os.path.join(here, "calls.log"), "a") as fh:
    fh.write(json.dumps({
        "argv": argv,
        "CONDA_SUBDIR": os.environ.get("CONDA_SUBDIR"),
        "CONDA_OVERRIDE_GLIBC": os.environ.get("CONDA_OVERRIDE_GLIBC"),
        "CONDA_OVERRIDE_OSX": os.environ.get("CONDA_OVERRIDE_OSX"),
        "CONDARC": os.environ.get("CONDARC"),
    }) + "\\n")
if argv[:2] == ["info", "--json"]:
    if os.path.exists(os.path.join(here, "fail_info")):
        sys.exit(1)
    print(json.dumps({"platform": "linux-64", "conda_version": "24.1.0", "default_prefix": os.path.dirname(here)}))
    sys.exit(0)
def history_specs(prefix):
    history = os.path.join(prefix, "conda-meta", "history")
    if not os.path.exists(history):
        return []
    specs = []
    for line in open(history):
        if line.startswith("# update specs:"):
            specs.extend(json.loads(line.split(":", 1)[1]))
    return specs
def option(*names):
    for name in names:
        if name in argv:
            return argv[argv.index(name) + 1]
def file_specs():
    specs = []
    for i, a in enumerate(argv):
        if a == "--file":
            specs.extend(l.strip() for l in open(argv[i + 1]) if l.strip())
    return specs
if argv[:1] == ["list"]:
    if "--export" in argv:
        env = option("--prefix", "-p") or os.path.join(os.path.dirname(here), "envs", option("--name", "-n"))
        for spec in history_specs(env):
            print(spec)
    else:
        print("[]")
    sys.exit(0)
if argv[:1] == ["install"] and option("--prefix", "-p"):
    prefix = option("--prefix", "-p")
    with open(os.path.join(prefix, "conda-meta", "history"), "a") as fh:
        fh.write("# update specs: " + json.dumps(file_specs()) + "\\n")
    sys.exit(0)
if argv[:1] == ["create"]:
    prefix = option("-p", "--prefix")
    if prefix is None:
        prefix = os.path.join(os.path.dirname(here), "envs", argv[argv.index("--name") + 1])
    fail = os.path.join(here, "fail_subdirs")
    subdir = os.environ.get("CONDA_SUBDIR")
    if not subdir and os.path.exists(os.path.join(here, "fail_native")):
        if os.path.exists(os.path.join(here, "partial_on_fail")):
            os.makedirs(prefix, exist_ok=True)
        print("fake solver error for the native platform")
        sys.exit(1)
    if subdir and os.path.exists(fail) and subdir in open(fail).read().split():
        if os.path.exists(os.path.join(here, "partial_on_fail")):
            os.makedirs(prefix, exist_ok=True)
        print("fake solver error for " + subdir)
        sys.exit(1)
    os.makedirs(os.path.join(prefix, "conda-meta"), exist_ok=True)
    value_flags = ("--name", "-p", "--prefix", "--platform", "-c", "--channel", "--solver", "--file")
    specs = [
        a for i, a in enumerate(argv[1:], 1) if not a.startswith("-") and not (argv[i - 1] in value_flags)
    ] + file_specs()
    with open(os.path.join(prefix, "conda-meta", "history"), "w") as fh:
        fh.write("==> 2026-01-01 00:00:00 <==\\n# cmd: conda create\\n# update specs: " + json.dumps(specs) + "\\n")
    for rel in ("bin/tool", "bin/activate", "share/note.txt", "lib/libx.a"):
        os.makedirs(os.path.dirname(os.path.join(prefix, rel)), exist_ok=True)
        with open(os.path.join(prefix, rel), "wb") as fh:
            fh.write(b"\\xcf\\xfa\\xed\\xfe" + b"content" if rel == "bin/tool" else b"!<arch>\\n" if rel == "lib/libx.a" else b"content")
    record = {"name": "pkg", "paths_data": {"paths": [
        {"_path": "bin/tool", "file_mode": "binary", "prefix_placeholder": "/old/prefix", "path_type": "hardlink"},
        {"_path": "share/note.txt", "file_mode": "text", "prefix_placeholder": "/old/prefix", "path_type": "hardlink"},
        {"_path": "lib/libx.a", "file_mode": "binary", "prefix_placeholder": "/old/prefix", "path_type": "hardlink"},
        {"_path": "bin/gone", "file_mode": "binary", "prefix_placeholder": "/old/prefix", "path_type": "hardlink"},
        {"_path": "bin/plain", "path_type": "hardlink"},
    ]}}
    with open(os.path.join(prefix, "conda-meta", "pkg-1.0-0.json"), "w") as fh:
        json.dump(record, fh)
    sys.exit(0)
sys.exit(0)
"""


def write_fake_executable(directory: str, name: str, python_body: str) -> str:
    """Write a fake executable as a POSIX sh wrapper that runs a Python body with the interpreter of the tests.

    A shebang with ``sys.executable`` breaks when the path of the interpreter has a space, the quoted ``exec`` does not.
    The body is a sibling file, so that ``__file__`` of the body is next to the logs and markers of the fake.
    """
    body_path = os.path.join(directory, f"{name}.py")
    with open(body_path, "w") as fh:
        fh.write(python_body)
    exec_path = os.path.join(directory, name)
    with open(exec_path, "w") as fh:
        fh.write(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(body_path)} "$@"\n')
    os.chmod(exec_path, os.stat(exec_path).st_mode | stat.S_IEXEC)
    return exec_path


class FakeConda:
    def __init__(self, base: str) -> None:
        self.prefix = os.path.join(base, "conda")
        bin_dir = os.path.join(self.prefix, "bin")
        os.makedirs(bin_dir)
        self.exec = write_fake_executable(bin_dir, "conda", FAKE_CONDA)
        self.log_path = os.path.join(bin_dir, "calls.log")
        self.fail_path = os.path.join(bin_dir, "fail_subdirs")
        self.bin_dir = bin_dir

    def fail_for(self, *subdirs: str) -> None:
        with open(self.fail_path, "w") as fh:
            fh.write("\n".join(subdirs))

    def fail_native(self, fail: bool = True) -> None:
        """Native creates (those without CONDA_SUBDIR) fail, as for a package without a build for the head's platform."""
        path = os.path.join(self.bin_dir, "fail_native")
        if fail:
            open(path, "w").close()
        elif os.path.exists(path):
            os.remove(path)

    def leave_partial_dirs_on_failure(self) -> None:
        open(os.path.join(self.bin_dir, "partial_on_fail"), "w").close()

    def fail_info(self) -> None:
        open(os.path.join(self.bin_dir, "fail_info"), "w").close()

    def calls(self, command: str | None = None) -> list[dict[str, Any]]:
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path) as fh:
            calls = [json.loads(line) for line in fh if line.strip()]
        if command:
            calls = [c for c in calls if c["argv"][0] == command]
        return calls

    def creates(self) -> list[dict[str, Any]]:
        return list(self.calls("create"))


FAKE_SIGNER = """\
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "signer.log"), "a") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\\n")
if os.path.exists(os.path.join(here, "fail_sign")):
    sys.stderr.write("fake signer error\\n")
    sys.exit(1)
sys.exit(0)
"""


class FakeSigner:
    def __init__(self, base: str) -> None:
        self.dir = os.path.join(base, "signer")
        os.makedirs(self.dir)
        self.exec = write_fake_executable(self.dir, "rcodesign", FAKE_SIGNER)

    def fail(self) -> None:
        open(os.path.join(self.dir, "fail_sign"), "w").close()

    def calls(self) -> list[list[str]]:
        path = os.path.join(self.dir, "signer.log")
        if not os.path.exists(path):
            return []
        with open(path) as fh:
            return [json.loads(line) for line in fh if line.strip()]


TRUE_EXEC = shutil.which("true") or "true"


@pytest.fixture(autouse=True)
def no_signer_on_path(monkeypatch, tmp_path) -> None:
    empty = tmp_path / "emptybin"
    empty.mkdir()
    monkeypatch.setenv("PATH", f"{empty}:/usr/bin:/bin")


@pytest.fixture
def fake_signer(tmp_path) -> FakeSigner:
    return FakeSigner(str(tmp_path))


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
    options: dict[str, Any] = dict(
        prefix=fake.prefix, exec=fake.exec, auto_init=True, auto_install=False, platforms_backfill=False
    )
    options.update(kwds)
    resolver = CondaDependencyResolver(dependency_manager, **options)
    dependency_manager.dependency_resolvers = [resolver]
    return resolver


def req(name: str, version: str | None = "1.0") -> ToolRequirement:
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


def test_environment_creation_per_platform(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=fake_signer.exec)
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
    assert not os.path.exists(os.path.join(fake_conda.prefix, "envs", "mulled-v1-abc", PLATFORM_OK_MARKER))


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
    assert not os.path.exists(os.path.join(fake_conda.prefix, "envs", "__samtools@1.9", PLATFORM_OK_MARKER))
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


def install_individually(resolver: CondaDependencyResolver, *targets: CondaTarget) -> None:
    for target in targets:
        assert install_conda_target(target, resolver.conda_context) == 0


def test_foreign_requirements_without_merged_environment_share_one_job_environment(
    fake_conda: FakeConda, tmp_path
) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    install_individually(resolver, CondaTarget("samtools", version="1.9"), CondaTarget("bwa", version="0.7"))
    dm = resolver.dependency_manager
    requirements = ToolRequirements([req("samtools", "1.9"), req("bwa", "0.7")])
    merged = resolver.merged_environment_name([CondaTarget("samtools", "1.9"), CondaTarget("bwa", "0.7")])
    assert not resolver.conda_context.platform_has_env("linux-aarch64", merged)
    # the individual environments are enough for the platform, because a job environment can be built from them
    assert dm.platforms_for_requirements(requirements) == ["linux-64", "linux-aarch64"]
    assert resolver.resolve_all(requirements, platform="linux-aarch64") == []

    job_directory = str(tmp_path / "job")
    os.makedirs(job_directory)
    n_calls = len(fake_conda.calls())
    commands = dm.dependency_shell_commands(requirements, platform="linux-aarch64", job_directory=job_directory)
    job_env = os.path.join(job_directory, "conda-env")
    foreign_activate = os.path.join(fake_conda.prefix, "platforms", "linux-aarch64", "bin", "activate")
    assert len(commands) == 2
    for command in commands:
        # every command activates the one job environment, never one of the individual environments
        assert f". '{foreign_activate}' '{job_env}'" in command
        assert "/envs/__" not in command

    new_calls = fake_conda.calls()[n_calls:]
    assert [c["argv"][0] for c in new_calls if c["argv"][0] in ("create", "install")] == ["create", "install"]
    for call in new_calls:
        if call["argv"][0] in ("create", "install"):
            assert call["CONDA_SUBDIR"] == "linux-aarch64"
            assert call["CONDA_OVERRIDE_GLIBC"] == "2.17"
            assert call["argv"][1:3] == ["--platform", "linux-aarch64"]
            assert "--offline" in call["argv"]
            assert call["argv"][call["argv"].index("--prefix") + 1] == job_env
    # the exports come from the foreign environments
    exports = [c["argv"] for c in new_calls if c["argv"][0] == "list"]
    assert [a[a.index("--prefix") + 1] for a in exports] == [
        foreign_env(fake_conda, "linux-aarch64", "__samtools@1.9"),
        foreign_env(fake_conda, "linux-aarch64", "__bwa@0.7"),
    ]
    with open(os.path.join(job_env, "conda-meta", "history")) as fh:
        specs = [
            spec for line in fh if line.startswith("# update specs:") for spec in json.loads(line.split(":", 1)[1])
        ]
    assert sorted(specs) == ["bwa=0.7", "samtools=1.9"]
    # nothing was written to the native environments
    assert not resolver.conda_context.has_env(merged)


def test_foreign_requirements_prefer_the_merged_environment(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    dm = resolver.dependency_manager
    requirements = ToolRequirements([req("samtools", "1.9"), req("bwa", "0.7")])
    job_directory = str(tmp_path / "job")
    os.makedirs(job_directory)
    commands = dm.dependency_shell_commands(requirements, platform="linux-aarch64", job_directory=job_directory)
    merged = resolver.merged_environment_name([CondaTarget("samtools", "1.9"), CondaTarget("bwa", "0.7")])
    merged_env = foreign_env(fake_conda, "linux-aarch64", merged)
    # created on demand and activated directly, no job environment is built
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", merged))
    assert all(f"'{merged_env}'" in command for command in commands)
    assert not os.path.exists(os.path.join(job_directory, "conda-env"))
    assert not [c for c in fake_conda.calls("list") if "--export" in c["argv"]]


def test_foreign_requirements_need_a_buildable_job_environment(fake_conda: FakeConda, tmp_path, monkeypatch) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    install_individually(resolver, CondaTarget("samtools", version="1.9"), CondaTarget("bwa", version="0.7"))
    dm = resolver.dependency_manager
    monkeypatch.setattr(CondaContext, "can_build_job_environment", lambda self, subdir: self.is_native_platform(subdir))
    assert dm.platforms_for_requirements(ToolRequirements([req("samtools", "1.9"), req("bwa", "0.7")])) == ["linux-64"]
    # a single requirement is activated directly and needs no job environment
    assert dm.platforms_for_requirements(ToolRequirements([req("samtools", "1.9")])) == ["linux-64", "linux-aarch64"]


def test_foreign_job_environment_is_signed_on_osx(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="osx-arm64", codesign_exec=fake_signer.exec)
    install_individually(resolver, CondaTarget("samtools", version="1.9"), CondaTarget("bwa", version="0.7"))
    job_directory = str(tmp_path / "job")
    os.makedirs(job_directory)
    n_signed = len(fake_signer.calls())
    resolver.dependency_manager.dependency_shell_commands(
        ToolRequirements([req("samtools", "1.9"), req("bwa", "0.7")]), platform="osx-arm64", job_directory=job_directory
    )
    signed = [call[-1] for call in fake_signer.calls()[n_signed:]]
    assert os.path.join(job_directory, "conda-env", "bin", "tool") in signed


def test_platforms_for_requirements(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=fake_signer.exec)
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


def env_binary(fake: FakeConda, subdir: str, env_name: str) -> str:
    return os.path.join(fake.prefix, "platforms", subdir, "envs", env_name, "bin", "tool")


def test_osx_signs_only_patched_binaries(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path, caplog) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=fake_signer.exec)
    base_signed = fake_signer.calls()
    base = os.path.join(fake_conda.prefix, "platforms", "osx-arm64")
    assert base_signed == [["sign", os.path.join(base, "bin", "tool")]]
    with caplog.at_level("INFO"):
        install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    calls = fake_signer.calls()[len(base_signed) :]
    assert calls == [["sign", env_binary(fake_conda, "osx-arm64", "__samtools@1.9")]]
    assert os.path.exists(foreign_marker(fake_conda, "osx-arm64", "__samtools@1.9"))
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))
    assert "Signed 1 Mach-O files for osx-arm64 (1 patched files were not Mach-O)" in caplog.text


def write_patched_file(prefix: str, rel: str, content: bytes) -> dict:
    path = os.path.join(prefix, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(content)
    return {"_path": rel, "file_mode": "binary", "prefix_placeholder": "/old/prefix", "path_type": "hardlink"}


def test_only_macho_files_are_signed(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path, caplog) -> None:
    context = make_context(fake_conda, codesign_exec=fake_signer.exec)
    prefix = str(tmp_path / "osx-env")
    entries = [
        write_patched_file(prefix, "bin/macho", b"\xcf\xfa\xed\xfe" + b"\x00" * 16),
        write_patched_file(prefix, "lib/fat.dylib", b"\xca\xfe\xba\xbe" + b"\x00" * 16),
        write_patched_file(prefix, "share/terminfo/x", b"xterm|terminal,\n\tam,\n"),
        write_patched_file(prefix, "lib/libhts.a", b"!<arch>\n" + b"\x00" * 16),
    ]
    os.makedirs(os.path.join(prefix, "conda-meta"))
    with open(os.path.join(prefix, "conda-meta", "pkg-1.0-0.json"), "w") as fh:
        json.dump({"name": "pkg", "paths_data": {"paths": entries}}, fh)
    with caplog.at_level("DEBUG"):
        assert context.sign_platform_files("osx-arm64", prefix)
    assert fake_signer.calls() == [
        ["sign", os.path.join(prefix, "bin", "macho")],
        ["sign", os.path.join(prefix, "lib", "fat.dylib")],
    ]
    assert "Signed 2 Mach-O files for osx-arm64 (2 patched files were not Mach-O)" in caplog.text


def test_non_macho_files_do_not_count_as_failures(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path) -> None:
    context = make_context(fake_conda, codesign_exec=fake_signer.exec)
    prefix = str(tmp_path / "osx-env")
    entries = [write_patched_file(prefix, "lib/libhts.a", b"!<arch>\n")]
    os.makedirs(os.path.join(prefix, "conda-meta"))
    with open(os.path.join(prefix, "conda-meta", "pkg-1.0-0.json"), "w") as fh:
        json.dump({"name": "pkg", "paths_data": {"paths": entries}}, fh)
    fake_signer.fail()
    assert context.sign_platform_files("osx-arm64", prefix)
    assert fake_signer.calls() == []


def test_marker_is_written_with_mixed_patched_files(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path) -> None:
    # the fake conda lists a Mach-O bin/tool and a patched static archive lib/libx.a
    resolver = make_resolver(fake_conda, tmp_path, platforms="osx-arm64", codesign_exec=fake_signer.exec)
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    env = os.path.join(fake_conda.prefix, "platforms", "osx-arm64", "envs", "__samtools@1.9")
    assert os.path.exists(foreign_marker(fake_conda, "osx-arm64", "__samtools@1.9"))
    assert fake_signer.calls()[-1:] == [["sign", os.path.join(env, "bin", "tool")]]
    assert all(call[1].endswith("bin/tool") for call in fake_signer.calls())


def test_osx_64_is_signed_too(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="osx-64", codesign_exec=fake_signer.exec)
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    assert ["sign", env_binary(fake_conda, "osx-64", "__samtools@1.9")] in fake_signer.calls()
    assert os.path.exists(foreign_marker(fake_conda, "osx-64", "__samtools@1.9"))


def test_nothing_signed_for_linux(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", codesign_exec=fake_signer.exec)
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    assert fake_signer.calls() == []
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))


def test_failing_signer_leaves_no_marker(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path, caplog) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=fake_signer.exec)
    fake_signer.fail()
    with caplog.at_level("INFO"):
        assert install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context) == 0
    assert os.path.isdir(os.path.join(fake_conda.prefix, "platforms", "osx-arm64", "envs", "__samtools@1.9"))
    assert not os.path.exists(foreign_marker(fake_conda, "osx-arm64", "__samtools@1.9"))
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))
    assert "fake signer error" in caplog.text
    assert "Signed 0 Mach-O files for osx-arm64 (1 patched files were not Mach-O), 1 failed" in caplog.text
    assert isinstance(resolver.resolve(req("samtools", "1.9"), platform="osx-arm64"), NullDependency)


def test_no_signer_warns_once_and_leaves_no_osx_marker(fake_conda: FakeConda, tmp_path, caplog) -> None:
    with caplog.at_level("WARNING"):
        resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64")
    warnings = [r for r in caplog.records if "No code signer found" in r.getMessage()]
    assert len(warnings) == 1
    assert "codesign_exec" in warnings[0].getMessage()
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    assert not os.path.exists(foreign_marker(fake_conda, "osx-arm64", "__samtools@1.9"))
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))


def test_no_warning_without_osx_platform(fake_conda: FakeConda, tmp_path, caplog) -> None:
    with caplog.at_level("WARNING"):
        make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    assert "No code signer found" not in caplog.text


def test_signer_found_on_path(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path, monkeypatch, caplog) -> None:
    monkeypatch.setenv("PATH", f"{fake_signer.dir}:/usr/bin:/bin")
    with caplog.at_level("WARNING"):
        resolver = make_resolver(fake_conda, tmp_path, platforms="osx-arm64")
    assert resolver.conda_context.codesign_exec == fake_signer.exec
    assert "No code signer found" not in caplog.text


def test_codesign_exec_from_global_config(fake_conda: FakeConda, fake_signer: FakeSigner, tmp_path) -> None:
    dependency_manager = make_dependency_manager(tmp_path, conda_codesign_exec=fake_signer.exec)
    resolver = CondaDependencyResolver(dependency_manager, prefix=fake_conda.prefix, exec=fake_conda.exec)
    assert resolver.conda_context.codesign_exec == fake_signer.exec


def foreign_env(fake: FakeConda, subdir: str, env_name: str) -> str:
    return os.path.join(fake.prefix, "platforms", subdir, "envs", env_name)


def test_no_platforms_writes_no_marker_and_never_asks_for_the_platform(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path)
    context = resolver.conda_context
    assert install_conda_target(CondaTarget("samtools", version="1.9"), context) == 0
    assert (
        install_conda_targets(
            [CondaTarget("samtools", version="1.9"), CondaTarget("bwa", version="0.7")], context, env_name="mulled-v1-x"
        )
        == 0
    )
    resolver.resolve(req("samtools", "1.9"))
    resolver.resolve_all(ToolRequirements([req("samtools", "1.9"), req("bwa", "0.7")]))
    # the conda version lookup of conda itself is cached, the platform code adds no further "conda info"
    n_info = len(fake_conda.calls("info"))
    resolver.platforms_for_requirements([req("samtools", "1.9")])
    resolver.dependency_manager.platforms_for_requirements(ToolRequirements([req("samtools", "1.9")]))
    for env_name in ("__samtools@1.9", "mulled-v1-x"):
        assert not os.path.exists(os.path.join(fake_conda.prefix, "envs", env_name, PLATFORM_OK_MARKER))
    assert len(fake_conda.calls("info")) == n_info
    assert not os.path.exists(os.path.join(fake_conda.prefix, "platforms"))
    assert not os.path.exists(os.path.join(fake_conda.prefix, ".locks"))
    assert [c["argv"][0] for c in fake_conda.calls()].count("create") == 2


def test_second_install_finds_the_environment_present_and_keeps_it(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=TRUE_EXEC)
    context = resolver.conda_context
    target = CondaTarget("samtools", version="1.9")
    assert install_conda_target(target, context) == 0
    env_name = "__samtools@1.9"
    for subdir in ("linux-aarch64", "osx-arm64"):
        with open(os.path.join(foreign_env(fake_conda, subdir, env_name), "share", "keep.txt"), "w") as fh:
            fh.write("keep")
    n_creates = len(fake_conda.creates())
    # a second install that raced the first and runs after it: nothing is created or deleted
    fake_conda.fail_for("linux-aarch64", "osx-arm64")
    assert install_conda_target(target, context) == 0
    assert len(fake_conda.creates()) == n_creates
    for subdir in ("linux-aarch64", "osx-arm64"):
        assert os.path.exists(foreign_marker(fake_conda, subdir, env_name))
        assert os.path.exists(os.path.join(foreign_env(fake_conda, subdir, env_name), "share", "keep.txt"))
    # lock files stay in place, they are never removed
    assert all(name.endswith(".lock") for name in os.listdir(os.path.join(fake_conda.prefix, ".locks")))


def test_second_install_only_adds_the_missing_foreign_environment(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    target = CondaTarget("samtools", version="1.9")
    install_conda_target(target, context)
    shutil.rmtree(foreign_env(fake_conda, "linux-aarch64", "__samtools@1.9"))
    n_creates = len(fake_conda.creates())
    assert install_conda_target(target, context) == 0
    new = fake_conda.creates()[n_creates:]
    assert len(new) == 1
    assert new[0]["CONDA_SUBDIR"] == "linux-aarch64"
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))


def test_failed_foreign_create_keeps_a_preexisting_directory(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=TRUE_EXEC)
    context = resolver.conda_context
    fake_conda.fail_for("linux-aarch64", "osx-arm64")
    fake_conda.leave_partial_dirs_on_failure()
    # a directory of an earlier attempt is not ours to delete, one the failing create made itself is removed
    existing = foreign_env(fake_conda, "linux-aarch64", "__samtools@1.9")
    os.makedirs(os.path.join(existing, "share"))
    with open(os.path.join(existing, "share", "earlier.txt"), "w") as fh:
        fh.write("earlier")
    assert install_conda_target(CondaTarget("samtools", version="1.9"), context) == 0
    assert os.path.exists(os.path.join(existing, "share", "earlier.txt"))
    assert not os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))
    assert not os.path.exists(foreign_env(fake_conda, "osx-arm64", "__samtools@1.9"))


def test_marked_environment_survives_a_failing_recreate(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    install_conda_target(CondaTarget("samtools", version="1.9"), context)
    fake_conda.fail_for("linux-aarch64")
    fake_conda.leave_partial_dirs_on_failure()
    marked = foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9")
    results = context.create_platform_environments("__samtools@1.9", ["samtools=1.9"])
    assert results == {"linux-aarch64": True}
    assert os.path.exists(marked)


LOCK_HOLDER = """
import sys
sys.path.insert(0, {lib!r})
from galaxy.tool_util.deps.conda_util import _env_lock
with _env_lock(sys.argv[1], 10) as locked:
    print("locked" if locked else "failed", flush=True)
    sys.stdin.read()
"""


def hold_lock_in_subprocess(path: str) -> "subprocess.Popen[str]":
    """Start a process that holds the lock on ``path`` until it is killed or its stdin closes."""
    lib = os.path.abspath(os.path.join(os.path.dirname(conda_util.__file__), "..", "..", ".."))
    process = subprocess.Popen(
        [sys.executable, "-c", LOCK_HOLDER.format(lib=lib), path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env=dict(os.environ, PYTHONPATH=os.pathsep.join(p for p in sys.path if p)),
    )
    assert process.stdout is not None
    assert process.stdout.readline().strip() == "locked"
    return process


def test_held_lock_makes_the_install_native_only(fake_conda: FakeConda, tmp_path, monkeypatch, caplog) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    monkeypatch.setattr(conda_util, "PLATFORM_LOCK_TIMEOUT", 0.2)
    lock_path = os.path.join(fake_conda.prefix, ".locks", "__samtools@1.9.lock")
    holder = hold_lock_in_subprocess(lock_path)
    try:
        with caplog.at_level("WARNING"):
            assert install_conda_target(CondaTarget("samtools", version="1.9"), context) == 0
    finally:
        holder.kill()
        holder.wait()
    assert "Timed out waiting for the lock" in caplog.text
    assert lock_path in caplog.text
    assert os.path.isdir(os.path.join(fake_conda.prefix, "envs", "__samtools@1.9"))
    assert not os.path.exists(foreign_env(fake_conda, "linux-aarch64", "__samtools@1.9"))


@pytest.mark.skipif(conda_util.fcntl is None, reason="needs POSIX locks")
def test_lock_is_released_when_the_holder_dies(tmp_path) -> None:
    lock_path = str(tmp_path / ".locks" / "__x@1.lock")
    holder = hold_lock_in_subprocess(lock_path)
    with conda_util._env_lock(lock_path, 0.3) as locked:
        assert not locked
    holder.send_signal(signal.SIGKILL)
    holder.wait()
    started = time.monotonic()
    with conda_util._env_lock(lock_path, 5) as locked:
        assert locked
    assert time.monotonic() - started < 2
    assert os.path.exists(lock_path)


def test_threads_of_one_process_exclude_each_other(tmp_path) -> None:
    lock_path = str(tmp_path / ".locks" / "__x@1.lock")
    first_holds = threading.Event()
    release_first = threading.Event()
    order: list[str] = []

    def first() -> None:
        with conda_util._env_lock(lock_path, 10) as locked:
            assert locked
            order.append("first acquired")
            first_holds.set()
            assert release_first.wait(10)
            order.append("first releasing")

    def second() -> None:
        with conda_util._env_lock(lock_path, 10) as locked:
            assert locked
            order.append("second acquired")

    t1 = threading.Thread(target=first)
    t2 = threading.Thread(target=second)
    t1.start()
    assert first_holds.wait(10)
    t2.start()
    t2.join(0.5)
    assert t2.is_alive()
    assert order == ["first acquired"]
    release_first.set()
    t1.join(10)
    t2.join(10)
    assert order == ["first acquired", "first releasing", "second acquired"]


def test_second_thread_times_out_while_the_first_holds_the_lock(tmp_path) -> None:
    lock_path = str(tmp_path / ".locks" / "__x@1.lock")
    first_holds = threading.Event()
    release_first = threading.Event()
    results: list[bool] = []

    def first() -> None:
        with conda_util._env_lock(lock_path, 10) as locked:
            results.append(locked)
            first_holds.set()
            release_first.wait(10)

    def second() -> None:
        start = time.monotonic()
        with conda_util._env_lock(lock_path, 0.3) as locked:
            results.append(locked)
        results.append(time.monotonic() - start >= 0.25)

    t1 = threading.Thread(target=first)
    t1.start()
    assert first_holds.wait(10)
    t2 = threading.Thread(target=second)
    t2.start()
    t2.join(10)
    release_first.set()
    t1.join(10)
    assert results == [True, False, True]
    with conda_util._env_lock(lock_path, 1) as locked:
        assert locked


def test_lock_can_be_taken_repeatedly(tmp_path) -> None:
    lock_path = str(tmp_path / ".locks" / "__x@1.lock")
    for _ in range(2):
        with conda_util._env_lock(lock_path, 1) as locked:
            assert locked
    assert os.path.exists(lock_path)


def test_foreign_environment_needs_the_platform_base(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    install_conda_target(CondaTarget("samtools", version="1.9"), context)
    assert context.platform_has_env("linux-aarch64", "__samtools@1.9")
    activate = context.platform_activate("linux-aarch64")
    os.remove(activate)
    assert not context.platform_has_env("linux-aarch64", "__samtools@1.9")
    assert isinstance(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"), NullDependency)
    assert resolver.platforms_for_requirements([req("samtools", "1.9")]) == ["linux-64"]


def test_marker_is_not_written_without_the_platform_base(fake_conda: FakeConda, tmp_path, caplog) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    os.remove(context.platform_activate("linux-aarch64"))
    os.makedirs(foreign_env(fake_conda, "linux-aarch64", "__x@1"))
    with caplog.at_level("WARNING"):
        assert context.mark_platform_env_ok("linux-aarch64", "__x@1") is False
    assert not os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__x@1"))
    # install without a base: the create succeeds but the environment is not usable
    assert install_conda_target(CondaTarget("samtools", version="1.9"), context) == 0
    assert not os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))


class RecordingResolver(DependencyResolver):
    resolver_type = "recording"

    def __init__(self, supports_platforms: bool = False) -> None:
        self.supports_platforms = supports_platforms
        self.calls: list[dict[str, Any]] = []

    def resolve(self, requirement, **kwds):
        self.calls.append(kwds)
        return NullDependency(version=requirement.version, name=requirement.name)


def test_resolvers_without_platform_support_are_skipped_for_foreign_platforms(fake_conda: FakeConda, tmp_path) -> None:
    conda_resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    install_conda_target(CondaTarget("samtools", version="1.9"), conda_resolver.conda_context)
    plain = RecordingResolver()
    aware = RecordingResolver(supports_platforms=True)
    dm = conda_resolver.dependency_manager
    dm.dependency_resolvers = [plain, aware, conda_resolver]
    requirements = ToolRequirements([req("samtools", "1.9")])

    resolved = dm.requirements_to_dependencies(requirements, platform="linux-aarch64")
    assert plain.calls == []
    assert len(aware.calls) == 1
    (dependency,) = resolved.values()
    assert "/platforms/linux-aarch64/envs/__samtools@1.9" in dependency.environment_path

    # native platform, explicit or not, keeps every resolver
    dm.requirements_to_dependencies(requirements, platform="linux-64")
    dm.requirements_to_dependencies(requirements)
    assert len(plain.calls) == 2


def test_resolve_dependency_shell_commands_resolves_once_with_the_tool_context(fake_conda: FakeConda, tmp_path) -> None:
    conda_resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    install_conda_target(CondaTarget("samtools", version="1.9"), conda_resolver.conda_context)
    recording = RecordingResolver(supports_platforms=True)
    dm = conda_resolver.dependency_manager
    dm.dependency_resolvers = [recording, conda_resolver]
    samtools, bwa = req("samtools", "1.9"), req("bwa", "0.7")

    commands, dependencies = dm.resolve_dependency_shell_commands(
        ToolRequirements([samtools, bwa]), platform="linux-aarch64", tool_dir="/tools/x", installed_tool_dependencies=[]
    )
    # one resolution, the unresolved requirement is reported and no incomplete activation is built
    assert commands == []
    assert not isinstance(dependencies[samtools], NullDependency)
    assert isinstance(dependencies[bwa], NullDependency)
    assert [c["tool_dir"] for c in recording.calls] == ["/tools/x", "/tools/x"]
    assert all(c["platform"] == "linux-aarch64" and c["return_null"] for c in recording.calls)

    commands, dependencies = dm.resolve_dependency_shell_commands(
        ToolRequirements([samtools]), platform="linux-aarch64", tool_dir="/tools/x"
    )
    assert len(commands) == 1 and "platforms/linux-aarch64/envs/__samtools@1.9" in commands[0]
    assert list(dependencies) == [samtools]


def test_cached_dependency_hash_includes_the_platform(tmp_path) -> None:
    manager = CachedDependencyManager(str(tmp_path), app_config=dict(dependency_resolvers=[]))

    def dep(platform: str | None) -> Bunch:
        return Bunch(name="samtools", version="1.9", exact=True, dependency_type="conda", platform=platform)

    native, native_again, foreign = (manager.hash_dependencies([dep(p)]) for p in (None, None, "linux-aarch64"))
    assert native == native_again
    assert native != foreign
    # dependencies without any platform notion keep the hash they always had
    plain = Bunch(name="samtools", version="1.9", exact=True, dependency_type="conda")
    assert manager.hash_dependencies([plain]) == native


def test_platform_is_not_filtered_without_a_conda_resolver(tmp_path) -> None:
    dm = make_dependency_manager(tmp_path)
    plain = RecordingResolver()
    dm.dependency_resolvers = [plain]
    dm.requirements_to_dependencies(ToolRequirements([req("samtools", "1.9")]), platform="linux-aarch64")
    assert len(plain.calls) == 1


def test_supports_platforms_flags() -> None:
    assert DependencyResolver.supports_platforms is False
    assert CondaDependencyResolver.supports_platforms is True


def make_tool_instance() -> Bunch:
    return Bunch(
        id="tool", version="1", containers=[], requires_galaxy_python_environment=False, dependencies="untouched"
    )


def test_requirements_to_dependencies_caches_on_the_tool_only_without_platform(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    dm = resolver.dependency_manager
    requirements = ToolRequirements([req("samtools", "1.9")])

    tool = make_tool_instance()
    dm.requirements_to_dependencies(requirements, tool_instance=tool, platform="linux-aarch64")
    assert tool.dependencies == "untouched"

    dm.requirements_to_dependencies(requirements, tool_instance=tool)
    assert isinstance(tool.dependencies, list) and len(tool.dependencies) == 1
    native_dependencies = tool.dependencies
    dm.requirements_to_dependencies(requirements, tool_instance=tool, platform="linux-aarch64")
    assert tool.dependencies is native_dependencies


def test_dependency_shell_commands_with_platform_leave_the_tool_alone(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    install_conda_target(CondaTarget("samtools", version="1.9"), resolver.conda_context)
    tool = make_tool_instance()
    resolver.dependency_manager.dependency_shell_commands(
        ToolRequirements([req("samtools", "1.9")]), platform="linux-aarch64", tool_instance=tool
    )
    assert tool.dependencies == "untouched"


def test_uninstall_ignores_empty_environment_names(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    install_conda_target(CondaTarget("samtools", version="1.9"), context)
    n_calls = len(fake_conda.calls())
    assert resolver.uninstall_environments(["", "  "]) == 0
    assert len(fake_conda.calls()) == n_calls
    for name in ("", "  ", ".", "..", "a/b"):
        context.remove_platform_environments(name)
    assert os.path.isdir(os.path.join(fake_conda.prefix, "platforms", "linux-aarch64", "envs"))
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))
    # a real name still removes the foreign copy
    resolver.uninstall_environments(["__samtools@1.9"])
    assert not os.path.exists(foreign_env(fake_conda, "linux-aarch64", "__samtools@1.9"))


def test_parse_platforms_splits_commas_inside_list_items() -> None:
    assert parse_platforms(["linux-aarch64,osx-arm64", " osx-64 ", "linux-aarch64"]) == [
        "linux-aarch64",
        "osx-arm64",
        "osx-64",
    ]
    assert parse_platforms("linux-aarch64, osx-arm64,,") == ["linux-aarch64", "osx-arm64"]
    assert parse_platforms(None) == []
    assert parse_platforms(["bad,linux-aarch64"]) == ["linux-aarch64"]


def test_failed_native_platform_lookup_is_cached(fake_conda: FakeConda, tmp_path) -> None:
    context = make_context(fake_conda, platforms="linux-aarch64")
    fake_conda.fail_info()
    assert context.configured_platforms == []
    assert context.foreign_platforms == []
    assert context.configured_platforms == []
    assert len(fake_conda.calls("info")) == 1


def test_disabled_resolver_has_no_platforms_and_does_not_ask_conda(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    resolver.disabled = True
    n_info = len(fake_conda.calls("info"))
    assert resolver.platforms_for_requirements([req("samtools", "1.9")]) == []
    assert len(fake_conda.calls("info")) == n_info


def test_conda_auto_install_enabled(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    dm = resolver.dependency_manager
    assert dm.conda_auto_install_enabled() is False
    resolver.auto_install = True
    resolver.read_only = False
    assert dm.conda_auto_install_enabled() is True
    resolver.read_only = True
    assert dm.conda_auto_install_enabled() is False
    resolver.read_only = False
    resolver.disabled = True
    assert dm.conda_auto_install_enabled() is False
    assert dm.configured_conda_platforms() == []
    resolver.disabled = False
    assert dm.configured_conda_platforms() == ["linux-64", "linux-aarch64"]


def native_only_env(fake: FakeConda, name: str, specs: list[str] | None) -> None:
    """A native environment as installed before conda_platforms was set."""
    meta = os.path.join(fake.prefix, "envs", name, "conda-meta")
    os.makedirs(meta)
    with open(os.path.join(meta, "history"), "w") as fh:
        if specs is not None:
            fh.write("==> 2026-01-01 00:00:00 <==\n# cmd: conda create\n# update specs: " + json.dumps(specs) + "\n")


def subdir_creates(fake: FakeConda) -> list[dict[str, Any]]:
    return [c for c in fake.creates() if "--platform" in c["argv"] and "-p" in c["argv"] and c["argv"][-1] != "python"]


def test_failure_is_recorded_and_cleared_by_a_later_success(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    fake_conda.fail_for("linux-aarch64")
    install_conda_target(CondaTarget("samtools", version="1.9"), context)
    failed = context.platform_failure_path("linux-aarch64", "__samtools@1.9")
    assert failed == foreign_env(fake_conda, "linux-aarch64", "__samtools@1.9") + ".failed"
    with open(failed) as fh:
        timestamp, *tail = fh.read().splitlines()
    assert timestamp.endswith("+00:00")
    assert "fake solver error for linux-aarch64" in tail
    assert context.platform_failure_is_fresh("linux-aarch64", "__samtools@1.9")
    fake_conda.fail_for()
    with context.env_lock("__samtools@1.9"):
        assert context.create_platform_environments("__samtools@1.9", ["samtools=1.9"]) == {"linux-aarch64": True}
    assert not os.path.exists(failed)


def test_backfill_creates_missing_foreign_environments(fake_conda: FakeConda, tmp_path, caplog) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=TRUE_EXEC)
    context = resolver.conda_context
    native_only_env(fake_conda, "__samtools@1.9", ["samtools=1.9"])
    native_only_env(fake_conda, "mulled-v1-abc", ["samtools=1.9", "bwa=0.7"])
    native_only_env(fake_conda, "__bwa@0.7", None)  # no recorded specs, the name gives them
    native_only_env(fake_conda, "mulled-v1-nospecs", None)
    native_only_env(fake_conda, "unrelated", ["x"])
    n_creates = len(fake_conda.creates())
    with caplog.at_level("INFO"):
        counts = context.backfill_platform_environments()
    assert counts == dict(environments=4, created=6, failed=0, present=0, recently_failed=0, without_specs=1)
    new = fake_conda.creates()[n_creates:]
    assert len(new) == 6
    assert {c["argv"][-1] for c in new} == {"samtools=1.9", "bwa=0.7"}
    merged = [c for c in new if c["argv"][-2:] == ["samtools=1.9", "bwa=0.7"]]
    assert len(merged) == 2
    for subdir in ("linux-aarch64", "osx-arm64"):
        for name in ("__samtools@1.9", "mulled-v1-abc", "__bwa@0.7"):
            assert os.path.exists(foreign_marker(fake_conda, subdir, name))
    assert not os.path.exists(foreign_env(fake_conda, "linux-aarch64", "unrelated"))
    assert "Starting backfill" in caplog.text and "Finished backfill" in caplog.text
    assert "6 created" in caplog.text
    # a second run finds everything present
    n_creates = len(fake_conda.creates())
    counts = context.backfill_platform_environments()
    assert len(fake_conda.creates()) == n_creates
    assert counts["created"] == 0 and counts["present"] == 6


def test_backfill_skips_fresh_failures_and_retries_old_ones(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=TRUE_EXEC)
    context = resolver.conda_context
    native_only_env(fake_conda, "__samtools@1.9", ["samtools=1.9"])
    context.record_platform_failure("linux-aarch64", "__samtools@1.9", "earlier error")
    context.record_platform_failure("osx-arm64", "__samtools@1.9", "earlier error")
    old = time.time() - 8 * 86400
    os.utime(context.platform_failure_path("osx-arm64", "__samtools@1.9"), (old, old))
    n_creates = len(fake_conda.creates())
    counts = context.backfill_platform_environments()
    new = fake_conda.creates()[n_creates:]
    assert [c["CONDA_SUBDIR"] for c in new] == ["osx-arm64"]
    assert counts["recently_failed"] == 1 and counts["created"] == 1
    assert os.path.exists(context.platform_failure_path("linux-aarch64", "__samtools@1.9"))
    assert not os.path.exists(context.platform_failure_path("osx-arm64", "__samtools@1.9"))
    assert os.path.exists(foreign_marker(fake_conda, "osx-arm64", "__samtools@1.9"))
    assert not os.path.exists(foreign_marker(fake_conda, "linux-aarch64", "__samtools@1.9"))


def test_backfill_failure_is_recorded_and_not_retried(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    native_only_env(fake_conda, "__samtools@1.9", ["samtools=1.9"])
    fake_conda.fail_for("linux-aarch64")
    counts = context.backfill_platform_environments()
    assert counts["failed"] == 1
    assert os.path.exists(context.platform_failure_path("linux-aarch64", "__samtools@1.9"))
    n_creates = len(fake_conda.creates())
    counts = context.backfill_platform_environments()
    assert len(fake_conda.creates()) == n_creates
    assert counts["recently_failed"] == 1


def test_retry_days_option(fake_conda: FakeConda, tmp_path) -> None:
    context = make_context(fake_conda, platforms="linux-aarch64", platforms_retry_days=1)
    context.record_platform_failure("linux-aarch64", "__x@1", "error")
    path = context.platform_failure_path("linux-aarch64", "__x@1")
    two_days = time.time() - 2 * 86400
    os.utime(path, (two_days, two_days))
    assert not context.platform_failure_is_fresh("linux-aarch64", "__x@1")
    resolver = make_resolver(fake_conda, tmp_path, platforms_retry_days="3")
    assert resolver.conda_context.platforms_retry_days == 3.0
    assert make_resolver(fake_conda, tmp_path).conda_context.platforms_retry_days == 7.0


def test_backfill_thread_is_gated_by_options(fake_conda: FakeConda, tmp_path, monkeypatch, caplog) -> None:
    started: list[int] = []
    monkeypatch.setattr(CondaDependencyResolver, "_backfill_platform_environments", lambda self: started.append(1))
    with caplog.at_level("INFO"):
        resolver = make_resolver(
            fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True, platforms_backfill=True
        )
        assert resolver._backfill_thread is None
        assert "Starting backfill" not in caplog.text
        assert started == []
        resolver.dependency_manager.start_background_tasks()
        resolver.dependency_manager.start_background_tasks()
    assert resolver._backfill_thread is not None
    resolver._backfill_thread.join(10)
    assert started == [1]
    assert caplog.text.count("Starting backfill") == 1
    for kwds in (
        dict(platforms="linux-aarch64", auto_install=False, platforms_backfill=True),
        dict(platforms="linux-aarch64", auto_install=True, platforms_backfill=False),
        dict(auto_install=True, platforms_backfill=True),
    ):
        other = make_resolver(fake_conda, tmp_path, **kwds)
        other.dependency_manager.start_background_tasks()
        assert other._backfill_thread is None
    assert started == [1]


def test_backfill_starts_once_per_prefix_across_resolver_instances(
    fake_conda: FakeConda, tmp_path, monkeypatch, caplog
) -> None:
    started: list[int] = []
    monkeypatch.setattr(CondaDependencyResolver, "_backfill_platform_environments", lambda self: started.append(1))
    kwds = dict(platforms="linux-aarch64", auto_install=True, platforms_backfill=True)
    with caplog.at_level("INFO"):
        first = make_resolver(fake_conda, tmp_path, **kwds)
        second = make_resolver(fake_conda, tmp_path, **kwds)
        first.dependency_manager.start_background_tasks()
        second.dependency_manager.start_background_tasks()
    assert first._backfill_thread is not None
    first._backfill_thread.join(10)
    assert second._backfill_thread is None
    assert started == [1]
    assert caplog.text.count("Starting backfill") == 1


def test_backfill_option_from_global_config(fake_conda: FakeConda, tmp_path) -> None:
    dependency_manager = make_dependency_manager(
        tmp_path, conda_platforms="linux-aarch64", conda_platforms_backfill=False, conda_auto_install=True
    )
    resolver = CondaDependencyResolver(dependency_manager, prefix=fake_conda.prefix, exec=fake_conda.exec)
    assert resolver._backfill_thread is None


def test_foreign_resolve_with_auto_install_creates_native_and_foreign(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    env_name = "__samtools@1.9"
    assert not resolver.conda_context.has_env(env_name)
    n_before = len(fake_conda.creates())
    dep = resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64")
    assert not isinstance(dep, NullDependency)
    assert dep.activate == os.path.join(fake_conda.prefix, "platforms", "linux-aarch64", "bin", "activate")
    assert dep.environment_path == foreign_env(fake_conda, "linux-aarch64", env_name)
    assert resolver.conda_context.has_env(env_name)
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", env_name))
    creates = fake_conda.creates()[n_before:]
    assert len(creates) == 2
    assert "--platform" not in creates[0]["argv"] and creates[1]["CONDA_SUBDIR"] == "linux-aarch64"
    # a second request finds the environment and does not call conda
    n_calls = len(fake_conda.calls())
    assert not isinstance(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"), NullDependency)
    assert len(fake_conda.calls()) == n_calls


def test_foreign_resolve_all_with_auto_install_creates_the_merged_environment(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    deps = resolver.resolve_all(ToolRequirements([req("a"), req("b")]), platform="linux-aarch64")
    assert len(deps) == 2
    assert all(d.platform == "linux-aarch64" for d in deps)
    assert all(os.path.exists(os.path.join(d.environment_path, PLATFORM_OK_MARKER)) for d in deps)


def test_foreign_resolve_does_not_retry_a_fresh_failure(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    context = resolver.conda_context
    context.record_platform_failure("linux-aarch64", "__samtools@1.9", "solver error")
    assert context.platform_failure_is_fresh("linux-aarch64", "__samtools@1.9")
    n_calls = len(fake_conda.calls())
    assert isinstance(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"), NullDependency)
    assert resolver.resolve_all(ToolRequirements([req("samtools", "1.9")]), platform="linux-aarch64") == []
    assert len(fake_conda.calls()) == n_calls
    assert not context.has_env("__samtools@1.9")


def test_foreign_resolve_retries_an_old_failure(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    context = resolver.conda_context
    context.record_platform_failure("linux-aarch64", "__samtools@1.9", "solver error")
    old = time.time() - 30 * 86400
    os.utime(context.platform_failure_path("linux-aarch64", "__samtools@1.9"), (old, old))
    assert not isinstance(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"), NullDependency)


def test_failed_on_demand_create_gives_null_dependency_and_records_the_failure(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    fake_conda.fail_for("linux-aarch64")
    assert isinstance(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"), NullDependency)
    assert resolver.conda_context.platform_failure_is_fresh("linux-aarch64", "__samtools@1.9")
    n_creates = len(fake_conda.creates())
    assert isinstance(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"), NullDependency)
    assert len(fake_conda.creates()) == n_creates


def test_foreign_resolve_without_auto_install_does_not_call_conda(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=False)
    n_calls = len(fake_conda.calls())
    assert isinstance(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"), NullDependency)
    assert resolver.resolve_all(ToolRequirements([req("a"), req("b")]), platform="linux-aarch64") == []
    assert len(fake_conda.calls()) == n_calls


def test_foreign_resolve_with_install_false_does_not_call_conda(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    n_calls = len(fake_conda.calls())
    dep = resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64", install=False)
    assert isinstance(dep, NullDependency)
    assert len(fake_conda.calls()) == n_calls


def test_foreign_resolve_waits_for_a_native_install_in_progress(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    context = resolver.conda_context
    env_name = "__samtools@1.9"
    holds_lock = threading.Event()
    finish_install = threading.Event()
    result: list[Any] = []

    def native_install() -> None:
        with context.env_lock(env_name) as locked:
            assert locked
            holds_lock.set()
            assert finish_install.wait(10)
            assert context.exec_create(["--name", env_name, "samtools=1.9"]) == 0
            context.create_platform_environments(env_name, ["samtools=1.9"])

    def foreign_request() -> None:
        result.append(resolver.resolve(req("samtools", "1.9"), platform="linux-aarch64"))

    t1 = threading.Thread(target=native_install)
    t1.start()
    assert holds_lock.wait(10)
    n_creates = len(fake_conda.creates())
    t2 = threading.Thread(target=foreign_request)
    t2.start()
    t2.join(0.5)
    assert t2.is_alive()
    assert result == []
    assert len(fake_conda.creates()) == n_creates
    finish_install.set()
    t1.join(10)
    t2.join(10)
    assert not t1.is_alive() and not t2.is_alive()
    assert len(result) == 1 and not isinstance(result[0], NullDependency)
    assert result[0].environment_path == foreign_env(fake_conda, "linux-aarch64", env_name)
    # the waiting request created nothing on its own: one native and one foreign create in total
    assert len(fake_conda.creates()) == n_creates + 2


def native_failure_path(fake: FakeConda, env_name: str) -> str:
    return os.path.join(fake.prefix, "envs", env_name + ".failed")


def test_native_failure_does_not_stop_the_foreign_creates(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=TRUE_EXEC)
    context = resolver.conda_context
    fake_conda.fail_native()
    fake_conda.fail_for("osx-arm64")
    env_name = "__blat@36"
    target = CondaTarget("blat", version="36")
    # a plain native request keeps the native return code
    assert install_conda_target(target, context) != 0
    assert not context.has_env(env_name)
    assert os.path.exists(foreign_marker(fake_conda, "linux-aarch64", env_name))
    assert not os.path.exists(foreign_marker(fake_conda, "osx-arm64", env_name))
    assert os.path.isfile(native_failure_path(fake_conda, env_name))
    assert os.path.isfile(context.platform_failure_path("osx-arm64", env_name))
    assert context.platform_failure_path("linux-64", env_name) == native_failure_path(fake_conda, env_name)
    assert context.platform_failure_is_fresh("linux-64", env_name)
    assert not context.platform_failure_is_fresh("linux-aarch64", env_name)
    with open(native_failure_path(fake_conda, env_name)) as fh:
        assert "fake solver error for the native platform" in fh.read()
    # the failure record is not an environment
    assert [t.package for t in installed_conda_targets(context)] == []


def test_install_counts_as_success_when_the_requested_platform_exists(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=TRUE_EXEC)
    context = resolver.conda_context
    fake_conda.fail_native()
    fake_conda.fail_for("osx-arm64")
    target = CondaTarget("blat", version="36")
    assert install_conda_targets([target], context, env_name="__blat@36", platform="linux-aarch64") == 0
    assert install_conda_targets([target], context, env_name="__blat@36", platform="osx-arm64") != 0


def test_successful_native_create_clears_the_native_failure_record(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    fake_conda.fail_native()
    assert install_conda_target(CondaTarget("blat", version="36"), context) != 0
    assert os.path.isfile(native_failure_path(fake_conda, "__blat@36"))
    fake_conda.fail_native(False)
    assert install_conda_target(CondaTarget("blat", version="36"), context) == 0
    assert not os.path.exists(native_failure_path(fake_conda, "__blat@36"))
    assert context.has_env("__blat@36")


def test_repeated_native_failure_leaves_recently_failed_foreign_platforms_alone(
    fake_conda: FakeConda, tmp_path
) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=TRUE_EXEC)
    context = resolver.conda_context
    fake_conda.fail_native()
    fake_conda.fail_for("osx-arm64")
    target = CondaTarget("blat", version="36")
    install_conda_target(target, context)
    n_creates = len(fake_conda.creates())
    assert install_conda_target(target, context) != 0
    # only the native create is repeated (with and without strict channel priority), linux-aarch64 exists and
    # osx-arm64 failed recently
    new = fake_conda.creates()[n_creates:]
    assert len(new) == 2 and all("--name" in c["argv"] for c in new)


def test_native_failure_leaves_no_partial_directory(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    fake_conda.fail_native()
    fake_conda.leave_partial_dirs_on_failure()
    assert install_conda_target(CondaTarget("blat", version="36"), resolver.conda_context) != 0
    assert not resolver.conda_context.has_env("__blat@36")


def test_routing_helpers_after_a_native_failure(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=TRUE_EXEC)
    dm = resolver.dependency_manager
    fake_conda.fail_native()
    fake_conda.fail_for("osx-arm64")
    install_conda_target(CondaTarget("blat", version="36"), resolver.conda_context)
    requirements = ToolRequirements([req("blat", "36")])
    n_calls = len(fake_conda.calls())
    assert dm.platforms_for_requirements(requirements) == ["linux-aarch64"]
    assert dm.platforms_with_failed_install(requirements) == ["linux-64", "osx-arm64"]
    assert dm.platforms_with_failed_install(ToolRequirements([req("other", "1")])) == []
    assert len(fake_conda.calls()) == n_calls


def test_failed_install_listing_for_merged_environments(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    requirements = ToolRequirements([req("a"), req("b")])
    targets = [CondaTarget("a", version="1.0"), CondaTarget("b", version="1.0")]
    merged = resolver.merged_environment_name(targets)
    context.record_platform_failure("linux-64", merged, "error")
    assert resolver.platforms_with_failed_install(requirements) == ["linux-64"]
    assert resolver.platforms_with_failed_install(ToolRequirements([req("a")])) == []


def test_backfill_creates_foreign_environments_for_a_failed_native_one(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64,osx-arm64", codesign_exec=TRUE_EXEC)
    context = resolver.conda_context
    os.makedirs(os.path.join(fake_conda.prefix, "envs"), exist_ok=True)
    for name in ("__blat@36", "mulled-v1-abc", "__nofailure@1"):
        assert not context.has_env(name)
    context.record_platform_failure("linux-64", "__blat@36", "no build")
    context.record_platform_failure("linux-64", "mulled-v1-abc", "no build")
    n_creates = len(fake_conda.creates())
    counts = context.backfill_platform_environments()
    assert counts["environments"] == 2 and counts["created"] == 2 and counts["without_specs"] == 1
    new = fake_conda.creates()[n_creates:]
    assert [c["argv"][-1] for c in new] == ["blat=36", "blat=36"]
    for subdir in ("linux-aarch64", "osx-arm64"):
        assert os.path.exists(foreign_marker(fake_conda, subdir, "__blat@36"))
        assert not os.path.exists(foreign_marker(fake_conda, subdir, "mulled-v1-abc"))
    assert not context.has_env("__blat@36")
    assert os.path.isfile(native_failure_path(fake_conda, "__blat@36"))
    # the second run finds them present
    n_creates = len(fake_conda.creates())
    counts = context.backfill_platform_environments()
    assert len(fake_conda.creates()) == n_creates
    assert counts["present"] == 2


def test_foreign_resolve_returns_the_foreign_environment_after_a_native_failure(
    fake_conda: FakeConda, tmp_path
) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    context = resolver.conda_context
    fake_conda.fail_native()
    dep = resolver.resolve(req("blat", "36"), platform="linux-aarch64")
    assert not isinstance(dep, NullDependency)
    assert dep.environment_path == foreign_env(fake_conda, "linux-aarch64", "__blat@36")
    assert not context.has_env("__blat@36")
    assert context.platform_failure_is_fresh("linux-64", "__blat@36")
    # a second tool with the merged environment
    deps = resolver.resolve_all(ToolRequirements([req("a"), req("b")]), platform="linux-aarch64")
    assert len(deps) == 2
    # the native request fails as before and the native create is attempted again
    n_creates = len(fake_conda.creates())
    assert isinstance(resolver.resolve(req("blat", "36")), NullDependency)
    new = fake_conda.creates()[n_creates:]
    assert len(new) == 2 and all("--name" in c["argv"] for c in new)


def test_foreign_request_skips_a_known_native_failure(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64", auto_install=True)
    context = resolver.conda_context
    fake_conda.fail_native()
    context.record_platform_failure("linux-64", "__blat@36", "no build")
    n_creates = len(fake_conda.creates())
    assert not isinstance(resolver.resolve(req("blat", "36"), platform="linux-aarch64"), NullDependency)
    new = fake_conda.creates()[n_creates:]
    assert [c["CONDA_SUBDIR"] for c in new] == ["linux-aarch64"]


def test_uninstall_removes_the_native_failure_record(fake_conda: FakeConda, tmp_path) -> None:
    resolver = make_resolver(fake_conda, tmp_path, platforms="linux-aarch64")
    context = resolver.conda_context
    context.record_platform_failure("linux-64", "__blat@36", "no build")
    context.remove_platform_environments("__blat@36")
    assert not os.path.exists(native_failure_path(fake_conda, "__blat@36"))
