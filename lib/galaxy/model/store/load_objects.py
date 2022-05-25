import argparse
import base64
import logging
import os
import sys
from typing import (
    Any,
    Dict,
)

import requests
import yaml

DESCRIPTION = """Load a Galaxy model store into a running Galaxy instance.

See the corresponding galaxy-build-objects script for one possible way to
create a model store to use with this script.

This script creates all datasets in "discarded"/"deferred" states (depending on if
source URIs are available). To actually load the datasets into a Galaxy instance's
object store the underlying libraries need to be used directly and fed your Galaxy's
database configuration and objectstore setup.
"""

logging.basicConfig()
log = logging.getLogger(__name__)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = _arg_parser().parse_args(argv)

    galaxy_url = args.galaxy_url
    api_url = f"{galaxy_url.rstrip('/')}/api"
    api_key = args.key
    assert api_key
    history_id = args.history_id
    if history_id:
        create_url = f"{api_url}/histories/{history_id}/contents_from_store?key={api_key}"
    else:
        create_url = f"{api_url}/histories/from_store?key={api_key}"

    store_path = args.store
    assert os.path.exists(store_path)
    is_json = False
    for json_ext in [".yml", ".yaml", ".json"]:
        if store_path.endswith(json_ext):
            is_json = True

    data: Dict[str, Any] = {}
    if is_json:
        with open(store_path, "r") as f:
            store_dict = yaml.safe_load(f)
        data["store_dict"] = store_dict
    else:
        with open(store_path, "rb") as fb:
            store_contents = fb.read()
        data["store_content_base64"] = base64.b64encode(store_contents)
    response = requests.post(create_url, json=data)
    response.raise_for_status()


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("store", metavar="STORE", help="file or directory containing the model store to connect to")
    # copied from test script in galaxy-tool-util...
    parser.add_argument("-u", "--galaxy-url", default="http://localhost:8080", help="Galaxy URL")
    parser.add_argument("-k", "--key", default=None, help="Galaxy User API Key")
    parser.add_argument("-t", "--history-id", default=None, help="Encoded history ID to load model store into")

    return parser


if __name__ == "__main__":
    main()
