from pkg_resources import resource_string

import yaml

data_yaml = resource_string(__name__, 'test-data.yml').decode("UTF-8")
TEST_DATA = yaml.load(data_yaml)
