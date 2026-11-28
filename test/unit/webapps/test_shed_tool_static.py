from typing import (
    Any,
    cast,
)

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.util.bunch import Bunch
from galaxy.web.framework.base import Response
from galaxy.webapps.base.webapp import GalaxyWebTransaction
from galaxy.webapps.galaxy.controllers.shed_tool_static import ShedToolStatic

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def test_shed_tool_static_serves_images_sandboxed(tmp_path):
    images = tmp_path / "static" / "images"
    images.mkdir(parents=True)
    (images / "figure.svg").write_bytes(SVG)
    tool = Bunch(_repository_dir=str(tmp_path))
    app: Any = MockApp()
    app.toolbox = Bunch(get_tool=lambda guid: tool, materialize_tool=lambda tool, reason: tool)
    trans = Bunch(app=app, response=Response())

    with ShedToolStatic(app).index(
        cast(GalaxyWebTransaction, trans), "toolshed.example.org", "iuc", "repo", "tool", "1.0", "figure.svg"
    ) as fh:
        assert fh.read() == SVG

    headers = trans.response.headers
    assert headers["Content-Security-Policy"] == (
        "default-src 'none'; img-src data:; font-src data:; style-src 'unsafe-inline'; sandbox"
    )
    assert headers["X-Content-Type-Options"] == "nosniff"
