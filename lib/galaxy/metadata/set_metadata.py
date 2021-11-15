"""
Execute an external process to set_meta() on a provided list of pickled datasets.

This was formerly scripts/set_metadata.py and expects these arguments:

    %prog datatypes_conf.xml job_metadata_file metadata_kwds,metadata_out,metadata_results_code,output_filename_override,metadata_override... max_metadata_value_size

Galaxy should be importable on sys.path and output_filename_override should be
set to the path of the dataset on which metadata is being set
(output_filename_override could previously be left empty and the path would be
constructed automatically).
"""
import glob
import json
import logging
import os
import sys
import traceback
from pathlib import Path

try:
    from pulsar.client.staging import COMMAND_VERSION_FILENAME
except ImportError:
    # Package unit tests
    COMMAND_VERSION_FILENAME = 'COMMAND_VERSION'

import galaxy.datatypes.registry
import galaxy.model.mapping
from galaxy.datatypes import sniff
from galaxy.datatypes.data import validate
from galaxy.job_execution.output_collect import (
    collect_dynamic_outputs,
    collect_extra_files,
    collect_primary_datasets,
    collect_shrinked_content_from_path,
    default_exit_code_file,
    read_exit_code_from,
    SessionlessJobContext,
)
from galaxy.job_execution.setup import TOOL_PROVIDED_JOB_METADATA_KEYS
from galaxy.model import (
    Dataset,
    HistoryDatasetAssociation,
    Job,
    store,
)
from galaxy.model.custom_types import total_size
from galaxy.model.metadata import MetadataTempFile
from galaxy.objectstore import build_object_store_from_config
from galaxy.tool_util.output_checker import (
    check_output,
    DETECTED_JOB_STATE,
)
from galaxy.tool_util.parser.stdio import (
    ToolStdioExitCode,
    ToolStdioRegex,
)
from galaxy.tool_util.provided_metadata import parse_tool_provided_metadata
from galaxy.util import (
    safe_contains,
    stringify_dictionary_keys,
)
from galaxy.util.expressions import ExpressionContext

logging.basicConfig()
log = logging.getLogger(__name__)


def set_validated_state(dataset_instance):
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
                log.info(f"Key {k} too large for metadata, discarding")
                dataset_instance.metadata.remove_key(k)


def set_metadata():
    set_metadata_portable()


def get_metadata_params(tool_job_working_directory):
    metadata_params_path = os.path.join("metadata", "params.json")
    try:
        with open(metadata_params_path) as f:
            return json.load(f)
    except OSError:
        raise Exception(f"Failed to find metadata/params.json from cwd [{tool_job_working_directory}]")


def get_object_store():
    object_store_conf_path = os.path.join("metadata", "object_store_conf.json")
    with open(object_store_conf_path) as f:
        config_dict = json.load(f)
    assert config_dict is not None
    object_store = build_object_store_from_config(None, config_dict=config_dict)
    Dataset.object_store = object_store
    return object_store


def set_metadata_portable():
    tool_job_working_directory = os.path.abspath(os.getcwd())
    metadata_tmp_files_dir = os.path.join(tool_job_working_directory, "metadata")
    MetadataTempFile.tmp_dir = metadata_tmp_files_dir

    metadata_params = get_metadata_params(tool_job_working_directory)
    datatypes_config = metadata_params["datatypes_config"]
    job_metadata = metadata_params["job_metadata"]
    provided_metadata_style = metadata_params.get("provided_metadata_style")
    max_metadata_value_size = metadata_params.get("max_metadata_value_size") or 0
    outputs = metadata_params["outputs"]

    datatypes_registry = validate_and_load_datatypes_config(datatypes_config)
    tool_provided_metadata = load_job_metadata(job_metadata, provided_metadata_style)

    def set_meta(new_dataset_instance, file_dict):
        set_meta_with_tool_provided(new_dataset_instance, file_dict, set_meta_kwds, datatypes_registry, max_metadata_value_size)

    try:
        object_store = get_object_store()
    except (FileNotFoundError, AssertionError):
        object_store = None
    extended_metadata_collection = bool(object_store)
    job_context = None
    version_string = None

    export_store = None
    final_job_state = Job.states.OK
    if extended_metadata_collection:
        tool_dict = metadata_params["tool"]
        stdio_exit_code_dicts, stdio_regex_dicts = tool_dict["stdio_exit_codes"], tool_dict["stdio_regexes"]
        stdio_exit_codes = list(map(ToolStdioExitCode, stdio_exit_code_dicts))
        stdio_regexes = list(map(ToolStdioRegex, stdio_regex_dicts))

        outputs_directory = os.path.join(tool_job_working_directory, "outputs")
        if not os.path.exists(outputs_directory):
            outputs_directory = tool_job_working_directory

        # TODO: constants...
        if os.path.exists(os.path.join(outputs_directory, "tool_stdout")):
            with open(os.path.join(outputs_directory, "tool_stdout"), "rb") as f:
                tool_stdout = f.read()

            with open(os.path.join(outputs_directory, "tool_stderr"), "rb") as f:
                tool_stderr = f.read()
        elif os.path.exists(os.path.join(tool_job_working_directory, "stdout")):
            with open(os.path.join(tool_job_working_directory, "stdout"), "rb") as f:
                tool_stdout = f.read()

            with open(os.path.join(tool_job_working_directory, "stderr"), "rb") as f:
                tool_stderr = f.read()
        elif os.path.exists(os.path.join(outputs_directory, "stdout")):
            # Puslar style output directory? Was this ever used - did this ever work?
            with open(os.path.join(outputs_directory, "stdout"), "rb") as f:
                tool_stdout = f.read()

            with open(os.path.join(outputs_directory, "stderr"), "rb") as f:
                tool_stderr = f.read()
        elif os.path.exists(os.path.join(tool_job_working_directory, 'task_0')):
            # We have a task splitting job
            tool_stdout = b''
            tool_stderr = b''
            paths = Path(tool_job_working_directory).glob('task_*')
            for path in paths:
                with open(path / 'outputs' / 'tool_stdout', 'rb') as f:
                    task_stdout = f.read()
                    if task_stdout:
                        tool_stdout = b"%s[%s stdout]\n%s\n" % (tool_stdout, path.name.encode(), task_stdout)
                with open(path / 'outputs' / 'tool_stderr', 'rb') as f:
                    task_stderr = f.read()
                    if task_stderr:
                        tool_stderr = b"%s[%s stdout]\n%s\n" % (tool_stderr, path.name.encode(), task_stderr)
        else:
            wdc = os.listdir(tool_job_working_directory)
            odc = os.listdir(outputs_directory)
            error_desc = "Failed to find tool_stdout or tool_stderr for this job, cannot collect metadata"
            error_extra = f"Working dir contents [{wdc}], output directory contents [{odc}]"
            log.warn(f"{error_desc}. {error_extra}")
            raise Exception(error_desc)

        job_id_tag = metadata_params["job_id_tag"]

        exit_code_file = default_exit_code_file(".", job_id_tag)
        tool_exit_code = read_exit_code_from(exit_code_file, job_id_tag)

        check_output_detected_state, tool_stdout, tool_stderr, job_messages = check_output(stdio_regexes, stdio_exit_codes, tool_stdout, tool_stderr, tool_exit_code, job_id_tag)
        if check_output_detected_state == DETECTED_JOB_STATE.OK and not tool_provided_metadata.has_failed_outputs():
            final_job_state = Job.states.OK
        else:
            final_job_state = Job.states.ERROR

        version_string_path = os.path.join('outputs', COMMAND_VERSION_FILENAME)
        version_string = collect_shrinked_content_from_path(version_string_path)

        expression_context = ExpressionContext(dict(stdout=tool_stdout, stderr=tool_stderr))

        # Load outputs.
        export_store = store.DirectoryModelExportStore('metadata/outputs_populated', serialize_dataset_objects=True, for_edit=True, strip_metadata_files=False, serialize_jobs=False)
    try:
        import_model_store = store.imported_store_for_metadata('metadata/outputs_new', object_store=object_store)
        job = next(iter(import_model_store.sa_session.objects[Job].values()))
        with open(os.path.join(tool_job_working_directory, 'tool_script.sh')) as command_fh:
            job.command_line = command_fh.read().strip()
            export_store.export_job(job, include_job_data=False)
    except AssertionError:
        # Remove in 21.09, this should only happen for jobs that started on <= 20.09 and finish now
        import_model_store = None

    job_context = SessionlessJobContext(
        metadata_params,
        tool_provided_metadata,
        object_store,
        export_store,
        import_model_store,
        os.path.join(tool_job_working_directory, "working"),
        final_job_state=final_job_state,
    )

    unnamed_id_to_path = {}
    for unnamed_output_dict in job_context.tool_provided_metadata.get_unnamed_outputs():
        destination = unnamed_output_dict["destination"]
        elements = unnamed_output_dict["elements"]
        destination_type = destination["type"]
        if destination_type == 'hdas':
            for element in elements:
                filename = element.get('filename')
                object_id = element.get('object_id')
                if filename and object_id:
                    unnamed_id_to_path[object_id] = os.path.join(job_context.job_working_directory, filename)

    for output_name, output_dict in outputs.items():
        dataset_instance_id = output_dict["id"]
        klass = getattr(galaxy.model, output_dict.get('model_class', 'HistoryDatasetAssociation'))
        dataset = None
        if import_model_store:
            dataset = import_model_store.sa_session.query(klass).find(dataset_instance_id)
        if dataset is None:
            # legacy check for jobs that started before 21.01, remove on 21.05
            filename_in = os.path.join(f"metadata/metadata_in_{output_name}")
            import pickle
            dataset = pickle.load(open(filename_in, 'rb'))  # load DatasetInstance
        assert dataset is not None

        filename_kwds = os.path.join(f"metadata/metadata_kwds_{output_name}")
        filename_out = os.path.join(f"metadata/metadata_out_{output_name}")
        filename_results_code = os.path.join(f"metadata/metadata_results_{output_name}")
        override_metadata = os.path.join(f"metadata/metadata_override_{output_name}")
        dataset_filename_override = output_dict["filename_override"]
        # pre-20.05 this was a per job parameter and not a per dataset parameter, drop in 21.XX
        legacy_object_store_store_by = metadata_params.get("object_store_store_by", "id")

        # Same block as below...
        set_meta_kwds = stringify_dictionary_keys(json.load(open(filename_kwds)))  # load kwds; need to ensure our keywords are not unicode
        try:
            external_filename = unnamed_id_to_path.get(dataset_instance_id, dataset_filename_override)
            if not os.path.exists(external_filename):
                matches = glob.glob(external_filename)
                assert len(matches) == 1, f"More than one file matched by output glob '{external_filename}'"
                external_filename = matches[0]
                assert safe_contains(tool_job_working_directory, external_filename), f"Cannot collect output '{external_filename}' from outside of working directory"
                created_from_basename = os.path.relpath(external_filename, os.path.join(tool_job_working_directory, 'working'))
                dataset.dataset.created_from_basename = created_from_basename
            # override filename if we're dealing with outputs to working directory and dataset is not linked to
            link_data_only = metadata_params.get("link_data_only")
            if not link_data_only:
                # Only set external filename if we're dealing with files in job working directory.
                # Fixes link_data_only uploads
                dataset.dataset.external_filename = external_filename
                store_by = output_dict.get("object_store_store_by", legacy_object_store_store_by)
                extra_files_dir_name = f"dataset_{getattr(dataset.dataset, store_by)}_files"
                files_path = os.path.abspath(os.path.join(tool_job_working_directory, "working", extra_files_dir_name))
                dataset.dataset.external_extra_files_path = files_path
            file_dict = tool_provided_metadata.get_dataset_meta(output_name, dataset.dataset.id, dataset.dataset.uuid)
            if 'ext' in file_dict:
                dataset.extension = file_dict['ext']
            # Metadata FileParameter types may not be writable on a cluster node, and are therefore temporarily substituted with MetadataTempFiles
            override_metadata = json.load(open(override_metadata))
            for metadata_name, metadata_file_override in override_metadata:
                if MetadataTempFile.is_JSONified_value(metadata_file_override):
                    metadata_file_override = MetadataTempFile.from_JSON(metadata_file_override)
                setattr(dataset.metadata, metadata_name, metadata_file_override)
            if output_dict.get("validate", False):
                set_validated_state(dataset)
            if dataset_instance_id not in unnamed_id_to_path:
                # We're going to run through set_metadata in collect_dynamic_outputs with more contextual metadata,
                # so skip set_meta here.
                set_meta(dataset, file_dict)
                if extended_metadata_collection:
                    collect_extra_files(object_store, dataset, ".")
                    dataset.state = dataset.dataset.state = final_job_state

            if extended_metadata_collection:
                if not link_data_only and os.path.getsize(external_filename):
                    # Here we might be updating a disk based objectstore when outputs_to_working_directory is used,
                    # or a remote object store from its cache path.
                    object_store.update_from_file(dataset.dataset, file_name=external_filename, create=True)
                # TODO: merge expression_context into tool_provided_metadata so we don't have to special case this (here and in _finish_dataset)
                meta = tool_provided_metadata.get_dataset_meta(output_name, dataset.dataset.id, dataset.dataset.uuid)
                if meta:
                    context = ExpressionContext(meta, expression_context)
                else:
                    context = expression_context
                dataset.blurb = 'done'
                dataset.peek = 'no peek'
                dataset.info = (dataset.info or '')
                if context['stdout'].strip():
                    # Ensure white space between entries
                    dataset.info = f"{dataset.info.rstrip()}\n{context['stdout'].strip()}"
                if context['stderr'].strip():
                    # Ensure white space between entries
                    dataset.info = f"{dataset.info.rstrip()}\n{context['stderr'].strip()}"
                dataset.tool_version = version_string
                if 'uuid' in context:
                    dataset.dataset.uuid = context['uuid']
                if not final_job_state == Job.states.ERROR:
                    line_count = context.get('line_count', None)
                    try:
                        # Certain datatype's set_peek methods contain a line_count argument
                        dataset.set_peek(line_count=line_count)
                    except TypeError:
                        # ... and others don't
                        dataset.set_peek()
                for context_key in TOOL_PROVIDED_JOB_METADATA_KEYS:
                    if context_key in context:
                        context_value = context[context_key]
                        setattr(dataset, context_key, context_value)
                # We only want to persist the external_filename if the dataset has been linked in.
                if not link_data_only:
                    dataset.dataset.external_filename = None
                    dataset.dataset.extra_files_path = None
                export_store.add_dataset(dataset)
            else:
                dataset.metadata.to_JSON_dict(filename_out)  # write out results of set_meta

            json.dump((True, 'Metadata has been set successfully'), open(filename_results_code, 'wt+'))  # setting metadata has succeeded
        except Exception:
            json.dump((False, traceback.format_exc()), open(filename_results_code, 'wt+'))  # setting metadata has failed somehow

    if extended_metadata_collection:
        # discover extra outputs...
        output_collections = {}
        for name, output_collection in metadata_params["output_collections"].items():
            # TODO: remove HistoryDatasetCollectionAssociation fallback on 22.01, model_class used to not be serialized prior to 21.09
            model_class = output_collection.get('model_class', 'HistoryDatasetCollectionAssociation')
            collection = import_model_store.sa_session.query(getattr(galaxy.model, model_class)).find(output_collection["id"])
            output_collections[name] = collection
        outputs = {}
        for name, output in metadata_params["outputs"].items():
            klass = getattr(galaxy.model, output.get('model_class', 'HistoryDatasetAssociation'))
            outputs[name] = import_model_store.sa_session.query(klass).find(output["id"])

        input_ext = json.loads(metadata_params["job_params"].get("__input_ext") or '"data"')
        collect_primary_datasets(
            job_context,
            outputs,
            input_ext=input_ext,
        )
        collect_dynamic_outputs(job_context, output_collections)

    if export_store:
        export_store._finalize()
    write_job_metadata(tool_job_working_directory, job_metadata, set_meta, tool_provided_metadata)


def validate_and_load_datatypes_config(datatypes_config):
    galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))

    if not os.path.exists(datatypes_config):
        # Hack for Pulsar on usegalaxy.org, drop ASAP.
        datatypes_config = "configs/registry.xml"

    if not os.path.exists(datatypes_config):
        print(f"Metadata setting failed because registry.xml [{datatypes_config}] could not be found. You may retry setting metadata.")
        sys.exit(1)
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
        new_dataset = Dataset(id=-i, external_filename=new_dataset_filename)
        extra_files = file_dict.get('extra_files', None)
        if extra_files is not None:
            new_dataset._extra_files_path = os.path.join(tool_job_working_directory, "working", extra_files)
        new_dataset.state = new_dataset.states.OK
        new_dataset_instance = HistoryDatasetAssociation(id=-i, dataset=new_dataset, extension=file_dict.get('ext', 'data'))
        set_meta(new_dataset_instance, file_dict)
        file_dict['metadata'] = json.loads(new_dataset_instance.metadata.to_JSON_dict())  # storing metadata in external form, need to turn back into dict, then later jsonify

    tool_provided_metadata.rewrite()
