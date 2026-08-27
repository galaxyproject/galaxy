import json
import os
import tempfile
from contextlib import contextmanager
from typing import cast

from sqlalchemy import select

from galaxy import (
    model,
    util,
)
from galaxy.app_unittest_utils import tools_support
from galaxy.model.store.discover import (
    ExternalOutputPathNotAllowedError,
    InvalidDiscoveredFilePathError,
    UntrustedToolProvidedMetadataError,
)
from galaxy.objectstore import BaseObjectStore
from galaxy.objectstore.examples import get_example as get_object_store_example
from galaxy.objectstore.unittest_utils import (
    Config as ObjectStoreTestConfig,
    DISK_TEST_CONFIG,
)
from galaxy.tool_util.parser import output_collection_def
from galaxy.tool_util.provided_metadata import (
    LegacyToolProvidedMetadata,
    NullToolProvidedMetadata,
    ToolProvidedMetadata,
)
from galaxy.util.unittest import TestCase

DEFAULT_TOOL_OUTPUT = "out1"
DEFAULT_EXTRA_NAME = "test1"


class TestCollectPrimaryDatasets(TestCase, tools_support.UsesTools):
    def setUp(self):
        self.setup_app()
        object_store = cast(BaseObjectStore, MockObjectStore())
        self.app.object_store = object_store
        self._init_tool(tools_support.SIMPLE_TOOL_CONTENTS)
        self._setup_test_output()

        model.Dataset.object_store = object_store

    def tearDown(self):
        if model.Dataset.object_store is self.app.object_store:
            model.Dataset.object_store = None

    def test_empty_collect(self):
        assert len(self._collect()) == 0

    def test_collect_multiple(self):
        path1 = self._setup_extra_file(name="test1")
        path2 = self._setup_extra_file(name="test2")

        datasets = self._collect()
        assert DEFAULT_TOOL_OUTPUT in datasets
        assert len(datasets[DEFAULT_TOOL_OUTPUT]) == 2

        # Test default order of collection.
        assert list(datasets[DEFAULT_TOOL_OUTPUT].keys()) == ["test1", "test2"]

        created_hda_1 = datasets[DEFAULT_TOOL_OUTPUT]["test1"]
        assert_created_with_path(self.app.object_store, created_hda_1.dataset, path1)

        created_hda_2 = datasets[DEFAULT_TOOL_OUTPUT]["test2"]
        assert_created_with_path(self.app.object_store, created_hda_2.dataset, path2)

        # Test default metadata stuff
        assert created_hda_1.visible

        # Since discover_datasets not specified, older name based pattern
        # didn't result in a dbkey being set.
        assert created_hda_1.dbkey == "?"

    def test_collect_multiple_recurse(self):
        self._replace_output_collectors("""<output>
            <discover_datasets pattern="__name__" directory="subdir1" recurse="true" ext="txt" />
            <discover_datasets pattern="__name__" directory="subdir2" recurse="true" ext="txt" />
        </output>""")
        path1 = self._setup_extra_file(filename="test1", subdir="subdir1")
        path2 = self._setup_extra_file(filename="test2", subdir="subdir2/nested1/")
        path3 = self._setup_extra_file(filename="test3", subdir="subdir2")

        datasets = self._collect()
        assert DEFAULT_TOOL_OUTPUT in datasets
        assert len(datasets[DEFAULT_TOOL_OUTPUT]) == 3

        # Test default order of collection.
        assert list(datasets[DEFAULT_TOOL_OUTPUT].keys()) == ["test1", "test2", "test3"]

        created_hda_1 = datasets[DEFAULT_TOOL_OUTPUT]["test1"]
        assert_created_with_path(self.app.object_store, created_hda_1.dataset, path1)

        created_hda_2 = datasets[DEFAULT_TOOL_OUTPUT]["test2"]
        assert_created_with_path(self.app.object_store, created_hda_2.dataset, path2)

        created_hda_3 = datasets[DEFAULT_TOOL_OUTPUT]["test3"]
        assert_created_with_path(self.app.object_store, created_hda_3.dataset, path3)

    def test_collect_multiple_recurse_dict(self):
        self._replace_output_collectors_from_dict(
            {
                "discover_datasets": [
                    {
                        "pattern": "__name__",
                        "directory": "subdir1",
                        "recurse": True,
                        "format": "txt",
                    },
                    {
                        "pattern": "__name__",
                        "directory": "subdir2",
                        "recurse": True,
                        "format": "txt",
                    },
                ]
            }
        )
        path1 = self._setup_extra_file(filename="test1", subdir="subdir1")
        path2 = self._setup_extra_file(filename="test2", subdir="subdir2/nested1/")
        path3 = self._setup_extra_file(filename="test3", subdir="subdir2")

        datasets = self._collect()
        assert DEFAULT_TOOL_OUTPUT in datasets
        assert len(datasets[DEFAULT_TOOL_OUTPUT]) == 3

        # Test default order of collection.
        assert list(datasets[DEFAULT_TOOL_OUTPUT].keys()) == ["test1", "test2", "test3"]

        created_hda_1 = datasets[DEFAULT_TOOL_OUTPUT]["test1"]
        assert_created_with_path(self.app.object_store, created_hda_1.dataset, path1)

        created_hda_2 = datasets[DEFAULT_TOOL_OUTPUT]["test2"]
        assert_created_with_path(self.app.object_store, created_hda_2.dataset, path2)

        created_hda_3 = datasets[DEFAULT_TOOL_OUTPUT]["test3"]
        assert_created_with_path(self.app.object_store, created_hda_3.dataset, path3)

    def test_collect_collection_default_format(self):
        self._replace_output_collectors("""<dataset_collection name="parent" format="abcdef">
            <discover_datasets pattern="__name__" directory="subdir_for_name_discovery" sort_by="reverse_filename" />
        </dataset_collection>""")
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="test1")
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="test2")

        datasets = self._collect()
        assert DEFAULT_TOOL_OUTPUT in datasets
        for dataset in datasets[DEFAULT_TOOL_OUTPUT].values():
            assert dataset.ext == "abcdef"

    def test_collect_sorted_reverse(self):
        self._replace_output_collectors("""<output>
            <discover_datasets pattern="__name__" directory="subdir_for_name_discovery" sort_by="reverse_filename" ext="txt" />
        </output>""")
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="test1")
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="test2")

        datasets = self._collect()
        assert DEFAULT_TOOL_OUTPUT in datasets

        # Test default order of collection.
        assert list(datasets[DEFAULT_TOOL_OUTPUT].keys()) == ["test2", "test1"]

    def test_collect_sorted_name(self):
        self._replace_output_collectors("""<output>
            <discover_datasets pattern="[abc](?P&lt;name&gt;.*)" directory="subdir_for_name_discovery" sort_by="name" ext="txt" />
        </output>""")
        # Setup filenames in reverse order and ensure name is used as key.
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="ctest1")
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="btest2")
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="atest3")

        datasets = self._collect()
        assert DEFAULT_TOOL_OUTPUT in datasets

        # Test default order of collection.
        assert list(datasets[DEFAULT_TOOL_OUTPUT].keys()) == ["test1", "test2", "test3"]

    def test_collect_sorted_numeric(self):
        self._replace_output_collectors("""<output>
            <discover_datasets pattern="[abc](?P&lt;name&gt;.*)" directory="subdir_for_name_discovery" sort_by="numeric_name" ext="txt" />
        </output>""")
        # Setup filenames in reverse order and ensure name is used as key.
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="c1")
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="b10")
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="a100")

        datasets = self._collect()
        assert DEFAULT_TOOL_OUTPUT in datasets

        # Test default order of collection.
        assert list(datasets[DEFAULT_TOOL_OUTPUT].keys()) == ["1", "10", "100"]

    def test_collect_hidden(self):
        self._setup_extra_file(visible="hidden")
        created_hda = self._collect_default_extra()
        assert not created_hda.visible

    def test_collect_ext(self):
        self._setup_extra_file(ext="txt")
        created_hda = self._collect_default_extra()
        assert created_hda.ext == "txt"

    def test_copied_to_imported_histories(self):
        self._setup_extra_file()
        cloned_hda = self.hda.copy()
        history_2 = self._new_history(hdas=[cloned_hda])
        assert len(history_2.datasets) == 1

        self._collect()
        self.app.model.context.flush()

        # Make sure extra primary was copied to cloned history with
        # cloned output.
        assert len(history_2.datasets) == 2

    def test_dbkey_from_filename(self):
        self._setup_extra_file(dbkey="hg19")
        created_hda = self._collect_default_extra()
        assert created_hda.dbkey == "hg19"

    def test_dbkey_from_galaxy_json(self):
        path = self._setup_extra_file()
        self._append_job_json(dict(dbkey="hg19"), output_path=path)
        created_hda = self._collect_default_extra()
        assert created_hda.dbkey == "hg19"

    def test_name_from_galaxy_json(self):
        path = self._setup_extra_file()
        self._append_job_json(dict(name="test_from_json"), output_path=path)
        created_hda = self._collect_default_extra()
        assert "test_from_json" in created_hda.name

    def test_info_from_galaxy_json(self):
        path = self._setup_extra_file()
        self._append_job_json(dict(info="extra output info"), output_path=path)
        created_hda = self._collect_default_extra()
        assert created_hda.info == "extra output info"

    def test_extension_from_galaxy_json(self):
        path = self._setup_extra_file()
        self._append_job_json(dict(ext="txt"), output_path=path)
        created_hda = self._collect_default_extra()
        assert created_hda.ext == "txt"

    def test_job_param(self):
        self._setup_extra_file()
        assert len(self.job.output_datasets) == 1
        self._collect_default_extra()
        assert len(self.job.output_datasets) == 2
        extra_job_assoc = [job_assoc for job_assoc in self.job.output_datasets if job_assoc.name.startswith("__")][0]
        assert extra_job_assoc.name == "__new_primary_file_out1|test1__"

    def test_pattern_override_designation(self):
        self._replace_output_collectors(
            """<output><discover_datasets pattern="__designation__" directory="subdir" ext="txt" /></output>"""
        )
        self._setup_extra_file(subdir="subdir", filename="foo.txt")
        primary_outputs = self._collect()[DEFAULT_TOOL_OUTPUT]
        assert len(primary_outputs) == 1
        created_hda = next(iter(primary_outputs.values()))
        assert "foo.txt" in created_hda.name
        assert created_hda.ext == "txt"
        assert created_hda.dbkey == "btau"
        assert created_hda.dbkey == "btau"

    def test_name_and_ext_pattern(self):
        self._replace_output_collectors(
            """<output><discover_datasets pattern="__name_and_ext__" directory="subdir" /></output>"""
        )
        self._setup_extra_file(subdir="subdir", filename="foo1.txt")
        self._setup_extra_file(subdir="subdir", filename="foo2.tabular")
        primary_outputs = self._collect()[DEFAULT_TOOL_OUTPUT]
        assert len(primary_outputs) == 2
        assert primary_outputs["foo1"].ext == "txt"
        assert primary_outputs["foo2"].ext == "tabular"
        assert primary_outputs["foo1"].dbkey == "btau"
        assert primary_outputs["foo2"].dbkey == "btau"

    def test_custom_pattern(self):
        # Hypothetical oral metagenomic classifier that populates a directory
        # of files based on name and genome. Use custom regex pattern to grab
        # and classify these files.
        self._replace_output_collectors(
            """<output><discover_datasets pattern="(?P&lt;designation&gt;.*)__(?P&lt;dbkey&gt;.*).fasta" directory="genome_breakdown" ext="fasta" /></output>"""
        )
        self._setup_extra_file(subdir="genome_breakdown", filename="samp1__hg19.fasta")
        self._setup_extra_file(subdir="genome_breakdown", filename="samp2__lactLact.fasta")
        self._setup_extra_file(subdir="genome_breakdown", filename="samp3__hg19.fasta")
        self._setup_extra_file(subdir="genome_breakdown", filename="samp4__lactPlan.fasta")
        self._setup_extra_file(subdir="genome_breakdown", filename="samp5__fusoNucl.fasta")

        # Put a file in directory we don't care about, just to make sure
        # it doesn't get picked up by pattern.
        self._setup_extra_file(subdir="genome_breakdown", filename="overview.txt")

        primary_outputs = self._collect()[DEFAULT_TOOL_OUTPUT]
        assert len(primary_outputs) == 5
        genomes = dict(
            samp1="hg19",
            samp2="lactLact",
            samp3="hg19",
            samp4="lactPlan",
            samp5="fusoNucl",
        )
        for key, hda in primary_outputs.items():
            assert hda.dbkey == genomes[key]

    def test_custom_pattern_dict(self):
        self._replace_output_collectors_from_dict(
            {
                "discover_datasets": {
                    "pattern": "(?P<designation>.*)__(?P<dbkey>.*).fasta",
                    "directory": "genome_breakdown",
                    "format": "fasta",
                }
            }
        )

        self._setup_extra_file(subdir="genome_breakdown", filename="samp1__hg19.fasta")
        self._setup_extra_file(subdir="genome_breakdown", filename="samp2__lactLact.fasta")
        self._setup_extra_file(subdir="genome_breakdown", filename="samp3__hg19.fasta")
        self._setup_extra_file(subdir="genome_breakdown", filename="samp4__lactPlan.fasta")
        self._setup_extra_file(subdir="genome_breakdown", filename="samp5__fusoNucl.fasta")

        # Put a file in directory we don't care about, just to make sure
        # it doesn't get picked up by pattern.
        self._setup_extra_file(subdir="genome_breakdown", filename="overview.txt")

        primary_outputs = self._collect()[DEFAULT_TOOL_OUTPUT]
        assert len(primary_outputs) == 5
        genomes = dict(
            samp1="hg19",
            samp2="lactLact",
            samp3="hg19",
            samp4="lactPlan",
            samp5="fusoNucl",
        )
        for key, hda in primary_outputs.items():
            assert hda.dbkey == genomes[key]

    def test_name_versus_designation(self):
        """This test demonstrates the difference between name and desgination
        in grouping patterns and named patterns such as __designation__,
        __name__, __designation_and_ext__, and __name_and_ext__.
        """
        self._replace_output_collectors("""<output>
            <discover_datasets pattern="__name_and_ext__" directory="subdir_for_name_discovery" />
            <discover_datasets pattern="__designation_and_ext__" directory="subdir_for_designation_discovery" />
        </output>""")
        self._setup_extra_file(subdir="subdir_for_name_discovery", filename="example1.txt")
        self._setup_extra_file(subdir="subdir_for_designation_discovery", filename="example2.txt")
        primary_outputs = self._collect()[DEFAULT_TOOL_OUTPUT]
        name_output = primary_outputs["example1"]
        designation_output = primary_outputs["example2"]
        # While name is also used for designation, designation is not the name -
        # it is used in the calculation of the name however...
        assert name_output.name == "example1"
        assert designation_output.name == "{} ({})".format(self.hda.name, "example2")

    def test_cannot_read_files_outside_job_directory(self):
        self._replace_output_collectors("""<output>
            <discover_datasets pattern="__name_and_ext__" directory="../../secrets" />
        </output>""")
        with self.assertRaises(InvalidDiscoveredFilePathError):
            self._collect()

    def test_tool_provided_metadata_cannot_read_traversing_filename(self):
        with tempfile.TemporaryDirectory(dir=os.path.dirname(self.test_directory)) as outside_directory:
            outside_path = os.path.join(outside_directory, "sentinel.txt")
            self._setup_extra_file(path=outside_path)
            filename = os.path.relpath(outside_path, self.test_directory)

            with self.assertRaises(InvalidDiscoveredFilePathError):
                self._collect_tool_provided_dataset(filename)

    def test_tool_provided_metadata_cannot_read_absolute_filename(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            outside_path = os.path.join(outside_directory, "sentinel.txt")
            self._setup_extra_file(path=outside_path)

            with self.assertRaises(InvalidDiscoveredFilePathError):
                self._collect_tool_provided_dataset(outside_path)

    def test_tool_provided_metadata_cannot_read_symlinked_filename(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            outside_path = os.path.join(outside_directory, "sentinel.txt")
            self._setup_extra_file(path=outside_path)
            filename = "symlinked-output.txt"
            os.symlink(outside_path, os.path.join(self.test_directory, filename))

            with self.assertRaises(InvalidDiscoveredFilePathError):
                self._collect_tool_provided_dataset(filename)

    def test_pattern_discovery_cannot_read_symlinked_filename(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            outside_path = os.path.join(outside_directory, "sentinel.txt")
            self._setup_extra_file(path=outside_path)
            filename = f"primary_{self.hda.id}_symlink_visible_data"
            os.symlink(outside_path, os.path.join(self.test_directory, filename))

            with self.assertRaises(InvalidDiscoveredFilePathError):
                self._collect()

    def test_tool_provided_metadata_cannot_read_external_extra_files(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            self._setup_extra_file(filename="sentinel.txt", directory=outside_directory)
            self._assert_tool_provided_metadata_rejects_extra_files(outside_directory)

    def test_tool_provided_metadata_cannot_read_traversing_extra_files(self):
        with tempfile.TemporaryDirectory(dir=os.path.dirname(self.test_directory)) as outside_directory:
            self._setup_extra_file(filename="sentinel.txt", directory=outside_directory)
            extra_files = os.path.relpath(outside_directory, self.test_directory)
            self._assert_tool_provided_metadata_rejects_extra_files(extra_files)

    def test_tool_provided_metadata_cannot_read_symlinked_extra_files(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            self._setup_extra_file(filename="sentinel.txt", directory=outside_directory)
            extra_files = "symlinked-extra-files"
            os.symlink(outside_directory, os.path.join(self.test_directory, extra_files))
            self._assert_tool_provided_metadata_rejects_extra_files(extra_files)

    def _assert_tool_provided_metadata_rejects_extra_files(self, extra_files):
        filename = "dataset.txt"
        self._setup_extra_file(filename=filename)
        metadata = self._tool_provided_metadata(filename, extra_files=extra_files)

        with self.assertRaises(InvalidDiscoveredFilePathError):
            self._collect(tool_provided_metadata=metadata)

        object_store = cast("MockObjectStore", self.app.object_store)
        assert object_store.created_datasets == {}

    def test_tool_provided_metadata_allows_nested_filename(self):
        filename = os.path.join("nested", "dataset.txt")
        path = self._setup_extra_file(filename="dataset.txt", subdir="nested")

        dataset = self._collect_tool_provided_dataset(filename)

        assert_created_with_path(self.app.object_store, dataset.dataset, path)

    def test_tool_provided_metadata_allows_in_directory_symlink(self):
        target_path = self._setup_extra_file(filename="target.txt")
        filename = "symlinked-output.txt"
        path = os.path.join(self.test_directory, filename)
        os.symlink(target_path, path)

        dataset = self._collect_tool_provided_dataset(filename)

        assert_created_with_path(self.app.object_store, dataset.dataset, path)

    def test_installed_tool_can_create_in_working_directory_unnamed_output(self):
        path = self._setup_extra_file(filename="unnamed.txt")
        metadata = self._metadata_from_dict(
            {
                "__unnamed_outputs": [
                    {
                        "destination": {"type": "hdas"},
                        "elements": [{"filename": os.path.basename(path), "name": "unnamed"}],
                    }
                ]
            }
        )

        self._collect(tool_provided_metadata=metadata)

        object_store = cast("MockObjectStore", self.app.object_store)
        assert os.path.realpath(path) in map(os.path.realpath, object_store.created_datasets.values())

    def test_installed_tool_cannot_link_external_unnamed_output(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            outside_path = os.path.join(outside_directory, "linked.txt")
            self._setup_extra_file(path=outside_path)
            metadata = self._metadata_from_dict(
                {
                    "__unnamed_outputs": [
                        {
                            "destination": {"type": "hdas"},
                            "elements": [
                                {
                                    "filename": outside_path,
                                    "link_data_only": True,
                                    "name": "linked output",
                                }
                            ],
                        }
                    ]
                }
            )

            with self.assertRaises(ExternalOutputPathNotAllowedError):
                self._collect(tool_provided_metadata=metadata)

    def test_tool_without_unnamed_outputs_capability_is_rejected(self):
        self.tool.allows_unnamed_outputs = False
        path = self._setup_extra_file(filename="unnamed.txt")
        metadata = self._metadata_from_dict(
            {
                "__unnamed_outputs": [
                    {
                        "destination": {"type": "hdas"},
                        "elements": [{"filename": os.path.basename(path), "name": "unnamed"}],
                    }
                ]
            }
        )

        with self.assertRaises(UntrustedToolProvidedMetadataError):
            self._collect(tool_provided_metadata=metadata)

        object_store = cast("MockObjectStore", self.app.object_store)
        assert object_store.created_datasets == {}

    def test_data_fetch_can_link_unnamed_output(self):
        self._mark_as_data_fetch()
        with tempfile.TemporaryDirectory() as outside_directory:
            outside_path = os.path.join(outside_directory, "linked.txt")
            self._setup_extra_file(path=outside_path)
            metadata = self._metadata_from_dict(
                {
                    "__unnamed_outputs": [
                        {
                            "destination": {"type": "hdas"},
                            "elements": [
                                {
                                    "filename": outside_path,
                                    "link_data_only": True,
                                    "name": "linked output",
                                }
                            ],
                        }
                    ]
                }
            )

            with self._disk_object_store():
                self._collect(tool_provided_metadata=metadata)

            session = self.app.model.context
            session.commit()
            linked_dataset = session.execute(
                select(model.HistoryDatasetAssociation).where(
                    model.HistoryDatasetAssociation.history_id == self.history.id,
                    model.HistoryDatasetAssociation.name == "linked output",
                )
            ).scalar_one()
            assert linked_dataset.get_file_name() == outside_path
            assert linked_dataset.dataset
            assert not linked_dataset.dataset.purgable

    def test_data_fetch_can_link_external_collection_element(self):
        self._mark_as_data_fetch()
        linked_collection = self._setup_hdca("linked collection")
        with tempfile.TemporaryDirectory() as outside_directory:
            outside_path = os.path.join(outside_directory, "linked.txt")
            self._setup_extra_file(path=outside_path)
            metadata = self._metadata_from_dict(
                {
                    "__unnamed_outputs": [
                        {
                            "destination": {
                                "type": "hdca",
                                "object_id": linked_collection.id,
                            },
                            "name": "linked collection",
                            "collection_type": "list",
                            "elements": [
                                {
                                    "filename": outside_path,
                                    "link_data_only": True,
                                    "name": "linked output",
                                }
                            ],
                        }
                    ]
                }
            )

            with self._disk_object_store():
                self._collect(tool_provided_metadata=metadata)

            linked_dataset = linked_collection.collection.elements[0].dataset_instance
            assert linked_dataset
            assert linked_dataset.get_file_name() == outside_path
            assert not linked_dataset.dataset.purgable

    def test_dynamic_tool_cannot_spoof_data_fetch_collection_link(self):
        self._mark_as_data_fetch(dynamic_tool_id=1)
        linked_collection = self._setup_hdca("linked collection")
        with tempfile.TemporaryDirectory() as outside_directory:
            outside_path = os.path.join(outside_directory, "linked.txt")
            self._setup_extra_file(path=outside_path)
            metadata = self._metadata_from_dict(
                {
                    "__unnamed_outputs": [
                        {
                            "destination": {
                                "type": "hdca",
                                "object_id": linked_collection.id,
                            },
                            "name": "linked collection",
                            "collection_type": "list",
                            "elements": [
                                {
                                    "filename": outside_path,
                                    "link_data_only": True,
                                    "name": "linked output",
                                }
                            ],
                        }
                    ]
                }
            )

            with self.assertRaises(ExternalOutputPathNotAllowedError):
                self._collect(tool_provided_metadata=metadata)

    def test_data_fetch_collection_allows_deferred_element(self):
        self._mark_as_data_fetch()
        deferred_collection = self._setup_hdca("deferred collection")
        metadata = self._metadata_from_dict(
            {
                "__unnamed_outputs": [
                    {
                        "destination": {
                            "type": "hdca",
                            "object_id": deferred_collection.id,
                        },
                        "name": "deferred collection",
                        "collection_type": "list",
                        "elements": [
                            {
                                "state": "deferred",
                                "name": "deferred output",
                                "ext": "txt",
                                "src": "url",
                                "url": "https://example.org/deferred.txt",
                            }
                        ],
                    }
                ]
            }
        )

        with self._distributed_object_store():
            self._collect(tool_provided_metadata=metadata)

        deferred_dataset = deferred_collection.collection.elements[0].dataset_instance
        assert deferred_dataset
        assert deferred_dataset.state == model.Dataset.states.DEFERRED
        assert deferred_dataset.dataset
        assert deferred_dataset.dataset.object_store_id is not None
        assert deferred_dataset.dataset.extra_files_path_name is not None

    def _collect_default_extra(self, **kwargs):
        collected = self._collect(**kwargs)
        assert DEFAULT_TOOL_OUTPUT in collected, f"No such key [{DEFAULT_TOOL_OUTPUT}], in {collected}"
        output_files = collected[DEFAULT_TOOL_OUTPUT]
        assert DEFAULT_EXTRA_NAME in output_files, f"No such key [{DEFAULT_EXTRA_NAME}]"
        return output_files[DEFAULT_EXTRA_NAME]

    def _collect_tool_provided_dataset(self, filename):
        metadata = self._tool_provided_metadata(filename)
        collected = self._collect(tool_provided_metadata=metadata)
        return collected[DEFAULT_TOOL_OUTPUT]["discovered"]

    def _tool_provided_metadata(self, filename, **dataset_attributes):
        self._replace_output_collectors("""<output>
            <discover_datasets discover_via="tool_provided_metadata" />
        </output>""")
        dataset = {
            "filename": filename,
            "name": "discovered",
            "designation": "discovered",
            "ext": "txt",
            **dataset_attributes,
        }
        return self._metadata_from_dict({DEFAULT_TOOL_OUTPUT: {"datasets": [dataset]}})

    def _metadata_from_dict(self, metadata):
        meta_file = os.path.join(self.test_directory, "tool_provided_metadata.json")
        with open(meta_file, "w") as f:
            json.dump(metadata, f)
        return ToolProvidedMetadata(meta_file)

    def _collect(self, job_working_directory=None, tool_provided_metadata=None):
        if not job_working_directory:
            job_working_directory = self.test_directory
        if tool_provided_metadata is None:
            meta_file = os.path.join(self.test_directory, "galaxy.json")
            if not os.path.exists(meta_file):
                tool_provided_metadata = NullToolProvidedMetadata()
            else:
                tool_provided_metadata = LegacyToolProvidedMetadata(meta_file)

        return self.tool.discover_outputs(
            self.outputs,
            {},
            tool_provided_metadata,
            job_working_directory,
            job=self.job,
            input_ext="txt",
            input_dbkey="btau",
            inp_data={},
        )

    def _replace_output_collectors(self, xml_str):
        # Rewrite tool as if it had been created with output containing
        # supplied dataset_collector elem.
        elem = util.parse_xml_string(xml_str)
        self.tool.outputs[DEFAULT_TOOL_OUTPUT].dataset_collector_descriptions = (
            output_collection_def.dataset_collector_descriptions_from_elem(elem)
        )

    def _replace_output_collectors_from_dict(self, output_dict):
        self.tool.outputs[DEFAULT_TOOL_OUTPUT].dataset_collector_descriptions = (
            output_collection_def.dataset_collector_descriptions_from_output_dict(output_dict)
        )

    def _append_job_json(self, object, output_path=None, line_type="new_primary_dataset"):
        object["type"] = line_type
        if output_path:
            name = os.path.basename(output_path)
            object["filename"] = name
        line = json.dumps(object)
        with open(os.path.join(self.test_directory, "galaxy.json"), "a") as f:
            f.write(f"{line}\n")

    def _setup_extra_file(self, **kwargs):
        path = kwargs.get("path", None)
        filename = kwargs.get("filename", None)
        if not path and not filename:
            name = kwargs.get("name", DEFAULT_EXTRA_NAME)
            visible = kwargs.get("visible", "visible")
            ext = kwargs.get("ext", "data")
            directory = kwargs.get("directory", self.test_directory)
            path = os.path.join(directory, f"primary_{self.hda.id}_{name}_{visible}_{ext}")
            if "dbkey" in kwargs:
                path = "{}_{}".format(path, kwargs["dbkey"])
        if not path:
            assert filename
            subdir = kwargs.get("subdir", ".")
            path = os.path.join(self.test_directory, subdir, filename)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        contents = kwargs.get("contents", "test contents")
        open(path, "w").write(contents)
        return path

    def _setup_test_output(self):
        dataset = model.Dataset()
        dataset.external_filename = "example_output"  # This way object store isn't asked about size...
        self.hda = model.HistoryDatasetAssociation(name="test", dataset=dataset)
        job = model.Job()
        job.add_output_dataset(DEFAULT_TOOL_OUTPUT, self.hda)
        self.app.model.context.add(job)
        self.job = job
        self.history = self._new_history(hdas=[self.hda])
        self.job.history = self.history
        self.outputs = {DEFAULT_TOOL_OUTPUT: self.hda}

    def _setup_hdca(self, name):
        collection = model.DatasetCollection(collection_type="list", populated=False)
        hdca = model.HistoryDatasetCollectionAssociation(name=name, history=self.history, collection=collection)
        self.app.model.context.add(hdca)
        self.app.model.context.commit()
        return hdca

    def _mark_as_data_fetch(self, dynamic_tool_id=None):
        self.tool.old_id = "__DATA_FETCH__"
        self.tool.dynamic_tool_id = dynamic_tool_id
        self.job.tool_id = "__DATA_FETCH__"
        self.job.dynamic_tool_id = dynamic_tool_id

    @contextmanager
    def _disk_object_store(self):
        with self._real_object_store(DISK_TEST_CONFIG):
            yield

    @contextmanager
    def _distributed_object_store(self):
        with self._real_object_store(get_object_store_example("distributed_disk.xml")):
            yield

    @contextmanager
    def _real_object_store(self, config):
        original_object_store = self.app.object_store
        with ObjectStoreTestConfig(config, store_by="uuid") as (_directory, object_store):
            self.app.object_store = object_store
            model.Dataset.object_store = object_store
            try:
                yield
            finally:
                self.app.object_store = original_object_store
                model.Dataset.object_store = original_object_store

    def _new_history(self, hdas=None, flush=True):
        hdas = hdas or []
        history = model.History()
        session = self.app.model.context
        session.add(history)
        for hda in hdas:
            history.add_dataset(hda, set_hid=False)
        session.commit()
        return history


class MockObjectStore:
    def __init__(self):
        self.created_datasets = {}

    def get_store_by(self, obj, **kwargs):
        return "uuid"

    def update_from_file(self, dataset, file_name, create):
        if create:
            self.created_datasets[dataset] = file_name

    def size(self, dataset):
        path = self.created_datasets[dataset]
        return os.stat(path).st_size

    def exists(self, *args, **kwargs):
        return True

    def get_filename(self, dataset, **kwargs):
        return self.created_datasets[dataset]


def assert_created_with_path(object_store, dataset, file_name):
    assert object_store.created_datasets[dataset] == file_name
