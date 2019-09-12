import argparse
import binascii
import os
import sys

from genomespaceclient import GenomeSpaceClient


def upload_to_genomespace(token, input_file, target_url):
    token = token or os.environ.get('GS_TOKEN')
    gs_client = GenomeSpaceClient(token=token)
    gs_client.copy(input_file, target_url)
    print("File successfully copied.")


def process_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input_file', type=str,
                        help="File to export", required=True)
    parser.add_argument('-o', '--target_url', type=str,
                        help="GenomeSpace output target folder location", required=True)
    parser.add_argument('-t', '--token', type=str,
                        help="Optional OpenID/GenomeSpace token if not passed in as part of the URL as URLs^Token."
                        " If none, the environment variable GS_TOKEN will be respected.", required=False)

    args = parser.parse_args(args[1:])
    return args


def main():
    args = process_args(sys.argv)
    upload_to_genomespace(args.token,
                          binascii.unhexlify(args.input_file).decode('utf-8'),
                          binascii.unhexlify(args.target_url).decode('utf-8'))


if __name__ == "__main__":
    sys.exit(main())
