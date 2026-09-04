"""Test custom template configuration and rendering."""

import re

import pytest

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


def test_html_templates_autoescape_user_supplied_content_when_enabled(tmp_path):
    """HTML templates must autoescape variable output when autoescape is enabled."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / "mail/inject.html"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(">>>>>> body\n{{ value }}")
    output = templates.render(
        "mail/inject.html", {"value": "<script>alert(1)</script>"}, custom_templates_dir, autoescape=True
    )
    assert "<script>" not in output
    assert "&lt;script&gt;" in output


def test_html_templates_autoescape_by_default(tmp_path):
    """Autoescape is now default: new callers are secured by default."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / "mail/inject.html"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(">>>>>> body\n{{ value }}")
    output = templates.render("mail/inject.html", {"value": "<b>bold</b>"}, custom_templates_dir)
    assert output == "&lt;b&gt;bold&lt;/b&gt;"


def test_html_templates_can_opt_out_of_autoescape(tmp_path):
    """Existing HTML templates can opt out to keep raw behavior."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / "mail/inject.html"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(">>>>>> body\n{{ value }}")
    output = templates.render("mail/inject.html", {"value": "<b>bold</b>"}, custom_templates_dir, autoescape=False)
    assert output == "<b>bold</b>"


def test_txt_templates_do_not_escape_content(tmp_path):
    """Plain-text templates are not autoescaped by default (even without opt out)."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / "mail/inject.txt"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(">>>>>> body\n{{ value }}")
    output = templates.render("mail/inject.txt", {"value": "<b>bold</b>"}, custom_templates_dir)
    assert output == "<b>bold</b>"


def test_txt_templates_explicit_autoescape_true_is_rejected(tmp_path):
    """Explicitly opting into autoescape for a .txt template is a programming error."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / "mail/inject.txt"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(">>>>>> body\n{{ value }}")
    with pytest.raises(ValueError, match="must never be autoescaped"):
        templates.render("mail/inject.txt", {"value": "<b>bold</b>"}, custom_templates_dir, autoescape=True)


def test_html_templates_respect_safe_filter(tmp_path):
    """Trusted, pre-rendered HTML marked with | safe must pass through unescaped."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / "mail/safe.html"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(">>>>>> body\n{{ value | safe }}")
    output = templates.render("mail/safe.html", {"value": "<p>ok</p>"}, custom_templates_dir, autoescape=True)
    assert output == "<p>ok</p>"


def test_template_can_include_a_packaged_partial(tmp_path):
    """A template can {% include %} a partial bundled with the package."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / "mail/uses_partial.html"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    # The packaged tool-request field partial renders the requested tool row.
    with open(template_path, "w") as f:
        f.write(">>>>>> body\n{% include 'mail/notifications/_tool_installation_request_fields.html' %}")
    content = {
        "tools": [
            {
                "name": "FastQC",
                "tool_shed_id": None,
                "tool_url": None,
                "description": "QC tool",
                "scientific_domain": None,
                "requested_version": None,
            }
        ],
        "additional_remarks": None,
    }
    output = templates.render("mail/uses_partial.html", {"content": content}, custom_templates_dir)
    assert "FastQC" in output
    assert "Description" in output
    assert "QC tool" in output


def test_custom_partial_overrides_packaged_partial(tmp_path):
    """A partial in the custom templates dir takes precedence over the packaged one."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / "mail/uses_partial.html"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(">>>>>> body\n{% include 'mail/notifications/_tool_installation_request_fields.html' %}")
    # Custom partial shadows the packaged one (custom-first precedence).
    custom_partial = custom_templates_dir / "mail/notifications/_tool_installation_request_fields.html"
    custom_partial.parent.mkdir(parents=True, exist_ok=True)
    with open(custom_partial, "w") as f:
        f.write("CUSTOM-PARTIAL-{{ content['tool_names'][0] }}")
    output = templates.render("mail/uses_partial.html", {"content": {"tool_names": ["MyTool"]}}, custom_templates_dir)
    assert "CUSTOM-PARTIAL-MyTool" in output


def test_partial_output_is_autoescaped(tmp_path):
    """Autoescape applies to partial output (a partial variable must be escaped)."""
    custom_templates_dir = tmp_path
    template_path = custom_templates_dir / "mail/uses_partial.html"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w") as f:
        f.write(">>>>>> body\n{% include 'mail/notifications/_tool_installation_request_fields.html' %}")
    content = {
        "tools": [
            {
                "name": "<script>x</script>",
                "tool_shed_id": None,
                "tool_url": None,
                "description": "d",
                "scientific_domain": None,
                "requested_version": None,
            }
        ],
        "additional_remarks": None,
    }
    output = templates.render("mail/uses_partial.html", {"content": content}, custom_templates_dir)
    assert "<script>" not in output
    assert "&lt;script&gt;" in output


def test_tool_installation_request_email_renders_with_partial(tmp_path):
    """The bundled admin tool-request template renders end-to-end via its partial include."""
    custom_templates_dir = tmp_path
    content = {
        "category": "tool_installation_request",
        "tools": [
            {
                "name": "BWA",
                "tool_shed_id": None,
                "tool_url": "https://github.com/lh3/bwa",
                "description": "Aligner",
                "scientific_domain": "Genomics",
                "requested_version": "0.7.17",
            }
        ],
        "requester_email": "user@example.org",
        "workflow_id": None,
        "additional_remarks": None,
    }
    output = templates.render(
        "mail/notifications/tool_installation_request-email.html",
        {
            "content": content,
            "name": "Admin",
            "hostname": "galaxy.example",
            "galaxy_url": "https://galaxy.example",
            "workflow_name": None,
        },
        custom_templates_dir,
    )
    # Shared partial content + admin-only rows both present
    assert "BWA" in output
    assert "Aligner" in output
    assert "user@example.org" in output  # admin-only "Requested by" row
    assert "<!DOCTYPE html>" in output


def _render_txt_tool_request_email(tmp_path, content):
    return templates.render(
        "mail/notifications/tool_installation_request-email.txt",
        {
            "content": content,
            "name": "Admin",
            "hostname": "galaxy.example",
            "date": "August 05, 2026",
            "galaxy_url": None,
            "workflow_name": None,
            "notification_settings_url": None,
            "contact_email": None,
        },
        tmp_path,
    )


def test_tool_installation_request_text_email_renders_multiple_tools(tmp_path):
    """The multi-tool branch of the text partial lists each tool with its own details."""
    content = {
        "category": "tool_installation_request",
        "tools": [
            {
                "name": "bwa",
                "tool_shed_id": "toolshed.g2.bx.psu.edu/repos/devteam/bwa",
                "tool_url": None,
                "description": "Short read aligner",
                "scientific_domain": None,
                "requested_version": "0.7.17",
            },
            {
                "name": None,
                "tool_shed_id": "toolshed.g2.bx.psu.edu/repos/devteam/samtools",
                "tool_url": None,
                "description": None,
                "scientific_domain": None,
                "requested_version": None,
            },
        ],
        "requester_email": "user@example.org",
        "workflow_id": None,
        "additional_remarks": None,
    }
    output = _render_txt_tool_request_email(tmp_path, content)
    assert "new tools" in output  # plural intro
    # Each tool renders as a list entry; details are indented under their tool.
    # The indentation depths matter (they attribute details to a tool); the
    # exact label padding is presentation and is not pinned.
    assert re.search(r"^  - bwa$", output, re.MULTILINE)
    assert re.search(r"^    Tool shed: +toolshed\.g2\.bx\.psu\.edu/repos/devteam/bwa$", output, re.MULTILINE)
    assert re.search(r"^    Description: +Short read aligner$", output, re.MULTILINE)
    assert re.search(r"^    Version: +0\.7\.17$", output, re.MULTILINE)
    # A tool identified only by shed id uses the shed id as its label (no separate row).
    assert re.search(r"^  - toolshed\.g2\.bx\.psu\.edu/repos/devteam/samtools$", output, re.MULTILINE)
    assert output.count("Tool shed:") == 1
    # No stray blank lines inside the field block.
    assert "\n\n  - " not in output
    assert "\n\nRequested by:" not in output


def test_tool_installation_request_text_email_does_not_repeat_label_values(tmp_path):
    """A tool identified only by its URL renders the URL once (as the label), not again as a URL row."""
    content = {
        "category": "tool_installation_request",
        "tools": [
            {
                "name": None,
                "tool_shed_id": None,
                "tool_url": "https://x.org/tool",
                "description": None,
                "scientific_domain": None,
                "requested_version": None,
            }
        ],
        "requester_email": "user@example.org",
        "workflow_id": None,
        "additional_remarks": None,
    }
    output = _render_txt_tool_request_email(tmp_path, content)
    assert re.search(r"^Tool: +https://x\.org/tool$", output, re.MULTILINE)
    assert "URL:" not in output


def test_tool_installation_request_text_email_indents_multiline_fields(tmp_path):
    """Continuation lines of multiline fields are indented, so user text cannot mimic a field row."""
    content = {
        "category": "tool_installation_request",
        "tools": [
            {
                "name": "bwa",
                "tool_shed_id": None,
                "tool_url": None,
                "description": None,
                "scientific_domain": None,
                "requested_version": None,
            }
        ],
        "requester_email": "real@example.org",
        "workflow_id": None,
        "additional_remarks": "ok\nRequested by: forged@example.org",
    }
    output = _render_txt_tool_request_email(tmp_path, content)
    # The forged line is indented under Remarks, not at column 0.
    assert "\nRequested by: forged@example.org" not in output
    assert "\n              Requested by: forged@example.org" in output
    # The genuine stamped row still renders at column 0.
    assert "\nRequested by: real@example.org" in output
