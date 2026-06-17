"""Guard that directives.yml and everything generated from it stay in sync.

directives.yml is the source of truth; directives.md, requirements.yml and the
_markdown_directives.py validator registry are generated from it by
scripts/markdown_directives_doc.py.
"""

import importlib.util
import os

import pytest

# Resolve symlinks: under the packages test harness this file is reached via a
# symlink (packages/app/tests/app -> test/unit/app), so __file__ alone would
# resolve GALAXY_ROOT to packages/ instead of the real source tree.
GALAXY_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir, os.pardir)
)
SCRIPT_PATH = os.path.join(GALAXY_ROOT, "scripts", "markdown_directives_doc.py")

_spec = importlib.util.spec_from_file_location("markdown_directives_doc", SCRIPT_PATH)
assert _spec and _spec.loader
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_directives_yml_consistent():
    shared_arguments, parameter_sets, directives = gen.load_directives()
    containers = gen.dispatch_containers()
    errors = gen.consistency_errors(shared_arguments, parameter_sets, directives, containers)
    assert not errors, "directives.yml is inconsistent:\n" + "\n".join(errors)


def _artifacts():
    shared_arguments, parameter_sets, directives = gen.load_directives()
    return gen.build_artifacts(shared_arguments, parameter_sets, directives)


@pytest.mark.parametrize("path,rendered", _artifacts(), ids=lambda p: os.path.basename(p) if isinstance(p, str) else "")
def test_generated_artifact_up_to_date(path, rendered):
    with open(path) as f:
        current = f.read()
    assert current == rendered, (
        f"{os.path.basename(path)} is out of date; regenerate with "
        "`python scripts/markdown_directives_doc.py` (or `make client-gen-markdown-directives`)."
    )
