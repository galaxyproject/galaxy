"""Unit tests for history_tools helper functions.

Exercises the sync ``_impl`` helpers against the real manager layer using
the standard manager test fixtures (MockTrans + in-memory database). The
public ``async def`` wrappers just offload to ``anyio.to_thread`` and are
covered indirectly; SQLite in-memory can't follow a session across threads
so we drive the impls directly.
"""

import pytest

pydantic_ai = pytest.importorskip("pydantic_ai")

from galaxy.agents.history_tools import (  # noqa: E402
    _format_size,
    _get_collection_structure_impl,
    _get_dataset_info_impl,
    _get_dataset_peek_impl,
    _list_history_items_impl,
    _resolve_hid_impl,
)
from galaxy.managers.collections import DatasetCollectionManager  # noqa: E402
from galaxy.managers.hdas import HDAManager  # noqa: E402
from galaxy.managers.histories import HistoryManager  # noqa: E402
from .managers.base import (  # noqa: E402
    BaseTestCase,
    CreatesCollectionsMixin,
)


class TestFormatSize:
    def test_none(self):
        assert _format_size(None) == ""

    def test_negative(self):
        assert _format_size(-1) == ""

    def test_zero(self):
        assert _format_size(0) == "0 bytes"

    def test_bytes(self):
        assert _format_size(512) == "512 bytes"

    def test_kilobytes(self):
        assert _format_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert _format_size(1_500_000) == "1.5 MB"

    def test_gigabytes(self):
        assert _format_size(2_147_483_648) == "2.1 GB"


class HistoryToolsBase(BaseTestCase, CreatesCollectionsMixin):
    def set_up_managers(self):
        super().set_up_managers()
        self.history_manager = self.app[HistoryManager]
        self.hda_manager = self.app[HDAManager]
        self.collection_manager = self.app[DatasetCollectionManager]

    def _make_history(self, name="h"):
        return self.history_manager.create(name=name, user=self.admin_user)

    def _add_hda(self, history, name="data.txt", extension="txt", **kwargs):
        dataset = self.hda_manager.dataset_manager.create()
        return self.hda_manager.create(history=history, dataset=dataset, name=name, extension=extension, **kwargs)

    def _add_list_collection(self, history, hdas, name="col"):
        return self.collection_manager.create(
            self.trans,
            history,
            name,
            "list",
            element_identifiers=self.build_element_identifiers(hdas),
        )


class TestListHistoryItems(HistoryToolsBase):
    def test_empty_history(self):
        history = self._make_history()
        result = _list_history_items_impl(self.trans, history.id)
        assert result == "No items found in history."

    def test_datasets_and_collections(self):
        history = self._make_history()
        self._add_hda(history, name="reads.fastq", extension="fastqsanger")
        hdas2 = [self._add_hda(history, name=f"r{i}.fastq") for i in range(2)]
        self._add_list_collection(history, hdas2, name="Paired Reads")

        result = _list_history_items_impl(self.trans, history.id)
        lines = result.split("\n")

        assert "4 shown" in lines[0]
        assert "total=4" in lines[0]
        assert "reads.fastq [dataset, fastqsanger]" in result
        assert "Paired Reads [collection, list]" in result

    def test_encoded_ids_in_output(self):
        history = self._make_history()
        hda = self._add_hda(history, name="reads.fastq")
        result = _list_history_items_impl(self.trans, history.id)
        assert f"history_dataset_id={self.app.security.encode_id(hda.id)}" in result

    def test_filters_deleted(self):
        history = self._make_history()
        self._add_hda(history, name="active.txt")
        deleted = self._add_hda(history, name="deleted.txt")
        deleted.deleted = True
        self.trans.sa_session.commit()

        result = _list_history_items_impl(self.trans, history.id, include_deleted=False)
        assert "active.txt" in result
        assert "deleted.txt" not in result

    def test_includes_deleted_when_asked(self):
        history = self._make_history()
        self._add_hda(history, name="active.txt")
        deleted = self._add_hda(history, name="deleted.txt")
        deleted.deleted = True
        self.trans.sa_session.commit()

        result = _list_history_items_impl(self.trans, history.id, include_deleted=True)
        assert "active.txt" in result
        assert "deleted.txt" in result

    def test_filters_hidden(self):
        history = self._make_history()
        self._add_hda(history, name="visible.txt")
        hidden = self._add_hda(history, name="hidden.txt")
        hidden.visible = False
        self.trans.sa_session.commit()

        result = _list_history_items_impl(self.trans, history.id, include_hidden=False)
        assert "visible.txt" in result
        assert "hidden.txt" not in result

    def test_pagination(self):
        history = self._make_history()
        for i in range(5):
            self._add_hda(history, name=f"file{i}.txt")

        result = _list_history_items_impl(self.trans, history.id, offset=2, limit=2)
        assert "2 shown" in result
        assert "total=5" in result
        assert "file2.txt" in result
        assert "file3.txt" in result
        assert "file0.txt" not in result
        assert "file4.txt" not in result

    def test_limit_capped_at_200(self):
        history = self._make_history()
        for i in range(3):
            self._add_hda(history, name=f"file{i}.txt")

        result = _list_history_items_impl(self.trans, history.id, limit=500)
        assert "3 shown" in result

    def test_sorted_by_hid(self):
        history = self._make_history()
        a = self._add_hda(history, name="first.txt")
        b = self._add_hda(history, name="second.txt")
        c = self._add_hda(history, name="third.txt")
        assert a.hid < b.hid < c.hid

        result = _list_history_items_impl(self.trans, history.id)
        first_pos = result.find("first.txt")
        second_pos = result.find("second.txt")
        third_pos = result.find("third.txt")
        assert 0 < first_pos < second_pos < third_pos


class TestGetDatasetInfo(HistoryToolsBase):
    def test_hda_basic(self):
        history = self._make_history()
        hda = self._add_hda(history, name="reads.fastq", extension="fastqsanger")

        result = _get_dataset_info_impl(self.trans, history.id, hda.hid)
        assert "reads.fastq" in result
        assert f"history_dataset_id={self.app.security.encode_id(hda.id)}" in result
        assert "fastqsanger" in result

    def test_implicitly_converted_hid_returns_original(self):
        """Implicit conversions share the original's HID with visible=False.

        get_hda_by_hid must return the original, not the converted child.
        """
        history = self._make_history()
        original = self._add_hda(history, name="reads.fastq", extension="fastqsanger")
        converted = self._add_hda(history, name="reads_converted.bam", extension="bam")
        converted.hid = original.hid
        converted.visible = False
        self.trans.sa_session.commit()

        result = _get_dataset_info_impl(self.trans, history.id, original.hid)
        assert "reads.fastq" in result
        assert "reads_converted.bam" not in result

    def test_not_found(self):
        history = self._make_history()
        result = _get_dataset_info_impl(self.trans, history.id, hid=99)
        assert "No dataset or collection found" in result

    def test_hdca(self):
        history = self._make_history()
        hdas = [self._add_hda(history, name=f"r{i}.fastq") for i in range(2)]
        hdca = self._add_list_collection(history, hdas, name="My List")

        result = _get_dataset_info_impl(self.trans, history.id, hdca.hid)
        assert "My List" in result
        assert "Type: list" in result


class TestGetDatasetPeek(HistoryToolsBase):
    def test_with_peek(self):
        history = self._make_history()
        hda = self._add_hda(history, name="data.tsv", extension="tabular")
        hda.peek = "<table><tr><td>col1</td><td>col2</td></tr></table>"
        self.trans.sa_session.commit()

        result = _get_dataset_peek_impl(self.trans, history.id, hda.hid)
        assert "col1" in result
        assert "col2" in result
        assert "<table>" not in result

    def test_no_peek(self):
        history = self._make_history()
        hda = self._add_hda(history, name="data.bam", extension="bam")
        hda.peek = None
        self.trans.sa_session.commit()

        result = _get_dataset_peek_impl(self.trans, history.id, hda.hid)
        assert "No preview available" in result

    def test_not_found(self):
        history = self._make_history()
        result = _get_dataset_peek_impl(self.trans, history.id, hid=99)
        assert "No dataset found" in result


class TestGetCollectionStructure(HistoryToolsBase):
    def test_list_collection(self):
        history = self._make_history()
        hdas = [self._add_hda(history, name=f"r{i}.fastq") for i in range(2)]
        hdca = self._add_list_collection(history, hdas, name="Paired Reads")

        result = _get_collection_structure_impl(self.trans, history.id, hdca.hid)
        assert "Paired Reads" in result
        assert "Type: list" in result
        assert "Elements: 2" in result
        for hda in hdas:
            assert hda.name in result

    def test_not_found(self):
        history = self._make_history()
        result = _get_collection_structure_impl(self.trans, history.id, hid=99)
        assert "No collection found" in result

    def test_max_elements_truncates(self):
        history = self._make_history()
        hdas = [self._add_hda(history, name=f"f{i}.txt") for i in range(5)]
        hdca = self._add_list_collection(history, hdas, name="Big")

        result = _get_collection_structure_impl(self.trans, history.id, hdca.hid, max_elements=3)
        assert "f0.txt" in result
        assert "f2.txt" in result
        assert "f4.txt" not in result
        assert "2 more elements" in result


class TestResolveHid(HistoryToolsBase):
    def test_dataset(self):
        history = self._make_history()
        hda = self._add_hda(history, name="reads.fastq")

        result = _resolve_hid_impl(self.trans, history.id, hda.hid)
        assert f"HID {hda.hid} is a dataset: reads.fastq" in result
        assert f"history_dataset_id={self.app.security.encode_id(hda.id)}" in result

    def test_collection(self):
        history = self._make_history()
        hdas = [self._add_hda(history, name=f"r{i}.fastq") for i in range(2)]
        hdca = self._add_list_collection(history, hdas, name="Paired Reads")

        result = _resolve_hid_impl(self.trans, history.id, hdca.hid)
        assert "is a collection: Paired Reads" in result
        assert f"history_dataset_collection_id={self.app.security.encode_id(hdca.id)}" in result

    def test_not_found(self):
        history = self._make_history()
        result = _resolve_hid_impl(self.trans, history.id, hid=99)
        assert "No dataset or collection found" in result
