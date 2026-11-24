"""Which outputs a tool state gives, and their name, format, visibility and collection structure.

Pins what ``DefaultToolAction.execute`` creates, and what the output planner describes without
creating anything. Uses the tools in ``test/functional/tools``."""

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
from galaxy.tools.output_planning import PlannedOutput
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


class ToolOutputsTestCase(TestCase, tools_support.UsesTools):
    def setUp(self):
        self.setup_app()
        self.app.object_store = cast(BaseObjectStore, MockObjectStore())
        self.app.dataset_collection_manager = self.app[DatasetCollectionManager]
        self.history = model.History()
        self.trans = MockTrans(self.app, self.history)
        self.app.model.context.add(self.history)
        self.app.model.context.commit()

    def _execute(self, tool_file: str, incoming: dict[str, Any]):
        tool = self._init_tool_for_path(functional_test_tool_path(tool_file))
        job, out_data, *_ = DefaultToolAction().execute(
            tool=tool,
            trans=cast(ProvidesHistoryContext, self.trans),
            history=self.history,
            incoming=incoming,
        )
        return job, out_data

    def _planned(self, tool_file: str, incoming: dict[str, Any]) -> list[PlannedOutput]:
        tool = self._init_tool_for_path(functional_test_tool_path(tool_file))
        tool_action = cast(DefaultToolAction, tool.tool_action)
        planner = tool_action.preview_output_planner(
            cast(ProvidesHistoryContext, self.trans), tool, incoming, self.history
        )
        return planner.planned_outputs()

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


class TestToolActionOutputs(ToolOutputsTestCase):

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


class TestPreviewOutputPlanner(ToolOutputsTestCase):
    def test_describes_outputs_without_creating_anything(self):
        incoming = {
            "input_data_1": self._dataset("fasta"),
            "input_data_2": self._dataset("tabular"),
            "input_text": "bar",
        }
        rows_before = self._row_counts()

        planned = self._planned("output_format.xml", incoming)

        label = "output_format on dataset 1 and 2"
        assert planned == [
            PlannedOutput("direct_output", label, "data", format="txt"),
            PlannedOutput("input_based_output", label, "data", format="fasta"),
            PlannedOutput("format_source_1_output", label, "data", format="fasta", format_source="input_data_1"),
            PlannedOutput("format_source_2_output", label, "data", format="tabular", format_source="input_data_2"),
            PlannedOutput("change_format_output", label, "data", format="fastqillumina"),
        ]
        assert self._row_counts() == rows_before

    def test_format_input_since_profile_16_04_is_left_to_the_job(self):
        planned = self._planned("output_format_input.xml", {"input": self._dataset("tabular")})

        assert planned == [PlannedOutput("output", "output_format_input on dataset 1", "data", format=None)]

    def test_format_changed_by_actions_is_left_to_the_job(self):
        incoming = {
            "input_cond": {"__current_case__": 1, "dispatch": "do", "input": self._dataset("tabular")},
            "asection": {"abool": True},
        }

        planned = self._planned("output_action_change_format.xml", incoming)

        assert planned == [PlannedOutput("out1", "output_action_change_format on dataset 1", "data", format=None)]

    def test_hidden_output_that_discovers_datasets(self):
        planned = self._planned("discover_metadata_files.xml", {"input_bam": self._dataset("bam")})

        assert planned == [
            PlannedOutput("bam_output", "discovered bam", "data", format="txt", hidden=True, dynamic=True)
        ]

    def test_static_collection_with_mixed_formats(self):
        planned = self._planned("collection_creates_pair.xml", {"input1": self._dataset("tabular")})

        assert planned == [
            PlannedOutput("paired_output", "Split Pair", "collection", collection_type="paired", element_count=2)
        ]

    def test_structured_like_collection(self):
        planned = self._planned("collection_paired_structured_like.xml", {"input1": self._pair()})

        # inherit_format gives the elements txt and fasta, so the collection has no single format
        assert planned == [
            PlannedOutput("list_output", "Duplicate List", "collection", collection_type="paired", element_count=2)
        ]

    def test_type_source_collection_discovers_its_elements(self):
        incoming = {"header": self._dataset("tabular"), "input_collect": self._pair()}

        planned = self._planned("collection_type_source.xml", incoming)

        assert planned == [
            PlannedOutput("list_output", "Duplicate List", "collection", collection_type="paired", dynamic=True)
        ]

    def test_expression_output(self):
        planned = self._planned("expression_forty_two.xml", {})

        assert planned == [PlannedOutput("out1", "expression_forty_two", "parameter")]

    def _row_counts(self) -> dict[str, int]:
        session = self.app.model.context
        return {
            model_class.__name__: session.query(model_class).count()
            for model_class in (model.Job, model.HistoryDatasetAssociation, model.HistoryDatasetCollectionAssociation)
        }


class _SingleToolToolbox:
    def __init__(self, tool):
        self.tool = tool

    def get_tool(self, tool_id, exact=False):
        return self.tool


class TestRerunRemap(ToolOutputsTestCase):
    def setUp(self):
        super().setUp()
        user = model.User(email="remap@example.org", password="password")
        self.app.model.context.add(user)
        self.app.model.context.commit()
        self.trans.user = user
        # The remap only asks the toolbox whether old and new job ran the same tool.
        tool = self._init_tool_for_path(functional_test_tool_path("environment_variables.xml"))
        self.app._toolbox = cast(Any, _SingleToolToolbox(tool))

    @pytest.mark.parametrize(
        "of_workflow, expected_actions",
        [
            # Runtime actions of a workflow run have no workflow step; the rerun keeps them.
            (True, ["DeleteDatasetAction"]),
            # The changes asked for a tool run come with the rerun request instead.
            (False, []),
        ],
    )
    def test_rerun_takes_over_the_post_job_actions_of_a_workflow_job(self, of_workflow, expected_actions):
        old_job, _ = self._execute("environment_variables.xml", {"inttest": "1"})
        old_job.add_post_job_action(model.PostJobAction("DeleteDatasetAction", output_name="out_file1"))
        if of_workflow:
            workflow = model.Workflow()
            workflow_step = model.WorkflowStep()
            workflow_step.order_index = 0
            workflow.steps = [workflow_step]
            invocation = model.WorkflowInvocation()
            invocation.workflow = workflow
            invocation.history = self.history
            invocation_step = model.WorkflowInvocationStep()
            invocation_step.workflow_invocation = invocation
            invocation_step.workflow_step = workflow_step
            invocation_step.job = old_job
            self.app.model.context.add(invocation_step)
        self.app.model.context.commit()
        new_job, out_data = self._execute("environment_variables.xml", {"inttest": "2"})

        DefaultToolAction()._remap_job_on_rerun(
            cast(ProvidesHistoryContext, self.trans), None, old_job.id, new_job, out_data
        )

        self.app.model.context.commit()
        self.app.model.context.refresh(new_job)
        assert [pjaa.post_job_action.action_type for pjaa in new_job.post_job_actions] == expected_actions
