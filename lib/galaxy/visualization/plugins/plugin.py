"""
Visualization plugins: instantiate/deserialize data and models
from a query string and render a webpage based on those data.
"""

import logging
import os

from galaxy.web import url_for

log = logging.getLogger(__name__)


class VisualizationPlugin:
    """
    A plugin that instantiates resources, serves static files.
    """

    def __init__(self, path: str, name: str, config: dict[str, Any]) -> None:
        self.path = path
        self.name = name
        self.config = config
        self.static_path = os.path.join("/static/plugins/visualizations/", name, "static")
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
            "href": url_for(self.static_path),
        }

    def _set_logo(self):
        if self.static_path:
            supported_formats = ["png", "svg"]
            for file_format in supported_formats:
                logo_path = f".{self.static_path}/logo.{file_format}"
                if os.path.isfile(logo_path):
                    self.config["logo"] = logo_path
                    return
