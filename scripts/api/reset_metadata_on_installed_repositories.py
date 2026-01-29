#!/usr/bin/env python
"""
Script to reset metadata on all Tool Shed repositories installed into a Galaxy instance.  The received
API key must be associated with a Galaxy admin user.

usage: reset_metadata_on_installed_repositories.py key

Here is a working example of how to use this script.
python ./reset_metadata_on_installed_repositories.py -a 22be3b -u http://localhost:8763/
"""
import argparse

from common import submit


def main(options):
    base_galaxy_url = options.galaxy_url.rstrip("/")
    url = f"{base_galaxy_url}/api/tool_shed_repositories/reset_metadata_on_installed_repositories"
    submit(options.api, url, {})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Reset metadata on all Tool Shed repositories installed into Galaxy via the Galaxy API."
    )
    parser.add_argument("-a", "--api", dest="api", required=True, help="API Key")
    parser.add_argument("-u", "--url", dest="galaxy_url", required=True, help="Galaxy URL")
    options = parser.parse_args()
    main(options)
