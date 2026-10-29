import yaml

from galaxy.util.resources import resource_string
from .components import Component


def load_root_component() -> Component:
    new_data_yaml = resource_string(__name__, "navigation.yml")
    navigation_raw = yaml.safe_load(new_data_yaml)
    return Component.from_dict("root", navigation_raw)
