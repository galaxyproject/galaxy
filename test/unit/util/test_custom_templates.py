"""Test custom template configuration and rendering."""

import os

from galaxy.util.custom_templates import template


TEMPLATE_FNAME = "default.html"  # This could also be a relative path e.g. mail/default.html
TEMPLATE = """
Here's my default template. It starts with a comment section to let admins
know how to use it.

>>>>>> The actual template starts from the next line
<h1>{{ title }}</h1>
{{ body }}

"""

CONTEXT = {
    'title': 'foo',
    'body': 'bar',
}

EXPECTED_OUTPUT = "<h1>foo</h1>\nbar\n"


def test_it_can_render_a_default_template(tmp_path):
    try:
        custom_templates_dir = tmp_path
        template_path = template.DEFAULT_TEMPLATES_DIR / TEMPLATE_FNAME

        with open(template_path, 'w') as f:
            f.write(TEMPLATE)

        # It won't find a custom template but will fall back on the
        # default we just created
        output = template.render(
            TEMPLATE_FNAME,
            CONTEXT,
            custom_templates_dir,
        )
        assert output == EXPECTED_OUTPUT
    finally:
        if template_path.exists():
            os.remove(template_path)


def test_it_can_render_a_custom_template(tmp_path):
    custom_templates_dir = tmp_path
    with open(custom_templates_dir / TEMPLATE_FNAME, 'w') as f:
        f.write(TEMPLATE)
    # It should find the custom template
    output = template.render(
        TEMPLATE_FNAME,
        CONTEXT,
        custom_templates_dir,
    )
    assert output == EXPECTED_OUTPUT
