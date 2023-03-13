"""Utilities to help job and tool code setup jobs."""
import json
import os
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from galaxy.files import (
    ConfiguredFileSources,
    DictFileSourcesUserContext,
    ProvidesUserFileSourcesUserContext,
)
from galaxy.job_execution.datasets import (
    DatasetPath,
    DatasetPathRewriter,
    get_path_rewriter,
)
from galaxy.model import (
    DatasetInstance,
    Job,
    JobExportHistoryArchive,
    MetadataFile,
)
from galaxy.util import safe_makedirs
from galaxy.util.dictifiable import Dictifiable

TOOL_PROVIDED_JOB_METADATA_FILE = "galaxy.json"
TOOL_PROVIDED_JOB_METADATA_KEYS = ["name", "info", "dbkey", "created_from_basename"]


OutputHdasAndType = Dict[str, Tuple[DatasetInstance, DatasetPath]]
OutputPaths = List[DatasetPath]


class JobIO(Dictifiable):
    dict_collection_visible_keys = (
        "job_id",
        "working_directory",
        "outputs_directory",
        "outputs_to_working_directory",
        "galaxy_url",
        "version_path",
        "tool_directory",
        "home_directory",
        "tmp_directory",
        "tool_data_path",
        "galaxy_data_manager_data_path",
        "new_file_path",
        "len_file_path",
        "builds_file_path",
        "file_sources_dict",
        "check_job_script_integrity",
        "check_job_script_integrity_count",
        "check_job_script_integrity_sleep",
        "tool_source",
        "tool_source_class",
        "tool_dir",
        "is_task",
    )

    def __init__(
        self,
        sa_session,
        job: Job,
        working_directory: str,
        outputs_directory: str,
        outputs_to_working_directory: bool,
        galaxy_url: str,
        version_path: str,
        tool_directory: str,
        home_directory: str,
        tmp_directory: str,
        tool_data_path: str,
        galaxy_data_manager_data_path: str,
        new_file_path: str,
        len_file_path: str,
        builds_file_path: str,
        check_job_script_integrity: bool,
        check_job_script_integrity_count: int,
        check_job_script_integrity_sleep: float,
        file_sources_dict: Dict[str, Any],
        user_context: Union[ProvidesUserFileSourcesUserContext, Dict["str", Any]],
        tool_source: Optional[str] = None,
        tool_source_class: Optional["str"] = "XmlToolSource",
        tool_dir: Optional[str] = None,
        is_task: bool = False,
    ):
        user_context_instance: Union[ProvidesUserFileSourcesUserContext, DictFileSourcesUserContext]
        self.file_sources_dict = file_sources_dict
        if isinstance(user_context, dict):
            user_context_instance = DictFileSourcesUserContext(**user_context, file_sources=self.file_sources)
        else:
            user_context_instance = user_context
        self.user_context = user_context_instance
        self.sa_session = sa_session
        self.job = job
        self.job_id = job.id
        self.working_directory = working_directory
        self.outputs_directory = outputs_directory
        self.outputs_to_working_directory = outputs_to_working_directory
        self.galaxy_url = galaxy_url
        self.version_path = version_path
        self.tool_directory = tool_directory
        self.home_directory = home_directory
        self.tmp_directory = tmp_directory
        self.tool_data_path = tool_data_path
        self.galaxy_data_manager_data_path = galaxy_data_manager_data_path
        self.new_file_path = new_file_path
        self.len_file_path = len_file_path
        self.builds_file_path = builds_file_path
        self.check_job_script_integrity = check_job_script_integrity
        self.check_job_script_integrity_count = check_job_script_integrity_count
        self.check_job_script_integrity_sleep = check_job_script_integrity_sleep
        self.tool_dir = tool_dir
        self.is_task = is_task
        self.tool_source = tool_source
        self.tool_source_class = tool_source_class
        self._output_paths: Optional[OutputPaths] = None
        self._output_hdas_and_paths: Optional[OutputHdasAndType] = None
        self._dataset_path_rewriter: Optional[DatasetPathRewriter] = None

    @classmethod
    def from_json(cls, path, sa_session):
        with open(path) as job_io_serialized:
            io_dict = json.load(job_io_serialized)
        return cls.from_dict(io_dict=io_dict, sa_session=sa_session)

    @classmethod
    def from_dict(cls, io_dict, sa_session):
        io_dict.pop("model_class")
        job_id = io_dict.pop("job_id")
        job = sa_session.query(Job).get(job_id)
        return cls(sa_session=sa_session, job=job, **io_dict)

    def to_dict(self):
        io_dict = super().to_dict()
        io_dict["user_context"] = self.user_context.to_dict()
        return io_dict

    def to_json(self, path):
        with open(path, "w") as out:
            out.write(json.dumps(self.to_dict()))

    @property
    def file_sources(self) -> ConfiguredFileSources:
        return ConfiguredFileSources.from_dict(self.file_sources_dict)

    @property
    def dataset_path_rewriter(self) -> DatasetPathRewriter:
        if self._dataset_path_rewriter is None:
            self._dataset_path_rewriter = get_path_rewriter(
                outputs_to_working_directory=self.outputs_to_working_directory,
                working_directory=self.working_directory,
                outputs_directory=self.outputs_directory,
                is_task=self.is_task,
            )
        assert self._dataset_path_rewriter is not None
        return self._dataset_path_rewriter

    @property
    def output_paths(self) -> OutputPaths:
        if self._output_paths is None:
            self.compute_outputs()
        return cast(OutputPaths, self._output_paths)

    @property
    def output_hdas_and_paths(self) -> OutputHdasAndType:
        if self._output_hdas_and_paths is None:
            self.compute_outputs()
        return cast(OutputHdasAndType, self._output_hdas_and_paths)

    def get_input_dataset_fnames(self, ds: DatasetInstance) -> List[str]:
        filenames = [ds.file_name]
        # we will need to stage in metadata file names also
        # TODO: would be better to only stage in metadata files that are actually needed (found in command line, referenced in config files, etc.)
        for value in ds.metadata.values():
            if isinstance(value, MetadataFile):
                filenames.append(value.file_name)
        return filenames

    def get_input_fnames(self) -> List[str]:
        job = self.job
        filenames = []
        for da in job.input_datasets + job.input_library_datasets:  # da is JobToInputDatasetAssociation object
            if da.dataset:
                filenames.extend(self.get_input_dataset_fnames(da.dataset))
        return filenames

    def get_input_paths(self) -> List[DatasetPath]:
        job = self.job
        paths = []
        for da in job.input_datasets + job.input_library_datasets:  # da is JobToInputDatasetAssociation object
            if da.dataset:
                paths.append(self.get_input_path(da.dataset))
        return paths

    def get_input_path(self, dataset: DatasetInstance) -> DatasetPath:
        real_path = dataset.file_name
        false_path = self.dataset_path_rewriter.rewrite_dataset_path(dataset, "input")
        return DatasetPath(
            dataset.dataset.id,
            real_path=real_path,
            false_path=false_path,
            mutable=False,
            dataset_uuid=dataset.dataset.uuid,
            object_store_id=dataset.dataset.object_store_id,
        )

    def get_output_basenames(self) -> List[str]:
        return [os.path.basename(str(fname)) for fname in self.get_output_fnames()]

    def get_output_fnames(self) -> OutputPaths:
        return self.output_paths

    def get_output_path(self, dataset):
        if getattr(dataset, "fake_dataset_association", False):
            return dataset.file_name
        assert dataset.id is not None, f"{dataset} needs to be flushed to find output path"
        for hda, dataset_path in self.output_hdas_and_paths.values():
            if hda.id == dataset.id:
                return dataset_path
        raise KeyError(f"Couldn't find job output for [{dataset}] in [{self.output_hdas_and_paths.values()}]")

    def get_mutable_output_fnames(self):
        return [dsp for dsp in self.output_paths if dsp.mutable]

    def get_output_hdas_and_fnames(self) -> OutputHdasAndType:
        return self.output_hdas_and_paths

    def compute_outputs(self) -> None:
        dataset_path_rewriter = self.dataset_path_rewriter

        job = self.job
        # Job output datasets are combination of history, library, and jeha datasets.
        special = self.sa_session.query(JobExportHistoryArchive).filter_by(job=job).first()
        false_path = None

        results = []
        for da in job.output_datasets + job.output_library_datasets:
            da_false_path = dataset_path_rewriter.rewrite_dataset_path(da.dataset, "output")
            mutable = da.dataset.dataset.external_filename is None
            dataset_path = DatasetPath(
                da.dataset.dataset.id, da.dataset.file_name, false_path=da_false_path, mutable=mutable
            )
            results.append((da.name, da.dataset, dataset_path))

        self._output_paths = [t[2] for t in results]
        self._output_hdas_and_paths = {t[0]: t[1:] for t in results}
        if special:
            false_path = dataset_path_rewriter.rewrite_dataset_path(special, "output")
            dsp = DatasetPath(special.dataset.id, special.dataset.file_name, false_path)
            self._output_paths.append(dsp)
            self._output_hdas_and_paths["output_file"] = (special.fda, dsp)

    def get_output_file_id(self, file: str) -> Optional[int]:
        for dp in self.output_paths:
            if self.outputs_to_working_directory and os.path.basename(dp.false_path) == file:
                return dp.dataset_id
            elif os.path.basename(dp.real_path) == file:
                return dp.dataset_id
        return None


def ensure_configs_directory(work_dir: str) -> str:
    configs_dir = os.path.join(work_dir, "configs")
    if not os.path.exists(configs_dir):
        safe_makedirs(configs_dir)
    return configs_dir


def create_working_directory_for_job(object_store, job) -> str:
    object_store.create(job, base_dir="job_work", dir_only=True, obj_dir=True)
    working_directory = object_store.get_filename(job, base_dir="job_work", dir_only=True, obj_dir=True)
    return working_directory
