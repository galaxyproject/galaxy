"""
Visualization plugins: instantiate/deserialize data and models
from a query string and render a webpage based on those data.
"""

import copy
import logging
import os
from typing import (
    Any,
    Dict,
)

import mako.lookup

from galaxy.visualization.plugins import (
    resource_parser,
    utils,
)
from galaxy.web import url_for

log = logging.getLogger(__name__)


class ServesTemplatesPluginMixin:
    """
    An object that renders (mako) template files from the server.
    """

    path: str

    #: default number of templates to search for plugin template lookup
    DEFAULT_TEMPLATE_COLLECTION_SIZE = 10

    def _set_up_template_plugin(self, template_cache_dir, **kwargs):
        """
        Detect and set up template paths if the plugin serves templates.
        """
        self.serves_templates = False
        if self._is_template_plugin():
            self.template_path = self._build_template_path()
            self.template_lookup = self._build_template_lookup(template_cache_dir)
            self.serves_templates = True
        return self.serves_templates

    def _is_template_plugin(self):
        return os.path.isdir(self._build_template_path())

    def _build_template_path(self):
        return os.path.join(self.path, "templates")

    def _build_template_lookup(self, template_cache_dir, collection_size=DEFAULT_TEMPLATE_COLLECTION_SIZE):
        """
        Build a mako template filename lookup for the plugin.
        """
        template_lookup_paths = self.template_path
        return mako.lookup.TemplateLookup(
            directories=template_lookup_paths, module_directory=template_cache_dir, collection_size=collection_size
        )


class VisualizationPlugin(ServesTemplatesPluginMixin):
    """
    A plugin that instantiates resources, serves static files, and uses mako
    templates to render web pages.
    """

    def __init__(self, app, path, name, config, context=None, **kwargs):
        context = context or {}
        self.app = app
        self.path = path
        self.name = name
        self.config = config
        base_url = context.get("base_url", "")
        self.base_url = "/".join((base_url, self.name)) if base_url else self.name
        self.static_path = os.path.join("./static/plugins/visualizations/", name, "static")
        template_cache_dir = context.get("template_cache_dir", None)
        self._set_up_template_plugin(template_cache_dir)
        self.resource_parser = resource_parser.ResourceParser(app)
        self._set_logo()

    def render(self, trans=None, embedded=None, **kwargs):
        """
        Render and return the text of the non-saved plugin webpage/fragment.
        """
        # not saved - no existing config
        # set up render vars based on plugin.config and kwargs
        render_vars = self._build_render_vars({}, trans=trans, **kwargs)
        return self._render(render_vars, trans=trans, embedded=embedded)

    def render_saved(self, visualization, trans=None, embedded=None, **kwargs):
        """
        Render and return the text of the plugin webpage/fragment using the
        config/data of a saved visualization.
        """
        config: Dict[str, Any] = self._get_saved_visualization_config(visualization, **kwargs)
        # pass the saved visualization config for parsing into render vars
        render_vars = self._build_render_vars(config, trans=trans, **kwargs)
        # update any values that were loaded from the saved Visualization
        render_vars.update(
            dict(
                title=visualization.latest_revision.title,
                saved_visualization=visualization,
                visualization_id=trans.security.encode_id(visualization.id),
            )
        )
        return self._render(render_vars, trans=trans, embedded=embedded)

    def to_dict(self):
        return {
            "name": self.name,
            "html": self.config.get("name"),
            "description": self.config.get("description"),
            "data_sources": self.config.get("data_sources"),
            "help": self.config.get("help"),
            "logo": self.config.get("logo"),
            "tags": self.config.get("tags"),
            "title": self.config.get("title"),
            "target": self.config.get("render_target", "galaxy_main"),
            "embeddable": self.config.get("embeddable"),
            "entry_point": self.config.get("entry_point"),
            "settings": self.config.get("settings"),
            "specs": self.config.get("specs"),
            "tracks": self.config.get("tracks"),
            "tests": self.config.get("tests"),
            "href": self._get_url(),
        }

    def _get_url(self):
        if self.name in self.app.visualizations_registry.BUILT_IN_VISUALIZATIONS:
            return url_for(controller="visualization", action=self.name)
        return url_for("visualization_plugin", visualization_name=self.name)

    def _get_saved_visualization_config(self, visualization, revision=None, **kwargs) -> Dict[str, Any]:
        """
        Return the config of a saved visualization and revision.

        If no revision given, default to latest revision.
        """
        # TODO: allow loading a specific revision - should be part of UsesVisualization
        return copy.copy(visualization.latest_revision.config)

    # ---- non-public
    def _build_render_vars(self, config: Dict[str, Any], trans=None, **kwargs) -> Dict[str, Any]:
        """
        Build all the variables that will be passed into the renderer.
        """
        render_vars: Dict[str, Any] = {}
        # Meta variables passed to the template/renderer to describe the visualization being rendered.
        render_vars.update(
            visualization_name=self.name,
            visualization_display_name=self.config["name"],
            title=kwargs.get("title", "Unnamed Visualization"),
            saved_visualization=None,
            visualization_id=None,
            visualization_plugin=self.to_dict(),
            # NOTE: passing *unparsed* kwargs as query
            query=kwargs,
        )
        # config based on existing or kwargs
        render_config = self._build_config(config, trans=trans, **kwargs)
        render_vars["config"] = render_config
        # further parse config to resources (models, etc.) used in template based on registry config
        resources = self._config_to_resources(trans, render_config)
        render_vars.update(resources)
        return render_vars

    def _build_config(self, config, trans=None, **kwargs) -> utils.OpenObject:
        """
        Build the configuration for this new/saved visualization by combining
        any existing config and the kwargs (gen. from the url query).
        """
        # first, pull from any existing config
        if config:
            config = copy.copy(config)
        else:
            config = {}
        # then, overwrite with keys/values from kwargs (gen. a query string)
        config_from_kwargs = self._kwargs_to_config(trans, kwargs)
        config.update(config_from_kwargs)
        # to object format for easier querying
        config = utils.OpenObject(**config)
        return config

    # TODO: the difference between config & resources is unclear in this section - is it needed?
    def _kwargs_to_config(self, trans, kwargs):
        """
        Given a kwargs dict (gen. a query string dict from a controller action), parse
        and return any key/value pairs found in the plugin's `params` section.
        """
        expected_params = self.config.get("params", {})
        config = self.resource_parser.parse_config(trans, expected_params, kwargs)
        return config

    def _config_to_resources(self, trans, config):
        """
        Instantiate/deserialize the resources (HDAs, LDDAs, etc.) given in a
        visualization config into models/variables a visualization renderer can use.
        """
        expected_params = self.config.get("params", {})
        param_modifiers = self.config.get("param_modifiers", {})
        resources = self.resource_parser.parse_parameter_dictionary(trans, expected_params, config, param_modifiers)
        return resources

    def _render(self, render_vars, trans=None, embedded=None, **kwargs):
        """
        Render the visualization via Mako and the plugin's template file.
        """
        render_vars["embedded"] = self._parse_embedded(embedded)
        # NOTE: (mako specific) vars is a dictionary for shared data in the template
        #   this feels hacky to me but it's what mako recommends:
        #   http://docs.makotemplates.org/en/latest/runtime.html
        render_vars.update(vars={})
        template_filename = self.config["entry_point"]["file"]
        return trans.fill_template(template_filename, template_lookup=self.template_lookup, **render_vars)

    def _parse_embedded(self, embedded):
        """
        Parse information on dimensions, readonly, etc. from the embedded query val.
        """
        # as is for now
        return embedded

    def _set_logo(self):
        if self.static_path:
            supported_formats = ["png", "svg"]
            for file_format in supported_formats:
                logo_path = os.path.join(self.static_path, f"logo.{file_format}")
                if os.path.isfile(logo_path):
                    self.config["logo"] = logo_path
                    return


class ScriptVisualizationPlugin(VisualizationPlugin):
    """
    A visualization plugin that starts by loading a single (js) script.

    The script is loaded into a pre-defined mako template: `script_entry_point.mako`
    """

    MAKO_TEMPLATE = "script_entry_point.mako"

    def _is_template_plugin(self):
        """
        Override to always yield true since this plugin type always uses the
        pre-determined mako template.
        """
        return True

    def _render(self, render_vars, trans=None, embedded=None, **kwargs):
        """
        Override to add script attributes and point mako at the script entry point
        template.
        """
        render_vars["embedded"] = self._parse_embedded(embedded)
        render_vars["host_url"] = trans.request.host_url
        render_vars["static_url"] = url_for(f"/{self.static_path}/")
        render_vars.update(vars={})
        render_vars.update({"script_attributes": self.config["entry_point"]["attr"]})
        template_filename = os.path.join(self.MAKO_TEMPLATE)
        return trans.fill_template(template_filename, **render_vars)
