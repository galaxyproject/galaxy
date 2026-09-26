#!/usr/bin/env python
# Retrieves data from external data source applications and stores in a dataset file.
# Data source application parameters are temporarily stored in the dataset file.
import json
import os
import sys
from contextlib import contextmanager
from urllib.parse import (
    urlencode,
    urlparse,
)
from urllib.request import (
    Request,
    urlopen,
)

from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    get_charset_from_http_headers,
    requests,
    stream_to_path,
)
from galaxy.util.user_agent import get_default_headers

GALAXY_PARAM_PREFIX = "GALAXY"
GALAXY_ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
GALAXY_DATATYPES_CONF_FILE = os.path.join(GALAXY_ROOT_DIR, "datatypes_conf.xml")


@contextmanager
def _open_remote_source(url, method, incoming_request_params, headers):
    scheme = urlparse(url).scheme
    if method not in ("get", "post"):
        raise ValueError(f"Unknown URL_method specified: {method}")

    if scheme == "ftp":
        data = urlencode(incoming_request_params).encode("utf-8") if method == "post" else None
        request = Request(url, data=data, headers=headers)
        with urlopen(request, timeout=DEFAULT_SOCKET_TIMEOUT) as response:
            yield response, response.headers
        return

    data = incoming_request_params if method == "post" else None
    with requests.Session() as session:
        request_method = session.get if method == "get" else session.post
        with request_method(
            url,
            data=data,
            headers=headers,
            stream=True,
            timeout=DEFAULT_SOCKET_TIMEOUT,
        ) as response:
            response.raise_for_status()
            response.raw.decode_content = True
            yield response.raw, response.headers


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
        cur_URL = params["param_dict"].get("{}|{}|URL".format(GALAXY_PARAM_PREFIX, data_dict["out_data_name"]), URL)
        if not cur_URL or urlparse(cur_URL).scheme not in ("http", "https", "ftp"):
            open(cur_filename, "w").write("")
            sys.exit("The remote data source application has not sent back a URL parameter in the request.")

        headers = get_default_headers()
        try:
            remote_source = _open_remote_source(
                cur_URL,
                URL_method,
                params["param_dict"].get("incoming_request_params", {}),
                headers,
            )
            page, response_headers = remote_source.__enter__()
        except Exception as e:
            sys.exit("The remote data source application may be off line, please try again later. Error: %s" % str(e))
        try:
            if max_file_size:
                file_size = int(response_headers.get("Content-Length", 0))
                if file_size > max_file_size:
                    sys.exit(
                        f"The size of the data ({file_size} bytes) you have requested exceeds the maximum allowed "
                        f"({max_file_size} bytes) on this server."
                    )
            cur_filename = stream_to_path(
                page,
                cur_filename,
                source_encoding=get_charset_from_http_headers(response_headers),
            )
        except Exception as e:
            sys.exit(f"Unable to fetch {cur_URL}:\n{e}")
        finally:
            remote_source.__exit__(None, None, None)

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
