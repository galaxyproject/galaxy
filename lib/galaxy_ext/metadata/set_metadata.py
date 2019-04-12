"""
Execute an external process to set_meta() on a provided list of pickled datasets.

This was formerly scripts/set_metadata.py and expects these arguments:

    %prog datatypes_conf.xml job_metadata_file metadata_in,metadata_kwds,metadata_out,metadata_results_code,output_filename_override,metadata_override... max_metadata_value_size

Galaxy should be importable on sys.path and output_filename_override should be
set to the path of the dataset on which metadata is being set
(output_filename_override could previously be left empty and the path would be
constructed automatically).
"""
import json
import logging
import os
import sys

# insert *this* galaxy before all others on sys.path
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))

from six.moves import cPickle
from sqlalchemy.orm import clear_mappers

import galaxy.model.mapping  # need to load this before we unpickle, in order to setup properties assigned by the mappers
from galaxy.model.custom_types import total_size
from galaxy.util import stringify_dictionary_keys
from ._provided_metadata import parse_tool_provided_metadata

# ensure supported version
assert sys.version_info[:2] >= (2, 7), 'Python version must be at least 2.7, this is: %s' % sys.version

logging.basicConfig()
log = logging.getLogger(__name__)

galaxy.model.Job()  # this looks REAL stupid, but it is REQUIRED in order for SA to insert parameters into the classes defined by the mappers --> it appears that instantiating ANY mapper'ed class would suffice here


def set_meta_with_tool_provided(dataset_instance, file_dict, set_meta_kwds, datatypes_registry, max_metadata_value_size):
    # This method is somewhat odd, in that we set the metadata attributes from tool,
    # then call set_meta, then set metadata attributes from tool again.
    # This is intentional due to interplay of overwrite kwd, the fact that some metadata
    # parameters may rely on the values of others, and that we are accepting the
    # values provided by the tool as Truth.
    extension = dataset_instance.extension
    if extension == "_sniff_":
        try:
            from galaxy.datatypes import sniff
            extension = sniff.handle_uploaded_dataset_file(dataset_instance.dataset.external_filename, datatypes_registry)
            # We need to both set the extension so it is available to set_meta
            # and record it in the metadata so it can be reloaded on the server
            # side and the model updated (see MetadataCollection.{from,to}_JSON_dict)
            dataset_instance.extension = extension
            # Set special metadata property that will reload this on server side.
            setattr(dataset_instance.metadata, "__extension__", extension)
        except Exception:
            log.exception("Problem sniffing datatype.")

    for metadata_name, metadata_value in file_dict.get('metadata', {}).items():
        setattr(dataset_instance.metadata, metadata_name, metadata_value)
    dataset_instance.datatype.set_meta(dataset_instance, **set_meta_kwds)
    for metadata_name, metadata_value in file_dict.get('metadata', {}).items():
        setattr(dataset_instance.metadata, metadata_name, metadata_value)

    if max_metadata_value_size:
        for k, v in list(dataset_instance.metadata.items()):
            if total_size(v) > max_metadata_value_size:
                log.info("Key %s too large for metadata, discarding" % k)
                dataset_instance.metadata.remove_key(k)


def set_metadata():
    if len(sys.argv) == 1:
        set_metadata_portable()
    else:
        set_metadata_legacy()


def set_metadata_portable():
    import galaxy.model
    galaxy.model.metadata.MetadataTempFile.tmp_dir = tool_job_working_directory = os.path.abspath(os.getcwd())

    metadata_params_path = os.path.join("metadata", "params.json")
    try:
        with open(metadata_params_path, "r") as f:
            metadata_params = json.load(f)
    except IOError:
        raise Exception("Failed to find metadata/params.json from cwd [%s]" % tool_job_working_directory)
    datatypes_config = metadata_params["datatypes_config"]
    job_metadata = metadata_params["job_metadata"]
    max_metadata_value_size = metadata_params.get("max_metadata_value_size") or 0
    outputs = metadata_params["outputs"]

    datatypes_registry = validate_and_load_datatypes_config(datatypes_config)
    tool_provided_metadata = load_job_metadata(job_metadata)

    def set_meta(new_dataset_instance, file_dict):
        set_meta_with_tool_provided(new_dataset_instance, file_dict, set_meta_kwds, datatypes_registry, max_metadata_value_size)

    for output_name, output_dict in outputs.items():
        filename_in = os.path.join("metadata/metadata_in_%s" % output_name)
        filename_kwds = os.path.join("metadata/metadata_kwds_%s" % output_name)
        filename_out = os.path.join("metadata/metadata_out_%s" % output_name)
        filename_results_code = os.path.join("metadata/metadata_results_%s" % output_name)
        override_metadata = os.path.join("metadata/metadata_override_%s" % output_name)
        dataset_filename_override = output_dict["filename_override"]

        # Same block as below...
        set_meta_kwds = stringify_dictionary_keys(json.load(open(filename_kwds)))  # load kwds; need to ensure our keywords are not unicode
        try:
            dataset = cPickle.load(open(filename_in, 'rb'))  # load DatasetInstance
            dataset.dataset.external_filename = dataset_filename_override
            store_by = metadata_params.get("object_store_store_by", "id")
            extra_files_dir_name = "dataset_%s_files" % getattr(dataset.dataset, store_by)
            files_path = os.path.abspath(os.path.join(tool_job_working_directory, extra_files_dir_name))
            dataset.dataset.external_extra_files_path = files_path
            file_dict = tool_provided_metadata.get_dataset_meta(output_name, dataset.dataset.id)
            if 'ext' in file_dict:
                dataset.extension = file_dict['ext']
            # Metadata FileParameter types may not be writable on a cluster node, and are therefore temporarily substituted with MetadataTempFiles
            override_metadata = json.load(open(override_metadata))
            for metadata_name, metadata_file_override in override_metadata:
                if galaxy.datatypes.metadata.MetadataTempFile.is_JSONified_value(metadata_file_override):
                    metadata_file_override = galaxy.datatypes.metadata.MetadataTempFile.from_JSON(metadata_file_override)
                setattr(dataset.metadata, metadata_name, metadata_file_override)
            set_meta(dataset, file_dict)
            dataset.metadata.to_JSON_dict(filename_out)  # write out results of set_meta
            json.dump((True, 'Metadata has been set successfully'), open(filename_results_code, 'wt+'))  # setting metadata has succeeded
        except Exception as e:
            json.dump((False, str(e)), open(filename_results_code, 'wt+'))  # setting metadata has failed somehow

    write_job_metadata(tool_job_working_directory, job_metadata, set_meta, tool_provided_metadata)


def set_metadata_legacy():
    import galaxy.model
    galaxy.model.metadata.MetadataTempFile.tmp_dir = tool_job_working_directory = os.path.abspath(os.getcwd())

    # This is ugly, but to transition from existing jobs without this parameter
    # to ones with, smoothly, it has to be the last optional parameter and we
    # have to sniff it.
    try:
        max_metadata_value_size = int(sys.argv[-1])
        sys.argv = sys.argv[:-1]
    except ValueError:
        max_metadata_value_size = 0
        # max_metadata_value_size is unspecified and should be 0

    # Set up datatypes registry
    datatypes_config = sys.argv.pop(1)
    datatypes_registry = validate_and_load_datatypes_config(datatypes_config)

    job_metadata = sys.argv.pop(1)
    tool_provided_metadata = load_job_metadata(job_metadata)

    def set_meta(new_dataset_instance, file_dict):
        set_meta_with_tool_provided(new_dataset_instance, file_dict, set_meta_kwds, datatypes_registry, max_metadata_value_size)

    for filenames in sys.argv[1:]:
        fields = filenames.split(',')
        filename_in = fields.pop(0)
        filename_kwds = fields.pop(0)
        filename_out = fields.pop(0)
        filename_results_code = fields.pop(0)
        dataset_filename_override = fields.pop(0)
        override_metadata = fields.pop(0)
        set_meta_kwds = stringify_dictionary_keys(json.load(open(filename_kwds)))  # load kwds; need to ensure our keywords are not unicode
        try:
            dataset = cPickle.load(open(filename_in, 'rb'))  # load DatasetInstance
            dataset.dataset.external_filename = dataset_filename_override
            files_path = os.path.abspath(os.path.join(tool_job_working_directory, "dataset_%s_files" % (dataset.dataset.id)))
            dataset.dataset.external_extra_files_path = files_path
            file_dict = tool_provided_metadata.get_dataset_meta(None, dataset.dataset.id)
            if 'ext' in file_dict:
                dataset.extension = file_dict['ext']
            # Metadata FileParameter types may not be writable on a cluster node, and are therefore temporarily substituted with MetadataTempFiles
            override_metadata = json.load(open(override_metadata))
            for metadata_name, metadata_file_override in override_metadata:
                if galaxy.datatypes.metadata.MetadataTempFile.is_JSONified_value(metadata_file_override):
                    metadata_file_override = galaxy.datatypes.metadata.MetadataTempFile.from_JSON(metadata_file_override)
                setattr(dataset.metadata, metadata_name, metadata_file_override)
            set_meta(dataset, file_dict)
            dataset.metadata.to_JSON_dict(filename_out)  # write out results of set_meta
            json.dump((True, 'Metadata has been set successfully'), open(filename_results_code, 'wt+'))  # setting metadata has succeeded
        except Exception as e:
            json.dump((False, str(e)), open(filename_results_code, 'wt+'))  # setting metadata has failed somehow

    write_job_metadata(tool_job_working_directory, job_metadata, set_meta, tool_provided_metadata)


def validate_and_load_datatypes_config(datatypes_config):
    galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))

    if not os.path.exists(datatypes_config):
        print("Metadata setting failed because registry.xml could not be found. You may retry setting metadata.")
        sys.exit(1)
    import galaxy.datatypes.registry
    datatypes_registry = galaxy.datatypes.registry.Registry()
    datatypes_registry.load_datatypes(root_dir=galaxy_root, config=datatypes_config)
    galaxy.model.set_datatypes_registry(datatypes_registry)
    return datatypes_registry


def load_job_metadata(job_metadata):
    return parse_tool_provided_metadata(job_metadata)


def write_job_metadata(tool_job_working_directory, job_metadata, set_meta, tool_provided_metadata):
    for i, file_dict in enumerate(tool_provided_metadata.get_new_datasets_for_metadata_collection(), start=1):
        filename = file_dict["filename"]
        new_dataset_filename = os.path.join(tool_job_working_directory, "working", filename)
        new_dataset = galaxy.model.Dataset(id=-i, external_filename=new_dataset_filename)
        extra_files = file_dict.get('extra_files', None)
        if extra_files is not None:
            new_dataset._extra_files_path = os.path.join(tool_job_working_directory, "working", extra_files)
        new_dataset.state = new_dataset.states.OK
        new_dataset_instance = galaxy.model.HistoryDatasetAssociation(id=-i, dataset=new_dataset, extension=file_dict.get('ext', 'data'))
        set_meta(new_dataset_instance, file_dict)
        file_dict['metadata'] = json.loads(new_dataset_instance.metadata.to_JSON_dict())  # storing metadata in external form, need to turn back into dict, then later jsonify

    tool_provided_metadata.rewrite()
    clear_mappers()
