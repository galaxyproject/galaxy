"""Utilities for finding Galaxy's configuration file.

This is for use by web framework code and scripts (e.g. scripts/galaxy_main.py).
"""
import os
from typing import (
    List,
    NamedTuple,
    Optional,
)

from galaxy.util.properties import find_config_file
from galaxy.web_stack import get_app_kwds

DEFAULT_INI_APP = "main"
DEFAULT_CONFIG_SECTION = "galaxy"


def default_relative_config_paths_for(app_name: str) -> List[str]:
    paths = [f"config/{app_name}.yml", f"config/{app_name}.ini", "universe_wsgi.ini"]
    # Do not load sample config for galaxy
    if app_name != "galaxy":
        paths.append(f"config/{app_name}.yml.sample")
    return paths


def absolute_config_path(path, galaxy_root: Optional[str]) -> Optional[str]:
    if path and not os.path.isabs(path) and galaxy_root:
        path = os.path.join(galaxy_root, path)
    return path


def config_is_ini(config_file: Optional[str]) -> bool:
    return bool(config_file and (config_file.endswith(".ini") or config_file.endswith(".ini.sample")))


def find_config(supplied_config: Optional[str], galaxy_root: Optional[str], app_name: str = "galaxy") -> Optional[str]:
    if supplied_config:
        return supplied_config

    if galaxy_root is None:
        return os.path.abspath(f"{app_name}.yml")

    for filename in default_relative_config_paths_for(app_name):
        config_path = os.path.join(galaxy_root, filename)
        if os.path.exists(config_path):
            return config_path

    return None


class WebappSetupProps(NamedTuple):
    """Basic properties to provide information about the App and the environment variables
    used to resolve the App configuration."""

    app_name: str
    default_section_name: str
    env_config_file: str
    env_config_section: Optional[str] = None
    check_galaxy_root: bool = False


class WebappConfig(NamedTuple):
    """The resolved configuration values for a Webapp."""

    global_conf: dict
    load_app_kwds: dict
    wsgi_preflight: bool = False


class WebappConfigResolver:
    def __init__(self, props: WebappSetupProps) -> None:
        self.props = props
        self.app_kwds = get_app_kwds(props.default_section_name, props.app_name)
        self.config_file = self._resolve_config_file_path()
        self.is_ini_file = config_is_ini(self.config_file)
        self.config_section = self._resolve_section_name()
        self._update_kwds()
        os.environ["IS_WEBAPP"] = "1"

    def resolve_config(self) -> WebappConfig:
        global_conf = {}
        if self.is_ini_file:
            global_conf["__file__"] = self.config_file

        return WebappConfig(global_conf=global_conf, load_app_kwds=self.app_kwds)

    def _resolve_config_file_path(self) -> Optional[str]:
        config_file = self.app_kwds.get("config_file")
        if not config_file and os.environ.get(self.props.env_config_file):
            config_file = os.path.abspath(os.environ[self.props.env_config_file])
        elif self.props.check_galaxy_root:
            galaxy_root = self.app_kwds.get("galaxy_root") or os.environ.get("GALAXY_ROOT_DIR")
            config_file = find_config(config_file, galaxy_root, app_name=self.props.app_name)
            config_file = absolute_config_path(config_file, galaxy_root=galaxy_root)
        else:
            config_file = find_config_file([self.props.app_name])
        return config_file

    def _resolve_section_name(self) -> str:
        config_section = self.props.default_section_name
        if self.props.env_config_section and self.props.env_config_section in os.environ:
            config_section = os.environ[self.props.env_config_section]
        elif self.is_ini_file:
            config_section = f"app:{DEFAULT_INI_APP}"
        return config_section

    def _update_kwds(self) -> None:
        if "config_file" not in self.app_kwds:
            self.app_kwds["config_file"] = self.config_file
        if "config_section" not in self.app_kwds:
            self.app_kwds["config_section"] = self.config_section
