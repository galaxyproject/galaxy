"""Define abstraction for capturing the metadata of job's output datasets."""

import abc
import json
import os
import shutil
from logging import getLogger
from typing import (
    Any,
    Dict,
    Optional,
    TYPE_CHECKING,
)

import galaxy.model
from galaxy.model import store
from galaxy.model.metadata import (
    FileParameter,
    MetadataTempFile,
)
from galaxy.model.store import DirectoryModelExportStore
from galaxy.util import safe_makedirs

if TYPE_CHECKING:
    from sqlalchemy.orm.scoping import scoped_session

log = getLogger(__name__)

SET_METADATA_SCRIPT = """
import os
import traceback
try:
    from galaxy_ext.metadata.set_metadata import set_metadata; set_metadata()
except Exception:
    WORKING_DIRECTORY = os.getcwd()
    WORKING_PARENT = os.path.join(WORKING_DIRECTORY, os.path.pardir)
    if not os.path.isdir("working") and os.path.isdir(os.path.join(WORKING_PARENT, "working")):
        # We're probably in pulsar
        WORKING_DIRECTORY = WORKING_PARENT
    METADATA_DIRECTORY = os.path.join(WORKING_DIRECTORY, "metadata")
    EXPORT_STORE_DIRECTORY = os.path.join(METADATA_DIRECTORY, "outputs_populated")
    os.makedirs(EXPORT_STORE_DIRECTORY, exist_ok=True)
    with open(os.path.join(EXPORT_STORE_DIRECTORY, "traceback.txt"), "w") as out:
        out.write(traceback.format_exc())
    raise
"""


def get_metadata_compute_strategy(config, job_id, metadata_strategy_override=None, tool_id=None, tool_type=None):
    metadata_strategy = metadata_strategy_override or config.metadata_strategy
    if metadata_strategy == "legacy":
        raise Exception("legacy metadata_strategy has been removed")
    elif "extended" in metadata_strategy and tool_id != "__SET_METADATA__" and tool_type != "interactive":
        return ExtendedDirectoryMetadataGenerator(job_id)
    else:
        return PortableDirectoryMetadataGenerator(job_id)


class MetadataCollectionStrategy(metaclass=abc.ABCMeta):
    """Interface describing the abstract process of writing out and collecting output metadata."""

    extended = False

    @abc.abstractmethod
    def setup_external_metadata(
        self,
        datasets_dict,
        out_collections,
        sa_session: "scoped_session",
        exec_dir=None,
        tmp_dir=None,
        dataset_files_path=None,
        output_fnames=None,
        config_root=None,
        use_bin=False,
        config_file=None,
        datatypes_config=None,
        job_metadata=None,
        provided_metadata_style=None,
        compute_tmp_dir=None,
        compute_version_path: Optional[str] = None,
        include_command=True,
        max_metadata_value_size=0,
        max_discovered_files=None,
        validate_outputs: bool = False,
        object_store_conf=None,
        tool=None,
        job: Optional[galaxy.model.Job] = None,
        link_data_only: bool = False,
        kwds=None,
    ):
        """Setup files needed for external metadata collection.

        If include_command is True, return full Python command to externally compute metadata
        otherwise just the arguments to galaxy_ext.metadata.set_metadata required to build.
        """

    @abc.abstractmethod
    def external_metadata_set_successfully(self, dataset, name, sa_session, working_directory):
        """Return boolean indicating if metadata for specified dataset was written properly."""

    @abc.abstractmethod
    def load_metadata(self, dataset, name, sa_session, working_directory, remote_metadata_directory=None):
        """Load metadata calculated externally into specified dataset."""

    def _load_metadata_from_path(self, dataset, metadata_output_path, working_directory, remote_metadata_directory):
        def path_rewriter(path):
            if not path:
                return path
            normalized_remote_metadata_directory = remote_metadata_directory and os.path.normpath(
                remote_metadata_directory
            )
            normalized_path = os.path.normpath(path)
            if remote_metadata_directory and normalized_path.startswith(normalized_remote_metadata_directory):
                if self.portable:
                    target_directory = os.path.join(working_directory, "metadata")
                else:
                    target_directory = working_directory
                return normalized_path.replace(normalized_remote_metadata_directory, target_directory, 1)
            return path

        dataset.metadata.from_JSON_dict(metadata_output_path, path_rewriter=path_rewriter)

    def _metadata_results_from_file(self, dataset, filename_results_code):
        try:
            with open(filename_results_code) as f:
                rval, rstring = json.load(f)
        except OSError:
            rval = False
            rstring = f"Metadata results could not be read from '{filename_results_code}'"

        if not rval:
            log.warning(f"setting metadata externally failed for {dataset.__class__.__name__} {dataset.id}: {rstring}")
        return rval


class PortableDirectoryMetadataGenerator(MetadataCollectionStrategy):
    portable = True
    write_object_store_conf = False

    def __init__(self, job_id):
        self.job_id = job_id

    def setup_external_metadata(
        self,
        datasets_dict,
        out_collections,
        sa_session: "scoped_session",
        exec_dir=None,
        tmp_dir=None,
        dataset_files_path=None,
        output_fnames=None,
        config_root=None,
        use_bin=False,
        config_file=None,
        datatypes_config=None,
        job_metadata=None,
        provided_metadata_style=None,
        compute_tmp_dir=None,
        compute_version_path: Optional[str] = None,
        include_command=True,
        max_metadata_value_size=0,
        max_discovered_files=None,
        validate_outputs: bool = False,
        object_store_conf=None,
        tool=None,
        job: Optional[galaxy.model.Job] = None,
        link_data_only: bool = False,
        kwds=None,
    ):
        assert job_metadata, "setup_external_metadata must be supplied with job_metadata path"
        kwds = kwds or {}
        if not job:
            job = sa_session.query(galaxy.model.Job).get(self.job_id)
            assert job
        tmp_dir = _init_tmp_dir(tmp_dir)

        metadata_dir = os.path.join(tmp_dir, "metadata")
        # may already exist (i.e. metadata collection in the job handler)
        safe_makedirs(metadata_dir)

        def job_relative_path(path):
            path_relative = os.path.relpath(path, tmp_dir)
            return path_relative

        outputs = {}
        output_collections = {}

        for name, dataset in datasets_dict.items():
            assert name is not None
            assert name not in outputs
            key = name

            def _metadata_path(what):
                return os.path.join(metadata_dir, f"metadata_{what}_{key}")  # noqa: B023

            _initialize_metadata_inputs(
                dataset, _metadata_path, tmp_dir, kwds, real_metadata_object=self.write_object_store_conf
            )

            outputs[name] = {
                "filename_override": _get_filename_override(output_fnames, dataset.get_file_name()),
                "validate": validate_outputs,
                "object_store_store_by": dataset.dataset.store_by,
                "id": dataset.id,
                "model_class": (
                    "LibraryDatasetDatasetAssociation"
                    if isinstance(dataset, galaxy.model.LibraryDatasetDatasetAssociation)
                    else "HistoryDatasetAssociation"
                ),
            }

        metadata_params_path = os.path.join(metadata_dir, "params.json")
        datatypes_config = os.path.relpath(datatypes_config, tmp_dir) if datatypes_config else None
        metadata_params = {
            "job_metadata": job_relative_path(job_metadata),
            "provided_metadata_style": provided_metadata_style,
            "datatypes_config": datatypes_config,
            "max_metadata_value_size": max_metadata_value_size,
            "max_discovered_files": max_discovered_files,
            "outputs": outputs,
            "change_datatype_actions": job.get_change_datatype_actions(),
        }

        # export model objects and object store configuration for extended metadata also.
        export_directory = os.path.join(metadata_dir, "outputs_new")
        with DirectoryModelExportStore(
            export_directory,
            for_edit=True,
            strip_metadata_files=False,
            serialize_dataset_objects=True,
            serialize_jobs=False,
        ) as export_store:
            export_store.export_job(job, tool=tool)
            for dataset in datasets_dict.values():
                export_store.add_dataset(dataset)

            for name, dataset_collection in out_collections.items():
                export_store.export_collection(dataset_collection)
                output_collections[name] = {
                    "id": dataset_collection.id,
                    "model_class": dataset_collection.__class__.__name__,
                }

        if self.write_object_store_conf:
            with open(os.path.join(metadata_dir, "object_store_conf.json"), "w") as f:
                json.dump(object_store_conf, f)

            # setup tool
            tool_as_dict: Dict[str, Any] = {}
            tool_as_dict["stdio_exit_codes"] = [e.to_dict() for e in tool.stdio_exit_codes]
            tool_as_dict["stdio_regexes"] = [r.to_dict() for r in tool.stdio_regexes]
            tool_as_dict["outputs"] = {name: output.to_dict() for name, output in tool.outputs.items()}
            tool_as_dict["output_collections"] = {
                name: output.to_dict() for name, output in tool.output_collections.items()
            }

            # setup the rest
            metadata_params["tool"] = tool_as_dict
            metadata_params["link_data_only"] = link_data_only
            metadata_params["tool_path"] = tool.config_file
            metadata_params["job_id_tag"] = job.get_id_tag()
            metadata_params["implicit_collection_jobs_association_id"] = (
                job.implicit_collection_jobs_association and job.implicit_collection_jobs_association.id
            )
            metadata_params["job_params"] = job.raw_param_dict()
            metadata_params["output_collections"] = output_collections
            if compute_version_path:
                metadata_params["compute_version_path"] = compute_version_path

        with open(metadata_params_path, "w") as f:
            json.dump(metadata_params, f)

        if include_command:
            # return command required to build
            if use_bin:
                return "galaxy-set-metadata"
            else:
                script_path = os.path.join(metadata_dir, "set.py")
                with open(script_path, "w") as f:
                    f.write(SET_METADATA_SCRIPT)
                return "python metadata/set.py"
        else:
            # return args to galaxy_ext.metadata.set_metadata required to build
            return ""

    def load_metadata(self, dataset, name, sa_session, working_directory, remote_metadata_directory=None):
        metadata_output_path = os.path.join(working_directory, "metadata", f"metadata_out_{name}")
        self._load_metadata_from_path(dataset, metadata_output_path, working_directory, remote_metadata_directory)

    def external_metadata_set_successfully(self, dataset, name, sa_session, working_directory):
        metadata_results_path = os.path.join(working_directory, "metadata", f"metadata_results_{name}")
        try:
            return self._metadata_results_from_file(dataset, metadata_results_path)
        except Exception:
            # if configured we need to try setting metadata internally
            return False


class ExtendedDirectoryMetadataGenerator(PortableDirectoryMetadataGenerator):
    extended = True
    write_object_store_conf = True

    def __init__(self, job_id):
        self.job_id = job_id

    def setup_external_metadata(self, datasets_dict, out_collections, sa_session, **kwd):
        command = super().setup_external_metadata(datasets_dict, out_collections, sa_session, **kwd)
        return command

    def load_metadata(self, dataset, name, sa_session, working_directory, remote_metadata_directory=None):
        # This method shouldn't really be called one-at-a-time dataset-wise like this and
        # isn't in job_wrapper.finish, instead finish just executes perform_import() on
        # the target model store within the context of a session to bring in all the changed objects.
        # However, this method is part of the metadata interface and is used by unit tests,
        # so we allow a sessionless import and loading of individual dataset as below.
        import_model_store = store.imported_store_for_metadata(
            os.path.join(working_directory, "metadata", "outputs_populated")
        )
        imported_dataset = import_model_store.sa_session.query(galaxy.model.HistoryDatasetAssociation).find(dataset.id)
        dataset.metadata = imported_dataset.metadata
        return dataset


def _initialize_metadata_inputs(dataset, path_for_part, tmp_dir, kwds, real_metadata_object=True):
    filename_out = path_for_part("out")
    filename_results_code = path_for_part("results")
    filename_kwds = path_for_part("kwds")
    filename_override_metadata = path_for_part("override")

    # create the file on disk, so it cannot be reused by tempfile (unlikely, but possible)
    with open(filename_out, "w+"):
        pass
    # create the file on disk, so it cannot be reused by tempfile (unlikely, but possible)
    with open(filename_results_code, "w+") as f:
        json.dump((False, "External set_meta() not called"), f)
    with open(filename_kwds, "w+") as f:
        json.dump(kwds, f, ensure_ascii=True)

    override_metadata = []
    for meta_key, spec_value in dataset.metadata.spec.items():
        if isinstance(spec_value.param, FileParameter) and dataset.metadata.get(meta_key, None) is not None:
            if not real_metadata_object:
                metadata_temp = MetadataTempFile()
                metadata_temp.tmp_dir = tmp_dir
                shutil.copy(dataset.metadata.get(meta_key, None).get_file_name(), metadata_temp.get_file_name())
                override_metadata.append((meta_key, metadata_temp.to_JSON()))

    with open(filename_override_metadata, "w+") as f:
        json.dump(override_metadata, f)

    return filename_out, filename_results_code, filename_kwds, filename_override_metadata


def _get_filename_override(output_fnames, file_name):
    if output_fnames:
        for dataset_path in output_fnames:
            if dataset_path.real_path == file_name:
                return dataset_path.false_path or dataset_path.real_path
    return ""


def _init_tmp_dir(tmp_dir):
    assert tmp_dir is not None
    safe_makedirs(tmp_dir)
    return tmp_dir
