"""
Build indexes for searching the Tool Shed.
Run this script from the root folder, example:

$ python scripts/tool_shed/build_ts_whoosh_index.py -c config/tool_shed.yml

Make sure you adjust your Toolshed config to:
 * turn on searching with "toolshed_search_on"
 * specify "whoosh_index_dir" where the indexes will be placed

This script expects the Tool Shed's runtime virtualenv to be active.
"""

import argparse
import logging
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "lib")))

from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
)
from tool_shed.util.shed_index import build_index
from tool_shed.webapp import config as ts_config

log = logging.getLogger()
log.addHandler(logging.StreamHandler(sys.stdout))


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Build a disk-backed Toolshed repository index and tool index for searching."
    )
    populate_config_args(parser)
    parser.add_argument("-d", "--debug", action="store_true", default=False, help="Print extra info")
    args = parser.parse_args()
    app_properties = app_properties_from_args(args)
    config = ts_config.ToolShedAppConfiguration(**app_properties)
    args.dburi = config.database_connection
    args.hgweb_config_dir = config.hgweb_config_dir
    args.hgweb_repo_prefix = config.hgweb_repo_prefix
    args.whoosh_index_dir = config.whoosh_index_dir
    args.file_path = config.file_path
    if args.debug:
        log.setLevel(logging.DEBUG)
        log.debug("Full options:")
        for key, value in vars(args).items():
            log.debug("%s: %s", key, value)
    return args


def main():
    args = parse_arguments()
    build_index(**vars(args))


if __name__ == "__main__":
    main()
