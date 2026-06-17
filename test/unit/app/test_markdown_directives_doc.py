"""Guard that directives.yml, the generated directives.md, and the validator stay in sync."""

import importlib.util
import os

GALAXY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
SCRIPT_PATH = os.path.join(GALAXY_ROOT, "scripts", "markdown_directives_doc.py")

_spec = importlib.util.spec_from_file_location("markdown_directives_doc", SCRIPT_PATH)
assert _spec and _spec.loader
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def test_directives_yml_consistent_with_validator():
    parameter_sets, directives = gen.load_directives()
    requirements = gen.load_requirements()
    errors = gen.consistency_errors(parameter_sets, directives, requirements)
    assert not errors, "directives.yml drifted from markdown_parse.py:\n" + "\n".join(errors)


def test_directives_md_up_to_date():
    parameter_sets, directives = gen.load_directives()
    rendered = gen.render_markdown(parameter_sets, directives) + "\n"
    with open(gen.OUTPUT_MD) as f:
        current = f.read()
    assert current == rendered, (
        "directives.md is out of date; regenerate with "
        "`python scripts/markdown_directives_doc.py` (or `make client-gen-markdown-directives`)."
    )
