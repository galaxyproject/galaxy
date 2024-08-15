import os
import subprocess

from galaxy import model
from galaxy.app_unittest_utils import tools_support
from galaxy.job_execution.datasets import DatasetPath
from galaxy.metadata import get_metadata_compute_strategy
from galaxy.model.base import transaction
from galaxy.objectstore import ObjectStorePopulator
from galaxy.util import (
    galaxy_directory,
    safe_makedirs,
)
from galaxy.util.unittest import TestCase


class TestMetadata(TestCase, tools_support.UsesTools):
    def setUp(self):
        super().setUp()
        self.setup_app()
        model.Dataset.object_store = self.app.object_store
        job = model.Job()
        sa_session = self.app.model.session
        sa_session.add(job)
        history = model.History()
        job.history = history
        with transaction(sa_session):
            sa_session.commit()
        self.job = job
        self.history = history
        self.job_working_directory = os.path.join(self.test_directory, "job_working")
        self.tool_working_directory = os.path.join(self.job_working_directory, "working")
        os.mkdir(self.job_working_directory)
        os.mkdir(self.tool_working_directory)

    def tearDown(self):
        super().tearDown()
        self.metadata_compute_strategy = None

    def test_simple_output_directory(self):
        self.app.config.metadata_strategy = "directory"
        self._test_simple_output()

    def test_simple_output_extended(self):
        self.app.config.metadata_strategy = "extended"
        self._test_simple_output()

    def _test_simple_output(self):
        source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        output_dataset = self._create_output_dataset(
            extension="fasta",
        )
        sa_session = self.app.model.session
        with transaction(sa_session):
            sa_session.commit()
        output_datasets = {
            "out_file1": output_dataset,
        }
        command = self.metadata_command(output_datasets)
        self._write_output_dataset_contents(output_dataset, ">seq1\nGCTGCATG\n")
        self._write_job_files()
        self.exec_metadata_command(command)
        assert self.metadata_compute_strategy
        metadata_set_successfully = self.metadata_compute_strategy.external_metadata_set_successfully(
            output_dataset, "out_file1", sa_session, working_directory=self.job_working_directory
        )
        assert metadata_set_successfully
        self.metadata_compute_strategy.load_metadata(
            output_dataset, "out_file1", sa_session, working_directory=self.job_working_directory
        )
        assert output_dataset.metadata.data_lines == 2
        assert output_dataset.metadata.sequences == 1

    def test_primary_dataset_output_extension_directory(self):
        self.app.config.metadata_strategy = "directory"
        self._test_primary_dataset_output_extension()

    def _test_primary_dataset_output_extension(self):
        source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        # setting extension to 'auto' here, results in the extension specified in
        # galaxy.json (below) being respected.
        output_dataset = self._create_output_dataset(
            extension="auto",
        )
        sa_session = self.app.model.session
        with transaction(sa_session):
            sa_session.commit()
        output_datasets = {
            "out_file1": output_dataset,
        }
        command = self.metadata_command(output_datasets)
        self._write_galaxy_json(
            f"""{{"type": "dataset", "dataset_id": "{output_dataset.dataset.id}", "name": "my dynamic name", "ext": "fasta", "info": "my dynamic info"}}"""
        )
        self._write_output_dataset_contents(output_dataset, ">seq1\nGCTGCATG\n")
        self._write_job_files()
        self.exec_metadata_command(command)
        assert self.metadata_compute_strategy
        metadata_set_successfully = self.metadata_compute_strategy.external_metadata_set_successfully(
            output_dataset, "out_file1", sa_session, working_directory=self.job_working_directory
        )
        assert metadata_set_successfully
        output_dataset.extension = "fasta"  # gets done in job finish...
        self.metadata_compute_strategy.load_metadata(
            output_dataset, "out_file1", sa_session, working_directory=self.job_working_directory
        )
        assert output_dataset.metadata.data_lines == 2
        assert output_dataset.metadata.sequences == 1

    def test_primary_dataset_output_metadata_override_directory(self):
        self.app.config.metadata_strategy = "directory"
        self._test_primary_dataset_output_metadata_override()

    def test_primary_dataset_output_metadata_override_extended(self):
        self.app.config.metadata_strategy = "extended"
        self._test_primary_dataset_output_metadata_override()

    def _test_primary_dataset_output_metadata_override(self):
        source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        output_dataset = self._create_output_dataset(
            extension="auto",
        )
        sa_session = self.app.model.session
        with transaction(sa_session):
            sa_session.commit()
        output_datasets = {
            "out_file1": output_dataset,
        }
        command = self.metadata_command(output_datasets)
        self._write_galaxy_json(
            f"""{{"type": "dataset", "dataset_id": "{output_dataset.dataset.id}", "name": "my dynamic name", "ext": "fasta", "info": "my dynamic info", "metadata": {{"sequences": 42}}}}"""
        )
        self._write_output_dataset_contents(output_dataset, ">seq1\nGCTGCATG\n")
        self._write_job_files()
        self.exec_metadata_command(command)
        assert self.metadata_compute_strategy
        metadata_set_successfully = self.metadata_compute_strategy.external_metadata_set_successfully(
            output_dataset, "out_file1", sa_session, working_directory=self.job_working_directory
        )
        assert metadata_set_successfully
        output_dataset.extension = "fasta"  # get done in job finish...
        self.metadata_compute_strategy.load_metadata(
            output_dataset, "out_file1", sa_session, working_directory=self.job_working_directory
        )
        assert output_dataset.metadata.data_lines == 2
        assert output_dataset.metadata.sequences == 42

    def test_list_discovery_extended(self):
        self.app.config.metadata_strategy = "extended"
        source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/collection_split_on_column.xml")
        self._init_tool_for_path(source_file_name)
        collection = model.DatasetCollection(populated=False)
        collection.collection_type = "list"
        output_dataset_collection = self._create_output_dataset_collection(
            collection=collection,
        )
        assert output_dataset_collection.collection
        command = self.metadata_command({}, {"split_output": output_dataset_collection})
        self._write_work_dir_file("1.tabular", "1\n2\n3")
        self._write_work_dir_file("2.tabular", "4\n5\n6")
        self._write_job_files()
        self.exec_metadata_command(command)
        # Emulate job stuff here...

    def _create_output_dataset_collection(self, **kwd):
        output_dataset_collection = model.HistoryDatasetCollectionAssociation(**kwd)
        self.history.add_dataset_collection(output_dataset_collection)
        assert output_dataset_collection.collection
        self.app.model.session.add(output_dataset_collection)
        session = self.app.model.session
        with transaction(session):
            session.commit()
        return output_dataset_collection

    def _create_output_dataset(self, **kwd):
        output_dataset = model.HistoryDatasetAssociation(
            sa_session=self.app.model.session, create_dataset=True, flush=True, **kwd
        )
        self.history.add_dataset(output_dataset)
        ObjectStorePopulator(self.app, user=self.job.user).set_object_store_id(output_dataset)
        return output_dataset

    def _write_work_dir_file(self, filename, contents):
        with open(os.path.join(self.tool_working_directory, filename), "w") as f:
            f.write(contents)

    def _write_output_dataset_contents(self, output_dataset, contents):
        with open(output_dataset.dataset.get_file_name(), "w") as f:
            f.write(contents)

    def _write_galaxy_json(self, contents):
        job_metadata = os.path.join(self.tool_working_directory, self.tool.provided_metadata_file)
        with open(job_metadata, "w") as f:
            f.write(contents)

    def _write_job_files(self, stdout="tool stdout", stderr="tool stderr"):
        with open(os.path.join(self.job_working_directory, "tool_script.sh"), "w") as f:
            f.write("echo hi")
        with open(os.path.join(self.job_working_directory, "tool_stdout"), "w") as f:
            f.write(stdout)
        with open(os.path.join(self.job_working_directory, "tool_stderr"), "w") as f:
            f.write(stderr)

    def metadata_command(self, output_datasets, output_collections=None):
        output_collections = output_collections or {}
        metadata_compute_strategy = get_metadata_compute_strategy(self.app.config, self.job.id)
        self.metadata_compute_strategy = metadata_compute_strategy

        exec_dir = None
        dataset_files_path = self.app.model.Dataset.file_path
        config_root = self.app.config.root
        config_file = None
        datatypes_config = os.path.join(self.job_working_directory, "metadata", "registry.xml")
        safe_makedirs(os.path.join(self.job_working_directory, "metadata"))
        self.app.datatypes_registry.to_xml_file(path=datatypes_config)
        job_metadata = os.path.join(self.tool_working_directory, self.tool.provided_metadata_file)
        output_fnames = [DatasetPath(o.dataset.id, o.dataset.get_file_name(), None) for o in output_datasets.values()]
        command = metadata_compute_strategy.setup_external_metadata(
            output_datasets,
            output_collections,
            self.app.model.session,
            exec_dir=exec_dir,
            tmp_dir=self.job_working_directory,  # set in jobs/runners.py - better if was default.
            dataset_files_path=dataset_files_path,
            config_root=config_root,
            config_file=config_file,
            datatypes_config=datatypes_config,
            job_metadata=job_metadata,
            output_fnames=output_fnames,
            tool=self.tool,
            job=self.job,
            object_store_conf=self.app.object_store.to_dict(),
            max_metadata_value_size=10000,
        )
        return command

    def exec_metadata_command(self, command):
        with open(self.stdout_path, "wb") as stdout_file, open(self.stderr_path, "wb") as stderr_file:
            _environ = os.environ.copy()
            _environ["PYTHONPATH"] = os.path.abspath("lib")
            proc = subprocess.Popen(
                args=command,
                shell=True,
                cwd=self.job_working_directory,
                env=_environ,
                stdout=stdout_file,
                stderr=stderr_file,
            )
            ret = proc.wait()
        self.print_command_output()
        assert ret == 0
        return ret

    def print_command_output(self):
        print(">unit test of external metadata setting (command standard output)")
        print(open(self.stdout_path).read())
        print(">unit test of external metadata setting (command standard error)")
        print(open(self.stderr_path).read())

    @property
    def stdout_path(self):
        return os.path.join(self.test_directory, "stdout")

    @property
    def stderr_path(self):
        return os.path.join(self.test_directory, "stderr")
