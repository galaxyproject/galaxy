import argparse
import binascii
import json
import os
import sys
import uuid

from genomespaceclient import GenomeSpaceClient


def create_output_path(input_url, metadata):
    """
    Creates an output path if the item to be downloaded is a folder.
    Returns the intended path.
    """
    path = os.path.join(os.getcwd(), metadata.name)
    if metadata.is_directory:
        os.mkdir(path)
    return path


def download_single_item(gs_client, input_url):
    """
    Downloads the file or folder specified through input_url
    to the current working directory.
    """
    # 1. Get file metadata
    metadata = gs_client.get_metadata(input_url)
    if metadata.is_directory and not input_url.endswith("/"):
        input_url += "/"

    # 2. Determine output file path
    output_filename = create_output_path(input_url, metadata)

    # 3. Download file
    gs_client.copy(input_url, output_filename, recurse=True)


def download_from_genomespace_importer(url_with_token, custom_token):

    # Extract input_urls and token  (format is input_urls^token). If a custom_token is
    # provided, use that instead.
    if custom_token:
        input_urls = url_with_token.split('^')[0]
        token = custom_token
    else:
        input_urls, token = url_with_token.split('^')
    input_url_list = input_urls.split(",")

    if not token:
        sys.exit("Invalid token. You must be logged into GenomeSpace through"
                 " OpenID or select a valid file through the GenomeSpace"
                 " browse dialog.")

    gs_client = GenomeSpaceClient(token=token)

    for idx, input_url in enumerate(input_url_list):
        download_single_item(gs_client, input_url)


def process_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_urls', type=str,
                        help="Comma separated list of input urls with an optional token at the end, separated by a ^.",
                        required=True)
    parser.add_argument('-t', '--token', type=str,
                        help="Optional OpenID/GenomeSpace token if not passed in as part of the input_urls as URLs^Token."
                        " If none, the environment variable GS_TOKEN will be respected.", required=False)

    args = parser.parse_args(args[1:])
    return args


def main():
    args = process_args(sys.argv)
    download_from_genomespace_importer(binascii.unhexlify(args.input_urls).decode('utf-8'),
                                       args.token or os.environ.get("GS_TOKEN"))


if __name__ == "__main__":
    sys.exit(main())
