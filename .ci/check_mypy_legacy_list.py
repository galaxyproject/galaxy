#!/usr/bin/env python
"""Find entries in the mypy.ini red list that are no longer needed.

A red list entry is a ``<flag> = False`` line for one of the strict default
flags in a section for a single module, e.g.::

    [mypy-galaxy.managers.example]
    disallow_untyped_defs = False

The script runs mypy once (per ``--python`` interpreter) with a copy of mypy.ini
that has all of these lines removed, over the same paths as ``make mypy`` plus
the modules that only exist in the web_client package. Each error is mapped
back to a (module, flag) pair; red list lines without a matching error are
stale. Glob sections such as the test code exemptions are left alone.

The per-package mypy runs in ``packages/test.sh`` use venvs with only that
package's dependencies, so they can fail on an entry this script considers
stale. The "Test Galaxy packages" CI job on the pull request catches that.

With ``--fix`` the stale lines are removed from mypy.ini, together with any
section left without options. With ``--add-missing`` entries are also added
for modules that fail a strict flag without having a red list entry, which
rebuilds the list from scratch when combined with ``--fix``.

Run it with ``tox -e mypy_legacy``, passing arguments after ``--``.
"""

import argparse
import collections
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import (
    dataclass,
    field,
)

from mypy.config_parser import parse_config_file
from mypy.find_sources import create_source_list
from mypy.options import Options

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
MYPY_INI = os.path.join(ROOT, "mypy.ini")
DEFAULT_CACHE_DIR = os.path.join(ROOT, ".mypy_cache_legacy_list")

# Error code reported for each strict default flag.
FLAG_FOR_CODE = {
    "type-arg": "disallow_any_generics",
    "untyped-decorator": "disallow_untyped_decorators",
    "no-untyped-def": "disallow_untyped_defs",
    "no-any-return": "warn_return_any",
}
STRICT_FLAGS = set(FLAG_FOR_CODE.values())
# Values configparser reads as False
FALSE_VALUES = {"false", "no", "off", "0"}

# (working directory, paths) for each mypy invocation: `make mypy`, then the
# web_client package, whose modules are not under lib/. packages/web_client/src
# is checked from inside src/ so its modules are named galaxy.web_client.*.
RUNS = [
    ("lib", [".", "../test"]),
    ("packages/web_client/src", ["."]),
    ("packages/web_client", ["tests"]),
]

SECTION_RE = re.compile(r"^\[(?P<name>[^\]]+)\]\s*$")
OPTION_RE = re.compile(r"^(?P<key>[a-z_]+)\s*=\s*(?P<value>.*?)\s*$")


@dataclass
class Section:
    name: str
    header: int
    # (line index, key, value)
    options: list[tuple[int, str, str]] = field(default_factory=list)

    @property
    def module(self) -> str | None:
        """The module this section applies to, if it is for a single module."""
        if not self.name.startswith("mypy-"):
            return None
        pattern = self.name[len("mypy-") :]
        if "*" in pattern or "," in pattern:
            return None
        return pattern

    def relaxed_flags(self) -> dict[str, int]:
        return {key: i for i, key, value in self.options if key in STRICT_FLAGS and value.lower() in FALSE_VALUES}


def parse_sections(lines: list[str]) -> list[Section]:
    sections: list[Section] = []
    for i, line in enumerate(lines):
        if match := SECTION_RE.match(line):
            sections.append(Section(match["name"], i))
        elif sections and (match := OPTION_RE.match(line)):
            sections[-1].options.append((i, match["key"], match["value"]))
    return sections


def red_list(sections: list[Section]) -> dict[tuple[str, str], int]:
    """Map (module, flag) to the line index of each red list entry."""
    entries = {}
    for section in sections:
        if module := section.module:
            for flag, i in section.relaxed_flags().items():
                entries[(module, flag)] = i
    return entries


class ModuleNames:
    """Map the file paths in mypy's output to module names, as mypy computes them."""

    def __init__(self, config_file: str) -> None:
        self.options = Options()
        parse_config_file(self.options, lambda: None, config_file, sys.stdout, sys.stderr)
        self.cache: dict[str, str] = {}

    def __call__(self, cwd: str, path: str) -> str:
        key = os.path.normpath(os.path.join(cwd, path))
        if key not in self.cache:
            previous = os.getcwd()
            os.chdir(cwd)
            try:
                (source,) = create_source_list([path], self.options)
            finally:
                os.chdir(previous)
            assert source.module
            self.cache[key] = source.module
        return self.cache[key]


def run_mypy(
    config_file: str, cache_dir: str, python: str, module_names: ModuleNames
) -> tuple[set[tuple[str, str]], list[str]]:
    """Return the (module, flag) pairs that fail and any errors not caused by a strict flag."""
    failing = set()
    unexpected = []
    for rel_cwd, paths in RUNS:
        cwd = os.path.join(ROOT, rel_cwd)
        cmd = [python, "-m", "mypy", "--config-file", config_file, "--cache-dir", cache_dir, "--output", "json"]
        print(f"Running {' '.join(cmd + paths)} in {rel_cwd}", file=sys.stderr, flush=True)
        result = subprocess.run(cmd + paths, cwd=cwd, capture_output=True, text=True)
        if result.returncode not in (0, 1):
            sys.exit(f"mypy failed in {rel_cwd}:\n{result.stdout}{result.stderr}")
        for line in result.stdout.splitlines():
            if not line.startswith("{"):
                continue
            error = json.loads(line)
            if error["severity"] != "error":
                continue
            flag = FLAG_FOR_CODE.get(error["code"])
            if flag is None:
                unexpected.append(f"{rel_cwd}/{error['file']}:{error['line']}: {error['message']} [{error['code']}]")
                continue
            failing.add((module_names(cwd, error["file"]), flag))
    return failing, unexpected


def rewrite(lines: list[str], sections: list[Section], stale: set[int], missing: set[tuple[str, str]]) -> list[str]:
    # Keep the strict flags of a section in alphabetical order.
    insert_before: dict[int, list[str]] = collections.defaultdict(list)
    insert_after: dict[int, list[str]] = collections.defaultdict(list)
    new_sections: dict[str, list[str]] = collections.defaultdict(list)
    extended: set[int] = set()
    by_module = {section.module: section for section in sections if section.module}
    for module, flag in sorted(missing):
        target = by_module.get(module)
        if target is None:
            new_sections[module].append(f"{flag} = False")
            continue
        extended.add(target.header)
        later = [i for relaxed, i in target.relaxed_flags().items() if relaxed > flag]
        if later:
            insert_before[min(later)].append(f"{flag} = False")
        else:
            insert_after[target.options[-1][0] if target.options else target.header].append(f"{flag} = False")
    drop = set(stale)
    for section in sections:
        if section.header not in extended and section.options and all(i in drop for i, _, _ in section.options):
            drop.add(section.header)
    out = []
    for i, line in enumerate(lines):
        out.extend(insert_before.get(i, []))
        if i not in drop:
            out.append(line)
        out.extend(insert_after.get(i, []))
    for module, flag_lines in sorted(new_sections.items()):
        out.append(f"[mypy-{module}]")
        out.extend(flag_lines)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fix", action="store_true", help="remove stale entries from mypy.ini")
    parser.add_argument(
        "--add-missing", action="store_true", help="add entries for modules that fail a strict flag without one"
    )
    parser.add_argument(
        "--python",
        action="append",
        dest="pythons",
        help="run mypy with this Python interpreter, which needs Galaxy's typecheck requirements installed "
        "(can be repeated, an entry is kept if any of them needs it; defaults to the running interpreter)",
    )
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE_DIR, help="mypy cache directory (default: %(default)s)")
    parser.add_argument("--summary", help="also write the result as Markdown to this file")
    args = parser.parse_args()

    with open(MYPY_INI) as f:
        lines = f.read().splitlines()
    sections = parse_sections(lines)
    entries = red_list(sections)

    with tempfile.TemporaryDirectory() as tmp:
        config_file = os.path.join(tmp, "mypy.ini")
        with open(config_file, "w") as f:
            f.write("\n".join(line for i, line in enumerate(lines) if i not in entries.values()) + "\n")
        module_names = ModuleNames(config_file)
        failing: set[tuple[str, str]] = set()
        unexpected: list[str] = []
        for python in args.pythons or [sys.executable]:
            python_failing, python_unexpected = run_mypy(config_file, args.cache_dir, python, module_names)
            failing |= python_failing
            unexpected += python_unexpected

    if unexpected:
        print("mypy reported errors not caused by the strict flags, fix these first:", file=sys.stderr)
        print("\n".join(sorted(set(unexpected))), file=sys.stderr)
        return 2

    print(
        f"{len({module for module, _ in failing})} modules fail a strict flag, "
        f"red list has {len(entries)} entries for {len({module for module, _ in entries})} modules",
        file=sys.stderr,
    )
    stale = sorted(key for key in entries if key not in failing)
    missing = sorted(key for key in failing if key not in entries)
    report = []
    if stale:
        modules = {module for module, _ in stale}
        report.append(f"{len(stale)} stale red list entries in {len(modules)} modules:\n")
        report += [f"- `{module}`: `{flag}`" for module, flag in stale]
    if missing:
        report.append(f"\n{len(missing)} modules/flags fail without a red list entry:\n")
        report += [f"- `{module}`: `{flag}`" for module, flag in missing]
    if not report:
        report.append("The red list is up to date.")
    print("\n".join(report))
    if args.summary:
        with open(args.summary, "w") as f:
            f.write("\n".join(report) + "\n")

    if args.fix or args.add_missing:
        new_lines = rewrite(
            lines,
            sections,
            {entries[key] for key in stale} if args.fix else set(),
            set(missing) if args.add_missing else set(),
        )
        if new_lines != lines:
            with open(MYPY_INI, "w") as f:
                f.write("\n".join(new_lines) + "\n")
            print("Updated mypy.ini", file=sys.stderr)
    if (stale and not args.fix) or (missing and not args.add_missing):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
