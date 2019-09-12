import argparse
import json
import os
import sys
import uuid

from genomespaceclient import GenomeSpaceClient

import galaxy
from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry


# Mappings for known genomespace formats to galaxy formats
GENOMESPACE_EXT_TO_GALAXY_EXT = {'rifles': 'rifles',
                                 'lifes': 'lifes',
                                 'cn': 'cn',
                                 'gtf': 'gtf',
                                 'res': 'res',
                                 'xcn': 'xcn',
                                 'lowercasetxt': 'lowercasetxt',
                                 'bed': 'bed',
                                 'cbs': 'cbs',
                                 'genomicatab': 'genomicatab',
                                 'gxp': 'gxp',
                                 'reversedtxt': 'reversedtxt',
                                 'nowhitespace': 'nowhitespace',
                                 'unknown': 'unknown',
                                 'txt': 'txt',
                                 'uppercasetxt': 'uppercasetxt',
                                 'gistic': 'gistic',
                                 'gff': 'gff',
                                 'gmt': 'gmt',
                                 'gct': 'gct'}


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
    However, this hook does not provide access to GALAXY_DATATYPES_CONF_FILE and GALAXY_ROOT_DIR
    properties, so these must be passed in as commandline params.
    """
    if param_dict is None:
        param_dict = {}
    json_params = {}
    json_params['param_dict'] = _prepare_json_param_dict(param_dict)
    json_params['output_data'] = []
    json_params['job_config'] = dict(GALAXY_DATATYPES_CONF_FILE=param_dict.get('GALAXY_DATATYPES_CONF_FILE'),
                                     GALAXY_ROOT_DIR=param_dict.get('GALAXY_ROOT_DIR'),
                                     TOOL_PROVIDED_JOB_METADATA_FILE=galaxy.jobs.TOOL_PROVIDED_JOB_METADATA_FILE)
    json_filename = None
    for i, (out_name, data) in enumerate(out_data.items()):
        file_name = data.get_file_name()
        data_dict = dict(out_data_name=out_name,
                         ext=data.ext,
                         dataset_id=data.dataset.id,
                         hda_id=data.id,
                         file_name=file_name)
        json_params['output_data'].append(data_dict)
        if json_filename is None:
            json_filename = file_name
    with open(json_filename, 'w') as out:
        out.write(json.dumps(json_params))


def get_galaxy_ext_from_genomespace_format(format):
    return GENOMESPACE_EXT_TO_GALAXY_EXT.get(format, None)


def get_galaxy_ext_from_file_ext(filename):
    if not filename:
        return None
    filename = filename.lower()
    ext = filename.rsplit('.', 1)[-1]
    return get_galaxy_ext_from_genomespace_format(ext)


def sniff_and_handle_data_type(json_params, output_file):
    """
    The sniff.handle_uploaded_dataset_file() method in Galaxy performs dual
    functions: it sniffs the filetype and if it's a compressed archive for
    a non compressed datatype such as fasta, it will be unpacked.
    """
    try:
        datatypes_registry = Registry()
        datatypes_registry.load_datatypes(
            root_dir=json_params['job_config']['GALAXY_ROOT_DIR'],
            config=json_params['job_config']['GALAXY_DATATYPES_CONF_FILE'])
        file_type = sniff.handle_uploaded_dataset_file(
            output_file,
            datatypes_registry)
        return file_type
    except Exception:
        return None


def determine_output_filename(input_url, metadata, json_params, primary_dataset):
    """
    Determines the output file name. If only a single output file, the dataset name
    is used. If multiple files are being downloaded, each file is given a unique dataset
    name
    """
    output_filename = json_params['output_data'][0]['file_name']

    if not primary_dataset or not output_filename:
        hda_id = json_params['output_data'][0]['hda_id']
        output_filename = 'primary_%i_%s_visible_%s' % (hda_id, metadata.name, uuid.uuid4())

    return os.path.join(os.getcwd(), output_filename)


def determine_file_type(input_url, output_filename, metadata, json_params, sniffed_type):
    """
    Determine the Galaxy data format for this file.
    """
    # Use genomespace metadata to map type
    file_format = metadata.data_format.name if metadata.data_format else None
    file_type = get_galaxy_ext_from_genomespace_format(file_format)

    # If genomespace metadata has no identifiable format, attempt to sniff type
    if not file_type:
        file_type = sniffed_type

    # Still no type? Attempt to use filename extension to determine a type
    if not file_type:
        file_type = get_galaxy_ext_from_file_ext(metadata.name)

    # Nothing works, use default
    if not file_type:
        file_type = "data"

    return file_type


def save_result_metadata(output_filename, file_type, metadata, json_params,
                         primary_dataset=False):
    """
    Generates a new job metadata file (typically galaxy.json) with details of
    all downloaded files, which Galaxy can read and use to display history items
    and associated metadata
    """
    dataset_id = json_params['output_data'][0]['dataset_id']
    with open(json_params['job_config']['TOOL_PROVIDED_JOB_METADATA_FILE'], 'ab') as metadata_parameter_file:
        if primary_dataset:
            metadata_parameter_file.write("%s\n" % json.dumps(dict(type='dataset',
                                                                   dataset_id=dataset_id,
                                                                   ext=file_type,
                                                                   name="GenomeSpace importer on %s" % (metadata.name))))
        else:
            metadata_parameter_file.write("%s\n" % json.dumps(dict(type='new_primary_dataset',
                                                                   base_dataset_id=dataset_id,
                                                                   ext=file_type,
                                                                   filename=output_filename,
                                                                   name="GenomeSpace importer on %s" % (metadata.name))))


def download_single_file(gs_client, input_url, json_params,
                         primary_dataset=False):
    # 1. Get file metadata
    metadata = gs_client.get_metadata(input_url)

    # 2. Determine output file name
    output_filename = determine_output_filename(input_url, metadata, json_params, primary_dataset)

    # 3. Download file
    gs_client.copy(input_url, output_filename)

    # 4. Decompress file if compressed and sniff type
    sniffed_type = sniff_and_handle_data_type(json_params, output_filename)

    # 5. Determine file type from available metadata
    file_type = determine_file_type(input_url, output_filename, metadata, json_params, sniffed_type)

    # 6. Write job output metadata
    save_result_metadata(output_filename, file_type, metadata, json_params,
                         primary_dataset=primary_dataset)


def download_from_genomespace_importer(json_parameter_file, root, data_conf, custom_token):
    with open(json_parameter_file, 'r') as param_file:
        json_params = json.load(param_file)

    # Add in missing job config properties that could not be set in the exec_before_job hook
    json_params['job_config']['GALAXY_ROOT_DIR'] = root
    json_params['job_config']['GALAXY_DATATYPES_CONF_FILE'] = data_conf

    # Extract input_urls and token  (format is input_urls^token). If a custom_token is
    # provided, use that instead.
    url_with_token = json_params.get('param_dict', {}).get("URL", "")
    if custom_token:
        input_urls = url_with_token.split('^')[0]
        token = custom_token
    else:
        input_urls, token = url_with_token.split('^')
    input_url_list = input_urls.split(",")

    gs_client = GenomeSpaceClient(token=token)

    for idx, input_url in enumerate(input_url_list):
        download_single_file(gs_client, input_url, json_params,
                             primary_dataset=(idx == 0))


def process_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--json_parameter_file', type=str,
                        help="JSON parameter file", required=True)
    parser.add_argument('-r', '--galaxy_root', type=str,
                        help="Galaxy root dir", required=True)
    parser.add_argument('-c', '--data_conf', type=str,
                        help="Galaxy data types conf file for mapping file types", required=True)
    parser.add_argument('-t', '--token', type=str,
                        help="Optional OpenID/GenomeSpace token if not passed in as part of the URL as URLs^Token."
                        " If none, the environment variable GS_TOKEN will be respected.", required=False)

    args = parser.parse_args(args[1:])
    return args


def main():
    args = process_args(sys.argv)
    download_from_genomespace_importer(args.json_parameter_file, args.galaxy_root, args.data_conf, args.token or os.environ.get("GS_TOKEN"))


if __name__ == "__main__":
    sys.exit(main())
