#!/usr/bin/env python
import subprocess
import sys
from pathlib import Path
import glob
import yaml
from yaml import SafeLoader

old_version = sys.argv[1]

def flatten(d, path):
    """
    Flatten a dictionary into ('some/path/to/key', value)

    >>> flatten({'a': {'b': 2}, 'q': 3}, [])
    [('a.b', 2), ('q', 3)]
    """

    if isinstance(d, dict):
        for k, v in d.items():
            yield from flatten(v, path + [k])
    # elif isinstance(d, list):
        # yield ('.'.join(path), d)
        # for i, x in enumerate(d):
            # yield from flatten(x, path + [i])
    else:
        yield (".".join(path), d)


def flat_dict(d):
    return dict(flatten(d, []))


# Load without the includes since we can't follow those across git revisions.
class MockOrderedLoader(SafeLoader):
    def include(self, node):
        return {}


MockOrderedLoader.add_constructor("!include", MockOrderedLoader.include)

# git show v20.01:lib/galaxy/config/sample/galaxy.yml.sample

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



files_to_diff = glob.glob('config/*.yml.sample')
added = {}
removed = {}
changed = {}

for file in files_to_diff:
    real_path = Path(file).resolve().relative_to(Path.cwd())
    try:
        contents = subprocess.check_output(['git', 'show', f'{old_version}:{real_path}'])
        old = yaml.load(contents, Loader=MockOrderedLoader)
        with open(real_path, 'r') as handle:
            new = yaml.load(handle, Loader=MockOrderedLoader)

        (a, r, c) = diff_files(old, new)
        if a:
            added[file] = a

        if r:
            removed[file] = r

        if c:
            changed[file] = c

    except subprocess.CalledProcessError:
        print(f"{file} did not exist in that revision.")

# Print out report
if added or changed or removed:
    print("Configuration Changes")
    print("=====================")
    print()

if added:
    print("Added")
    print("-----")
    print()
    print("The following configuration options are new")
    print()
    for fn in added:
        print(fn)
        print('~' * len(fn))
        print()
        for k in added[fn]:
            print(f"-  {k}")
        print()
    print()

if changed:
    print("Changed")
    print("-------")
    print()
    print("The following configuration options have been changed")
    print()
    for fn in changed:
        print(fn)
        print('~' * len(fn))
        print()
        for (k, o, n) in changed[fn]:
            print(f"-  {k} has changed from ``{o}`` to ``{n}``")
        print()
    print()

if removed:
    print("Removed")
    print("-------")
    print()
    print("The following configuration options have been completely removed")
    print()
    for fn in removed:
        print(fn)
        print('~' * len(fn))
        print()
        for k in removed[fn]:
            print(f"-  {k}")
        print()
    print()
