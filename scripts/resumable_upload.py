import os

import aiotus
import asyncclick as click

creation_url = "http://localhost:8000/"
UPLOAD_ENDPOINT = '/api/upload/resumable_upload'


@click.command()
@click.option("--url", default='http://localhost:8080', help="URL of Galaxy instance")
@click.option("--api_key", envvar="GALAXY_API_KEY", help="API key for Galaxy instance")
@click.option('--history_id', type=str, required=True, help="Target History ID")
@click.option('--file_type', default="auto", type=str, help="Galaxy file type to use")
@click.option('--dbkey', default="?", type=str, help="Genome Build for dataset")
@click.option('--filename', type=str, help="Filename to use in Galaxy history, if different from path")
@click.argument('path', type=click.Path())
async def upload_file(url, path, api_key, history_id, file_type='auto', dbkey='?', filename=None):
    filename = filename or os.path.basename(path)
    metadata = {
        'filename': filename.encode(),
        'history_id': history_id.encode(),
        'file_type': file_type.encode(),
        'dbkey': dbkey.encode(),
    }
    headers = {'x-api-key': api_key}

    # Upload a file to a tus server.
    with open(path, "rb") as f:
        location = await aiotus.upload(f"{url}{UPLOAD_ENDPOINT}", f, metadata, headers=headers)
        # 'location' is the URL where the file was uploaded to.

    # Read back the metadata from the server.
    metadata = await aiotus.metadata(location, headers=headers)
    print(metadata)


if __name__ == '__main__':
    upload_file()
