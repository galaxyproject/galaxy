"""Which outputs ``DefaultToolAction.execute`` creates for a tool state, and their name, format,
visibility and collection structure. Uses the tools in ``test/functional/tools``."""

from typing import (
    Any,
    cast,
)

import pytest

from galaxy import model
from galaxy.app_unittest_utils import tools_support
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.objectstore import BaseObjectStore
from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.tools.actions import DefaultToolAction
from galaxy.util.unittest import TestCase
from .test_actions import (
    MockObjectStore,
    MockTrans,
)

OUTPUT_FILTER_DEFAULTS = {
    "produce_out_1": False,
    "filter_text_1": "1",
    "produce_collection": False,
    "produce_paired_collection": False,
    "repeat": [],
}
REPEAT_MATCHING_FILTER = [{"cond": {"select": "a", "inner_cond": {"inner_select": "2", "text": "x"}}}]


class TestToolActionOutputs(TestCase, tools_support.UsesTools):
    def setUp(self):
        self.setup_app()
        self.app.object_store = cast(BaseObjectStore, MockObjectStore())
        self.app.dataset_collection_manager = self.app[DatasetCollectionManager]
        self.history = model.History()
        self.trans = MockTrans(self.app, self.history)
        self.app.model.context.add(self.history)
        self.app.model.context.commit()

    @pytest.mark.parametrize(
        "state, expected_datasets, expected_collections",
        [
            pytest.param({}, [], [], id="all_filtered_by_default"),
            pytest.param({"produce_out_1": True}, ["out_1"], [], id="boolean_filter"),
            pytest.param({"filter_text_1": "bar"}, [], [], id="one_of_two_filters_passes"),
            pytest.param({"filter_text_1": "foo"}, ["out_2"], [], id="both_filters_pass"),
            pytest.param({"repeat": REPEAT_MATCHING_FILTER}, ["repeat_cond_output"], [], id="filter_on_repeat"),
            pytest.param({"produce_collection": True}, [], ["list_output"], id="collection_filter"),
        ],
    )
    def test_filters_decide_which_outputs_are_created(self, state, expected_datasets, expected_collections):
        job, out_data = self._execute("output_filter.xml", {**OUTPUT_FILTER_DEFAULTS, **state})

        assert sorted(out_data) == expected_datasets
        assert sorted(self._collections(job)) == expected_collections

    @pytest.mark.parametrize(
        "input_text, expected_changed_format",
        [
            pytest.param("foo", "fastqsolexa", id="first_when"),
            pytest.param("bar", "fastqillumina", id="second_when"),
            pytest.param("1", "txt", id="no_when_matches"),
        ],
    )
    def test_output_formats(self, input_text, expected_changed_format):
        incoming = {
            "input_data_1": self._dataset("fasta"),
            "input_data_2": self._dataset("tabular"),
            "input_text": input_text,
        }
        _, out_data = self._execute("output_format.xml", incoming)

        assert {name: data.extension for name, data in out_data.items()} == {
            "direct_output": "txt",
            # format="input" on a tool with profile < 16.04 takes the first data input's format
            "input_based_output": "fasta",
            "format_source_1_output": "fasta",
            "format_source_2_output": "tabular",
            "change_format_output": expected_changed_format,
        }

    def test_format_input_is_kept_literally_since_profile_16_04(self):
        _, out_data = self._execute("output_format_input.xml", {"input": self._dataset("tabular")})

        assert out_data["output"].extension == "input"

    def test_hidden_output_is_created_invisible_with_its_label(self):
        _, out_data = self._execute("discover_metadata_files.xml", {"input_bam": self._dataset("bam")})

        bam_output = out_data["bam_output"]
        assert (bam_output.name, bam_output.extension, bam_output.visible) == ("discovered bam", "txt", False)

    def test_static_collection_output(self):
        job, out_data = self._execute("collection_creates_pair.xml", {"input1": self._dataset("tabular")})

        hdca = self._collections(job)["paired_output"]
        assert (hdca.name, hdca.collection.collection_type, hdca.collection.populated_state) == (
            "Split Pair",
            "paired",
            "ok",
        )
        assert self._elements(hdca) == {"forward": ("txt", False), "reverse": ("tabular", False)}
        assert sorted(out_data) == ["paired_output|__part__|forward", "paired_output|__part__|reverse"]

    def test_discovered_collection_output_is_created_unpopulated(self):
        job, _ = self._execute("output_filter.xml", {**OUTPUT_FILTER_DEFAULTS, "produce_collection": True})

        hdca = self._collections(job)["list_output"]
        assert (hdca.name, hdca.collection.collection_type, hdca.collection.populated_state) == ("List", "list", "new")
        assert self._elements(hdca) == {}

    def test_structured_like_collection_copies_input_structure(self):
        job, _ = self._execute("collection_paired_structured_like.xml", {"input1": self._pair()})

        hdca = self._collections(job)["list_output"]
        assert (hdca.name, hdca.collection.collection_type) == ("Duplicate List", "paired")
        # inherit_format: each element takes the format of the matching input element
        assert self._elements(hdca) == {"forward": ("txt", False), "reverse": ("fasta", False)}

    def test_type_source_collection_takes_input_collection_type(self):
        incoming = {"header": self._dataset("tabular"), "input_collect": self._pair()}
        job, _ = self._execute("collection_type_source.xml", incoming)

        hdca = self._collections(job)["list_output"]
        assert (hdca.name, hdca.collection.collection_type, hdca.collection.populated_state) == (
            "Duplicate List",
            "paired",
            "new",
        )

    def _execute(self, tool_file: str, incoming: dict[str, Any]):
        tool = self._init_tool_for_path(functional_test_tool_path(tool_file))
        job, out_data, *_ = DefaultToolAction().execute(
            tool=tool,
            trans=cast(ProvidesHistoryContext, self.trans),
            history=self.history,
            incoming=incoming,
        )
        return job, out_data

    def _collections(self, job: model.Job) -> dict[str, model.HistoryDatasetCollectionAssociation]:
        return {assoc.name: assoc.dataset_collection_instance for assoc in job.output_dataset_collection_instances}

    def _elements(self, hdca: model.HistoryDatasetCollectionAssociation) -> dict[str, tuple[str, bool]]:
        elements = {}
        for element in hdca.collection.elements:
            assert element.element_identifier and element.hda
            elements[element.element_identifier] = (element.hda.extension, element.hda.visible)
        return elements

    def _dataset(self, extension: str) -> model.HistoryDatasetAssociation:
        hda = model.HistoryDatasetAssociation(extension=extension)
        hda.dataset = model.Dataset()
        hda.dataset.state = "ok"
        self.history.add_dataset(hda)
        self.app.model.context.commit()
        return hda

    def _pair(self) -> model.HistoryDatasetCollectionAssociation:
        collection = model.DatasetCollection(collection_type="paired")
        for index, (identifier, extension) in enumerate([("forward", "txt"), ("reverse", "fasta")]):
            model.DatasetCollectionElement(
                collection=collection,
                element=self._dataset(extension),
                element_identifier=identifier,
                element_index=index,
            )
        hdca = model.HistoryDatasetCollectionAssociation(collection=collection, name="input pair")
        self.history.add_dataset_collection(hdca)
        self.app.model.context.commit()
        return hdca
