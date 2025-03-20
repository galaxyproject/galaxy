"""
Test lib/galaxy/visualization/plugins/registry.
"""

import os

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
additional_templates_dir = os.path.join(glx_dir, "config", "plugins", "visualizations", "common", "templates")
vis_reg_path = "config/plugins/visualizations"

config1 = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE visualization SYSTEM "../../visualization.dtd">
<visualization name="scatterplot">
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
    <specs>
        <exports>
            <exports>png</exports>
            <exports>svg</exports>
            <exports>pdf</exports>
        </exports>
    </specs>
    <template>scatterplot.mako</template>
</visualization>
"""


class TestVisualizationsRegistry(VisualizationsBase_TestCase):
    def test_plugin_load_from_repo(self):
        """should attempt load if criteria met"""
        mock_app = galaxy_mock.MockApp(root=glx_dir)
        plugin_mgr = VisualizationsRegistry(mock_app, directories_setting=vis_reg_path, template_cache_dir=None)

        expected_plugins_path = os.path.join(glx_dir, vis_reg_path)
        assert plugin_mgr.base_url == "visualizations"
        assert plugin_mgr.directories == [expected_plugins_path]

        scatterplot = plugin_mgr.plugins["scatterplot"]
        assert scatterplot.name == "scatterplot"
        assert scatterplot.path == os.path.join(expected_plugins_path, "scatterplot")
        assert scatterplot.base_url == "/".join((plugin_mgr.base_url, scatterplot.name))
        assert scatterplot.serves_templates
        assert scatterplot.template_path == os.path.join(scatterplot.path, "templates")
        assert scatterplot.template_lookup.__class__.__name__ == "TemplateLookup"

        trackster = plugin_mgr.plugins["trackster"]
        assert trackster.name == "trackster"
        assert trackster.path == os.path.join(expected_plugins_path, "trackster")
        assert trackster.base_url == "/".join((plugin_mgr.base_url, trackster.name))
        assert not trackster.serves_templates

    def test_plugin_load(self):
        """"""
        mock_app_dir = galaxy_mock.MockDir(
            {
                "plugins": {
                    "vis1": {
                        "config": {"vis1.xml": config1},
                        "static": {},
                        "templates": {},
                    },
                    "vis2": {"config": {"vis2.xml": config1}},
                    "not_a_vis1": {
                        "config": {"vis1.xml": "blerbler"},
                    },
                    # empty
                    "not_a_vis2": {},
                    "not_a_vis3": "blerbler",
                    # bad config
                    "not_a_vis4": {"config": {"not_a_vis4.xml": "blerbler"}},
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
        assert plugin_mgr.directories == [expected_plugins_path]
        assert sorted(plugin_mgr.plugins.keys()) == expected_plugin_names

        vis1 = plugin_mgr.plugins["vis1"]
        assert vis1.name == "vis1"
        assert vis1.path == os.path.join(expected_plugins_path, "vis1")
        assert vis1.base_url == "/".join((plugin_mgr.base_url, vis1.name))
        assert vis1.serves_templates
        assert vis1.template_path == os.path.join(vis1.path, "templates")
        assert vis1.template_lookup.__class__.__name__ == "TemplateLookup"

        vis1_as_dict = vis1.to_dict()
        assert vis1_as_dict["specs"]
        specs = vis1_as_dict["specs"]
        assert "exports" in specs
        exports = specs["exports"]
        assert len(exports) == 3
        assert "png" in exports
        assert "svg" in exports
        assert "pdf" in exports

        vis2 = plugin_mgr.plugins["vis2"]
        assert vis2.name == "vis2"
        assert vis2.path == os.path.join(expected_plugins_path, "vis2")
        assert vis2.base_url == "/".join((plugin_mgr.base_url, vis2.name))
        assert not vis2.serves_templates

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
            <entry_point entry_point_type="script" container="mycontainer" src="mysrc" css="mycss"></entry_point>
        </visualization>
        """
        )

        mock_app_dir = galaxy_mock.MockDir(
            {
                "plugins": {
                    "jstest": {"config": {"jstest.xml": script_entry_config}, "static": {}},
                }
            }
        )
        mock_app = galaxy_mock.MockApp(root=mock_app_dir.root_path)
        plugin_mgr = VisualizationsRegistry(
            mock_app, directories_setting="plugins", template_cache_dir=template_cache_dir
        )
        script_entry = plugin_mgr.plugins["jstest"]

        assert isinstance(script_entry, plugin.ScriptVisualizationPlugin)
        assert script_entry.name == "jstest"
        assert script_entry.serves_templates

        trans = galaxy_mock.MockTrans()
        script_entry._set_up_template_plugin(mock_app_dir.root_path, [additional_templates_dir])
        response = script_entry.render(trans=trans, embedded=True)
        assert '<script type="module" src="mysrc">' in response
        assert '<link rel="stylesheet" href="mycss">' in response
        assert "<div id=\"mycontainer\" data-incoming='{}'></div>" in response
        mock_app_dir.remove()


# -----------------------------------------------------------------------------
# TODO: config parser tests (in separate file)
