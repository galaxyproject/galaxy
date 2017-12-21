import argparse
import json
import os
import sys
import uuid

from genomespaceclient import GenomeSpaceClient

import galaxy


def _prepare_json_list(param_list):
    """
    JSON serialization Support functions for exec_before_job hook
    """
    rval = []
    for value in param_list:
        if isinstance(value, dict):
            rval.append(_prepare_json_param_dict(value))
        elif isinstance(value, list):
            rval.append(_prepare_json_list(value))
        else:
            rval.append(str(value))
    return rval


def _prepare_json_param_dict(param_dict):
    """
    JSON serialization Support functions for exec_before_job hook
    """
    rval = {}
    for key, value in param_dict.items():
        if isinstance(value, dict):
            rval[key] = _prepare_json_param_dict(value)
        elif isinstance(value, list):
            rval[key] = _prepare_json_list(value)
        else:
            rval[key] = str(value)
    return rval


def exec_before_job(app, inp_data, out_data, param_dict=None, tool=None):
    """
    Galaxy override hook
    See: https://wiki.galaxyproject.org/Admin/Tools/ToolConfigSyntax#A.3Ccode.3E_tag_set
    Since only tools with tool_type="data_source" provides functionality for having a JSON param file such as this:
    https://wiki.galaxyproject.org/Admin/Tools/DataManagers/DataManagerJSONSyntax#Example_JSON_input_to_tool,
    this hook is used to manually create a similar JSON file.
    """
    if param_dict is None:
        param_dict = {}
    json_params = {}
    json_params['param_dict'] = _prepare_json_param_dict(param_dict)
    json_filename = None
    for i, (out_name, data) in enumerate(out_data.items()):
        file_name = data.get_file_name()
        if json_filename is None:
            json_filename = file_name
    with open(json_filename, 'w') as out:
        out.write(json.dumps(json_params))

def create_output_path(input_url, metadata):
    """
    Creates an output path if the item to be downloaded is a folder.
    Returns the intended path.
    """
    path = os.path.join(os.getcwd(), metadata.name)
    if metadata.isDirectory:
        os.mkdir(path)
    return path


def download_single_item(gs_client, input_url):
    """
    Downloads the file or folder specified through input_url
    to the current working directory.
    """
    # 1. Get file metadata
    metadata = gs_client.get_metadata(input_url)
    if metadata.isDirectory and not input_url.endswith("/"):
        input_url += "/"

    # 2. Determine output file path
    output_filename = create_output_path(input_url, metadata)

    # 3. Download file
    gs_client.copy(input_url, output_filename, recurse=True)


def download_from_genomespace_importer(json_parameter_file, custom_token):
    with open(json_parameter_file, 'r') as param_file:
        json_params = json.load(param_file)

    # Extract input_urls and token  (format is input_urls^token). If a custom_token is
    # provided, use that instead.
    url_with_token = json_params.get('param_dict', {}).get("URL", "")
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
    parser.add_argument('-p', '--json_parameter_file', type=str,
                        help="JSON parameter file", required=True)
    parser.add_argument('-t', '--token', type=str,
                        help="Optional OpenID/GenomeSpace token if not passed in as part of the URL as URLs^Token."
                        " If none, the environment variable GS_TOKEN will be respected.", required=False)

    args = parser.parse_args(args[1:])
    return args


def main():
    args = process_args(sys.argv)
    download_from_genomespace_importer(args.json_parameter_file, args.token or os.environ.get("GS_TOKEN"))


if __name__ == "__main__":
    sys.exit(main())
