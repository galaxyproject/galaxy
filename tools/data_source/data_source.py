#!/usr/bin/env python
# Retrieves data from external data source applications and stores in a dataset file.
# Data source application parameters are temporarily stored in the dataset file.
import json
import os
import sys
from urllib.parse import (
    urlencode,
    urlparse,
)
from urllib.request import urlopen

from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    get_charset_from_http_headers,
    stream_to_open_named_file,
)

GALAXY_PARAM_PREFIX = "GALAXY"
GALAXY_ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
GALAXY_DATATYPES_CONF_FILE = os.path.join(GALAXY_ROOT_DIR, "datatypes_conf.xml")


def __main__():
    if len(sys.argv) >= 3:
        max_file_size = int(sys.argv[2])
    else:
        max_file_size = 0

    with open(sys.argv[1]) as fh:
        params = json.load(fh)

    out_data_name = params["output_data"][0]["out_data_name"]

    URL = params["param_dict"].get("URL", None)  # using exactly URL indicates that only one dataset is being downloaded
    URL_method = params["param_dict"].get("URL_method", "get")

    datatypes_registry = Registry()
    datatypes_registry.load_datatypes(
        root_dir=params["job_config"]["GALAXY_ROOT_DIR"],
        config=params["job_config"]["GALAXY_DATATYPES_CONF_FILE"],
    )

    for data_dict in params["output_data"]:
        cur_filename = data_dict["file_name"]
        cur_URL = params["param_dict"].get("%s|%s|URL" % (GALAXY_PARAM_PREFIX, data_dict["out_data_name"]), URL)
        if not cur_URL or urlparse(cur_URL).scheme not in ("http", "https", "ftp"):
            open(cur_filename, "w").write("")
            sys.exit("The remote data source application has not sent back a URL parameter in the request.")

        # The following calls to urlopen() will use the above default timeout
        try:
            if URL_method == "get":
                page = urlopen(cur_URL, timeout=DEFAULT_SOCKET_TIMEOUT)
            elif URL_method == "post":
                page = urlopen(
                    cur_URL,
                    urlencode(params["param_dict"]["incoming_request_params"]).encode("utf-8"),
                    timeout=DEFAULT_SOCKET_TIMEOUT,
                )
        except Exception as e:
            sys.exit("The remote data source application may be off line, please try again later. Error: %s" % str(e))
        if max_file_size:
            file_size = int(page.info().get("Content-Length", 0))
            if file_size > max_file_size:
                sys.exit(
                    "The size of the data (%d bytes) you have requested exceeds the maximum allowed (%d bytes) on this server."
                    % (file_size, max_file_size)
                )
        try:
            cur_filename = stream_to_open_named_file(
                page,
                os.open(cur_filename, os.O_WRONLY | os.O_TRUNC | os.O_CREAT),
                cur_filename,
                source_encoding=get_charset_from_http_headers(page.headers),
            )
        except Exception as e:
            sys.exit("Unable to fetch %s:\n%s" % (cur_URL, e))

        # here import checks that upload tool performs
        try:
            ext = sniff.handle_uploaded_dataset_file(cur_filename, datatypes_registry, ext=data_dict["ext"])
        except Exception as e:
            sys.exit(str(e))

        tool_provided_metadata = {out_data_name: {"ext": ext}}

        with open(params["job_config"]["TOOL_PROVIDED_JOB_METADATA_FILE"], "w") as json_file:
            json.dump(tool_provided_metadata, json_file)


if __name__ == "__main__":
    __main__()
