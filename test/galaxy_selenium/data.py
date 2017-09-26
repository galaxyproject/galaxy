import yaml
from pkg_resources import resource_string

data_yaml = resource_string(__name__, 'navigation-data.yml').decode("UTF-8")
NAVIGATION_DATA = yaml.safe_load(data_yaml)
