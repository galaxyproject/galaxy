import yaml
from pkg_resources import resource_string

from .components import Component

new_data_yaml = resource_string(__name__, 'navigation.yml').decode("UTF-8")
NAVIGATION_RAW = yaml.safe_load(new_data_yaml)

NAVIGATION = Component.from_dict("root", NAVIGATION_RAW)
