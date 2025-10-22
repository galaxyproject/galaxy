"""
Test lib/galaxy/visualization/plugins/plugin.
"""

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.util import clean_multiline_string
from galaxy.visualization.plugins import (
    plugin as vis_plugin,
    resource_parser,
    utils as vis_utils,
)
from . import VisualizationsBase_TestCase


class TestVisualizationsPlugin(VisualizationsBase_TestCase):
    plugin_class = vis_plugin.VisualizationPlugin

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
        plugin = self.plugin_class(vis_dir.root_path, "myvis", {})
        assert plugin.name == "myvis"
        assert plugin.path == vis_dir.root_path
        assert plugin.config == {}
