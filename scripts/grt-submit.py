#!/usr/bin/env python
"""Script for submitting Galaxy job information to the Galactic radio telescope.

See doc/source/admin/grt.rst for more detailed usage information.
"""
from __future__ import print_function

import argparse
import os
import sys
import time
import yaml
import logging
import urllib2

sample_config = os.path.abspath(os.path.join(os.path.dirname(__file__), 'grt.yml.sample'))
default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), 'grt.yml'))


def main(argv):
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-r', '--report-directory', help='Directory in which reports are stored',
                        default=os.path.abspath(os.path.join('.', 'reports')))
    parser.add_argument('-c', '--config', help='Path to GRT config file',
                        default=default_config)
    parser.add_argument("-l", "--loglevel", choices=['debug', 'info', 'warning', 'error', 'critical'],
                        help="Set the logging level", default='warning')
    args = parser.parse_args()

    logging.info('Loading GRT ini...')
    try:
        with open(args.config) as handle:
            config = yaml.load(handle)
    except Exception:
        logging.info('Using default GRT Configuration')
        with open(sample_config) as handle:
            config = yaml.load(handle)

    REPORT_DIR = args.report_directory
    CHECK_POINT_FILE = os.path.join(REPORT_DIR, '.checkpoint')
    ARCHIVE_DIR = os.path.join(REPORT_DIR, 'archives')
    METADATA_FILE = os.path.join(REPORT_DIR, 'meta.json')
    REPORT_BASE = os.path.join(ARCHIVE_DIR, REPORT_IDENTIFIER)

    GRT_URL = config['grt']['url']
    GRT_INSTANCE_ID = config['grt']['instance_id']
    GRT_API_KEY = config['grt']['api_key']
    # Contact the server and check auth details.

    # TODO: server interaction.


if __name__ == '__main__':
    main(sys.argv)
