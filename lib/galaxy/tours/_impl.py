"""
This module manages loading/etc of Galaxy interactive tours.
"""
import logging
import os
from typing import (
    List,
    Union,
)

import yaml
from pydantic import parse_obj_as

from galaxy.exceptions import ObjectNotFound
from galaxy.selenium.data import load_root_component
from galaxy.util import config_directories_from_setting
from ._interface import ToursRegistry
from ._schema import TourList

log = logging.getLogger(__name__)

TOUR_EXTENSIONS = (".yml", ".yaml")

ROOT_COMPONENT = load_root_component()


def build_tours_registry(tour_directories: str):
    return ToursRegistryImpl(tour_directories)


def noop_warn(str):
    pass


def load_tour_steps(contents_dict, warn=None, resolve_components=True):
    warn = warn or noop_warn
    #  Some of this can be done on the clientside.  Maybe even should?
    title_default = contents_dict.get("title_default")
    if "requirements" not in contents_dict:
        contents_dict["requirements"] = []

    for step in contents_dict["steps"]:
        # Remove attributes no longer used, so they are attempted to be
        # validated.
        if "backdrop" in step:
            warn(f"Deprecated and dropped property backdrop found in step {step}")
            step.pop("backdrop")

        if "component" in step and resolve_components:
            component = step.pop("component")
            step["element"] = ROOT_COMPONENT.resolve_element_locator(component)[1]

        if "intro" in step:
            step["content"] = step.pop("intro")
        if "position" in step:
            step["placement"] = step.pop("position")
        if "element" not in step:
            step["orphan"] = True
        if title_default and "title" not in step:
            step["title"] = title_default


def get_tour_id_from_path(tour_path: Union[str, os.PathLike]) -> str:
    filename = os.path.basename(tour_path)
    return os.path.splitext(filename)[0]


def load_tour_from_path(tour_path: Union[str, os.PathLike], warn=None, resolve_components=True) -> dict:
    with open(tour_path) as f:
        tour = yaml.safe_load(f)
        load_tour_steps(tour, warn=warn, resolve_components=resolve_components)
    return tour


def is_yaml(filename: str) -> bool:
    for ext in TOUR_EXTENSIONS:
        if filename.endswith(ext):
            return True
    return False


def tour_paths(target_path: Union[str, os.PathLike]) -> List[str]:
    paths = []
    if os.path.isdir(target_path):
        for filename in os.listdir(target_path):
            if is_yaml(filename):
                paths.append(str(os.path.join(target_path, filename)))
    else:
        paths.append(str(target_path))
    return paths


@ToursRegistry.register
class ToursRegistryImpl:
    def __init__(self, tour_directories):
        self.tour_directories = config_directories_from_setting(tour_directories)
        self._load_tours()

    def get_tours(self):
        """Return list of tours."""
        tours = []
        for k in self.tours.keys():
            tourdata = {
                "id": k,
                "name": self.tours[k].get("name"),
                "description": self.tours[k].get("description"),
                "tags": self.tours[k].get("tags"),
                "requirements": self.tours[k].get("requirements"),
            }
            tours.append(tourdata)
        return parse_obj_as(TourList, tours)

    def tour_contents(self, tour_id):
        """Return tour contents."""
        # Extra format translation could happen here (like the previous intro_to_tour)
        # For now just return the loaded contents.
        if tour_id not in self.tours:
            raise ObjectNotFound(f"tour {tour_id} not found")
        return self.tours.get(tour_id)

    def load_tour(self, tour_id):
        """Reload tour and return its contents."""
        tour_path = self._get_path_from_tour_id(tour_id)
        self._load_tour_from_path(tour_path)
        return self.tours.get(tour_id)

    def reload_tour(self, path):
        """Reload tour."""
        # We may safely assume that the path is within the tour directory
        filename = os.path.basename(path)
        if is_yaml(filename):
            self._load_tour_from_path(path)

    def _load_tours(self):
        self.tours = {}
        for tour_dir in self.tour_directories:
            for tour_path in tour_paths(tour_dir):
                self._load_tour_from_path(tour_path)

    def _load_tour_from_path(self, tour_path):
        tour_id = get_tour_id_from_path(tour_path)
        try:
            tour = load_tour_from_path(tour_path)
            self.tours[tour_id] = tour
            log.info(f"Loaded tour '{tour_id}'")
        except OSError:
            log.exception(f"Tour '{tour_id}' could not be loaded, error reading file.")
        except yaml.error.YAMLError:
            log.exception(
                "Tour '%s' could not be loaded, error within file." " Please check your yaml syntax." % tour_id
            )
        except TypeError:
            log.exception(
                "Tour '%s' could not be loaded, error within file."
                " Possibly spacing related. Please check your yaml syntax." % tour_id
            )

    def _get_path_from_tour_id(self, tour_id):
        for tour_dir in self.tour_directories:
            for ext in TOUR_EXTENSIONS:
                tour_path = os.path.join(tour_dir, tour_id + ext)
                if os.path.exists(tour_path):
                    return tour_path
