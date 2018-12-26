import os
import subprocess
import unittest

from galaxy import model
from galaxy.jobs.datasets import DatasetPath
from galaxy.metadata import get_metadata_compute_strategy
from galaxy.objectstore import ObjectStorePopulator
from .. import tools_support


class MetadataTestCase(unittest.TestCase, tools_support.UsesApp, tools_support.UsesTools):

    def setUp(self):
        super(MetadataTestCase, self).setUp()
        self.setup_app()
        model.Dataset.object_store = self.app.object_store
        job = model.Job()
        sa_session = self.app.model.session
        sa_session.add(job)
        history = model.History()
        job.history = history
        sa_session.flush()
        self.job = job
        self.history = history
        self.job_working_directory = os.path.join(self.test_directory, "job_working")
        self.tool_working_directory = os.path.join(self.job_working_directory, "working")
        os.mkdir(self.job_working_directory)
        os.mkdir(self.tool_working_directory)

    def tearDown(self):
        super(MetadataTestCase, self).tearDown()
        self.metadata_compute_strategy = None

    def test_simple_output(self):
        source_file_name = os.path.join(os.getcwd(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        output_dataset = self._create_output_dataset(
            extension="fasta",
        )
        sa_session = self.app.model.session
        sa_session.flush()
        output_datasets = {
            "out_file1": output_dataset,
        }
        command = self.metadata_command(output_datasets)
        self._write_output_dataset_contents(output_dataset, ">seq1\nGCTGCATG\n")
        self.exec_metadata_command(command)
        metadata_set_successfully = self.metadata_compute_strategy.external_metadata_set_successfully(output_dataset, sa_session)
        assert metadata_set_successfully
        self.metadata_compute_strategy.load_metadata(output_dataset, "out_file1", sa_session, working_directory=self.job_working_directory)
        assert output_dataset.metadata.data_lines == 2
        assert output_dataset.metadata.sequences == 1

    def test_primary_dataset_output_extension(self):
        source_file_name = os.path.join(os.getcwd(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        # setting extension to 'auto' here, results in the extension specified in
        # galaxy.json (below) being respected.
        output_dataset = self._create_output_dataset(
            extension="auto",
        )
        sa_session = self.app.model.session
        sa_session.flush()
        output_datasets = {
            "out_file1": output_dataset,
        }
        command = self.metadata_command(output_datasets)
        self._write_galaxy_json("""{"type": "dataset", "dataset_id": "%s", "name": "my dynamic name", "ext": "fasta", "info": "my dynamic info"}""" % output_dataset.dataset.id)
        self._write_output_dataset_contents(output_dataset, ">seq1\nGCTGCATG\n")
        self.exec_metadata_command(command)
        metadata_set_successfully = self.metadata_compute_strategy.external_metadata_set_successfully(output_dataset, sa_session)
        assert metadata_set_successfully
        output_dataset.extension = "fasta"  # gets done in job finish...
        self.metadata_compute_strategy.load_metadata(output_dataset, "out_file1", sa_session, working_directory=self.job_working_directory)
        assert output_dataset.metadata.data_lines == 2
        assert output_dataset.metadata.sequences == 1

    def test_primary_dataset_output_metadata_override(self):
        source_file_name = os.path.join(os.getcwd(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        output_dataset = self._create_output_dataset(
            extension="auto",
        )
        sa_session = self.app.model.session
        sa_session.flush()
        output_datasets = {
            "out_file1": output_dataset,
        }
        command = self.metadata_command(output_datasets)
        self._write_galaxy_json("""{"type": "dataset", "dataset_id": "%s", "name": "my dynamic name", "ext": "fasta", "info": "my dynamic info", "metadata": {"sequences": 42}}""" % output_dataset.dataset.id)
        self._write_output_dataset_contents(output_dataset, ">seq1\nGCTGCATG\n")
        self.exec_metadata_command(command)
        metadata_set_successfully = self.metadata_compute_strategy.external_metadata_set_successfully(output_dataset, sa_session)
        assert metadata_set_successfully
        output_dataset.extension = "fasta"  # get done in job finish...
        self.metadata_compute_strategy.load_metadata(output_dataset, "out_file1", sa_session, working_directory=self.job_working_directory)
        assert output_dataset.metadata.data_lines == 2
        assert output_dataset.metadata.sequences == 42

    def _create_output_dataset(self, **kwd):
        output_dataset = model.HistoryDatasetAssociation(
            sa_session=self.app.model.session,
            create_dataset=True,
            flush=True,
            **kwd
        )
        self.history.add_dataset(output_dataset)
        ObjectStorePopulator(self.app).set_object_store_id(output_dataset)
        return output_dataset

    def _write_output_dataset_contents(self, output_dataset, contents):
        with open(output_dataset.dataset.file_name, "w") as f:
            f.write(contents)

    def _write_galaxy_json(self, contents):
        job_metadata = os.path.join(self.tool_working_directory, self.tool.provided_metadata_file)
        with open(job_metadata, "w") as f:
            f.write(contents)

    def metadata_command(self, output_datasets):
        metadata_compute_strategy = get_metadata_compute_strategy(self.app, self.job.id)
        self.metadata_compute_strategy = metadata_compute_strategy

        exec_dir = None
        dataset_files_path = self.app.model.Dataset.file_path
        config_root = self.app.config.root
        config_file = None
        datatypes_config = os.path.join(self.job_working_directory, 'registry.xml')
        self.app.datatypes_registry.to_xml_file(path=datatypes_config)
        job_metadata = os.path.join(self.tool_working_directory, self.tool.provided_metadata_file)
        output_fnames = [DatasetPath(o.dataset.id, o.dataset.file_name, None) for o in output_datasets.values()]
        command = metadata_compute_strategy.setup_external_metadata(output_datasets,
                                                                    self.app.model.session,
                                                                    exec_dir=exec_dir,
                                                                    tmp_dir=self.job_working_directory,  # set in jobs/runners.py - better if was default.
                                                                    dataset_files_path=dataset_files_path,
                                                                    config_root=config_root,
                                                                    config_file=config_file,
                                                                    datatypes_config=datatypes_config,
                                                                    job_metadata=job_metadata,
                                                                    output_fnames=output_fnames,
                                                                    max_metadata_value_size=10000)
        return command

    def exec_metadata_command(self, command):
        with open(self.stdout_path, "wb") as stdout_file, open(self.stderr_path, "wb") as stderr_file:
            _environ = os.environ.copy()
            _environ["PYTHONPATH"] = os.path.abspath("lib")
            proc = subprocess.Popen(args=command,
                                    shell=True,
                                    cwd=self.job_working_directory,
                                    env=_environ,
                                    stdout=stdout_file,
                                    stderr=stderr_file)
            ret = proc.wait()
        self.print_command_output()
        assert ret == 0
        return ret

    def print_command_output(self):
        print(">unit test of external metadata setting (command standard output)")
        print(open(self.stdout_path, "r").read())
        print(">unit test of external metadata setting (command standard error)")
        print(open(self.stderr_path, "r").read())

    @property
    def stdout_path(self):
        return os.path.join(self.test_directory, "stdout")

    @property
    def stderr_path(self):
        return os.path.join(self.test_directory, "stderr")
