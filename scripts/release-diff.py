#!/usr/bin/env python
import sys
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
    elif isinstance(d, list):
        for x in d:
            yield from flatten(x, path + [x])
    else:
        yield (".".join(path), d)


def flat_dict(d):
    return dict(flatten(d, []))


# Load without the includes since we can't follow those across git revisions.
class MockOrderedLoader(SafeLoader):
    def include(self, node):
        return {}


MockOrderedLoader.add_constructor("!include", MockOrderedLoader.include)

# Load our two files
with open(sys.argv[1], "r") as handle:
    old = yaml.load(handle, Loader=MockOrderedLoader)

with open(sys.argv[2], "r") as handle:
    new = yaml.load(handle, Loader=MockOrderedLoader)


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
    for k in added:
        print(f"-  {k}")
    print()

if changed:
    print("Changed")
    print("-------")
    print()
    print("The following configuration options have been changed")
    print()
    for (k, o, n) in changed:
        print(f"-  {k} has changed from ``{o}`` to ``{n}``")
    print()

if removed:
    print("Removed")
    print("-------")
    print()
    print("The following configuration options have been completely removed")
    print()
    for k in removed:
        print(f"-  {k}")
    print()
