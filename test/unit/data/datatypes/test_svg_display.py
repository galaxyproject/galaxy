from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from galaxy.datatypes.xml import GenericXml

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 300"><text>Example</text></svg>'


@pytest.fixture
def svg_display(tmp_path):
    path = tmp_path / "image.svg"
    datatype = GenericXml()
    dataset = SimpleNamespace(
        id=1,
        hid=1,
        name="image",
        extension="svg",
        datatype=datatype,
        dataset=SimpleNamespace(file_size=0, object_store=None, extra_files_path_name="extra"),
        get_file_name=lambda: str(path),
        get_mime=lambda: "image/svg+xml",
    )
    trans = Mock()
    trans.app.config.serve_xss_vulnerable_mimetypes = False
    trans.app.config.sanitize_all_html = True
    trans.app.object_store.get_filename.return_value = str(path)
    trans.app.datatypes_registry.get_composite_extensions.return_value = []

    def display(content=SVG, **kwd):
        path.write_bytes(content)
        body, headers = datatype.display_data(trans, dataset, **kwd)
        if hasattr(body, "read"):
            with body:
                body = body.read()
        return body, headers

    return display, trans, dataset


@pytest.mark.parametrize("padding", [0, 1_100_000])
@pytest.mark.parametrize("preview", [False, True])
@pytest.mark.parametrize("serve_vulnerable", [False, True])
def test_svg_image_response(svg_display, padding, preview, serve_vulnerable):
    display, trans, _ = svg_display
    trans.app.config.serve_xss_vulnerable_mimetypes = serve_vulnerable
    content = SVG.replace(b"</svg>", b"<!--" + b" " * padding + b"--></svg>")
    body, headers = display(content, as_image="true", preview=preview)
    assert body == content
    assert headers["content-type"] == "image/svg+xml"
    assert headers["X-Content-Type-Options"] == "nosniff"
    policy = headers["Content-Security-Policy"]
    assert "sandbox;" in policy
    assert "default-src 'none'" in policy
    assert "allow-scripts" not in policy
    assert "x-content-truncated" not in headers


@pytest.mark.parametrize("options", [{}, {"as_image": "false"}])
def test_normal_svg_response_is_still_plain_text(svg_display, options):
    display, _, _ = svg_display
    body, headers = display(**options)
    assert body == SVG
    assert headers["content-type"] == "text/plain"
    assert "Content-Security-Policy" not in headers


def test_normal_large_svg_preview_is_still_truncated(svg_display):
    display, _, _ = svg_display
    body, headers = display(SVG + b" " * 1_100_000, preview=True)
    assert len(body) == 1_000_000
    assert headers["x-content-truncated"] == "1000000"
    assert headers["content-type"] == "text/plain; charset=utf-8"


def test_extra_file_svg_image_response(svg_display):
    display, _, _ = svg_display
    body, headers = display(filename="image.svg", as_image="true")
    assert body == SVG
    assert headers["content-type"] == "image/svg+xml"
    assert "sandbox;" in headers["Content-Security-Policy"]


@pytest.mark.parametrize("mime", ["application/xml", "text/html", "text/plain", "image/png"])
def test_image_flag_does_not_change_other_mime_types(svg_display, mime):
    display, trans, dataset = svg_display
    trans.app.config.sanitize_all_html = False
    dataset.get_mime = lambda: mime
    _, headers = display(as_image="true")
    assert headers["content-type"] == ("text/plain" if mime == "application/xml" else mime)
    assert "Content-Security-Policy" not in headers


def test_svg_download_ignores_image_flag(svg_display):
    display, _, _ = svg_display
    body, headers = display(as_image="true", to_ext="svg")
    assert body == SVG
    assert headers["content-type"] == "application/octet-stream"
    assert "Content-Disposition" in headers
    assert "Content-Security-Policy" not in headers
