"""Test custom template configuration and rendering."""

from galaxy.config import templates

TEMPLATE_RELPATH = "mail/activation-email.html"
CONTEXT = {"name": "Jane Doe"}
CUSTOM_TEMPLATE = """
Here's my custom template. It starts with a comment section to let admins
know how to use it.

>>>>>> The actual template starts from the next line
This is my custom template!
Name: {{ name }}
"""
DEFAULT_TEMPLATE_HEADER_SUBSTRING = "The following variables are available"
DEFAULT_TEMPLATE_OUTPUT_SUBSTRING = "<!DOCTYPE html>"
CUSTOM_TEMPLATE_OUTPUT = f"This is my custom template!\nName: {CONTEXT['name']}"


def test_it_can_render_a_default_template(tmp_path):
    """It should fall back on codebase default."""
    custom_templates_dir = tmp_path
    output = templates.render(
        TEMPLATE_RELPATH,
        CONTEXT,
        custom_templates_dir,
    )
    # Make sure it's parsed out the doc header
    assert DEFAULT_TEMPLATE_HEADER_SUBSTRING not in output
    # Make sure the template content is present
    assert DEFAULT_TEMPLATE_OUTPUT_SUBSTRING in output


def test_it_can_render_a_custom_template(tmp_path):
    """It should use the custom template and ignore the default."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / TEMPLATE_RELPATH
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(CUSTOM_TEMPLATE)
    # It should find the custom template
    output = templates.render(
        TEMPLATE_RELPATH,
        CONTEXT,
        custom_templates_dir,
    )
    assert output == CUSTOM_TEMPLATE_OUTPUT
