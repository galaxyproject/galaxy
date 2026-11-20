"""``POST /api/tools/outputs_preview``: the outputs a tool request would create, created by nothing."""

from typing import Any

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_tool,
    TargetHistory,
)
from ._framework import ApiTestCase


def _output(name: str, label: str | None, output_type: str, **fields: Any) -> dict[str, Any]:
    output = {
        "name": name,
        "label": label,
        "output_type": output_type,
        "format": None,
        "format_source": None,
        "collection_type": None,
        "element_count": None,
        "hidden": False,
        "dynamic": False,
        "mapped_over": False,
    }
    output.update(fields)
    return output


class TestToolOutputsPreviewApi(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.history = TargetHistory(
            self.dataset_populator, self.dataset_collection_populator, self.dataset_populator.new_history()
        )

    @skip_without_tool("output_filter")
    def test_filtered_outputs_are_left_out(self):
        inputs = {"produce_out_1": True, "filter_text_1": "foo", "produce_collection": True}

        preview = self._preview("output_filter", inputs)

        assert preview == {
            "supported": True,
            "unsupported_reason": None,
            "job_count": 1,
            # in the order a run creates them, collections first
            "outputs": [
                _output("list_output", "List", "collection", collection_type="list", dynamic=True),
                _output("out_1", "output_filter", "data", format="txt"),
                _output("out_2", "output_filter", "data", format="txt"),
            ],
        }

    @skip_without_tool("output_format")
    def test_formats_follow_inputs_and_creates_nothing(self):
        fasta = self._dataset(">seq\nACGT\n", "fasta")
        tabular = self._dataset("1\t2\n", "tabular")
        inputs = {"input_data_1": fasta, "input_data_2": tabular, "input_text": "bar"}
        history_before = self._history_state()

        preview = self._preview("output_format", inputs)

        label = "output_format on dataset 1 and 2"
        assert preview["outputs"] == [
            _output("direct_output", label, "data", format="txt"),
            # format="input" on a tool with profile < 16.04 takes the first data input's format
            _output("input_based_output", label, "data", format="fasta"),
            _output("format_source_1_output", label, "data", format="fasta", format_source="input_data_1"),
            _output("format_source_2_output", label, "data", format="tabular", format_source="input_data_2"),
            _output("change_format_output", label, "data", format="fastqillumina"),
        ]
        assert self._history_state() == history_before

    @skip_without_tool("collection_creates_pair")
    def test_map_over_list_nests_output_collection(self):
        hdca = self.history.with_list([("a", "1\n2\n"), ("b", "3\n4\n")])
        history_before = self._history_state()

        preview = self._preview(
            "collection_creates_pair", {"input1": {"__class__": "Batch", "values": [hdca.src_dict]}}
        )

        assert preview["job_count"] == 2
        assert preview["outputs"] == [
            _output(
                "paired_output",
                "Split Pair",
                "collection",
                collection_type="list:paired",
                element_count=2,
                mapped_over=True,
            )
        ]
        assert self._history_state() == history_before

    @skip_without_tool("collection_creates_pair")
    def test_map_over_empty_list(self):
        hdca = self.history.with_list([])

        preview = self._preview(
            "collection_creates_pair", {"input1": {"__class__": "Batch", "values": [hdca.src_dict]}}
        )

        assert preview["job_count"] == 0
        assert preview["outputs"] == [
            _output(
                "paired_output",
                "Split Pair",
                "collection",
                collection_type="list:paired",
                element_count=0,
                mapped_over=True,
            )
        ]

    @skip_without_tool("implicit_conversion_format_input")
    def test_format_following_input_that_needs_conversion_is_left_to_the_job(self):
        # A run converts fasta.gz to fasta first and its output is fasta.
        compressed = self.history.with_dataset_for_test_file("1.fasta.gz", file_type="fasta.gz")
        history_before = self._history_state()

        preview = self._preview("implicit_conversion_format_input", {"input1": compressed.src_dict})

        assert preview["outputs"] == [
            _output("output1", "implicit_conversion with input format on dataset 1", "data", format=None)
        ]
        assert self._history_state() == history_before

    @skip_without_tool("explicit_conversion")
    def test_input_with_explicit_conversion_creates_nothing(self):
        fasta = self._dataset(">seq\nACGT\n", "fasta")
        history_before = self._history_state()

        preview = self._preview("explicit_conversion", {"input1": fasta})

        assert preview["outputs"] == [_output("output1", "explicit_conversion on dataset 1", "data", format="tabular")]
        assert self._history_state() == history_before

    @skip_without_tool("cat_data_and_sleep")
    def test_map_over_list_collects_dataset_outputs(self):
        hdca = self.history.with_list([("a", "1\t2\n"), ("b", "3\t4\n")])
        hdca_hid = self.dataset_populator.get_history_collection_details(self.history.id, content_id=hdca.id)["hid"]

        preview = self._preview("cat_data_and_sleep", {"input1": {"__class__": "Batch", "values": [hdca.src_dict]}})

        assert preview["job_count"] == 2
        assert preview["outputs"] == [
            _output(
                "out_file1",
                f"Concatenate datasets (with sleep) on collection {hdca_hid}",
                "collection",
                # the list elements are uploaded as txt
                format="txt",
                format_source="input1",
                collection_type="list",
                element_count=2,
                mapped_over=True,
            )
        ]

    @skip_without_tool("cat_data_and_sleep")
    def test_input_from_url_is_not_described(self):
        history_before = self._history_state()
        url_input = {"src": "url", "url": "https://example.org/data.txt", "ext": "txt"}

        preview = self._preview("cat_data_and_sleep", {"input1": url_input})

        assert preview == {
            "supported": False,
            "unsupported_reason": "Outputs of runs that fetch inputs from URLs can't be described.",
            "job_count": 0,
            "outputs": [],
        }
        assert self._history_state() == history_before

    @skip_without_tool("cat_data_and_sleep")
    def test_input_still_uploading_is_described(self):
        uploading = self.dataset_populator.new_dataset(self.history.id, content="1\t2\n", file_type="tabular")

        preview = self._preview("cat_data_and_sleep", {"input1": {"src": "hda", "id": uploading["id"]}})

        assert preview["outputs"] == [
            _output(
                "out_file1",
                "Concatenate datasets (with sleep) on dataset 1",
                "data",
                format="tabular",
                format_source="input1",
            )
        ]

    @skip_without_tool("implicit_conversion_format_input")
    def test_refuses_private_dataset_of_another_user_that_needs_conversion(self):
        with self._different_user_history() as other_history_id:
            other_history = TargetHistory(self.dataset_populator, self.dataset_collection_populator, other_history_id)
            private = other_history.with_dataset_for_test_file("1.fasta.gz", file_type="fasta.gz")
            self.dataset_populator.make_private(other_history_id, private.id)

        response = self._preview_raw("implicit_conversion_format_input", {"input1": private.src_dict})

        self._assert_status_code_is(response, 403)

    @skip_without_tool("collection_creates_pair")
    def test_refuses_private_collection_of_another_user(self):
        with self._different_user_history() as other_history_id:
            other_history = TargetHistory(self.dataset_populator, self.dataset_collection_populator, other_history_id)
            private = other_history.with_list([("a", "1\n")])
            element = self.dataset_populator.get_history_collection_details(other_history_id, content_id=private.id)
            self.dataset_populator.make_private(other_history_id, element["elements"][0]["object"]["id"])

        response = self._preview_raw(
            "collection_creates_pair", {"input1": {"__class__": "Batch", "values": [private.src_dict]}}
        )

        self._assert_status_code_is(response, 403)

    @skip_without_tool("output_filter")
    def test_invalid_tool_state_is_rejected(self):
        response = self._preview_raw("output_filter", {"produce_out_1": "not a boolean"})

        self._assert_status_code_is(response, 400)

    @skip_without_tool("output_format")
    def test_refuses_private_dataset_of_another_user(self):
        with self._different_user_history() as other_history_id:
            private = self.dataset_populator.new_dataset(other_history_id, content="secret\n", wait=True)
            self.dataset_populator.make_private(other_history_id, private["id"])
        private_ref = {"src": "hda", "id": private["id"]}
        inputs = {"input_data_1": private_ref, "input_data_2": private_ref}

        response = self._preview_raw("output_format", inputs)

        self._assert_status_code_is(response, 403)

    @skip_without_tool("output_filter")
    def test_refuses_history_of_another_user(self):
        with self._different_user_history() as other_history_id:
            pass

        response = self._preview_raw("output_filter", {}, history_id=other_history_id)

        self._assert_status_code_is(response, 403)

    @skip_without_tool("__FILTER_FAILED_DATASETS__")
    def test_model_operation_outputs_are_not_described(self):
        hdca = self.history.with_list([("a", "1\n")])

        preview = self._preview("__FILTER_FAILED_DATASETS__", {"input": hdca.src_dict})

        assert preview == {
            "supported": False,
            "unsupported_reason": "The outputs of this tool can't be described before it runs.",
            "job_count": 0,
            "outputs": [],
        }

    def _preview(self, tool_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
        response = self._preview_raw(tool_id, inputs)
        self._assert_status_code_is_ok(response)
        return response.json()

    def _preview_raw(self, tool_id: str, inputs: dict[str, Any], history_id: str | None = None):
        payload = {"tool_id": tool_id, "history_id": history_id or self.history.id, "inputs": inputs}
        return self._post("tools/outputs_preview", payload, json=True)

    def _dataset(self, content: str, file_type: str) -> dict[str, str]:
        hda = self.dataset_populator.new_dataset(self.history.id, content=content, file_type=file_type, wait=True)
        return {"src": "hda", "id": hda["id"]}

    def _history_state(self) -> tuple[list[tuple[int, str]], list[str]]:
        """The history's items and jobs, to check a preview added none."""
        contents = self.dataset_populator.get_history_contents(self.history.id)
        jobs = self.dataset_populator.history_jobs(self.history.id)
        return [(item["hid"], item["history_content_type"]) for item in contents], [job["id"] for job in jobs]
