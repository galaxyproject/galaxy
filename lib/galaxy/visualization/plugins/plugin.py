"""
Visualization plugins: instantiate/deserialize data and models
from a query string and render a webpage based on those data.
"""

import logging
import os
from typing import (
    Any,
    TYPE_CHECKING,
)

from galaxy.web import url_for

if TYPE_CHECKING:
    from galaxy.visualization.parameters import VisualizationParameterBundleModel

log = logging.getLogger(__name__)


class VisualizationPlugin:
    """
    A plugin that instantiates resources, serves static files.
    """

    def __init__(
        self,
        path: str,
        name: str,
        config: dict[str, Any],
        parameters_schema: dict[str, Any] | None = None,
        parameter_bundle: "VisualizationParameterBundleModel | None" = None,
    ) -> None:
        self.path = path
        self.name = name
        self.config = config
        self.parameters_schema = parameters_schema
        self.parameter_bundle = parameter_bundle
        self.static_path = os.path.join("/static/plugins/visualizations/", name, "static")
        self._set_logo()

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.config.get("description"),
            "data_sources": self.config.get("data_sources"),
            "embeddable": self.config.get("embeddable"),
            "entry_point": self.config.get("entry_point"),
            "html": self.config.get("name"),
            "href": url_for(self.static_path),
            "help": self.config.get("help"),
            "logo": self.config.get("logo"),
            "params": self.config.get("params"),
            "tags": self.config.get("tags"),
            "tests": self.config.get("tests"),
            "title": self.config.get("title"),
            "tracks": self.config.get("tracks"),
            "settings": self.config.get("settings"),
            "specs": self.config.get("specs"),
            "parameters_schema": self.parameters_schema,
        }

    def _set_logo(self):
        if self.static_path:
            supported_formats = ["png", "svg"]
            for file_format in supported_formats:
                logo_path = os.path.join(f".{self.static_path}", f"logo.{file_format}")
                if os.path.isfile(logo_path):
                    self.config["logo"] = logo_path
                    return
