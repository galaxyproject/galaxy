#!/usr/bin/env python
"""Script for submitting Galaxy job information to the Galactic Radio Telescope.

See doc/source/admin/grt.rst for more detailed usage information.
"""
import argparse
import logging
import os
import sys

import requests
import yaml

sample_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "grt.yml.sample"))
default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "grt.yml"))


def main(argv):
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-r",
        "--report-directory",
        help="Directory in which reports are stored",
        default=os.path.abspath(os.path.join(".", "reports")),
    )
    parser.add_argument("-g", "--grt-config", help="Path to GRT config file", default=default_config)
    parser.add_argument(
        "-l",
        "--loglevel",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set the logging level",
        default="warning",
    )

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.loglevel.upper()))

    logging.info("Loading GRT configuration...")
    try:
        with open(args.grt_config) as handle:
            config = yaml.safe_load(handle)
    except Exception:
        logging.exception("Could not parse GRT configuration")
        sys.exit(1)

    REPORT_DIR = args.report_directory
    GRT_URL = config["grt"]["url"].rstrip("/") + "/"
    GRT_INSTANCE_ID = config["grt"]["instance_id"]
    GRT_API_KEY = config["grt"]["api_key"]

    # Contact the server and check auth details.
    headers = {"AUTHORIZATION": f"{GRT_INSTANCE_ID}:{GRT_API_KEY}"}
    r = requests.post(GRT_URL + "api/whoami", headers=headers)
    data = r.json()
    # Get back some information about which reports had previously been uploaded.
    remote_reports = data["uploaded_reports"]
    logging.debug("Remote reports: %s", remote_reports)
    local_reports = [x.strip(".json") for x in os.listdir(REPORT_DIR) if x.endswith(".json")]
    logging.debug("Local reports: %s", local_reports)
    # Now we know which to send.
    for report_id in local_reports:
        if report_id not in remote_reports:
            logging.info("Uploading %s", report_id)
            files = {
                "meta": open(os.path.join(REPORT_DIR, report_id + ".json"), "rb"),
                "data": open(os.path.join(REPORT_DIR, report_id + ".tar.gz"), "rb"),
            }
            data = {"identifier": report_id}
            r = requests.post(GRT_URL + "api/v2/upload", files=files, headers=headers, data=data)
            if r.ok:
                logging.info("Uploaded successfully %s", report_id)
            else:
                logging.critical("Non-OK response: %s", r.status_code)


if __name__ == "__main__":
    main(sys.argv)
