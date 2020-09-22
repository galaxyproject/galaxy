#!/usr/bin/env python
import subprocess
import argparse
from pathlib import Path
import glob
import yaml
from yaml import SafeLoader


def flatten(d, path):
    """
    Flatten a dictionary into ('some/path/to/key', value)

    >>> flatten({'a': {'b': 2}, 'q': 3}, [])
    [('a.b', 2), ('q', 3)]
    """

    if isinstance(d, dict):
        for k, v in d.items():
            yield from flatten(v, path + [k])
    else:
        yield (".".join(path), d)


def flat_dict(d):
    return dict(flatten(d, []))


# Load without the includes since we can't follow those across git revisions.
class MockOrderedLoader(SafeLoader):
    def include(self, node):
        return {}


MockOrderedLoader.add_constructor("!include", MockOrderedLoader.include)


def diff_files(old, new):
    # Flatten them
    old_kv = flat_dict(old)
    new_kv = flat_dict(new)

    # Compare them
    old_k = set(old_kv.keys())
    new_k = set(new_kv.keys())

    added = new_k - old_k
    removed = old_k - new_k
    shared = old_k & new_k
    changed = [(k, old_kv[k], new_kv[k]) for k in shared if old_kv[k] != new_kv[k]]

    return added, removed, changed


def _report_dict(title, subheading, data, mapper):
    print(title)
    print("-" * len(title))
    print()
    print(subheading)
    print()
    for fn in data:
        print(fn)
        print("~" * len(fn))
        print()
        for k in data[fn]:
            print(mapper(k))
        print()
    print()


def report_diff(added, changed, removed, new_files):
    # Print out report
    if added or changed or removed:
        print("Configuration Changes")
        print("=====================")
        print()

    if added:
        _report_dict(
            "Added",
            "The following configuration options are new",
            added,
            lambda x: f"-  {x}"
        )

    if changed:
        _report_dict(
            "Changed",
            "The following configuration options have been changed",
            changed,
            lambda x: f"-  {x[0]} has changed from ``{x[1]}`` to ``{x[2]}``"
        )

    if removed:
        _report_dict(
            "Removed",
            "The following configuration options have been completely removed",
            removed,
            lambda x: f"-  {x}"
        )

    if new_files:
        print("New Configuration Files")
        print("-----------------------")
        print()
        print(f"The following files are new, or recently converted to yaml")
        print()
        for k in new_files:
            print(f"-  ``{k}``")


def load_at_time(path, revision=None):
    if revision is not None:
        return subprocess.check_output(
            ["git", "show", f"{revision}:{path}"], stderr=subprocess.STDOUT
        )
    else:
        with open(path, "r") as handle:
            return handle.read()


def main(old_revision, new_revision=None):
    files_to_diff = glob.glob("config/*.yml.sample")
    added = {}
    removed = {}
    changed = {}
    new_files = []

    for file in files_to_diff:
        real_path = Path(file).resolve().relative_to(Path.cwd())
        try:
            old_contents = yaml.load(
                load_at_time(real_path, old_revision), Loader=MockOrderedLoader
            )
            new_contents = yaml.load(
                load_at_time(real_path, new_revision), Loader=MockOrderedLoader
            )

            (a, r, c) = diff_files(old_contents, new_contents)
            if a:
                added[file] = a

            if r:
                removed[file] = r

            if c:
                changed[file] = c

        except subprocess.CalledProcessError:
            new_files.append(file)

    report_diff(added, changed, removed, new_files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Diff yaml configuration files between two points in time."
    )
    parser.add_argument("old_revision", help="Old revision")
    parser.add_argument(
        "--new_revision",
        help="New revision (defaults to whatever is currently in tree)",
    )
    args = parser.parse_args()
    main(args.old_revision, args.new_revision)
