#!/usr/bin/env python
"""Find entries in the ty.toml exemption list that are no longer needed.

The exemption list is the section of ``ty.toml`` between the
``ty-exemptions`` markers. It holds one ``[[overrides]]`` block per rule,
each listing the files that still fail that rule:

    [[overrides]]
    include = [
        "lib/galaxy/managers/example.py",
    ]

    [overrides.rules]
    unresolved-attribute = "ignore"

Only ever remove entries from this list; it functions as a TODO list of
typing debt (see ``ty.toml`` and doc/source/dev/type_checking.md).

The script runs ty over lib/ and test/ (what ``make ty`` checks) and once
per package under packages/ via ``.ci/ty_check.sh`` (what
``packages/test.sh`` checks), and compares the reported (file, rule) pairs
against the exemption list: entries whose files no longer fail the rule are
*stale*, diagnostics without an entry are *missing*.

With ``--fix`` the stale entries are removed from ty.toml, together with
any block left without patterns. With ``--add-missing`` entries are also
added for diagnostics that fail without one, which rebuilds the list from
scratch when combined with ``--fix``.

The per-package runs in ``packages/test.sh`` use venvs with only that
package's dependencies installed, so they can still fail on an entry this
script considers stale. The "Test Galaxy packages" CI job on the pull
request catches that.

For the same reason pass one ``--ty`` per Python version the linting job runs
ty on: an entry is only removed when *every* given environment no longer needs
it, so pruning with a single environment can drop entries another version
still fails.

Run it with ``tox -e ty_exemptions``, passing arguments after ``--``.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TY_TOML = ROOT / "ty.toml"

MARKER_START = "# >>> ty-exemptions (generated) >>>"
MARKER_END = "# <<< ty-exemptions <<<"

# ty compiles the include patterns of an override into a single regular
# expression and gives up on it (falling back to slower directory traversal,
# with a warning on every run) when it grows past a megabyte or so, so long
# lists are split into several blocks for the same rule.
PATTERNS_PER_OVERRIDE = 100


@dataclass
class Entry:
    rule: str
    includes: list[str]

    def sort_key(self) -> tuple[str, ...]:
        return (self.rule, *sorted(self.includes))


def parse_exemptions(lines: list[str]) -> tuple[list[Entry], int, int]:
    """Return the exemption entries and the start/end line indexes of the section."""
    try:
        start = lines.index(MARKER_START)
        end = lines.index(MARKER_END)
    except ValueError:
        sys.exit(f"{TY_TOML} has no {MARKER_START!r} ... {MARKER_END!r} section")
    entries = []
    includes: list[str] = []
    for line in lines[start + 1 : end]:
        stripped = line.strip()
        if stripped in ("[[overrides]]", "[overrides.rules]", "") or stripped.startswith("#"):
            continue
        if stripped == "include = [":
            includes = []
        elif stripped.startswith('"'):
            includes.append(stripped.rstrip(",").strip('"'))
        elif stripped.endswith('= "ignore"') and includes:
            entries.append(Entry(stripped[: -len(' = "ignore"')], includes))
    return entries, start, end


def render_exemptions(entries: list[Entry]) -> list[str]:
    out = [MARKER_START]
    for entry in sorted(entries, key=Entry.sort_key):
        includes = sorted(entry.includes)
        for i in range(0, len(includes), PATTERNS_PER_OVERRIDE):
            out += ["[[overrides]]", "include = ["]
            out += [f'    "{pattern}",' for pattern in includes[i : i + PATTERNS_PER_OVERRIDE]]
            out += ["]", "", "[overrides.rules]", f'{entry.rule} = "ignore"', ""]
    out.append(MARKER_END)
    return out


def parse_diagnostics(result: subprocess.CompletedProcess, label: str) -> list[tuple[str, str]]:
    if result.returncode not in (0, 1):
        sys.exit(f"ty failed in {label}:\n{result.stdout}{result.stderr}")
    try:
        diagnostics = json.loads(result.stdout)
    except json.JSONDecodeError:
        sys.exit(f"unexpected ty output in {label}:\n{result.stdout[:2000]}")
    pairs = []
    unexpected = []
    for diagnostic in diagnostics:
        rule = diagnostic["check_name"]
        if rule == "invalid-syntax":
            # Syntax errors cannot be configured away; they have to be fixed
            # or the file added to [src].exclude.
            unexpected.append(f'{diagnostic["location"]["path"]}: {diagnostic["description"]}')
            continue
        # ty reports warnings as "minor"; they fail the build too, so they are
        # collected like the errors. Don't resolve() the path: ty would
        # canonicalize symlinked directories and tools/ would lose its module
        # path.
        relative = os.path.normpath(os.path.join(ROOT, diagnostic["location"]["path"]))
        if not relative.endswith(".py"):
            continue  # e.g. diagnostics reported against ty.toml itself
        pairs.append((os.path.relpath(relative, ROOT), rule))
    if unexpected:
        sys.exit(
            "ty reported syntax errors, fix these or exclude the files first:\n" + "\n".join(sorted(set(unexpected)))
        )
    return pairs


def run_ty(ty: str, config_file: str, label: str, helper_args: list[str]) -> list[tuple[str, str]]:
    """Run ty over the files `.ci/ty_check.sh` selects and return the (file, rule) pairs."""
    print(f"Running ty over {label}", file=sys.stderr, flush=True)
    helper = str(ROOT / ".ci" / "ty_check.sh")
    # ty resolves third-party imports through its Python environment, which it
    # would otherwise take from VIRTUAL_ENV (the tox environment, say). Point it
    # at the environment the ty executable belongs to.
    environment = Path(ty).resolve().parent / "python"
    if environment.exists():
        helper_args = ["--python", str(environment), *helper_args]
    result = subprocess.run(
        [helper, "--output-format", "gitlab", "--no-progress", *helper_args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "TY": ty, "TY_CHECK_CONFIG_FILE": config_file},
    )
    return parse_diagnostics(result, label)


def collect(ty: str, config_file: str) -> list[tuple[str, str]]:
    """Run ty everywhere ``make ty`` and ``packages/test.sh`` run it.

    ``.ci/ty_check.sh`` knows how to select the files of the lib/ and test/
    tree and of each package; the pruner reuses it so that every run checks
    exactly the same files.
    """
    pairs = run_ty(ty, config_file, "lib/ and test/", [])
    for package in sorted((ROOT / "packages").iterdir()):
        if package.name == "meta" or not (package / "src").is_dir():
            continue
        pairs += run_ty(ty, config_file, f"packages/{package.name}", ["-p", str(package.relative_to(ROOT))])
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fix", action="store_true", help="remove stale entries from ty.toml")
    parser.add_argument("--add-missing", action="store_true", help="add entries for diagnostics that fail without one")
    parser.add_argument(
        "--ty",
        action="append",
        dest="tys",
        help="ty executable to run (can be repeated, an entry is kept if any of them needs it; "
        "defaults to the one on PATH)",
    )
    parser.add_argument("--summary", help="also write the result as Markdown to this file")
    args = parser.parse_args()
    tys = args.tys or [shutil.which("ty")]
    if not all(tys):
        sys.exit("ty not found on PATH, pass it with --ty")

    with open(TY_TOML) as f:
        lines = f.read().splitlines()
    entries, start, end = parse_exemptions(lines)
    exempted = {(pattern, entry.rule) for entry in entries for pattern in entry.includes}

    # ty resolves the paths of its configuration relative to the working
    # directory, and `.ci/ty_check.sh` runs it from the repository root, so the
    # configuration without the exemption list has to live there too.
    handle, config_file = tempfile.mkstemp(dir=ROOT, prefix=".ty_exemptions-", suffix=".toml")
    os.close(handle)
    with open(config_file, "w") as f:
        f.write("\n".join(lines[:start] + lines[end + 1 :]) + "\n")
    try:
        reported = []
        for ty in tys:
            reported += collect(ty, config_file)
    finally:
        os.unlink(config_file)

    by_rule: dict[str, set[str]] = defaultdict(set)
    for path, rule in reported:
        by_rule[rule].add(path)

    stale = {
        (pattern, entry.rule) for entry in entries for pattern in entry.includes if pattern not in by_rule[entry.rule]
    }
    missing = {
        (pattern, rule) for rule, patterns in by_rule.items() for pattern in patterns if (pattern, rule) not in exempted
    }

    print(
        f"{len(reported)} diagnostics; exemption list has {len(exempted)} entries",
        file=sys.stderr,
    )
    report = []
    if stale:
        report.append(f"{len(stale)} stale exemption entries:\n")
        report += [f"- `{pattern}`: `{rule}`" for pattern, rule in sorted(stale)]
    if missing:
        report.append(f"\n{len(missing)} diagnostics fail without an exemption entry:\n")
        report += [f"- `{pattern}`: `{rule}`" for pattern, rule in sorted(missing)]
    if not report:
        report.append("The exemption list is up to date.")
    print("\n".join(report))
    if args.summary:
        with open(args.summary, "w") as f:
            f.write("\n".join(report) + "\n")

    if args.fix or args.add_missing:
        if args.fix:
            entries = [
                Entry(entry.rule, [p for p in entry.includes if (p, entry.rule) not in stale]) for entry in entries
            ]
            entries = [entry for entry in entries if entry.includes]
        if args.add_missing:
            kept: dict[str, set[str]] = defaultdict(set)
            for entry in entries:
                kept[entry.rule].update(entry.includes)
            for pattern, rule in missing:
                kept[rule].add(pattern)
            entries = [Entry(rule, sorted(patterns)) for rule, patterns in kept.items()]
        new_lines = lines[:start] + render_exemptions(entries) + lines[end + 1 :]
        if new_lines != lines:
            with open(TY_TOML, "w") as f:
                f.write("\n".join(new_lines) + "\n")
            print("Updated ty.toml", file=sys.stderr)
    if (stale and not args.fix) or (missing and not args.add_missing):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
