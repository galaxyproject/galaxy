from pkg_resources import resource_string

import yaml

data_yaml = resource_string(__name__, 'navigation-data.yml').decode("UTF-8")
NAVIGATION_DATA = yaml.load(data_yaml)
