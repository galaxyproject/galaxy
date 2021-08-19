import logging
import os
from typing import Dict, List

import yaml

from galaxy.util import config_directories_from_setting
from .definitions import StaticToolBoxView

log = logging.getLogger(__name__)

EXTENSIONS = [".yml", ".yaml", ".json"]


class StaticToolBoxViewSources:
    view_directories: List[str]
    view_dicts: List[Dict]

    def __init__(self, view_directories=None, view_dicts=None):
        self.view_directories = config_directories_from_setting(view_directories) or []
        self.view_dicts = view_dicts or []

    def get_definitions(self) -> List[StaticToolBoxView]:
        view_definitions = []

        for view_dict in self.view_dicts:
            view_definitions.append(StaticToolBoxView.from_dict(view_dict))

        for view_directory in self.view_directories:
            if not os.path.exists(view_directory):
                log.warning(f"Failed to find toolbox view directory {view_directory}")

            for filename in os.listdir(view_directory):
                if not looks_like_view_source_filename(filename):
                    continue

                view_path = os.path.join(view_directory, filename)
                with open(view_path) as f:
                    view_dict = yaml.safe_load(f)
                if "id" not in view_dict:
                    file_id = os.path.splitext(filename)[0]
                    view_dict["id"] = file_id
                view_definitions.append(StaticToolBoxView.from_dict(view_dict))

        return view_definitions


def looks_like_view_source_filename(filename: str) -> bool:
    for ext in EXTENSIONS:
        if filename.endswith(ext):
            return True
    return False
