#!/bin/env python3
# The stop hook doesn't take any arguments (except possibly the --debug flag)
# but it is passed the AMP_ROOT and AMP_DATA_ROOT environment variables

import argparse
import os
from amp.config import load_amp_config
from amp.logging import setup_logging
import logging
import subprocess

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    args = parser.parse_args()

    setup_logging(None, args.debug)

    try:
        subprocess.run([f"{os.environ['AMP_ROOT']}/galaxy/run.sh", "stop"], check=True)
    except Exception as e:
        logging.error(f"Cannot stop Galaxy: {e}")


if __name__ == "__main__":
    main()



