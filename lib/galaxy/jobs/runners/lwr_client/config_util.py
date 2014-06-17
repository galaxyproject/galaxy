""" Generic interface for reading YAML/INI/JSON config files into nested dictionaries.
"""

try:
    from galaxy import eggs
    eggs.require('PyYAML')
except Exception:
    # If not in Galaxy, ignore this.
    pass
try:
    import yaml
except ImportError:
    yaml = None
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
import json


CONFIG_TYPE_JSON = "json"
CONFIG_TYPE_YAML = "yaml"
CONFIG_TYPE_INI = "ini"

DEFAULT_CONFIG_TYPE = CONFIG_TYPE_YAML

JSON_EXTS = [".json"]
YAML_EXTS = [".yaml", ".yml"]
INI_EXTS = [".ini"]

EXT_MAP = {
    CONFIG_TYPE_JSON: JSON_EXTS,
    CONFIG_TYPE_YAML: YAML_EXTS,
    CONFIG_TYPE_INI: INI_EXTS,
}


def read_file(path, type=None, default_type=DEFAULT_CONFIG_TYPE):
    if path is None:
        raise ValueError("Undefined path supplied.")

    config_type = __find_type(path, type, default_type)
    return EXT_READERS[config_type](path)


def __find_type(path, explicit_type, default_type):
    if explicit_type:
        return explicit_type

    for config_type, config_exts in EXT_MAP.items():
        for ext in config_exts:
            if path.endswith(ext):
                return config_type

    return default_type


def __read_yaml(path):
    if yaml is None:
        raise ImportError("Attempting to read YAML configuration file - but PyYAML dependency unavailable.")

    with open(path, "rb") as f:
        return yaml.load(f)


def __read_ini(path):
    config = ConfigParser()
    config.read(path)
    return config._sections


def __read_json(path):
    with open(path, "rb") as f:
        return json.load(f)

EXT_READERS = {
    CONFIG_TYPE_JSON: __read_json,
    CONFIG_TYPE_YAML: __read_yaml,
    CONFIG_TYPE_INI: __read_ini,
}
