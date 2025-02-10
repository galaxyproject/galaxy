#!/usr/bin/env python

# % brew vinstall samtools 1.0
# % brew vinstall samtools 0.1.19
# % brew vinstall samtools 1.1
# % brew env samtools 1.1
# PATH=/home/john/.linuxbrew/Cellar/htslib/1.1/bin:/home/john/.linuxbrew/Cellar/samtools/1.1/bin:$PATH
# export PATH
# LD_LIBRARY_PATH=/home/john/.linuxbrew/Cellar/htslib/1.1/lib:/home/john/.linuxbrew/Cellar/samtools/1.1/lib:$LD_LIBRARY_PATH
# export LD_LIBRARY_PATH
# % . <(brew env samtools 1.1)
# % which samtools
# /home/john/.linuxbrew/Cellar/samtools/1.1/bin/samtools
# % . <(brew env samtools 0.1.19)
# % which samtools
# /home/john/.linuxbrew/Cellar/samtools/0.1.19/bin/samtools
# % brew vuninstall samtools 1.0
# % brew vdeps samtools 1.1
# htslib@1.1
# % brew vdeps samtools 0.1.19


import argparse
import contextlib
import glob
import json
import os
import re
import string
import subprocess
import sys
from typing import (
    List,
    Tuple,
)

WHITESPACE_PATTERN = re.compile(r"[\s]+")

DESCRIPTION = "Script built on top of linuxbrew to operate on isolated, versioned brew installed environments."

if sys.platform == "darwin":
    DEFAULT_HOMEBREW_ROOT = "/usr/local"
else:
    DEFAULT_HOMEBREW_ROOT = os.path.join(os.path.expanduser("~"), ".linuxbrew")

NO_BREW_ERROR_MESSAGE = "Could not find brew on PATH, please place on path or pass to script with --brew argument."
CANNOT_DETERMINE_TAP_ERROR_MESSAGE = (
    "Cannot determine tap of specified recipe - please use fully qualified recipe (e.g. homebrew/science/samtools)."
)
VERBOSE = False
RELAXED = False
BREW_ARGS = []


class BrewContext:
    def __init__(self, args=None):
        ensure_brew_on_path(args)
        raw_config = brew_execute(["config"])
        config_lines = [line.strip().split(":", 1) for line in raw_config.split("\n") if line]
        config = {p[0].strip(): p[1].strip() for p in config_lines}
        # unset if "/usr/local" -> https://github.com/Homebrew/homebrew/blob/master/Library/Homebrew/cmd/config.rb
        homebrew_prefix = config.get("HOMEBREW_PREFIX", "/usr/local")
        homebrew_cellar = config.get("HOMEBREW_CELLAR", os.path.join(homebrew_prefix, "Cellar"))
        self.homebrew_prefix = homebrew_prefix
        self.homebrew_cellar = homebrew_cellar


class RecipeContext:
    @staticmethod
    def from_args(args, brew_context=None):
        return RecipeContext(args.recipe, args.version, brew_context)

    def __init__(self, recipe, version, brew_context=None):
        self.recipe = recipe
        self.version = version
        self.brew_context = brew_context or BrewContext()

    @property
    def cellar_path(self):
        return recipe_cellar_path(self.brew_context.homebrew_cellar, self.recipe, self.version)

    @property
    def tap_path(self) -> str:
        return os.path.join(self.brew_context.homebrew_prefix, "Library", "Taps", self.__tap_path(self.recipe))

    def __tap_path(self, recipe):
        parts = recipe.split("/")
        if len(parts) == 1:
            info = brew_info(self.recipe)
            from_url = info["from_url"]
            if not from_url:
                raise Exception(CANNOT_DETERMINE_TAP_ERROR_MESSAGE)
            from_url_parts = from_url.split("/")
            blob_index = from_url_parts.index("blob")  # comes right after username and repository
            if blob_index < 2:
                raise Exception(CANNOT_DETERMINE_TAP_ERROR_MESSAGE)
            username = from_url_parts[blob_index - 2]
            repository = from_url_parts[blob_index - 1]
        else:
            assert len(parts) == 3
            parts = recipe.split("/")
            username = parts[0]
            repository = f"homebrew-{parts[1]}"

        path = os.path.join(username, repository)
        return path


def main():
    global VERBOSE
    global RELAXED
    global BREW_ARGS
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--brew", help="Path to linuxbrew 'brew' executable to target")
    actions = ["vinstall", "vuninstall", "vdeps", "vinfo", "env"]
    action = __action(sys)
    if not action:
        parser.add_argument("action", metavar="action", help="Versioned action to perform.", choices=actions)
    parser.add_argument(
        "recipe", metavar="recipe", help="Recipe for action - should be absolute (e.g. homebrew/science/samtools)."
    )
    parser.add_argument("version", metavar="version", help="Version for action (e.g. 0.1.19).")
    parser.add_argument(
        "--relaxed",
        action="store_true",
        help="Relaxed processing - for instance allow use of env on non-vinstall-ed recipes.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("restargs", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.verbose:
        VERBOSE = True
    if args.relaxed:
        RELAXED = True
    BREW_ARGS = args.restargs
    if not action:
        action = args.action
    brew_context = BrewContext(args)
    recipe_context = RecipeContext.from_args(args, brew_context)
    if action == "vinstall":
        versioned_install(recipe_context, args.recipe, args.version)
    elif action == "vuninstall":
        brew_execute(["switch", args.recipe, args.version])
        brew_execute(["uninstall", args.recipe])
    elif action == "vdeps":
        print_versioned_deps(recipe_context, args.recipe, args.version)
    elif action == "env":
        env_statements = build_env_statements_from_recipe_context(recipe_context)
        print(env_statements)
    elif action == "vinfo":
        with brew_head_at_version(recipe_context, args.recipe, args.version):
            print(brew_info(args.recipe))
    else:
        raise NotImplementedError()


class CommandLineException(Exception):
    def __init__(self, command, stdout, stderr):
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.message = (
            f"Failed to execute command-line {command}, stderr was:\n"
            "-------->>begin stderr<<--------\n"
            f"{stderr}\n"
            "-------->>end stderr<<--------\n"
            "-------->>begin stdout<<--------\n"
            f"{stdout}\n"
            "-------->>end stdout<<--------\n"
        )

    def __str__(self):
        return self.message


def versioned_install(recipe_context, package=None, version=None, installed_deps=None):
    if installed_deps is None:
        installed_deps = []
    if package is None:
        package = recipe_context.recipe
        version = recipe_context.version

    attempt_unlink(package)
    with brew_head_at_version(recipe_context, package, version):
        deps = brew_deps(package)
        deps_metadata = []
        dep_to_version = {}
        for dep in deps:
            version_info = brew_versions_info(dep, recipe_context.tap_path)[0]
            dep_version = version_info[0]
            dep_to_version[dep] = dep_version
            versioned = version_info[2]
            if versioned:
                dep_to_version[dep] = dep_version
                if dep in installed_deps:
                    continue
                versioned_install(recipe_context, dep, dep_version)
                installed_deps.append(dep)
            else:
                # Install latest.
                dep_to_version[dep] = None
                if dep in installed_deps:
                    continue
                unversioned_install(dep)
        try:
            for dep in deps:
                dep_version = dep_to_version[dep]
                if dep_version:
                    brew_execute(["switch", dep, dep_version])
                else:
                    brew_execute(["link", dep])
                # dep_version obtained from brew versions doesn't
                # include revision. This linked_keg attribute does.
                keg_verion = brew_info(dep)["linked_keg"]
                dep_metadata = {"name": dep, "version": keg_verion, "versioned": versioned}
                deps_metadata.append(dep_metadata)

            cellar_root = recipe_context.brew_context.homebrew_cellar
            cellar_path = recipe_context.cellar_path
            env_actions = build_env_actions(deps_metadata, cellar_root, cellar_path, custom_only=True)
            env = EnvAction.build_env(env_actions)
            args = ["install"]
            if VERBOSE:
                args.append("--verbose")
            args.extend(BREW_ARGS)
            args.append(package)
            brew_execute(args, env=env)
            deps = brew_execute(["deps", package])
            deps = [d.strip() for d in deps.split("\n") if d]
            metadata = {"deps": deps_metadata}
            cellar_root = recipe_context.brew_context.homebrew_cellar
            cellar_path = recipe_cellar_path(cellar_root, package, version)
            v_metadata_path = os.path.join(cellar_path, "INSTALL_RECEIPT_VERSIONED.json")
            with open(v_metadata_path, "w") as f:
                json.dump(metadata, f)

        finally:
            attempt_unlink_all(package, deps)


def commit_for_version(recipe_context: RecipeContext, package, version):
    tap_path = recipe_context.tap_path
    commit = None
    with brew_head_at_commit("master", tap_path):
        version_to_commit = brew_versions_info(package, tap_path)
        if version is None:
            version = version_to_commit[0][0]
            commit = version_to_commit[0][1]
        else:
            for mapping in version_to_commit:
                if mapping[0] == version:
                    commit = mapping[1]
    if commit is None:
        raise Exception(f"Failed to find commit for version {version}")
    return commit


def print_versioned_deps(recipe_context, recipe, version):
    deps = load_versioned_deps(recipe_context.cellar_path)
    for dep in deps:
        val = dep["name"]
        if dep["versioned"]:
            val += f"@{dep['version']}"
        print(val)


def load_versioned_deps(cellar_path, relaxed=None):
    if relaxed is None:
        relaxed = RELAXED
    v_metadata_path = os.path.join(cellar_path, "INSTALL_RECEIPT_VERSIONED.json")
    if not os.path.isfile(v_metadata_path):
        if RELAXED:
            return []
        else:
            raise OSError(f"Could not locate versioned receipt file: {v_metadata_path}")
    with open(v_metadata_path) as f:
        metadata = json.load(f)
    return metadata["deps"]


def unversioned_install(package):
    try:
        deps = brew_deps(package)
        for dep in deps:
            brew_execute(["link", dep])
        brew_execute(["install", package])
    finally:
        attempt_unlink_all(package, deps)


def attempt_unlink_all(package, deps):
    for dep in deps:
        attempt_unlink(dep)
    attempt_unlink(package)


def attempt_unlink(package):
    try:
        brew_execute(["unlink", package])
    except Exception:
        # TODO: warn
        pass


def brew_execute(args, env=None):
    os.environ["HOMEBREW_NO_EMOJI"] = "1"  # simplify brew parsing.
    cmds = ["brew"] + args
    return execute(cmds, env=env)


def build_env_statements_from_recipe_context(recipe_context, **kwds):
    cellar_root = recipe_context.brew_context.homebrew_cellar
    env_statements = build_env_statements(cellar_root, recipe_context.cellar_path, **kwds)
    return env_statements


def build_env_statements(cellar_root, cellar_path, relaxed=None, custom_only=False):
    deps = load_versioned_deps(cellar_path, relaxed=relaxed)
    actions = build_env_actions(deps, cellar_root, cellar_path, relaxed, custom_only)
    env_statements = []
    for action in actions:
        env_statements.extend(action.to_statements())
    return "\n".join(env_statements)


def build_env_actions(deps, cellar_root, cellar_path, relaxed=None, custom_only=False):
    path_appends = []
    ld_path_appends = []
    actions = []

    def handle_keg(cellar_path):
        bin_path = os.path.join(cellar_path, "bin")
        if os.path.isdir(bin_path):
            path_appends.append(bin_path)
        lib_path = os.path.join(cellar_path, "lib")
        if os.path.isdir(lib_path):
            ld_path_appends.append(lib_path)
        env_path = os.path.join(cellar_path, "platform_environment.json")
        if os.path.exists(env_path):
            with open(env_path) as f:
                env_metadata = json.load(f)
                if "actions" in env_metadata:

                    def to_action(desc):
                        return EnvAction(cellar_path, desc)

                    actions.extend(map(to_action, env_metadata["actions"]))

    for dep in deps:
        package = dep["name"]
        version = dep["version"]
        dep_cellar_path = recipe_cellar_path(cellar_root, package, version)
        handle_keg(dep_cellar_path)

    handle_keg(cellar_path)
    if not custom_only:
        if path_appends:
            actions.append(
                EnvAction(cellar_path, {"action": "prepend", "variable": "PATH", "value": ":".join(path_appends)})
            )
        if ld_path_appends:
            actions.append(
                EnvAction(
                    cellar_path, {"action": "prepend", "variable": "LD_LIBRARY_PATH", "value": ":".join(path_appends)}
                )
            )
    return actions


class EnvAction:
    def __init__(self, keg_root, action_description):
        self.variable = action_description["variable"]
        self.action = action_description["action"]
        self.value = string.Template(action_description["value"]).safe_substitute(
            {
                "KEG_ROOT": keg_root,
            }
        )

    @staticmethod
    def build_env(env_actions):
        new_env = os.environ.copy()
        (env_action.modify_environ(new_env) for env_action in env_actions)
        return new_env

    def modify_environ(self, environ):
        if self.action == "set" or not environ.get(self.variable, ""):
            environ[self.variable] = self.__eval("${value}")
        elif self.action == "prepend":
            environ[self.variable] = self.__eval(f"${{value}}:{environ[self.variable]}")
        else:
            environ[self.variable] = self.__eval(f"{environ[self.variable]}:${{value}}")

    def __eval(self, template):
        return string.Template(template).safe_substitute(
            variable=self.variable,
            value=self.value,
        )

    def to_statements(self):
        if self.action == "set":
            template = '''${variable}="${value}"'''
        elif self.action == "prepend":
            template = '''${variable}="${value}:$$${variable}"'''
        else:
            template = '''${variable}="$$${variable}:${value}"'''
        return [self.__eval(template), f"export {self.variable}"]


@contextlib.contextmanager
def brew_head_at_version(recipe_context, package, version):
    commit = commit_for_version(recipe_context, package, version)
    tap_path = recipe_context.tap_path
    with brew_head_at_commit(commit, tap_path):
        yield


@contextlib.contextmanager
def brew_head_at_commit(commit, tap_path):
    try:
        os.chdir(tap_path)
        current_commit = git_execute(["rev-parse", "HEAD"]).strip()
        try:
            git_execute(["checkout", commit])
            yield
        finally:
            git_execute(["checkout", current_commit])
    finally:
        # TODO: restore chdir - or better yet just don't chdir
        # shouldn't be needed.
        pass


def git_execute(args):
    cmds = ["git"] + args
    return execute(cmds)


def execute(cmds, env=None):
    subprocess_kwds = dict(
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if env:
        subprocess_kwds["env"] = env
    p = subprocess.Popen(cmds, **subprocess_kwds)
    # log = p.stdout.read()
    global VERBOSE
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise CommandLineException(" ".join(cmds), stdout, stderr)
    if VERBOSE:
        print(stdout)
    return stdout


def brew_deps(package):
    args = ["deps"]
    args.extend(BREW_ARGS)
    args.append(package)
    stdout = brew_execute(args)
    return [p.strip() for p in stdout.split("\n") if p]


def brew_info(recipe):
    info_json = brew_execute(["info", "--json=v1", recipe])
    info = json.loads(info_json)[0]
    info.update(extended_brew_info(recipe))
    return info


def extended_brew_info(recipe):
    # Extract more info from non-json variant. JSON variant should
    # include this in a backward compatible way (TODO: Open PR).
    raw_info = brew_execute(["info", recipe])
    extra_info = dict(
        from_url=None,
        build_dependencies=[],
        required_dependencies=[],
        recommended_dependencies=[],
        optional_dependencies=[],
    )

    for line in raw_info.split("\n"):
        if line.startswith("From: "):
            extra_info["from_url"] = line[len("From: ") :].strip()
        for dep_type in ["Build", "Required", "Recommended", "Optional"]:
            if line.startswith(f"{dep_type}: "):
                key = f"{dep_type.lower()}_dependencies"
                raw_val = line[len(f"{dep_type}: ") :]
                extra_info[key].extend(raw_val.split(", "))
    return extra_info


def brew_versions_info(package, tap_path: str) -> List[Tuple[str, str, bool]]:
    def versioned(recipe_path: str):
        if not os.path.isabs(recipe_path):
            recipe_path = os.path.join(os.getcwd(), recipe_path)
        # Dependencies in the same repository should be versioned,
        # core dependencies (presumably in base homebrew) are not
        # versioned.
        return tap_path in recipe_path

    # TODO: Also use tags.
    stdout = brew_execute(["versions", package])
    version_parts = [line for line in stdout.split("\n") if line and "git checkout" in line]
    version_parts = [WHITESPACE_PATTERN.split(line) for line in version_parts]
    info = [(p[0], p[3], versioned(p[4])) for p in version_parts]
    return info


def __action(sys):
    script_name = os.path.basename(sys.argv[0])
    if script_name.startswith("brew-"):
        return script_name[len("brew-") :]
    else:
        return None


def recipe_cellar_path(cellar_path, recipe, version):
    recipe_base = recipe.split("/")[-1]
    recipe_base_path = os.path.join(cellar_path, recipe_base, version)
    revision_paths = glob.glob(f"{recipe_base_path}_*")
    if revision_paths:
        revisions = (int(x.rsplit("_", 1)[-1]) for x in revision_paths)
        max_revision = max(revisions)
        recipe_path = f"{recipe_base_path}_{max_revision}"
    else:
        recipe_path = recipe_base_path
    return recipe_path


def ensure_brew_on_path(args):
    brew_on_path = which("brew")
    if brew_on_path:
        brew_on_path = os.path.abspath(brew_on_path)

    def ensure_on_path(brew):
        if brew != brew_on_path:
            os.environ["PATH"] = f"{os.path.dirname(brew)}:{os.environ['PATH']}"

    default_brew_path = os.path.join(DEFAULT_HOMEBREW_ROOT, "bin", "brew")
    if args and args.brew:
        user_brew_path = os.path.abspath(args.brew)
        ensure_on_path(user_brew_path)
    elif brew_on_path:
        return brew_on_path
    elif os.path.exists(default_brew_path):
        ensure_on_path(default_brew_path)
    else:
        raise Exception(NO_BREW_ERROR_MESSAGE)


def which(file):
    # http://stackoverflow.com/questions/5226958/which-equivalent-function-in-python
    for path in os.environ["PATH"].split(":"):
        if os.path.exists(f"{path}/{file}"):
            return f"{path}/{file}"

    return None


if __name__ == "__main__":
    main()
