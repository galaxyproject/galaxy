#!/usr/bin/env python
"""
Upload a file to the desired history.
"""

import json
import os
import sys

import requests


def upload_file(base_url, api_key, history_id, filepath, **kwargs):
    full_url = base_url + "/api/tools"

    payload = {
        "key": api_key,
        "tool_id": "upload1",
        "history_id": history_id,
    }
    inputs = {
        "files_0|NAME": kwargs.get("filename", os.path.basename(filepath)),
        "files_0|type": "upload_dataset",
        # TODO: the following doesn't work with tools.py
        "dbkey": "?",
        "file_type": kwargs.get("file_type", "auto"),
        "ajax_upload": "true",
    }
    payload["inputs"] = json.dumps(inputs)

    response = None
    with open(filepath, "rb") as file_to_upload:
        files = {"files_0|file_data": file_to_upload}
        response = requests.post(full_url, data=payload, files=files)
    return response.json()


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(
            "history_upload.py <api key> <galaxy base url> <history id> <filepath to upload>\n"
            "  (where galaxy base url is just the root url where your Galaxy is served; e.g. 'localhost:8080')"
        )
        sys.exit(1)

    api_key, base_url, history_id, filepath = sys.argv[1:5]
    kwargs = dict([kwarg.split("=", 1) for kwarg in sys.argv[5:]])

    response = upload_file(base_url, api_key, history_id, filepath, **kwargs)
    print(response, file=sys.stderr)
