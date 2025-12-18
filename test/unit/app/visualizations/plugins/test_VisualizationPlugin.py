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
