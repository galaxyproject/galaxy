"""
Test lib/galaxy/visualization/plugins/plugin.
"""
import unittest

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.util import clean_multiline_string
from galaxy.visualization.plugins import plugin as vis_plugin
from galaxy.visualization.plugins import resource_parser
from galaxy.visualization.plugins import utils as vis_utils
from . import VisualizationsBase_TestCase


class VisualizationsPlugin_TestCase(VisualizationsBase_TestCase):
    plugin_class = vis_plugin.VisualizationPlugin

    def test_default_init(self):
        """
        A plugin with no context passed in should have sane defaults.
        """
        vis_dir = galaxy_mock.MockDir(
            {
                "config": {"vis1.xml": ""},
                "static": {},
                "templates": {},
            }
        )
        plugin = self.plugin_class(galaxy_mock.MockApp(), vis_dir.root_path, "myvis", {})
        self.assertEqual(plugin.name, "myvis")
        self.assertEqual(plugin.path, vis_dir.root_path)
        self.assertEqual(plugin.config, {})
        self.assertEqual(plugin.base_url, "myvis")
        # template
        self.assertTrue(plugin.serves_templates)
        self.assertEqual(plugin.template_path, vis_dir.root_path + "/templates")
        self.assertEqual(plugin.template_lookup.__class__.__name__, "TemplateLookup")
        # resource parser
        self.assertIsInstance(plugin.resource_parser, resource_parser.ResourceParser)

    def test_init_with_context(self):
        """
        A plugin with context passed in should use those in it's set up.
        """
        vis_dir = galaxy_mock.MockDir(
            {
                "config": {"vis1.xml": ""},
                "static": {},
                "templates": {},
            }
        )
        context = dict(base_url="u/wot/m8", template_cache_dir="template_cache", additional_template_paths=["one"])
        plugin = self.plugin_class(galaxy_mock.MockApp(), vis_dir.root_path, "myvis", {}, context=context)
        self.assertEqual(plugin.base_url, "u/wot/m8/myvis")
        self.assertEqual(plugin.template_lookup.__class__.__name__, "TemplateLookup")

    def test_init_without_static_or_templates(self):
        """
        A plugin that has neither template or static directory should serve neither.
        """
        vis_dir = galaxy_mock.MockDir({"config": {"vis1.xml": ""}})
        plugin = self.plugin_class(galaxy_mock.MockApp(), vis_dir.root_path, "myvis", dict())
        self.assertFalse(plugin.serves_templates)
        # not sure what this would do, but...

    def test_build_render_vars_default(self):
        """
        Render vars passed to render should default properly.
        """
        # well, that's kind of a lot of typing to say nothing new
        config = dict(name="Cat Fancy Magazine's Genomic Visualization")
        plugin = self.plugin_class(galaxy_mock.MockApp(), "", "myvis", config)

        render_vars = plugin._build_render_vars(config)
        self.assertEqual(render_vars["visualization_name"], plugin.name)
        self.assertEqual(render_vars["visualization_display_name"], plugin.config["name"])
        self.assertEqual(render_vars["title"], None)
        self.assertEqual(render_vars["saved_visualization"], None)
        self.assertEqual(render_vars["visualization_id"], None)
        self.assertEqual(render_vars["query"], {})
        self.assertIsInstance(render_vars["config"], vis_utils.OpenObject)
        self.assertEqual(render_vars["config"].__dict__, {})

    def test_build_config(self):
        """ """
        plugin_config: dict = dict()
        plugin = self.plugin_class(galaxy_mock.MockApp(), "", "myvis", plugin_config)
        config = plugin._build_config({})
        self.assertIsInstance(config, vis_utils.OpenObject)
        self.assertEqual(config.__dict__, {})

        # existing should flow through
        plugin_config = dict()
        plugin = self.plugin_class(galaxy_mock.MockApp(), "", "myvis", plugin_config)
        existing_config = dict(wat=1)
        config = plugin._build_config(existing_config)
        self.assertEqual(config.wat, 1)

        # unlisted/non-param kwargs should NOT overwrite existing
        plugin_config = dict()
        plugin = self.plugin_class(galaxy_mock.MockApp(), "", "myvis", plugin_config)
        existing_config = dict(wat=1)
        config = plugin._build_config(existing_config, wat=2)
        self.assertEqual(config.wat, 1)

        # listed/param kwargs *should* overwrite existing
        plugin_config = dict(
            params=dict(
                wat={"csv": False, "required": False, "type": "int", "var_name_in_template": "wot"},
            )
        )
        plugin = self.plugin_class(galaxy_mock.MockApp(), "", "myvis", plugin_config)
        existing_config = dict(wat=1)
        # send as string like a query would - should be parsed
        config = plugin._build_config(existing_config, wat="2")
        self.assertEqual(config.wat, 2)

    def test_render(self):
        """ """
        # use the python in a template to test for variables that should be there
        # TODO: gotta be a better way
        testing_template = clean_multiline_string(
            """\
        <%
            found_all = True
            should_have = [
                title, visualization_name, visualization_display_name,
                visualization_id, saved_visualization,
                query, config,
                embedded,
                vars
            ]
            for var in should_have:
                try:
                    var = str( var )
                except NameError as name_err:
                    found_all = False
                    break
        %>
        ${ found_all }
        """
        )

        mock_app_dir = galaxy_mock.MockDir({"cache": {}, "template.mako": testing_template})
        mock_app = galaxy_mock.MockApp(root=mock_app_dir.root_path)
        plugin = self.plugin_class(mock_app, "", "myvis", {"name": "Vlad News Bears"})

        # somewhat easier to set this up by hand
        plugin.config["entry_point"] = {"file": "template.mako"}
        plugin.template_path = mock_app_dir.root_path
        plugin.template_lookup = plugin._build_template_lookup(mock_app_dir.root_path)

        response = plugin.render(trans=galaxy_mock.MockTrans(app=mock_app))
        self.assertIsInstance(response, str)
        self.assertEqual(response.strip(), "True")


# -----------------------------------------------------------------------------
# TODO: config parser tests (in separate file)

if __name__ == "__main__":
    unittest.main()
