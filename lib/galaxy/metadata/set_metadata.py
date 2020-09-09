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
import traceback

from six.moves import cPickle
from sqlalchemy.orm import clear_mappers

import galaxy.model.mapping  # need to load this before we unpickle, in order to setup properties assigned by the mappers
from galaxy.model import store
from galaxy.model.custom_types import total_size
from galaxy.tool_util.provided_metadata import parse_tool_provided_metadata
from galaxy.util import (
    stringify_dictionary_keys,
    unicodify,
)

logging.basicConfig()
log = logging.getLogger(__name__)


def set_validated_state(dataset_instance):
    from galaxy.datatypes.data import validate
    datatype_validation = validate(dataset_instance)

    dataset_instance.validated_state = datatype_validation.state
    dataset_instance.validated_state_message = datatype_validation.message

    # Set special metadata property that will reload this on server side.
    dataset_instance.metadata.__validated_state__ = datatype_validation.state
    dataset_instance.metadata.__validated_state_message__ = datatype_validation.message


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
            dataset_instance.metadata.__extension__ = extension
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
    tool_job_working_directory = os.path.abspath(os.getcwd())
    metadata_tmp_files_dir = os.path.join(tool_job_working_directory, "metadata")
    galaxy.model.metadata.MetadataTempFile.tmp_dir = metadata_tmp_files_dir

    metadata_params_path = os.path.join("metadata", "params.json")
    try:
        with open(metadata_params_path) as f:
            metadata_params = json.load(f)
    except OSError:
        raise Exception("Failed to find metadata/params.json from cwd [%s]" % tool_job_working_directory)
    datatypes_config = metadata_params["datatypes_config"]
    job_metadata = metadata_params["job_metadata"]
    provided_metadata_style = metadata_params.get("provided_metadata_style")
    max_metadata_value_size = metadata_params.get("max_metadata_value_size") or 0
    outputs = metadata_params["outputs"]

    datatypes_registry = validate_and_load_datatypes_config(datatypes_config)
    tool_provided_metadata = load_job_metadata(job_metadata, provided_metadata_style)

    def set_meta(new_dataset_instance, file_dict):
        set_meta_with_tool_provided(new_dataset_instance, file_dict, set_meta_kwds, datatypes_registry, max_metadata_value_size)

    object_store_conf_path = os.path.join("metadata", "object_store_conf.json")
    extended_metadata_collection = os.path.exists(object_store_conf_path)

    object_store = None
    job_context = None
    version_string = ""

    export_store = None
    if extended_metadata_collection:
        from galaxy.tool_util.parser.stdio import ToolStdioRegex, ToolStdioExitCode
        tool_dict = metadata_params["tool"]
        stdio_exit_code_dicts, stdio_regex_dicts = tool_dict["stdio_exit_codes"], tool_dict["stdio_regexes"]
        stdio_exit_codes = list(map(ToolStdioExitCode, stdio_exit_code_dicts))
        stdio_regexes = list(map(ToolStdioRegex, stdio_regex_dicts))

        with open(object_store_conf_path) as f:
            config_dict = json.load(f)
        from galaxy.objectstore import build_object_store_from_config
        assert config_dict is not None
        object_store = build_object_store_from_config(None, config_dict=config_dict)
        galaxy.model.Dataset.object_store = object_store

        outputs_directory = os.path.join(tool_job_working_directory, "outputs")
        if not os.path.exists(outputs_directory):
            outputs_directory = tool_job_working_directory

        # TODO: constants...
        if os.path.exists(os.path.join(outputs_directory, "tool_stdout")):
            with open(os.path.join(outputs_directory, "tool_stdout"), "rb") as f:
                tool_stdout = f.read()

            with open(os.path.join(outputs_directory, "tool_stderr"), "rb") as f:
                tool_stderr = f.read()
        elif os.path.exists(os.path.join(outputs_directory, "stdout")):
            # Puslar style working directory.
            with open(os.path.join(outputs_directory, "stdout"), "rb") as f:
                tool_stdout = f.read()

            with open(os.path.join(outputs_directory, "stderr"), "rb") as f:
                tool_stderr = f.read()

        job_id_tag = metadata_params["job_id_tag"]

        # TODO: this clearly needs to be refactored, nothing in runners should be imported here..
        from galaxy.job_execution.output_collect import default_exit_code_file, read_exit_code_from
        exit_code_file = default_exit_code_file(".", job_id_tag)
        tool_exit_code = read_exit_code_from(exit_code_file, job_id_tag)

        from galaxy.tool_util.output_checker import check_output, DETECTED_JOB_STATE
        check_output_detected_state, tool_stdout, tool_stderr, job_messages = check_output(stdio_regexes, stdio_exit_codes, tool_stdout, tool_stderr, tool_exit_code, job_id_tag)
        if check_output_detected_state == DETECTED_JOB_STATE.OK and not tool_provided_metadata.has_failed_outputs():
            final_job_state = galaxy.model.Job.states.OK
        else:
            final_job_state = galaxy.model.Job.states.ERROR

        from pulsar.client.staging import COMMAND_VERSION_FILENAME
        version_string = ""
        if os.path.exists(COMMAND_VERSION_FILENAME):
            version_string = open(COMMAND_VERSION_FILENAME).read()

        from galaxy.util.expressions import ExpressionContext
        job_context = ExpressionContext(dict(stdout=tool_stdout, stderr=tool_stderr))

        # Load outputs.
        import_model_store = store.imported_store_for_metadata('metadata/outputs_new', object_store=object_store)
        export_store = store.DirectoryModelExportStore('metadata/outputs_populated', serialize_dataset_objects=True, for_edit=True, strip_metadata_files=False)

    for output_name, output_dict in outputs.items():
        if extended_metadata_collection:
            dataset_instance_id = output_dict["id"]
            dataset = import_model_store.sa_session.query(galaxy.model.HistoryDatasetAssociation).find(dataset_instance_id)
            assert dataset is not None
        else:
            filename_in = os.path.join("metadata/metadata_in_%s" % output_name)
            dataset = cPickle.load(open(filename_in, 'rb'))  # load DatasetInstance

        filename_kwds = os.path.join("metadata/metadata_kwds_%s" % output_name)
        filename_out = os.path.join("metadata/metadata_out_%s" % output_name)
        filename_results_code = os.path.join("metadata/metadata_results_%s" % output_name)
        override_metadata = os.path.join("metadata/metadata_override_%s" % output_name)
        dataset_filename_override = output_dict["filename_override"]
        # pre-20.05 this was a per job parameter and not a per dataset parameter, drop in 21.XX
        legacy_object_store_store_by = metadata_params.get("object_store_store_by", "id")

        # Same block as below...
        set_meta_kwds = stringify_dictionary_keys(json.load(open(filename_kwds)))  # load kwds; need to ensure our keywords are not unicode
        try:
            dataset.dataset.external_filename = dataset_filename_override
            store_by = output_dict.get("object_store_store_by", legacy_object_store_store_by)
            extra_files_dir_name = "dataset_%s_files" % getattr(dataset.dataset, store_by)
            files_path = os.path.abspath(os.path.join(tool_job_working_directory, "working", extra_files_dir_name))
            dataset.dataset.external_extra_files_path = files_path
            file_dict = tool_provided_metadata.get_dataset_meta(output_name, dataset.dataset.id, dataset.dataset.uuid)
            if 'ext' in file_dict:
                dataset.extension = file_dict['ext']
            # Metadata FileParameter types may not be writable on a cluster node, and are therefore temporarily substituted with MetadataTempFiles
            override_metadata = json.load(open(override_metadata))
            for metadata_name, metadata_file_override in override_metadata:
                if galaxy.datatypes.metadata.MetadataTempFile.is_JSONified_value(metadata_file_override):
                    metadata_file_override = galaxy.datatypes.metadata.MetadataTempFile.from_JSON(metadata_file_override)
                setattr(dataset.metadata, metadata_name, metadata_file_override)
            if output_dict.get("validate", False):
                set_validated_state(dataset)
            set_meta(dataset, file_dict)

            if extended_metadata_collection:
                meta = tool_provided_metadata.get_dataset_meta(output_name, dataset.dataset.id, dataset.dataset.uuid)
                if meta:
                    context = ExpressionContext(meta, job_context)
                else:
                    context = job_context

                # Lazy and unattached
                # if getattr(dataset, "hidden_beneath_collection_instance", None):
                #    dataset.visible = False
                dataset.blurb = 'done'
                dataset.peek = 'no peek'
                dataset.info = (dataset.info or '')
                if context['stdout'].strip():
                    # Ensure white space between entries
                    dataset.info = dataset.info.rstrip() + "\n" + context['stdout'].strip()
                if context['stderr'].strip():
                    # Ensure white space between entries
                    dataset.info = dataset.info.rstrip() + "\n" + context['stderr'].strip()
                dataset.tool_version = version_string
                dataset.set_size()
                if 'uuid' in context:
                    dataset.dataset.uuid = context['uuid']
                if dataset_filename_override and dataset_filename_override != dataset.file_name:
                    # This has to be a job with outputs_to_working_directory set.
                    # We update the object store with the created output file.
                    object_store.update_from_file(dataset.dataset, file_name=dataset_filename_override, create=True)
                from galaxy.job_execution.output_collect import collect_extra_files
                collect_extra_files(object_store, dataset, ".")
                if galaxy.model.Job.states.ERROR == final_job_state:
                    dataset.blurb = "error"
                    dataset.mark_unhidden()
                else:
                    # If the tool was expected to set the extension, attempt to retrieve it
                    if dataset.ext == 'auto':
                        dataset.extension = context.get('ext', 'data')
                        dataset.init_meta(copy_from=dataset)

                    # This has already been done:
                    # else:
                    #     self.external_output_metadata.load_metadata(dataset, output_name, self.sa_session, working_directory=self.working_directory, remote_metadata_directory=remote_metadata_directory)
                    line_count = context.get('line_count', None)
                    try:
                        # Certain datatype's set_peek methods contain a line_count argument
                        dataset.set_peek(line_count=line_count)
                    except TypeError:
                        # ... and others don't
                        dataset.set_peek()

                from galaxy.jobs import TOOL_PROVIDED_JOB_METADATA_KEYS
                for context_key in TOOL_PROVIDED_JOB_METADATA_KEYS:
                    if context_key in context:
                        context_value = context[context_key]
                        setattr(dataset, context_key, context_value)
                # We never want to persist the external_filename.
                dataset.dataset.external_filename = None
                export_store.add_dataset(dataset)
            else:
                dataset.metadata.to_JSON_dict(filename_out)  # write out results of set_meta

            json.dump((True, 'Metadata has been set successfully'), open(filename_results_code, 'wt+'))  # setting metadata has succeeded
        except Exception:
            json.dump((False, traceback.format_exc()), open(filename_results_code, 'wt+'))  # setting metadata has failed somehow

    if extended_metadata_collection:
        # discover extra outputs...
        from galaxy.job_execution.output_collect import collect_dynamic_outputs, collect_primary_datasets, SessionlessJobContext

        job_context = SessionlessJobContext(
            metadata_params,
            tool_provided_metadata,
            object_store,
            export_store,
            import_model_store,
            os.path.join(tool_job_working_directory, "working"),
            final_job_state=final_job_state,
        )

        output_collections = {}
        for name, output_collection in metadata_params["output_collections"].items():
            output_collections[name] = import_model_store.sa_session.query(galaxy.model.HistoryDatasetCollectionAssociation).find(output_collection["id"])
        outputs = {}
        for name, output in metadata_params["outputs"].items():
            outputs[name] = import_model_store.sa_session.query(galaxy.model.HistoryDatasetAssociation).find(output["id"])

        input_ext = json.loads(metadata_params["job_params"].get("__input_ext", '"data"'))
        collect_primary_datasets(
            job_context,
            outputs,
            input_ext=input_ext,
        )
        collect_dynamic_outputs(job_context, output_collections)

    if export_store:
        export_store._finalize()
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
    tool_provided_metadata = load_job_metadata(job_metadata, None)

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
            store_by = "id"
            extra_files_dir_name = "dataset_%s_files" % getattr(dataset.dataset, store_by)
            files_path = os.path.abspath(os.path.join(tool_job_working_directory, "working", extra_files_dir_name))
            dataset.dataset.external_extra_files_path = files_path
            file_dict = tool_provided_metadata.get_dataset_meta(None, dataset.dataset.id, dataset.dataset.uuid)
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
            json.dump((False, unicodify(e)), open(filename_results_code, 'wt+'))  # setting metadata has failed somehow

    write_job_metadata(tool_job_working_directory, job_metadata, set_meta, tool_provided_metadata)


def validate_and_load_datatypes_config(datatypes_config):
    galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))

    if not os.path.exists(datatypes_config):
        # Hack for Pulsar on usegalaxy.org, drop ASAP.
        datatypes_config = "configs/registry.xml"

    if not os.path.exists(datatypes_config):
        print("Metadata setting failed because registry.xml [%s] could not be found. You may retry setting metadata." % datatypes_config)
        sys.exit(1)
    import galaxy.datatypes.registry
    datatypes_registry = galaxy.datatypes.registry.Registry()
    datatypes_registry.load_datatypes(root_dir=galaxy_root, config=datatypes_config, use_build_sites=False, use_converters=False, use_display_applications=False)
    galaxy.model.set_datatypes_registry(datatypes_registry)
    return datatypes_registry


def load_job_metadata(job_metadata, provided_metadata_style):
    return parse_tool_provided_metadata(job_metadata, provided_metadata_style=provided_metadata_style)


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
