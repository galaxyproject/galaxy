"""
Test lib/galaxy/visualization/plugins/registry.
"""

import os
import re

from markupsafe import escape

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.util import (
    clean_multiline_string,
    galaxy_directory,
)
from galaxy.visualization.plugins import plugin
from galaxy.visualization.plugins.registry import VisualizationsRegistry
from . import VisualizationsBase_TestCase

glx_dir = galaxy_directory()
template_cache_dir = os.path.join(glx_dir, "database", "compiled_templates")
vis_reg_path = "config/plugins/visualizations"

config1 = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE visualization SYSTEM "../../visualization.dtd">
<visualization name="Minimal Example" hidden="true">
    <description>Welcome to the Minimal JS-Based Example Plugin.</description>
    <data_sources>
        <data_source>
            <model_class>HistoryDatasetAssociation</model_class>
            <test type="isinstance" test_attr="datatype" result_type="datatype">tabular.Tabular</test>
            <to_param param_attr="id">dataset_id</to_param>
        </data_source>
    </data_sources>
    <params>
        <param type="dataset" var_name_in_template="hda" required="true">dataset_id</param>
    </params>
    <entry_point entry_point_type="script" src="script.js" />
    <settings>
        <input>
            <name>setting_input</name>
            <help>setting help</help>
            <type>setting_type</type>
        </input>
    </settings>
    <tracks>
        <input>
            <name>track_input</name>
            <help>track help</help>
            <type>track_type</type>
        </input>
    </tracks>
    <specs>
        <exports>
            <exports>export_a</exports>
            <exports>export_b</exports>
            <exports>export_c</exports>
        </exports>
    </specs>
</visualization>
"""


class TestVisualizationsRegistry(VisualizationsBase_TestCase):
    def test_plugin_load_from_repo(self):
        """should attempt load if criteria met"""
        mock_app = galaxy_mock.MockApp(root=glx_dir)
        plugin_mgr = VisualizationsRegistry(mock_app, directories_setting=vis_reg_path, template_cache_dir=None)

        expected_plugins_path = os.path.join(glx_dir, vis_reg_path)
        assert plugin_mgr.base_url == "visualizations"
        assert expected_plugins_path in plugin_mgr.directories

        example = plugin_mgr.plugins["example"]
        assert example.name == "example"
        assert example.path == os.path.join(expected_plugins_path, "example")
        assert example.base_url == "/".join((plugin_mgr.base_url, example.name))

    def test_plugin_load(self):
        """"""
        mock_app_dir = galaxy_mock.MockDir(
            {
                "plugins": {
                    "vis1": {
                        "static": {"vis1.xml": config1},
                        "templates": {},
                    },
                    "vis2": {"static": {"vis2.xml": config1}},
                    "not_a_vis1": {
                        "static": {"vis1.xml": "blerbler"},
                    },
                    # empty
                    "not_a_vis2": {},
                    "not_a_vis3": "blerbler",
                    # bad config
                    "not_a_vis4": {"static": {"not_a_vis4.xml": "blerbler"}},
                    "not_a_vis5": {
                        # no config
                        "static": {},
                        "templates": {},
                    },
                }
            }
        )
        mock_app = galaxy_mock.MockApp(root=mock_app_dir.root_path)
        plugin_mgr = VisualizationsRegistry(
            mock_app, directories_setting="plugins", template_cache_dir=template_cache_dir
        )

        expected_plugins_path = os.path.join(mock_app_dir.root_path, "plugins")
        expected_plugin_names = ["vis1", "vis2"]

        assert plugin_mgr.base_url == "visualizations"
        assert expected_plugins_path in plugin_mgr.directories
        assert sorted(plugin_mgr.plugins.keys()) == expected_plugin_names

        vis1 = plugin_mgr.plugins["vis1"]
        assert vis1.name == "vis1"
        assert vis1.path == os.path.join(expected_plugins_path, "vis1")
        assert vis1.base_url == "/".join((plugin_mgr.base_url, vis1.name))

        vis1_as_dict = vis1.to_dict()
        assert vis1_as_dict["specs"]
        specs = vis1_as_dict["specs"]
        assert "exports" in specs
        exports = specs["exports"]
        assert len(exports) == 3
        assert "export_a" in exports
        assert "export_b" in exports
        assert "export_c" in exports

        vis2 = plugin_mgr.plugins["vis2"]
        assert vis2.name == "vis2"
        assert vis2.path == os.path.join(expected_plugins_path, "vis2")
        assert vis2.base_url == "/".join((plugin_mgr.base_url, vis2.name))

        mock_app_dir.remove()

    def test_script_entry(self):
        """"""
        script_entry_config = clean_multiline_string(
            """\
        <?xml version="1.0" encoding="UTF-8"?>
        <visualization name="js-test">
            <data_sources>
                <data_source>
                    <model_class>HistoryDatasetAssociation</model_class>
                </data_source>
            </data_sources>
            <entry_point container="mycontainer" src="mysrc" css="mycss"></entry_point>
        </visualization>
        """
        )

        mock_app_dir = galaxy_mock.MockDir(
            {
                "plugins": {
                    "jstest": {"static": {"jstest.xml": script_entry_config}},
                }
            }
        )
        mock_app = galaxy_mock.MockApp(root=mock_app_dir.root_path)
        plugin_mgr = VisualizationsRegistry(
            mock_app, directories_setting="plugins", template_cache_dir=template_cache_dir
        )
        script_entry = plugin_mgr.plugins["jstest"]

        assert isinstance(script_entry, plugin.VisualizationPlugin)
        assert script_entry.name == "jstest"

        trans = galaxy_mock.MockTrans()
        response = script_entry.to_dict()
        entry_point_attr = response["entry_point"]["attr"]
        assert entry_point_attr["container"] == "mycontainer"
        assert entry_point_attr["src"] == "mysrc"
        assert entry_point_attr["css"] == "mycss"
        mock_app_dir.remove()
