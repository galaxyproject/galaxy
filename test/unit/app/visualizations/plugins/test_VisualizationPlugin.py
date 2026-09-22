"""
Test lib/galaxy/visualization/plugins/plugin.
"""

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.visualization.plugins.plugin import VisualizationPlugin
from . import VisualizationsBase_TestCase


class TestVisualizationsPlugin(VisualizationsBase_TestCase):

    def test_default_init(self):
        """
        A plugin with no context passed in should have sane defaults.
        """
        vis_dir = galaxy_mock.MockDir(
            {
                "config": {"vis1.xml": ""},
                "static": {},
            }
        )
        plugin = VisualizationPlugin(vis_dir.root_path, "myvis", {})
        assert plugin.name == "myvis"
        assert plugin.path == vis_dir.root_path
        assert plugin.config == {}
        assert plugin.url_prefix == ""

    def test_href_without_url_prefix(self):
        """Without a url_prefix, href is just the static path."""
        plugin = VisualizationPlugin("/path", "myvis", {})
        assert plugin.to_dict()["href"] == plugin.static_path
        assert plugin.to_dict()["href"] == "/static/plugins/visualizations/myvis/static"

    def test_href_with_url_prefix(self):
        """A url_prefix is prepended to the static path when building href."""
        plugin = VisualizationPlugin("/path", "myvis", {}, url_prefix="/galaxy")
        assert plugin.to_dict()["href"] == "/galaxy/static/plugins/visualizations/myvis/static"
