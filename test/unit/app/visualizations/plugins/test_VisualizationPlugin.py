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
                "templates": {},
            }
        )
        plugin = self.plugin_class(galaxy_mock.MockApp(), vis_dir.root_path, "myvis", {})
        assert plugin.name == "myvis"
        assert plugin.path == vis_dir.root_path
        assert plugin.config == {}
        assert plugin.base_url == "myvis"
        # template
        assert plugin.serves_templates
        assert plugin.template_path == vis_dir.root_path + "/templates"
        assert plugin.template_lookup.__class__.__name__ == "TemplateLookup"
        # resource parser
        assert isinstance(plugin.resource_parser, resource_parser.ResourceParser)

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
        assert plugin.base_url == "u/wot/m8/myvis"
        assert plugin.template_lookup.__class__.__name__ == "TemplateLookup"

    def test_init_without_static_or_templates(self):
        """
        A plugin that has neither template or static directory should serve neither.
        """
        vis_dir = galaxy_mock.MockDir({"config": {"vis1.xml": ""}})
        plugin = self.plugin_class(galaxy_mock.MockApp(), vis_dir.root_path, "myvis", {})
        assert not plugin.serves_templates
        # not sure what this would do, but...

    def test_build_render_vars_default(self):
        """
        Render vars passed to render should default properly.
        """
        # well, that's kind of a lot of typing to say nothing new
        config = dict(name="Cat Fancy Magazine's Genomic Visualization")
        plugin = self.plugin_class(galaxy_mock.MockApp(), "", "myvis", config)

        render_vars = plugin._build_render_vars(config)
        assert render_vars["visualization_name"] == plugin.name
        assert render_vars["visualization_display_name"] == plugin.config["name"]
        assert render_vars["title"] == "Unnamed Visualization"
        assert render_vars["saved_visualization"] is None
        assert render_vars["visualization_id"] is None
        assert render_vars["query"] == {}
        assert isinstance(render_vars["config"], vis_utils.OpenObject)
        assert render_vars["config"].__dict__ == {}

    def test_build_config(self):
        """ """
        plugin_config: dict = {}
        plugin = self.plugin_class(galaxy_mock.MockApp(), "", "myvis", plugin_config)
        config = plugin._build_config({})
        assert isinstance(config, vis_utils.OpenObject)
        assert config.__dict__ == {}

        # existing should flow through
        plugin_config = {}
        plugin = self.plugin_class(galaxy_mock.MockApp(), "", "myvis", plugin_config)
        existing_config = dict(wat=1)
        config = plugin._build_config(existing_config)
        assert config.wat == 1

        # unlisted/non-param kwargs should NOT overwrite existing
        plugin_config = {}
        plugin = self.plugin_class(galaxy_mock.MockApp(), "", "myvis", plugin_config)
        existing_config = dict(wat=1)
        config = plugin._build_config(existing_config, wat=2)
        assert config.wat == 1

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
        assert config.wat == 2

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
        assert isinstance(response, str)
        assert response.strip() == "True"


# -----------------------------------------------------------------------------
# TODO: config parser tests (in separate file)
