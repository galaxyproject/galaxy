from tool_shed.util.readme_util import render_readme


def test_rst_readme_is_not_evaluated_as_template():
    html = render_readme("README.rst", "Sum: ${7*6} <% import os %>\n")
    assert "42" not in html
    assert "${7*6}" in html


def test_rst_readme_raw_html_is_sanitized():
    rst = "Title\n\n.. raw:: html\n\n   <script>alert(1)</script><img src=x onerror=alert(2)>\n"
    html = render_readme("README.rst", rst)
    assert "<script" not in html
    assert "onerror" not in html


def test_rst_readme_keeps_formatting():
    html = render_readme("README.rst", "Some **bold** text and a `link <https://galaxyproject.org>`__.\n")
    assert "<strong>bold</strong>" in html
    assert 'href="https://galaxyproject.org"' in html


def test_plain_readme_is_escaped():
    html = render_readme("README.txt", "<script>alert(1)</script>")
    assert "<script" not in html
    assert "&lt;script&gt;" in html


def test_rst_readme_substitutes_legacy_placeholders(monkeypatch):
    def url_for(path, qualified=False):
        return "https://shed.example.org/" if qualified else "/shed_static"

    monkeypatch.setattr("tool_shed.util.readme_util.web.url_for", url_for)
    rst = "See `home <${host_url}view>`__.\n\n.. image:: ${static_path}/logo.png\n"
    html = render_readme("README.rst", rst)
    assert 'href="https://shed.example.org/view"' in html
    assert 'src="/shed_static/logo.png"' in html
    assert "${" not in html


def test_rst_readme_keeps_tables_code_and_images():
    rst = (
        "+---+---+\n| a | b |\n+---+---+\n\n"
        "::\n\n    samtools view in.bam\n\n"
        ".. image:: https://example.org/logo.png\n"
    )
    html = render_readme("README.rst", rst)
    assert "<table" in html
    assert "<pre" in html
    assert 'src="https://example.org/logo.png"' in html
