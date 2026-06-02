"""Unit tests for the backward job-closure walk that seeds page extraction.

The closure logic is pure graph traversal over job/dataset provenance, so it is
exercised here with lightweight mocks rather than a live app. The full
serialization (build_extraction_summary) is covered by the API tests.
"""

from typing import (
    cast,
    Optional,
)

from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.workflow_extraction_summary import (
    _backward_job_closure,
    _content_key,
)
from galaxy.model import HistoryItem

TARGET_HISTORY = 1


class MockTool:
    def __init__(self, workflow_compatible: bool = True):
        self.is_workflow_compatible = workflow_compatible


class MockToolbox:
    def __init__(self, by_job_id: Optional[dict] = None, default_compatible: bool = True):
        self._by_job_id = by_job_id or {}
        self._default = default_compatible

    def tool_for_job(self, job, user=None):
        if job.id in self._by_job_id:
            return self._by_job_id[job.id]
        return MockTool(self._default)


class MockApp:
    def __init__(self, toolbox):
        self.toolbox = toolbox


class MockSession:
    def __init__(self):
        self._by_key: dict = {}

    def register(self, content):
        kind = "hdca" if content.history_content_type == "dataset_collection" else "hda"
        self._by_key[(kind, content.id)] = content

    def get(self, model_class, id_):
        kind = "hdca" if "Collection" in model_class.__name__ else "hda"
        return self._by_key.get((kind, id_))


class MockTrans:
    def __init__(self, session, toolbox):
        self.sa_session = session
        self.app = MockApp(toolbox)
        self.user = None


class MockOutputAssoc:
    def __init__(self, job):
        self.job = job


class MockInputDatasetAssoc:
    def __init__(self, dataset):
        self.dataset = dataset


class MockInputCollectionAssoc:
    def __init__(self, dataset_collection):
        self.dataset_collection = dataset_collection


class MockIcjAssoc:
    def __init__(self, icj_id):
        self.implicit_collection_jobs_id = icj_id


class MockJob:
    def __init__(self, id, history_id=TARGET_HISTORY, inputs=(), input_collections=(), icj_id=None):
        self.id = id
        self.history_id = history_id
        self.input_datasets = [MockInputDatasetAssoc(d) for d in inputs]
        self.input_dataset_collections = [MockInputCollectionAssoc(c) for c in input_collections]
        self.implicit_collection_jobs_association = MockIcjAssoc(icj_id) if icj_id is not None else None


class MockHda:
    history_content_type = "dataset"

    def __init__(self, id, creating_jobs=(), copied_from=None):
        self.id = id
        self.creating_job_associations = [MockOutputAssoc(j) for j in creating_jobs]
        self.copied_from_history_dataset_association = copied_from


class MockHdca:
    history_content_type = "dataset_collection"

    def __init__(self, id, creating_jobs=(), copied_from=None):
        self.id = id
        self.creating_job_associations = [MockOutputAssoc(j) for j in creating_jobs]
        self.copied_from_history_dataset_collection_association = copied_from


def _trans(contents, toolbox=None):
    session = MockSession()
    for content in contents:
        session.register(content)
    return cast(ProvidesHistoryContext, MockTrans(session, toolbox or MockToolbox()))


def _closure(trans, refs):
    return _backward_job_closure(trans, refs, TARGET_HISTORY)


def test_linear_chain_collects_all_upstream_jobs():
    upload = MockHda(3)  # no creating job -> boundary input
    job2 = MockJob(2, inputs=[upload])
    mid = MockHda(2, creating_jobs=[job2])
    job1 = MockJob(1, inputs=[mid])
    out = MockHda(1, creating_jobs=[job1])
    trans = _trans([out, mid, upload])

    result = _closure(trans, [("hda", 1)])

    assert result.job_ids == {1, 2}
    assert result.referenced_output_refs == {("hda", 1)}
    assert ("hda", 3) in result.boundary_input_refs


def test_no_creating_job_is_boundary_input():
    out = MockHda(1)
    trans = _trans([out])

    result = _closure(trans, [("hda", 1)])

    assert result.job_ids == set()
    assert result.boundary_input_refs == {("hda", 1)}


def test_non_workflow_compatible_producer_is_boundary():
    upload_job = MockJob(5)
    out = MockHda(1, creating_jobs=[upload_job])
    toolbox = MockToolbox(by_job_id={5: MockTool(workflow_compatible=False)})
    trans = _trans([out], toolbox=toolbox)

    result = _closure(trans, [("hda", 1)])

    assert result.job_ids == set()
    assert ("hda", 1) in result.boundary_input_refs


def test_inaccessible_tool_is_boundary():
    job = MockJob(5)
    out = MockHda(1, creating_jobs=[job])
    toolbox = MockToolbox(by_job_id={5: None})
    trans = _trans([out], toolbox=toolbox)

    result = _closure(trans, [("hda", 1)])

    assert result.job_ids == set()
    assert ("hda", 1) in result.boundary_input_refs


def test_cross_history_producer_is_boundary():
    job = MockJob(9, history_id=TARGET_HISTORY + 1)
    out = MockHda(1, creating_jobs=[job])
    trans = _trans([out])

    result = _closure(trans, [("hda", 1)])

    assert result.job_ids == set()
    assert ("hda", 1) in result.boundary_input_refs


def test_implicit_collection_job_records_icj_id():
    job = MockJob(2, icj_id=99)
    out = MockHdca(1, creating_jobs=[job])
    trans = _trans([out])

    result = _closure(trans, [("hdca", 1)])

    assert result.job_ids == {2}
    assert result.icj_ids == {99}
    assert result.referenced_output_refs == {("hdca", 1)}


def test_missing_seed_skipped_with_warning():
    trans = _trans([])  # nothing registered -> session.get returns None

    result = _closure(trans, [("hda", 42)])

    assert not result.job_ids
    assert not result.referenced_output_refs
    assert not result.content_refs
    assert len(result.warnings) == 1


def test_cycle_guard_terminates():
    job = MockJob(1)
    out = MockHda(1, creating_jobs=[job])
    job.input_datasets = [MockInputDatasetAssoc(out)]  # self-referential input
    trans = _trans([out])

    result = _closure(trans, [("hda", 1)])

    assert result.job_ids == {1}


def test_copied_dataset_normalized_to_original():
    original = MockHda(10)
    copy = MockHda(11, copied_from=original)
    assert _content_key(cast(HistoryItem, copy)) == ("hda", 10)
