"""The route that serves runtime-installed visualization packages' static files."""

import os
from unittest.mock import MagicMock

import pytest

from galaxy.exceptions import ObjectNotFound
from galaxy.webapps.base.api import GalaxyFileResponse
from galaxy.webapps.galaxy.api.plugins import FastAPIPlugins


def _controller(registry):
    controller = FastAPIPlugins.__new__(FastAPIPlugins)
    controller.app = MagicMock(visualizations_registry=registry)
    return controller


def test_serves_the_resolved_file_and_revalidates(tmp_path):
    index = tmp_path / "index.js"
    index.write_text("runtime")
    registry = MagicMock()
    registry.get_runtime_static_file.return_value = str(index)

    response = _controller(registry).static_file(plugin_name="h5web", file_path="index.js")

    registry.get_runtime_static_file.assert_called_once_with("h5web", "index.js")
    assert isinstance(response, GalaxyFileResponse)
    assert os.path.samefile(response.path, index)
    # files change in place when a package is updated
    assert response.headers["cache-control"] == "no-cache"


def test_unresolvable_files_are_not_found():
    registry = MagicMock()
    registry.get_runtime_static_file.side_effect = ObjectNotFound("nope")
    with pytest.raises(ObjectNotFound):
        _controller(registry).static_file(plugin_name="builtin", file_path="builtin.xml")
