import argparse
import os
import pprint
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))
from galaxy.config import GalaxyAppConfiguration
from galaxy.util.properties import load_app_properties


def main(config, setting):
    # Use explicit config, then env, then guess.
    config = config or os.environ.get("GALAXY_CONFIG_FILE", "config/galaxy.yml")
    if config and os.path.exists(config):
        app_properties = load_app_properties(config_file=config)
        gx_config = GalaxyAppConfiguration(**app_properties)
        if setting:
            print(gx_config.get(setting))
        else:
            pprint.pprint(gx_config.config_dict)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Fetch values from Galaxy config, or print all set values.")
    # add optional 'setting' argument
    arg_parser.add_argument("-s", "--setting", default=None, help="setting")
    arg_parser.add_argument(
        "-c", "--config-file", default=None, help="Galaxy config file (defaults to config/galaxy.ini)"
    )
    args = arg_parser.parse_args()
    main(args.config_file, args.setting)
