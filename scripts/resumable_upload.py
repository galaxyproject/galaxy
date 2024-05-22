#!/usr/bin/env python3
import os

import click
import requests
from tusclient import client
from tusclient.storage import filestorage

UPLOAD_ENDPOINT = "/api/upload/resumable_upload"
SUBMISSION_ENDPOINT = "/api/tools/fetch"
CHUNK_SIZE = 10**7


@click.command()
@click.option("--url", default="http://localhost:8080", help="URL of Galaxy instance")
@click.option("--api_key", envvar="GALAXY_API_KEY", required=True, help="API key for Galaxy instance")
@click.option("--history_id", type=str, required=True, help="Target History ID")
@click.option("--file_type", default="auto", type=str, help="Galaxy file type to use")
@click.option("--dbkey", default="?", type=str, help="Genome Build for dataset")
@click.option("--filename", type=str, help="Filename to use in Galaxy history, if different from path")
@click.option("--storage", type=click.Path(), required=False, help="Store URLs to resume here")
@click.argument("path", type=click.Path())
def upload_file(url, path, api_key, history_id, file_type="auto", dbkey="?", filename=None, storage=None):
    headers = {"x-api-key": api_key}
    my_client = client.TusClient(f"{url}{UPLOAD_ENDPOINT}", headers=headers)
    filename = filename or os.path.basename(path)
    metadata = {
        "filename": filename,
        "history_id": history_id,
        "file_type": file_type,
        "dbkey": dbkey,
    }

    # Upload a file to a tus server.
    if storage:
        storage = filestorage.FileStorage(storage)
    uploader = my_client.uploader(path, metadata=metadata, url_storage=storage)
    uploader.chunk_size = CHUNK_SIZE
    uploader.upload()

    # Extract session from created upload URL
    session_id = uploader.url.rsplit("/", 1)[1]
    payload = {
        "history_id": history_id,
        "targets": [
            {
                "destination": {"type": "hdas"},
                "elements": [{"src": "files", "ext": file_type, "dbkey": dbkey, "name": filename}],
            }
        ],
        "files_0|file_data": {"session_id": session_id, "name": filename},
    }
    response = requests.post(
        f"{url}{SUBMISSION_ENDPOINT}",
        json=payload,
        headers=headers,
    )
    response.raise_for_status()


if __name__ == "__main__":
    upload_file()
