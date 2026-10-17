"""Batch (meta parameter) expansion of tool requests into per-job states."""

import copy
from typing import Any

import pytest

from galaxy import (
    exceptions,
    model,
)
from galaxy.app_unittest_utils import tools_support
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.tool_util.parameters import (
    RequestInternalDereferencedToolState,
    RequestInternalToolState,
)
from galaxy.tools.parameters.meta import (
    expand_meta_parameters,
    expand_meta_parameters_async,
    validate_matched_batch_lengths,
)
from galaxy.util.permutations import InputMatchedException
from galaxy.util.unittest import TestCase
from galaxy.work.context import WorkRequestContext

BATCH_TOOL_CONTENTS = """<tool id="batch_tool" name="Batch Tool" version="1.0">
    <command>cat "$input1" > "$out1"</command>
    <inputs>
        <param type="data" name="input1" format="txt" />
        <param type="data" name="input2" format="txt" optional="true" />
        <param type="data_collection" name="pair" collection_type="paired" optional="true" />
    </inputs>
    <outputs>
        <data name="out1" format="txt" />
    </outputs>
</tool>
"""

# Nested collection shape: an int is that many datasets, a list holds one child shape per element.
ShapeT = int | list[Any]


class TestMetaExpansion(TestCase, tools_support.UsesTools):
    def setUp(self):
        self.setup_app()
        self.app.dataset_collection_manager = self.app[DatasetCollectionManager]
        self.session = self.app.model.session
        self.user = self._user("owner")
        self.history = model.History(user=self.user)
        self.session.add(self.history)
        self.session.commit()
        self.trans = WorkRequestContext(app=self.app, user=self.user, history=self.history)
        self._init_tool(BATCH_TOOL_CONTENTS)

    def tearDown(self):
        self.tear_down_app()

    def test_hda_batch(self):
        incoming = {"input1": self._hda_batch(3)}
        self._assert_job_count(incoming, 3)

    def test_list_into_data_input(self):
        self._assert_job_count({"input1": self._hdca_batch("list", 4)}, 4)

    def test_list_list_into_data_input_counts_all_datasets(self):
        self._assert_job_count({"input1": self._hdca_batch("list:list", [3, 2])}, 5)

    def test_list_paired_mapped_over_paired(self):
        incoming = {"input1": self._hda_ref(), "pair": self._hdca_batch("list:paired", [2, 2, 2], "paired")}
        self._assert_job_count(incoming, 3)

    def test_nested_list_list_paired_mapped_over_paired(self):
        incoming = {
            "input1": self._hda_ref(),
            "pair": self._hdca_batch("list:list:paired", [[2, 2], [], [2]], "paired"),
        }
        self._assert_job_count(incoming, 3)

    def test_dce_batch(self):
        outer = self._collection("list:list", [3, 2])
        dce_value = {"src": "dce", "id": self._encode(outer.elements[0].id)}
        self._assert_job_count({"input1": {"batch": True, "values": [dce_value]}}, 3)

    def test_linked_batches_of_equal_length(self):
        incoming = {"input1": self._hdca_batch("list", 3), "input2": self._hda_batch(3)}
        self._assert_job_count(incoming, 3)

    def test_linked_collections_of_equal_length(self):
        incoming = {"input1": self._hdca_batch("list", 3), "input2": self._hdca_batch("list", 3)}
        self._assert_job_count(incoming, 3)

    def test_unlinked_batches_multiply(self):
        incoming = {"input1": self._hda_batch(3, linked=False), "input2": self._hdca_batch("list", 2, linked=False)}
        self._assert_job_count(incoming, 6)

    def test_linked_and_unlinked_batches(self):
        incoming = {"input1": self._hda_batch(3), "input2": self._hda_batch(2, linked=False)}
        self._assert_job_count(incoming, 6)

    def test_empty_collection(self):
        self._assert_job_count({"input1": self._hdca_batch("list", 0)}, 0)

    def test_mismatched_batch_lengths(self):
        incoming = {"input1": self._hda_batch(3), "input2": self._hdca_batch("list", 2)}
        with pytest.raises(InputMatchedException):
            self._expand(incoming)

    def test_mismatched_collection_shapes(self):
        incoming = {"input1": self._hdca_batch("list:list", [2, 2]), "input2": self._hdca_batch("list", 4)}
        with pytest.raises(exceptions.MessageException):
            self._expand(incoming)

    def test_unpopulated_collection(self):
        incoming = {"input1": self._hdca_batch("list", 2, populated=False)}
        with pytest.raises(exceptions.ToolInputsNotReadyException):
            self._expand(incoming)

    def test_invalid_map_over_type(self):
        incoming = {"input1": self._hda_ref(), "pair": self._hdca_batch("list:list", [2], "paired")}
        with pytest.raises(exceptions.MessageException):
            self._expand(incoming)

    def test_unknown_collection_id(self):
        incoming = {"input1": {"batch": True, "values": [{"src": "hdca", "id": self._encode(987654)}]}}
        with pytest.raises(exceptions.ObjectNotFound):
            self._expand(incoming)

    def test_unknown_collection_element_id(self):
        incoming = {"input1": {"batch": True, "values": [{"src": "dce", "id": self._encode(987654)}]}}
        with pytest.raises(exceptions.ObjectNotFound):
            self._expand(incoming)

    def test_async_hda_batch(self):
        hda_ids = [self._hda().id for _ in range(3)]
        state = {"input1": {"__class__": "Batch", "values": [{"src": "hda", "id": i} for i in hda_ids]}}
        expanded, job_states, collection_info = self._expand_async(state)
        assert len(expanded) == 3
        assert [s["input1"] for s in job_states] == [{"src": "hda", "id": i} for i in hda_ids]
        assert collection_info is None

    def test_async_hdca_mapped_over_paired(self):
        hda_id = self._hda().id
        state = {
            "input1": {"src": "hda", "id": hda_id},
            "pair": {"__class__": "Batch", "values": [self._internal_hdca("list:paired", [2, 2, 2], "paired")]},
        }
        expanded, job_states, collection_info = self._expand_async(state)
        assert len(expanded) == 3
        assert all(s["input1"] == {"src": "hda", "id": hda_id} for s in job_states)
        assert collection_info is not None

    def test_async_list_into_data_input(self):
        state = {"input1": {"__class__": "Batch", "values": [self._internal_hdca("list:list", [3, 2])]}}
        expanded, job_states, _ = self._expand_async(state)
        assert len(expanded) == 5
        assert all(s["input1"]["src"] == "hda" for s in job_states)

    def test_async_dce_batch(self):
        outer = self._collection("list:list", [3, 2])
        state = {"input1": {"__class__": "Batch", "values": [{"src": "dce", "id": outer.elements[1].id}]}}
        expanded, _, collection_info = self._expand_async(state)
        assert len(expanded) == 2
        assert collection_info is not None

    def test_async_unlinked_batches_multiply(self):
        state = {
            "input1": {"__class__": "Batch", "linked": False, "values": self._internal_hdas(3)},
            "input2": {"__class__": "Batch", "linked": False, "values": [self._internal_hdca("list", 2)]},
        }
        expanded, _, _ = self._expand_async(state)
        assert len(expanded) == 6

    def test_async_mismatched_batch_lengths(self):
        state = {
            "input1": {"__class__": "Batch", "values": self._internal_hdas(3)},
            "input2": {"__class__": "Batch", "values": self._internal_hdas(2)},
        }
        with pytest.raises(InputMatchedException):
            self._expand_async(state)

    def test_async_unknown_collection_id(self):
        for src in ("hdca", "dce"):
            state = {"input1": {"__class__": "Batch", "values": [{"src": src, "id": 987654}]}}
            with pytest.raises(exceptions.ObjectNotFound):
                self._expand_async(state)

    def test_validate_matched_batch_lengths_mismatch(self):
        state = {
            "input1": {"__class__": "Batch", "values": self._internal_hdas(3)},
            "input2": {"__class__": "Batch", "values": self._internal_hdas(2)},
        }
        with pytest.raises(InputMatchedException):
            validate_matched_batch_lengths(self.tool, RequestInternalToolState(state))

    def test_validate_matched_batch_lengths_ignores_collections_and_unlinked(self):
        hdca_batch = {"__class__": "Batch", "values": [self._internal_hdca("list", 2)]}
        validate_matched_batch_lengths(
            self.tool,
            RequestInternalToolState(
                {"input1": {"__class__": "Batch", "values": self._internal_hdas(3)}, "input2": hdca_batch}
            ),
        )
        unlinked = {"__class__": "Batch", "linked": False, "values": self._internal_hdas(2)}
        validate_matched_batch_lengths(
            self.tool,
            RequestInternalToolState(
                {"input1": {"__class__": "Batch", "values": self._internal_hdas(3)}, "input2": unlinked}
            ),
        )

    def test_validate_matched_batch_lengths_does_not_mutate_state(self):
        state = {
            "input1": {"__class__": "Batch", "values": self._internal_hdas(2)},
            "input2": {"__class__": "Batch", "values": self._internal_hdas(2)},
        }
        before = copy.deepcopy(state)
        validate_matched_batch_lengths(self.tool, RequestInternalToolState(state))
        assert state == before

    def _assert_job_count(self, incoming, expected: int):
        assert len(self._expand(incoming)) == expected

    def _expand(self, incoming):
        expanded, _ = expand_meta_parameters(self.trans, self.tool, copy.deepcopy(incoming), "legacy")
        return expanded

    def _expand_async(self, state: dict[str, Any]):
        return expand_meta_parameters_async(self.app, self.tool, RequestInternalDereferencedToolState(state))

    def _encode(self, id: int) -> str:
        return self.app.security.encode_id(id)

    def _user(self, name: str) -> model.User:
        return self.app.user_manager.create(email=f"{name}@example.org", username=name, password="password123")

    def _hda(self) -> model.HistoryDatasetAssociation:
        hda = model.HistoryDatasetAssociation(
            history=self.history, extension="txt", create_dataset=True, sa_session=self.session
        )
        assert hda.dataset
        hda.dataset.state = model.Dataset.states.OK
        self.session.add(hda)
        self.session.commit()
        return hda

    def _hda_ref(self) -> dict[str, Any]:
        return {"src": "hda", "id": self._encode(self._hda().id)}

    def _hda_batch(self, count: int, linked: bool = True) -> dict[str, Any]:
        return {"batch": True, "linked": linked, "values": [self._hda_ref() for _ in range(count)]}

    def _internal_hdas(self, count: int) -> list[dict[str, Any]]:
        return [{"src": "hda", "id": self._hda().id} for _ in range(count)]

    def _collection(self, collection_type: str, shape: ShapeT, populated: bool = True) -> model.DatasetCollection:
        collection = model.DatasetCollection(collection_type=collection_type, populated=populated)
        if isinstance(shape, int):
            children: list[Any] = [self._hda() for _ in range(shape)]
        else:
            child_type = collection_type.split(":", 1)[1]
            children = [self._collection(child_type, child_shape) for child_shape in shape]
        for index, child in enumerate(children):
            model.DatasetCollectionElement(
                collection=collection, element=child, element_identifier=f"e{index}", element_index=index
            )
        self.session.add(collection)
        self.session.commit()
        return collection

    def _hdca(
        self, collection_type: str, shape: ShapeT, populated: bool = True
    ) -> model.HistoryDatasetCollectionAssociation:
        hdca = model.HistoryDatasetCollectionAssociation(
            collection=self._collection(collection_type, shape, populated=populated), history=self.history
        )
        self.session.add(hdca)
        self.session.commit()
        return hdca

    def _internal_hdca(self, collection_type: str, shape: ShapeT, map_over_type: str | None = None) -> dict[str, Any]:
        value: dict[str, Any] = {"src": "hdca", "id": self._hdca(collection_type, shape).id}
        if map_over_type:
            value["map_over_type"] = map_over_type
        return value

    def _hdca_batch(
        self,
        collection_type: str,
        shape: ShapeT,
        map_over_type: str | None = None,
        linked: bool = True,
        populated: bool = True,
    ) -> dict[str, Any]:
        hdca = self._hdca(collection_type, shape, populated=populated)
        value: dict[str, Any] = {"src": "hdca", "id": self._encode(hdca.id)}
        if map_over_type:
            value["map_over_type"] = map_over_type
        return {"batch": True, "linked": linked, "values": [value]}
