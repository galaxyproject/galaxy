"""
This module manages loading/etc of Galaxy interactive tours.
"""

import logging
import os

import yaml
from pydantic import TypeAdapter

from galaxy.exceptions import ObjectNotFound
from galaxy.navigation.tours import (
    get_tour_id_from_path,
    load_tour_from_path,
)
from galaxy.schema.tours import TourList
from galaxy.util import config_directories_from_setting
from galaxy.util.path import StrPath
from ._interface import ToursRegistry

log = logging.getLogger(__name__)

TOUR_EXTENSIONS = (".yml", ".yaml")


def build_tours_registry(tour_directories: str):
    return ToursRegistryImpl(tour_directories)


def is_yaml(filename: str) -> bool:
    for ext in TOUR_EXTENSIONS:
        if filename.endswith(ext):
            return True
    return False


def tour_paths(target_path: StrPath) -> list[str]:
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
        return TypeAdapter(TourList).validate_python(tours)

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
        except OSError:
            log.exception(f"Tour '{tour_id}' could not be loaded, error reading file.")
        except yaml.error.YAMLError:
            log.exception(f"Tour '{tour_id}' could not be loaded, error within file. Please check your YAML syntax.")
        except TypeError:
            log.exception(
                f"Tour '{tour_id}' could not be loaded, error within file."
                " Possibly spacing related. Please check your YAML syntax."
            )
        self.tours[tour_id] = tour
        log.info(f"Loaded tour '{tour_id}'")

    def _get_path_from_tour_id(self, tour_id):
        for tour_dir in self.tour_directories:
            for ext in TOUR_EXTENSIONS:
                tour_path = os.path.join(tour_dir, tour_id + ext)
                if os.path.exists(tour_path):
                    return tour_path
