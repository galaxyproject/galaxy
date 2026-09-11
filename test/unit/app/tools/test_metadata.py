import json
import os
import subprocess

import pytest

from galaxy import model
from galaxy.app_unittest_utils import tools_support
from galaxy.job_execution.datasets import DatasetPath
from galaxy.metadata import get_metadata_compute_strategy
from galaxy.metadata.set_metadata import load_job_metadata
from galaxy.model.store.discover import InvalidDiscoveredFilePathError
from galaxy.objectstore import ObjectStorePopulator
from galaxy.tool_util.parser.yaml import YamlToolSource
from galaxy.tool_util.provided_metadata import NullToolProvidedMetadata
from galaxy.tool_util_models import UserToolSource
from galaxy.tools import create_tool_from_source
from galaxy.util import (
    galaxy_directory,
    safe_makedirs,
)
from galaxy.util.unittest import TestCase


def test_extended_metadata_rejects_metadata_file_symlink_outside_working_directory(
    tmp_path,
):
    working_directory = tmp_path / "working"
    working_directory.mkdir()
    outside_metadata = tmp_path / "outside.json"
    outside_metadata.write_text("{}")
    metadata_symlink = working_directory / "galaxy.json"
    metadata_symlink.symlink_to(outside_metadata)

    with pytest.raises(InvalidDiscoveredFilePathError):
        load_job_metadata(
            metadata_symlink,
            "default",
            uses_tool_provided_metadata=True,
            job_working_directory=working_directory,
        )


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
            output_dataset,
            "out_file1",
            sa_session,
            working_directory=self.job_working_directory,
        )
        assert metadata_set_successfully
        self.metadata_compute_strategy.load_metadata(
            output_dataset,
            "out_file1",
            sa_session,
            working_directory=self.job_working_directory,
        )
        assert output_dataset.metadata.data_lines == 2
        assert output_dataset.metadata.sequences == 1

    def test_primary_dataset_output_extension_directory(self):
        self.app.config.metadata_strategy = "directory"
        self._test_primary_dataset_output_extension()

    def _test_primary_dataset_output_extension(self):
        source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        self.tool.uses_tool_provided_metadata = True
        # setting extension to 'auto' here, results in the extension specified in
        # galaxy.json (below) being respected.
        output_dataset = self._create_output_dataset(
            extension="auto",
        )
        sa_session = self.app.model.session
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
            output_dataset,
            "out_file1",
            sa_session,
            working_directory=self.job_working_directory,
        )
        assert metadata_set_successfully
        output_dataset.extension = "fasta"  # gets done in job finish...
        self.metadata_compute_strategy.load_metadata(
            output_dataset,
            "out_file1",
            sa_session,
            working_directory=self.job_working_directory,
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
        self.tool.uses_tool_provided_metadata = True
        output_dataset = self._create_output_dataset(
            extension="auto",
        )
        sa_session = self.app.model.session
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
            output_dataset,
            "out_file1",
            sa_session,
            working_directory=self.job_working_directory,
        )
        assert metadata_set_successfully
        output_dataset.extension = "fasta"  # get done in job finish...
        self.metadata_compute_strategy.load_metadata(
            output_dataset,
            "out_file1",
            sa_session,
            working_directory=self.job_working_directory,
        )
        assert output_dataset.metadata.data_lines == 2
        assert output_dataset.metadata.sequences == 42

    def test_extended_metadata_ignores_metadata_file_when_disabled(self):
        self.app.config.metadata_strategy = "extended"
        source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        self.tool.uses_tool_provided_metadata = False
        output_dataset = self._create_output_dataset(extension="fasta")
        self.app.model.session.commit()
        command = self.metadata_command({"out_file1": output_dataset})
        self._write_galaxy_json(
            f"""{{"type": "dataset", "dataset_id": "{output_dataset.dataset.id}", "metadata": {{"sequences": 42}}}}"""
        )
        self._write_output_dataset_contents(output_dataset, ">seq1\nGCTGCATG\n")
        self._write_job_files()

        self.exec_metadata_command(command)

        assert self.metadata_compute_strategy
        assert self.metadata_compute_strategy.external_metadata_set_successfully(
            output_dataset,
            "out_file1",
            self.app.model.session,
            working_directory=self.job_working_directory,
        )
        self.metadata_compute_strategy.load_metadata(
            output_dataset,
            "out_file1",
            self.app.model.session,
            working_directory=self.job_working_directory,
        )
        assert output_dataset.metadata.sequences == 1

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

    @pytest.mark.parametrize("source_kind", ["xml", "user"])
    @pytest.mark.parametrize("strategy", ["directory", "extended"])
    @pytest.mark.parametrize("discovery_format", [None, "tabular", "captured", "metadata_only", "missing_source"])
    def test_collection_input_sources(self, source_kind, strategy, discovery_format):
        self.app.config.metadata_strategy = strategy
        pattern = r"(?P<name>result)\.txt"
        discovery = {"pattern": pattern}
        expected_format = "interval"
        if discovery_format == "captured":
            discovery["pattern"] = r"(?P<name>result)\.(?P<ext>txt)"
            expected_format = "txt"
        elif discovery_format == "tabular":
            discovery["format"] = discovery_format
            expected_format = discovery_format
        format_source = "input"
        if discovery_format == "metadata_only":
            format_source = None
            expected_format = "txt"
        elif discovery_format == "missing_source":
            format_source = "unavailable"
            expected_format = "txt"
        if source_kind == "user":
            source = UserToolSource.model_validate(
                {
                    "class": "GalaxyUserTool",
                    "id": "collection_sources",
                    "name": "Collection sources",
                    "version": "1.0",
                    "container": "busybox",
                    "shell_command": "true",
                    "inputs": [{"name": "input", "type": "data", "format": ["interval"]}],
                    "outputs": [
                        {
                            "name": "output",
                            "type": "collection",
                            "collection_type": "list",
                            "format": "txt",
                            "format_source": format_source,
                            "metadata_source": "input",
                            "discover_datasets": [discovery],
                        }
                    ],
                }
            )
            self.tool = create_tool_from_source(self.app, YamlToolSource(source.model_dump(by_alias=True)))
        else:
            attributes = " ".join(f'{key}="{value}"' for key, value in discovery.items())
            source_attribute = f'format_source="{format_source}"' if format_source else ""
            self._init_tool(f"""<tool id="sources" name="Collection sources" version="1.0" profile="26.1">
                <command>exit 0</command>
                <inputs><param name="input" type="data" format="interval" /></inputs>
                <outputs><collection name="output" type="list" format="txt"
                    {source_attribute} metadata_source="input">
                    <discover_datasets {attributes} />
                </collection></outputs>
            </tool>""".replace("(?P<", "(?P&lt;"))
        output_model = self.tool.output_collections["output"].to_model()
        assert output_model.format_source == format_source
        assert output_model.metadata_source == "input"
        input_dataset = self._create_output_dataset(extension="interval")
        input_dataset.init_meta()
        input_dataset.metadata.chromCol = 3
        input_dataset.metadata.startCol = 1
        input_dataset.metadata.endCol = 2
        input_dataset.metadata.data_lines = 42
        input_dataset.dbkey = "hg38"
        self._write_output_dataset_contents(input_dataset, "10\t20\tchr1\n")
        self.job.add_input_dataset("input", input_dataset)
        collection = model.DatasetCollection(collection_type="list", populated=False)
        hdca = self._create_output_dataset_collection(collection=collection)
        self._write_work_dir_file("result.txt", "10\t20\tchr1\n")
        if strategy == "extended":
            command = self.metadata_command({}, {"output": hdca})
            self._write_job_files()
            self.exec_metadata_command(command)
            populated_path = os.path.join(self.job_working_directory, "metadata", "outputs_populated")
            with open(os.path.join(populated_path, "datasets_attrs.txt")) as f:
                datasets = json.load(f)
            assert len(datasets) == 1
            dataset_attrs = datasets[0]
            assert dataset_attrs["extension"] == expected_format
            metadata = dataset_attrs["metadata"]
            assert metadata["dbkey"] == "hg38"
            if expected_format == "interval":
                assert metadata["chromCol"] == 3
                assert metadata["startCol"] == 1
                assert metadata["endCol"] == 2
                assert metadata["data_lines"] == 1
            return
        else:
            self.tool.discover_outputs(
                {},
                {"output": hdca},
                NullToolProvidedMetadata(),
                self.tool_working_directory,
                self.job,
                input_ext="interval",
                input_dbkey="?",
                inp_data={"input": input_dataset},
            )
        self.app.model.session.flush()
        assert hdca.collection.populated
        assert len(hdca.collection.dataset_instances) == 1
        dataset = hdca.collection.dataset_instances[0]
        assert dataset.extension == expected_format
        assert dataset.dbkey == "hg38"
        if expected_format == "interval":
            assert dataset.metadata.chromCol == 3
            assert dataset.metadata.startCol == 1
            assert dataset.metadata.endCol == 2
            assert dataset.metadata.data_lines == 1

    def test_extended_metadata_rejects_unprivileged_tool_unnamed_outputs(self):
        self.app.config.metadata_strategy = "extended"
        source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        self.tool.uses_tool_provided_metadata = True
        self.tool.allows_unnamed_outputs = False
        output_dataset = self._create_output_dataset(extension="txt")
        self.app.model.session.commit()
        command = self.metadata_command({"out_file1": output_dataset})
        replacement_name = "replacement.txt"
        self._write_work_dir_file(replacement_name, "replacement")
        self._write_galaxy_json(
            json.dumps(
                {
                    "__unnamed_outputs": [
                        {
                            "destination": {"type": "hdas"},
                            "elements": [{"filename": replacement_name, "name": "replacement"}],
                        }
                    ]
                }
            )
        )
        self._write_output_dataset_contents(output_dataset, "original")
        self._write_job_files()

        self.exec_metadata_command(command)

        self._assert_extended_metadata_security_failure(
            output_dataset, "This tool is not permitted to create unnamed outputs."
        )

    def test_extended_metadata_rejects_dynamic_tool_spoofing_data_fetch(self):
        self.app.config.metadata_strategy = "extended"
        source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/for_workflows/cat.xml")
        self._init_tool_for_path(source_file_name)
        self.tool.uses_tool_provided_metadata = True
        self.tool.old_id = "__DATA_FETCH__"
        self.tool.dynamic_tool_id = 1
        self.job.tool_id = "__DATA_FETCH__"
        self.job.dynamic_tool_id = 1
        output_dataset = self._create_output_dataset(extension="txt")
        self.app.model.session.commit()
        command = self.metadata_command({"out_file1": output_dataset})
        outside_path = os.path.join(self.test_directory, "outside.txt")
        with open(outside_path, "w") as outside_file:
            outside_file.write("outside")
        self._write_galaxy_json(
            json.dumps(
                {
                    "__unnamed_outputs": [
                        {
                            "destination": {"type": "hdas"},
                            "elements": [
                                {
                                    "filename": outside_path,
                                    "link_data_only": True,
                                    "name": "external link",
                                }
                            ],
                        }
                    ]
                }
            )
        )
        self._write_output_dataset_contents(output_dataset, "original")
        self._write_job_files()

        self.exec_metadata_command(command)

        self._assert_extended_metadata_security_failure(
            output_dataset,
            "This tool is not permitted to collect output files from outside its working directory.",
            metadata_set_successfully=True,
        )

    def _assert_extended_metadata_security_failure(
        self, output_dataset, expected_message, metadata_set_successfully=False
    ):
        assert self.metadata_compute_strategy
        assert metadata_set_successfully is self.metadata_compute_strategy.external_metadata_set_successfully(
            output_dataset,
            "out_file1",
            self.app.model.session,
            working_directory=self.job_working_directory,
        )
        jobs_attrs_path = os.path.join(
            self.job_working_directory,
            "metadata",
            "outputs_populated",
            "jobs_attrs.txt",
        )
        with open(jobs_attrs_path) as jobs_attrs_file:
            jobs_attrs = json.load(jobs_attrs_file)
        assert len(jobs_attrs) == 1
        assert jobs_attrs[0]["state"] == model.Job.states.ERROR
        security_messages = [
            message for message in jobs_attrs[0]["job_messages"] if message["type"] == "output_collection_security"
        ]
        assert len(security_messages) == 1
        assert security_messages[0]["desc"] == expected_message

    def _create_output_dataset_collection(self, **kwd):
        output_dataset_collection = model.HistoryDatasetCollectionAssociation(**kwd)
        self.history.add_dataset_collection(output_dataset_collection)
        assert output_dataset_collection.collection
        session = self.app.model.session
        session.add(output_dataset_collection)
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
        dataset_files_path = model.Dataset.file_path
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
            uses_tool_provided_metadata=self.tool.uses_tool_provided_metadata,
            allows_unnamed_outputs=self.tool.allows_unnamed_outputs,
            allows_external_output_paths=self.tool.allows_external_output_paths,
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
        with (
            open(self.stdout_path, "wb") as stdout_file,
            open(self.stderr_path, "wb") as stderr_file,
        ):
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
