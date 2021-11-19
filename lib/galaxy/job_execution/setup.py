"""Utilities to help job and tool code setup jobs."""
import json
import os

from galaxy import model
from galaxy.files import ConfiguredFileSources
from galaxy.job_execution.datasets import (
    DatasetPath,
    get_path_rewriter,
)
from galaxy.util import safe_makedirs
from galaxy.util.dictifiable import Dictifiable

TOOL_PROVIDED_JOB_METADATA_FILE = 'galaxy.json'
TOOL_PROVIDED_JOB_METADATA_KEYS = ['name', 'info', 'dbkey', 'created_from_basename']


class JobIO(Dictifiable):
    dict_collection_visible_keys = (
        'working_directory',
        'outputs_directory',
        'outputs_to_working_directory',
        'galaxy_url',
        'version_path',
        'tool_directory',
        'home_directory',
        'tmp_directory',
        'tool_data_path',
        'new_file_path',
        'len_file_path',
        'builds_file_path',
        '_file_sources',
        'check_job_script_integrity',
        'check_job_script_integrity_count',
        'check_job_script_integrity_sleep',
        'is_task',
    )

    def __init__(
            self,
            sa_session,
            job,
            working_directory,
            outputs_directory,
            outputs_to_working_directory,
            galaxy_url,
            version_path,
            tool_directory,
            home_directory,
            tmp_directory,
            tool_data_path,
            new_file_path,
            len_file_path,
            builds_file_path,
            _file_sources,
            check_job_script_integrity,
            check_job_script_integrity_count,
            check_job_script_integrity_sleep,
            is_task=False):
        self.sa_session = sa_session
        self.job = job
        self.working_directory = working_directory
        self.outputs_directory = outputs_directory
        self.outputs_to_working_directory = outputs_to_working_directory
        self.galaxy_url = galaxy_url
        self.version_path = version_path
        self.tool_directory = tool_directory
        self.home_directory = home_directory
        self.tmp_directory = tmp_directory
        self.tool_data_path = tool_data_path
        self.new_file_path = new_file_path
        self.len_file_path = len_file_path
        self.builds_file_path = builds_file_path
        self._file_sources = _file_sources
        self.check_job_script_integrity = check_job_script_integrity
        self.check_job_script_integrity_count = check_job_script_integrity_count
        self.check_job_script_integrity_sleep = check_job_script_integrity_sleep
        self.is_task = is_task
        self.output_paths = None
        self.output_hdas_and_paths = None
        self._dataset_path_rewriter = None

    @classmethod
    def from_json(cls, path, sa_session, job):
        with open(path) as job_io_serialized:
            kwargs = json.load(job_io_serialized)
        kwargs.pop('model_class')
        return cls(sa_session=sa_session, job=job, **kwargs)

    @property
    def file_sources(self) -> ConfiguredFileSources:
        return ConfiguredFileSources.from_dict(json.loads(self._file_sources))

    def to_json(self, path):
        with open(path, 'w') as out:
            out.write(json.dumps(self.to_dict()))

    @property
    def dataset_path_rewriter(self):
        if self._dataset_path_rewriter is None:
            self._dataset_path_rewriter = get_path_rewriter(
                outputs_to_working_directory=self.outputs_to_working_directory,
                working_directory=self.working_directory,
                outputs_directory=self.outputs_directory,
                is_task=self.is_task,
            )
        return self._dataset_path_rewriter

    def get_input_dataset_fnames(self, ds):
        filenames = []
        filenames = [ds.file_name]
        # we will need to stage in metadata file names also
        # TODO: would be better to only stage in metadata files that are actually needed (found in command line, referenced in config files, etc.)
        for value in ds.metadata.values():
            if isinstance(value, model.MetadataFile):
                filenames.append(value.file_name)
        return filenames

    def get_input_fnames(self):
        job = self.job
        filenames = []
        for da in job.input_datasets + job.input_library_datasets:  # da is JobToInputDatasetAssociation object
            if da.dataset:
                filenames.extend(self.get_input_dataset_fnames(da.dataset))
        return filenames

    def get_input_paths(self):
        job = self.job
        paths = []
        for da in job.input_datasets + job.input_library_datasets:  # da is JobToInputDatasetAssociation object
            if da.dataset:
                paths.append(self.get_input_path(da.dataset))
        return paths

    def get_input_path(self, dataset):
        real_path = dataset.file_name
        false_path = self.dataset_path_rewriter.rewrite_dataset_path(dataset, 'input')
        return DatasetPath(
            dataset.dataset.id,
            real_path=real_path,
            false_path=false_path,
            mutable=False,
            dataset_uuid=dataset.dataset.uuid,
            object_store_id=dataset.dataset.object_store_id,
        )

    def get_output_basenames(self):
        return [os.path.basename(str(fname)) for fname in self.get_output_fnames()]

    def get_output_fnames(self):
        if self.output_paths is None:
            self.compute_outputs()
        return self.output_paths

    def get_output_path(self, dataset):
        if getattr(dataset, "fake_dataset_association", False):
            return dataset.file_name
        assert dataset.id is not None, f"{dataset} needs to be flushed to find output path"
        if self.output_paths is None:
            self.compute_outputs()
        if self.output_hdas_and_paths is not None:
            for (hda, dataset_path) in self.output_hdas_and_paths.values():
                if hda.id == dataset.id:
                    return dataset_path
        raise KeyError(f"Couldn't find job output for [{dataset}] in [{self.output_hdas_and_paths.values()}]")

    def get_mutable_output_fnames(self):
        if self.output_paths is None:
            self.compute_outputs()
        return [dsp for dsp in self.output_paths or [] if dsp.mutable]

    def get_output_hdas_and_fnames(self):
        if self.output_hdas_and_paths is None:
            self.compute_outputs()
        return self.output_hdas_and_paths

    def compute_outputs(self):
        dataset_path_rewriter = self.dataset_path_rewriter

        job = self.job
        # Job output datasets are combination of history, library, and jeha datasets.
        special = self.sa_session.query(model.JobExportHistoryArchive).filter_by(job=job).first()
        false_path = None

        results = []
        for da in job.output_datasets + job.output_library_datasets:
            da_false_path = dataset_path_rewriter.rewrite_dataset_path(da.dataset, 'output')
            mutable = da.dataset.dataset.external_filename is None
            dataset_path = DatasetPath(da.dataset.dataset.id, da.dataset.file_name, false_path=da_false_path, mutable=mutable)
            results.append((da.name, da.dataset, dataset_path))

        self.output_paths = [t[2] for t in results]
        self.output_hdas_and_paths = {t[0]: t[1:] for t in results}
        if special:
            false_path = dataset_path_rewriter.rewrite_dataset_path(special, 'output')
            dsp = DatasetPath(special.dataset.id, special.dataset.file_name, false_path)
            self.output_paths.append(dsp)
            self.output_hdas_and_paths["output_file"] = [special.fda, dsp]
        return self.output_paths

    def get_output_file_id(self, file):
        if self.output_paths is None:
            self.get_output_fnames()
        for dp in self.output_paths or []:
            if self.outputs_to_working_directory and os.path.basename(dp.false_path) == file:
                return dp.dataset_id
            elif os.path.basename(dp.real_path) == file:
                return dp.dataset_id
        return None


def ensure_configs_directory(work_dir):
    configs_dir = os.path.join(work_dir, "configs")
    if not os.path.exists(configs_dir):
        safe_makedirs(configs_dir)
    return configs_dir


def create_working_directory_for_job(object_store, job):
    object_store.create(
        job, base_dir='job_work', dir_only=True, obj_dir=True)
    working_directory = object_store.get_filename(
        job, base_dir='job_work', dir_only=True, obj_dir=True)
    return working_directory
