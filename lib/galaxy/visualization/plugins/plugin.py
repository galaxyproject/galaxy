"""
Visualization plugins: instantiate/deserialize data and models
from a query string and render a webpage based on those data.
"""

import logging
import os

from galaxy.visualization.plugins import resource_parser
from galaxy.web import url_for

log = logging.getLogger(__name__)


class VisualizationPlugin:
    """
    A plugin that instantiates resources, serves static files.
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
        self.resource_parser = resource_parser.ResourceParser(app)
        self._set_logo()

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
            "params": self.config.get("params"),
            "embeddable": self.config.get("embeddable"),
            "entry_point": self.config.get("entry_point"),
            "settings": self.config.get("settings"),
            "specs": self.config.get("specs"),
            "tracks": self.config.get("tracks"),
            "tests": self.config.get("tests"),
            "href": self._get_href(),
        }

    def _get_href(self):
        return url_for(f"/static/plugins/visualizations/{self.name}/static/")

    def _set_logo(self):
        if self.static_path:
            supported_formats = ["png", "svg"]
            for file_format in supported_formats:
                logo_path = os.path.join(self.static_path, f"logo.{file_format}")
                if os.path.isfile(logo_path):
                    self.config["logo"] = logo_path
                    return
