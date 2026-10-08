"""
Visualization plugins: instantiate/deserialize data and models
from a query string and render a webpage based on those data.
"""

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


class VisualizationPlugin:
    """
    A plugin that instantiates resources, serves static files.
    """

    def __init__(
        self, path: str, name: str, config: dict[str, Any], url_prefix: str = "", static_path: str | None = None
    ) -> None:
        self.path = path
        self.name = name
        self.config = config
        self.url_prefix = url_prefix
        # Built-ins are served from Galaxy's static tree; runtime-installed packages pass their own URL
        self.static_path = static_path or os.path.join("/static/plugins/visualizations/", name, "static")
        self._set_logo()

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.config.get("description"),
            "data_sources": self.config.get("data_sources"),
            "embeddable": self.config.get("embeddable"),
            "entry_point": self.config.get("entry_point"),
            "html": self.config.get("name"),
            "href": self.url_prefix + self.static_path,
            "help": self.config.get("help"),
            "logo": self.config.get("logo"),
            "params": self.config.get("params"),
            "tags": self.config.get("tags"),
            "tests": self.config.get("tests"),
            "title": self.config.get("title"),
            "tracks": self.config.get("tracks"),
            "settings": self.config.get("settings"),
            "specs": self.config.get("specs"),
        }

    def _set_logo(self):
        for file_format in ("png", "svg"):
            if os.path.isfile(os.path.join(self.path, "static", f"logo.{file_format}")):
                self.config["logo"] = f".{self.static_path}/logo.{file_format}"
                return
