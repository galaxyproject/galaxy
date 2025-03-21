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
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

try:
    from pulsar.client.staging import COMMAND_VERSION_FILENAME
except ImportError:
    # Package unit tests
    COMMAND_VERSION_FILENAME = "COMMAND_VERSION"

import galaxy.datatypes.registry
import galaxy.model.mapping
from galaxy.datatypes import sniff
from galaxy.datatypes.data import validate
from galaxy.job_execution.compute_environment import dataset_path_to_extra_path
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
    DatasetInstance,
    HistoryDatasetAssociation,
    Job,
    store,
)
from galaxy.model.custom_types import total_size
from galaxy.model.metadata import MetadataTempFile
from galaxy.model.store.discover import MaxDiscoveredFilesExceededError
from galaxy.objectstore import (
    build_object_store_from_config,
    ObjectStore,
)
from galaxy.tool_util.output_checker import (
    check_output,
    DETECTED_JOB_STATE,
)
from galaxy.tool_util.parser.stdio import (
    StdioErrorLevel,
    ToolStdioExitCode,
    ToolStdioRegex,
)
from galaxy.tool_util.provided_metadata import parse_tool_provided_metadata
from galaxy.util import (
    safe_contains,
    stringify_dictionary_keys,
    unicodify,
)
from galaxy.util.expressions import ExpressionContext

logging.basicConfig()
log = logging.getLogger(__name__)


MAX_STDIO_READ_BYTES = 100 * 10**6  # 100 MB


def reset_external_filename(dataset_instance: DatasetInstance):
    assert dataset_instance.dataset
    dataset_instance.dataset.external_filename = None
    dataset_instance.dataset.extra_files_path = None


def push_if_necessary(object_store: ObjectStore, dataset: DatasetInstance, external_filename):
    # Here we might be updating a disk based objectstore when outputs_to_working_directory is used,
    # or a remote object store from its cache path.
    # empty files could happen when outputs are discovered from working dir,
    # empty file check needed for e.g. test/integration/test_extended_metadata_outputs_to_working_directory.py::test_tools[multi_output_assign_primary]
    if not dataset.dataset.purged and os.path.getsize(external_filename):
        object_store.update_from_file(dataset.dataset, file_name=external_filename, create=True)


def set_validated_state(dataset_instance):
    datatype_validation = validate(dataset_instance)

    dataset_instance.validated_state = datatype_validation.state
    dataset_instance.validated_state_message = datatype_validation.message

    # Set special metadata property that will reload this on server side.
    dataset_instance.metadata.__validated_state__ = datatype_validation.state
    dataset_instance.metadata.__validated_state_message__ = datatype_validation.message


def set_meta_with_tool_provided(
    dataset_instance,
    file_dict,
    set_meta_kwds,
    datatypes_registry,
    max_metadata_value_size,
):
    # This method is somewhat odd, in that we set the metadata attributes from tool,
    # then call set_meta, then set metadata attributes from tool again.
    # This is intentional due to interplay of overwrite kwd, the fact that some metadata
    # parameters may rely on the values of others, and that we are accepting the
    # values provided by the tool as Truth.
    if (extension := dataset_instance.extension) == "_sniff_":
        try:
            extension = sniff.handle_uploaded_dataset_file(dataset_instance.dataset.get_file_name(), datatypes_registry)
            # We need to both set the extension so it is available to set_meta
            # and record it in the metadata so it can be reloaded on the server
            # side and the model updated (see MetadataCollection.{from,to}_JSON_dict)
            dataset_instance.extension = extension
            # Set special metadata property that will reload this on server side.
            dataset_instance.metadata.__extension__ = extension
        except Exception:
            log.exception("Problem sniffing datatype.")

    for metadata_name, metadata_value in file_dict.get("metadata", {}).items():
        setattr(dataset_instance.metadata, metadata_name, metadata_value)
    if not dataset_instance.metadata_deferred:
        dataset_instance.datatype.set_meta(dataset_instance, **set_meta_kwds)
    for metadata_name, metadata_value in file_dict.get("metadata", {}).items():
        setattr(dataset_instance.metadata, metadata_name, metadata_value)

    if max_metadata_value_size:
        for k, v in list(dataset_instance.metadata.items()):
            if total_size(v) > max_metadata_value_size:
                log.info(f"Key {k} too large for metadata, discarding")
                dataset_instance.metadata.remove_key(k)


def set_metadata():
    set_metadata_portable()


def get_metadata_params(tool_job_working_directory):
    metadata_params_path = os.path.join(tool_job_working_directory, "metadata", "params.json")
    try:
        with open(metadata_params_path) as f:
            return json.load(f)
    except OSError:
        raise Exception(f"Failed to find metadata/params.json from cwd [{tool_job_working_directory}]")


def get_object_store(tool_job_working_directory, object_store=None):
    if not object_store:
        object_store_conf_path = os.path.join(tool_job_working_directory, "metadata", "object_store_conf.json")
        with open(object_store_conf_path) as f:
            config_dict = json.load(f)
        assert config_dict is not None
        # build an object store but disable any process management associated with it
        # we're using it as a library - not as a service.
        object_store = build_object_store_from_config(None, config_dict=config_dict, disable_process_management=True)
    Dataset.object_store = object_store
    return object_store


def set_metadata_portable(
    tool_job_working_directory=None,
    object_store: Optional[ObjectStore] = None,
    extended_metadata_collection: Optional[bool] = None,
):
    is_celery_task = tool_job_working_directory is not None
    tool_job_working_directory = Path(tool_job_working_directory or os.path.abspath(os.getcwd()))
    metadata_tmp_files_dir = os.path.join(tool_job_working_directory, "metadata")
    metadata_params = get_metadata_params(tool_job_working_directory)
    if not is_celery_task:
        if not extended_metadata_collection:
            # Legacy handling for datatypes that don't pass metadata_tmp_files_dir from set_meta kwargs
            # to MetadataTempFile constructor. Remove if we ever remove TS datatypes.
            MetadataTempFile.tmp_dir = metadata_tmp_files_dir
    datatypes_config = tool_job_working_directory / metadata_params["datatypes_config"]
    datatypes_registry = validate_and_load_datatypes_config(datatypes_config)
    job_metadata = tool_job_working_directory / metadata_params["job_metadata"]
    provided_metadata_style = metadata_params.get("provided_metadata_style")
    max_metadata_value_size = metadata_params.get("max_metadata_value_size") or 0
    max_discovered_files = metadata_params.get("max_discovered_files")
    outputs = metadata_params["outputs"]

    tool_provided_metadata = load_job_metadata(job_metadata, provided_metadata_style)

    def set_meta(new_dataset_instance, file_dict):
        if not extended_metadata_collection:
            set_meta_kwds["metadata_tmp_files_dir"] = metadata_tmp_files_dir
        set_meta_with_tool_provided(
            new_dataset_instance,
            file_dict,
            set_meta_kwds,
            datatypes_registry,
            max_metadata_value_size,
        )

    try:
        object_store = get_object_store(
            tool_job_working_directory=tool_job_working_directory, object_store=object_store
        )
    except (FileNotFoundError, AssertionError):
        object_store = None
    if extended_metadata_collection is None:
        extended_metadata_collection = bool(object_store)
    job_context = None
    version_string = None

    export_store = None
    final_job_state = Job.states.OK
    job_messages: List[Dict[str, Any]] = []
    if extended_metadata_collection:
        tool_dict = metadata_params["tool"]
        stdio_exit_code_dicts, stdio_regex_dicts = tool_dict["stdio_exit_codes"], tool_dict["stdio_regexes"]
        stdio_exit_codes = list(map(ToolStdioExitCode, stdio_exit_code_dicts))
        stdio_regexes = list(map(ToolStdioRegex, stdio_regex_dicts))

        outputs_directory = os.path.join(tool_job_working_directory, "outputs")
        if not os.path.exists(outputs_directory):
            outputs_directory = tool_job_working_directory
        metadata_directory = os.path.join(tool_job_working_directory, "metadata")

        # TODO: constants...
        locations = [
            (metadata_directory, "tool_"),
            (outputs_directory, "tool_"),
            (tool_job_working_directory, ""),
        ]
        for directory, prefix in locations:
            if directory and os.path.exists(os.path.join(directory, f"{prefix}stdout")):
                with open(os.path.join(directory, f"{prefix}stdout"), "rb") as f:
                    tool_stdout = unicodify(f.read(MAX_STDIO_READ_BYTES), strip_null=True)
                with open(os.path.join(directory, f"{prefix}stderr"), "rb") as f:
                    tool_stderr = unicodify(f.read(MAX_STDIO_READ_BYTES), strip_null=True)
                break
        else:
            if os.path.exists(os.path.join(tool_job_working_directory, "task_0")):
                # We have a task splitting job
                tool_stdout = ""
                tool_stderr = ""
                paths = tool_job_working_directory.glob("task_*")
                for path in paths:
                    with open(path / "outputs" / "tool_stdout", "rb") as f:
                        task_stdout = unicodify(f.read(MAX_STDIO_READ_BYTES), strip_null=True)
                        if task_stdout:
                            tool_stdout = f"{tool_stdout}[{path.name} stdout]\n{task_stdout}\n"
                    with open(path / "outputs" / "tool_stderr", "rb") as f:
                        task_stderr = unicodify(f.read(MAX_STDIO_READ_BYTES), strip_null=True)
                        if task_stderr:
                            tool_stderr = f"{tool_stderr}[{path.name} stderr]\n{task_stderr}\n"
            else:
                wdc = os.listdir(tool_job_working_directory)
                odc = os.listdir(outputs_directory)
                if not is_celery_task:
                    error_desc = "Failed to find tool_stdout or tool_stderr for this job, cannot collect metadata"
                    error_extra = f"Working dir contents [{wdc}], output directory contents [{odc}]"
                    log.warning(f"{error_desc}. {error_extra}")
                    raise Exception(error_desc)
                else:
                    tool_stdout = tool_stderr = ""

        job_id_tag = metadata_params["job_id_tag"]

        exit_code_file = default_exit_code_file(".", job_id_tag)
        tool_exit_code = read_exit_code_from(exit_code_file, job_id_tag)

        check_output_detected_state, tool_stdout, tool_stderr, job_messages = check_output(
            stdio_regexes, stdio_exit_codes, tool_stdout, tool_stderr, tool_exit_code
        )
        if check_output_detected_state == DETECTED_JOB_STATE.OK and not tool_provided_metadata.has_failed_outputs():
            final_job_state = Job.states.OK
        else:
            final_job_state = Job.states.ERROR

        default_version_string_path = os.path.join("outputs", COMMAND_VERSION_FILENAME)
        version_string_path = metadata_params.get("compute_version_path", default_version_string_path)
        version_string = collect_shrinked_content_from_path(version_string_path)
        expression_context = ExpressionContext(dict(stdout=tool_stdout[:255], stderr=tool_stderr[:255]))

        # Load outputs.
        export_store = store.DirectoryModelExportStore(
            tool_job_working_directory / "metadata/outputs_populated",
            serialize_dataset_objects=True,
            for_edit=True,
            strip_metadata_files=False,
            serialize_jobs=True,
        )
    import_model_store = store.imported_store_for_metadata(
        tool_job_working_directory / "metadata/outputs_new", object_store=object_store
    )

    tool_script_file = tool_job_working_directory / "tool_script.sh"
    job: Optional[Job] = None
    if export_store:
        job = next(iter(import_model_store.sa_session.objects[Job].values()))

    job_context = SessionlessJobContext(
        metadata_params,
        tool_provided_metadata,
        object_store,
        export_store,
        import_model_store,
        tool_job_working_directory / "working",
        final_job_state=final_job_state,
        max_discovered_files=max_discovered_files,
    )

    if extended_metadata_collection:
        if not export_store:
            # Can't happen, but type system doesn't know
            raise Exception("export_store not built")
        # discover extra outputs...
        output_collections = {}
        for name, output_collection in metadata_params["output_collections"].items():
            model_class = output_collection["model_class"]
            collection = import_model_store.sa_session.query(getattr(galaxy.model, model_class)).find(
                output_collection["id"]
            )
            output_collections[name] = collection
        output_instances = {}
        for name, output in metadata_params["outputs"].items():
            klass = getattr(galaxy.model, output.get("model_class", "HistoryDatasetAssociation"))
            output_instances[name] = import_model_store.sa_session.query(klass).find(output["id"])

        input_ext = json.loads(metadata_params["job_params"].get("__input_ext") or '"data"')
        try:
            collect_primary_datasets(
                job_context,
                output_instances,
                input_ext=input_ext,
            )
            collect_dynamic_outputs(job_context, output_collections)
        except MaxDiscoveredFilesExceededError as e:
            final_job_state = Job.states.ERROR
            job_messages.append(
                {
                    "type": "max_discovered_files",
                    "desc": str(e),
                    "code_desc": None,
                    "error_level": StdioErrorLevel.FATAL,
                }
            )

        if job:
            job.set_streams(tool_stdout=tool_stdout, tool_stderr=tool_stderr, job_messages=job_messages)
            job.state = final_job_state
            if os.path.exists(tool_script_file):
                with open(tool_script_file) as command_fh:
                    command_line_lines = []
                    for i, line in enumerate(command_fh):
                        if i == 0 and line.endswith("COMMAND_VERSION 2>&1;"):
                            # Don't record version command as part of command line
                            continue
                        command_line_lines.append(line)
                    job.command_line = "".join(command_line_lines).strip()
                    export_store.export_job(job, include_job_data=False)

    unnamed_id_to_path = {}
    unnamed_is_deferred = {}
    for unnamed_output_dict in job_context.tool_provided_metadata.get_unnamed_outputs():
        destination = unnamed_output_dict["destination"]
        elements = unnamed_output_dict["elements"]
        destination_type = destination["type"]
        if destination_type == "hdas":
            for element in elements:
                object_id = element.get("object_id")
                if element.get("state") == "deferred":
                    unnamed_is_deferred[object_id] = True
                    continue
                filename = element.get("filename")
                if filename and object_id:
                    unnamed_id_to_path[object_id] = os.path.join(job_context.job_working_directory, filename)

    for output_name, output_dict in outputs.items():
        dataset_instance_id = output_dict["id"]
        klass = getattr(galaxy.model, output_dict.get("model_class", "HistoryDatasetAssociation"))
        dataset = import_model_store.sa_session.query(klass).find(dataset_instance_id)
        assert dataset is not None

        filename_kwds = tool_job_working_directory / f"metadata/metadata_kwds_{output_name}"
        filename_out = tool_job_working_directory / f"metadata/metadata_out_{output_name}"
        filename_results_code = tool_job_working_directory / f"metadata/metadata_results_{output_name}"
        override_metadata = tool_job_working_directory / f"metadata/metadata_override_{output_name}"
        dataset_filename_override = output_dict["filename_override"]
        # Same block as below...
        set_meta_kwds = stringify_dictionary_keys(
            json.load(open(filename_kwds))
        )  # load kwds; need to ensure our keywords are not unicode
        object_store_update_actions = []
        try:
            is_deferred = bool(unnamed_is_deferred.get(dataset_instance_id))
            dataset.metadata_deferred = is_deferred
            if not is_deferred:
                external_filename = unnamed_id_to_path.get(dataset_instance_id, dataset_filename_override)
                if not os.path.exists(external_filename):
                    matches = glob.glob(external_filename)
                    if matches:
                        assert len(matches) == 1, f"{len(matches)} file(s) matched by output glob '{external_filename}'"
                        external_filename = matches[0]
                        assert safe_contains(
                            tool_job_working_directory, external_filename
                        ), f"Cannot collect output '{external_filename}' from outside of working directory"
                        created_from_basename = os.path.relpath(
                            external_filename, os.path.join(tool_job_working_directory, "working")
                        )
                        dataset.dataset.created_from_basename = created_from_basename
                    elif os.path.exists(dataset_path_to_extra_path(external_filename)):
                        # Only output is extra files dir, but no primary output file, that's fine,
                        # but make sure we create an empty primary output file. It's a little
                        # weird to do this, but it does indicate that there's nothing wrong with the file,
                        # as opposed to perhaps a storage issue.
                        with open(external_filename, "wb"):
                            pass
                    elif not os.path.exists(dataset_filename_override):
                        # purged output ?
                        dataset.purged = True
                        dataset.dataset.purged = True
                    else:
                        raise Exception(f"Output file '{external_filename}' not found")

                # override filename if we're dealing with outputs to working directory and dataset is not linked to
                link_data_only = metadata_params.get("link_data_only")
                if not link_data_only:
                    # Only set external filename if we're dealing with files in job working directory.
                    # Fixes link_data_only uploads
                    dataset.dataset.external_filename = external_filename
                    # We derive extra_files_dir_name from external_filename, because OutputsToWorkingDirectoryPathRewriter
                    # always rewrites the path to include the uuid, even if store_by is set to id, and the extra files
                    # rewrite is derived from the dataset path (since https://github.com/galaxyproject/galaxy/pull/16541).
                    extra_files_dir_name = os.path.basename(dataset_path_to_extra_path(external_filename))
                    # TODO: all extra file outputs should be stored in outputs, but keep fallback for running jobs. Remove in 23.2.
                    for output_location in ("outputs", "working"):
                        files_path = os.path.abspath(
                            os.path.join(tool_job_working_directory, output_location, extra_files_dir_name)
                        )
                        if os.path.exists(files_path):
                            dataset.dataset.external_extra_files_path = files_path
                            break
                    else:
                        # extra files dir didn't exist in working or outputs directory
                        if dataset_filename_override and not object_store:
                            # not extended metadata (so no object store) and outputs_to_working_directory off
                            dataset.dataset.external_extra_files_path = os.path.join(
                                os.path.dirname(dataset_filename_override), extra_files_dir_name
                            )
            file_dict = tool_provided_metadata.get_dataset_meta(output_name, dataset.dataset.id, dataset.dataset.uuid)
            if "ext" in file_dict:
                dataset.extension = file_dict["ext"]
            # Metadata FileParameter types may not be writable on a cluster node, and are therefore temporarily substituted with MetadataTempFiles
            override_metadata = json.load(open(override_metadata))
            for metadata_name, metadata_file_override in override_metadata:
                if MetadataTempFile.is_JSONified_value(metadata_file_override):
                    metadata_file_override = MetadataTempFile.from_JSON(metadata_file_override)
                setattr(dataset.metadata, metadata_name, metadata_file_override)
            if output_dict.get("validate", False):
                set_validated_state(dataset)

            if extended_metadata_collection:
                if not object_store or not export_store:
                    # Can't happen, but type system doesn't know
                    raise Exception("object_store not built")
                if not is_deferred and not link_data_only:
                    if dataset_instance_id not in unnamed_id_to_path:
                        object_store_update_actions.append(
                            partial(push_if_necessary, object_store, dataset, external_filename)
                        )
                    object_store_update_actions.append(partial(reset_external_filename, dataset))
                object_store_update_actions.append(partial(dataset.set_total_size))
                object_store_update_actions.append(partial(export_store.add_dataset, dataset))
                if dataset_instance_id not in unnamed_id_to_path and not dataset.dataset.purged:
                    object_store_update_actions.append(partial(collect_extra_files, object_store, dataset, "."))
                    dataset_state = "deferred" if (is_deferred and final_job_state == "ok") else final_job_state
                    if not dataset.state == dataset.states.ERROR:
                        # Don't overwrite failed state (for invalid content) here
                        dataset.state = dataset.dataset.state = dataset_state
                    # We're going to run through set_metadata in collect_dynamic_outputs with more contextual metadata,
                    # so only run set_meta for fixed outputs
                    if not dataset.dataset.purged:
                        set_meta(dataset, file_dict)
                # TODO: merge expression_context into tool_provided_metadata so we don't have to special case this (here and in _finish_dataset)
                meta = tool_provided_metadata.get_dataset_meta(output_name, dataset.dataset.id, dataset.dataset.uuid)
                if meta:
                    context = ExpressionContext(meta, expression_context)
                else:
                    context = expression_context
                dataset.blurb = "done"
                dataset.peek = "no peek"
                dataset.info = dataset.info or ""
                if context["stdout"].strip():
                    # Ensure white space between entries
                    dataset.info = f"{dataset.info.rstrip()}\n{context['stdout'].strip()}"
                if context["stderr"].strip():
                    # Ensure white space between entries
                    dataset.info = f"{dataset.info.rstrip()}\n{context['stderr'].strip()}"
                dataset.tool_version = version_string
                if "uuid" in context:
                    dataset.dataset.uuid = context["uuid"]
                if not final_job_state == Job.states.ERROR:
                    line_count = context.get("line_count", None)
                    dataset.set_peek(line_count=line_count)
                for context_key in TOOL_PROVIDED_JOB_METADATA_KEYS:
                    if context_key in context:
                        context_value = context[context_key]
                        setattr(dataset, context_key, context_value)
            else:
                if dataset_instance_id not in unnamed_id_to_path and not dataset.dataset.purged:
                    # We're going to run through set_metadata in collect_dynamic_outputs with more contextual metadata,
                    # so only run set_meta for fixed outputs
                    set_meta(dataset, file_dict)
                dataset.metadata.to_JSON_dict(filename_out)  # write out results of set_meta

            with open(filename_results_code, "w+") as tf:
                json.dump((True, "Metadata has been set successfully"), tf)  # setting metadata has succeeded
        except Exception:
            with open(filename_results_code, "w+") as tf:
                json.dump((False, traceback.format_exc()), tf)  # setting metadata has failed somehow
        finally:
            for action in object_store_update_actions:
                action()

    if export_store:
        export_store.push_metadata_files()
        export_store._finalize()
    write_job_metadata(tool_job_working_directory, job_metadata, set_meta, tool_provided_metadata)


def validate_and_load_datatypes_config(datatypes_config):
    galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))

    if not os.path.exists(datatypes_config):
        # Hack for Pulsar on usegalaxy.org, drop ASAP.
        datatypes_config = "configs/registry.xml"

    if not os.path.exists(datatypes_config):
        print(
            f"Metadata setting failed because registry.xml [{datatypes_config}] could not be found. You may retry setting metadata."
        )
        sys.exit(1)
    datatypes_registry = galaxy.datatypes.registry.Registry()
    datatypes_registry.load_datatypes(
        root_dir=galaxy_root,
        config=datatypes_config,
        use_build_sites=False,
        use_converters=False,
        use_display_applications=False,
    )
    galaxy.model.set_datatypes_registry(datatypes_registry)
    return datatypes_registry


def load_job_metadata(job_metadata, provided_metadata_style):
    return parse_tool_provided_metadata(job_metadata, provided_metadata_style=provided_metadata_style)


def write_job_metadata(tool_job_working_directory, job_metadata, set_meta, tool_provided_metadata):
    for i, file_dict in enumerate(tool_provided_metadata.get_new_datasets_for_metadata_collection(), start=1):
        filename = file_dict["filename"]
        new_dataset_filename = os.path.join(tool_job_working_directory, "working", filename)
        new_dataset = Dataset(id=-i, external_filename=new_dataset_filename)
        extra_files = file_dict.get("extra_files", None)
        if extra_files is not None:
            new_dataset._extra_files_path = os.path.join(tool_job_working_directory, "outputs", extra_files)
        new_dataset.state = new_dataset.states.OK
        new_dataset_instance = HistoryDatasetAssociation(
            id=-i, dataset=new_dataset, extension=file_dict.get("ext", "data")
        )
        set_meta(new_dataset_instance, file_dict)
        file_dict["metadata"] = json.loads(
            new_dataset_instance.metadata.to_JSON_dict()
        )  # storing metadata in external form, need to turn back into dict, then later jsonify

    tool_provided_metadata.rewrite()
