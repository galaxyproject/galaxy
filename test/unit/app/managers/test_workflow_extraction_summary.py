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
        self._jobs: dict = {}
        self._icjs: dict = {}

    def register(self, content):
        kind = "hdca" if content.history_content_type == "dataset_collection" else "hda"
        self._by_key[(kind, content.id)] = content

    def register_job(self, job):
        self._jobs[job.id] = job

    def register_icj(self, icj):
        self._icjs[icj.id] = icj

    def get(self, model_class, id_):
        name = model_class.__name__
        if name == "Job":
            return self._jobs.get(id_)
        if name == "ImplicitCollectionJobs":
            return self._icjs.get(id_)
        kind = "hdca" if "Collection" in name else "hda"
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
    def __init__(self, dataset, name=None):
        self.dataset = dataset
        self.name = name


class MockInputCollectionAssoc:
    def __init__(self, dataset_collection):
        self.dataset_collection = dataset_collection


class MockImplicitInputCollection:
    def __init__(self, input_dataset_collection, name=None):
        self.input_dataset_collection = input_dataset_collection
        self.name = name


class MockIcjAssoc:
    def __init__(self, implicit_collection_jobs):
        self.implicit_collection_jobs = implicit_collection_jobs
        self.implicit_collection_jobs_id = implicit_collection_jobs.id


class MockOutputDatasetAssoc:
    def __init__(self, dataset):
        self.dataset = dataset


class MockOutputCollectionAssoc:
    def __init__(self, dataset_collection_instance):
        self.dataset_collection_instance = dataset_collection_instance


class MockJob:
    def __init__(
        self,
        id,
        history_id=TARGET_HISTORY,
        inputs=(),
        input_collections=(),
        icj_id=None,
        icj=None,
        outputs=(),
        output_collections=(),
    ):
        self.id = id
        self.history_id = history_id
        self.input_datasets = [MockInputDatasetAssoc(d) for d in inputs]
        self.input_dataset_collections = [MockInputCollectionAssoc(c) for c in input_collections]
        self.output_datasets = [MockOutputDatasetAssoc(d) for d in outputs]
        self.output_dataset_collection_instances = [MockOutputCollectionAssoc(c) for c in output_collections]
        if icj is None and icj_id is not None:
            icj = MockImplicitCollectionJobs(icj_id)
        self.implicit_collection_jobs_association = MockIcjAssoc(icj) if icj is not None else None


class MockImplicitCollectionJobs:
    def __init__(self, id, output_collections=()):
        self.id = id
        self.output_dataset_collection_instances = list(output_collections)


class MockHda:
    history_content_type = "dataset"

    def __init__(self, id, creating_jobs=(), copied_from=None):
        self.id = id
        self.creating_job_associations = [MockOutputAssoc(j) for j in creating_jobs]
        self.copied_from_history_dataset_association = copied_from


class MockHdca:
    history_content_type = "dataset_collection"

    def __init__(self, id, creating_jobs=(), copied_from=None, implicit_input_collections=()):
        self.id = id
        self.creating_job_associations = [MockOutputAssoc(j) for j in creating_jobs]
        self.copied_from_history_dataset_collection_association = copied_from
        self.implicit_input_collections = list(implicit_input_collections)


def _trans(contents, toolbox=None, jobs=(), icjs=()):
    session = MockSession()
    for content in contents:
        session.register(content)
    for job in jobs:
        session.register_job(job)
    for icj in icjs:
        session.register_icj(icj)
    return cast(ProvidesHistoryContext, MockTrans(session, toolbox or MockToolbox()))


def _closure(trans, refs, job_refs=(), icj_refs=()):
    return _backward_job_closure(trans, refs, list(job_refs), list(icj_refs), TARGET_HISTORY)


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


def test_plain_job_ref_seeds_producing_subgraph():
    upload = MockHda(3)  # boundary input
    out = MockHda(1)
    job1 = MockJob(1, inputs=[upload], outputs=[out])
    out.creating_job_associations = [MockOutputAssoc(job1)]
    trans = _trans([], jobs=[job1])

    result = _closure(trans, [], job_refs=[1])

    assert result.job_ids == {1}
    assert ("hda", 1) in result.content_refs
    assert ("hda", 3) in result.content_refs  # upstream input walked & seeded
    assert result.referenced_output_refs == set()  # job-seeded output is not exposed
    assert result.seed_warning_refs == set()


def test_icj_ref_seeds_mapped_input():
    input_collection = MockHdca(20)  # the mapped-over input collection (boundary)
    element_job = MockJob(2, icj_id=7)
    impl_out = MockHdca(
        10,
        creating_jobs=[element_job],
        implicit_input_collections=[MockImplicitInputCollection(input_collection, name="input")],
    )
    icj = MockImplicitCollectionJobs(7, output_collections=[impl_out])
    trans = _trans([], icjs=[icj])

    result = _closure(trans, [], icj_refs=[7])

    assert 7 in result.icj_ids
    assert ("hdca", 20) in result.content_refs  # mapped-over input collection recovered & seeded
    assert result.referenced_output_refs == set()  # implicit output not exposed


def test_loose_element_of_map_output_seeds_input_collection():
    # A downstream tool consumes a single ELEMENT of a map output collection
    # (e.g. MACS2 reading one BAM out of an alignment collection) rather than the
    # whole collection. The walk reaches the map via the loose element, not via
    # the output collection, so it must still recover and seed the map's input
    # collection -- and not surface the element's per-element input as a loose
    # dataset.
    input_collection = MockHdca(20)  # mapped-over input collection -> boundary input
    impl_out = MockHdca(
        30, implicit_input_collections=[MockImplicitInputCollection(input_collection, name="library|input_1")]
    )
    icj = MockImplicitCollectionJobs(7, output_collections=[impl_out])
    fastq_element = MockHda(5)  # per-element input -> must NOT surface as a loose input
    element_job = MockJob(2, icj=icj)
    element_job.input_datasets = [MockInputDatasetAssoc(fastq_element, name="library|input_1")]
    bam_element = MockHda(10, creating_jobs=[element_job])  # loose element of the map output
    downstream_job = MockJob(1, inputs=[bam_element])
    out = MockHda(1, creating_jobs=[downstream_job])
    trans = _trans([out])

    result = _closure(trans, [("hda", 1)])

    assert {1, 2}.issubset(result.job_ids)  # downstream tool + element job crossed
    assert 7 in result.icj_ids  # map step seeded
    assert ("hdca", 20) in result.content_refs  # input collection recovered & seeded (the fix)
    assert ("hda", 5) not in result.content_refs  # per-element input not chased as a loose dataset


def test_non_compatible_job_ref_warns_only_when_directly_referenced():
    # Directly job-referenced upload -> seed_warning.
    direct_upload_out = MockHda(1)
    direct_upload_job = MockJob(5, outputs=[direct_upload_out])
    direct_upload_out.creating_job_associations = [MockOutputAssoc(direct_upload_job)]

    # An ordinary content ref whose upstream is an upload -> no warning on that upload.
    walk_upload = MockHda(3)  # boundary upload reached only by the walk
    step_out = MockHda(2)
    step_job = MockJob(6, inputs=[walk_upload])
    step_out.creating_job_associations = [MockOutputAssoc(step_job)]

    toolbox = MockToolbox(by_job_id={5: MockTool(workflow_compatible=False)})
    trans = _trans([step_out], toolbox=toolbox, jobs=[direct_upload_job])

    result = _closure(trans, [("hda", 2)], job_refs=[5])

    assert ("hda", 1) in result.seed_warning_refs
    assert ("hda", 3) not in result.seed_warning_refs


def test_referenced_and_job_seeded_dedup():
    upload = MockHda(2)
    out = MockHda(1)
    job1 = MockJob(1, inputs=[upload], outputs=[out])
    out.creating_job_associations = [MockOutputAssoc(job1)]
    trans = _trans([out], jobs=[job1])

    result = _closure(trans, [("hda", 1)], job_refs=[1])

    assert result.referenced_output_refs == {("hda", 1)}  # exposed via the content ref
    assert result.job_ids == {1}  # and seeded via the job ref, deduped


def test_job_ref_multiple_outputs_none_exposed():
    out_a = MockHda(1)
    out_b = MockHda(2)
    job1 = MockJob(1, outputs=[out_a, out_b])
    out_a.creating_job_associations = [MockOutputAssoc(job1)]
    out_b.creating_job_associations = [MockOutputAssoc(job1)]
    trans = _trans([], jobs=[job1])

    result = _closure(trans, [], job_refs=[1])

    assert result.job_ids == {1}  # seeded once despite two outputs
    assert result.referenced_output_refs == set()  # neither output exposed


def test_missing_job_ref_skipped_with_warning():
    trans = _trans([])  # nothing registered -> session.get(Job) returns None

    result = _closure(trans, [], job_refs=[42])

    assert not result.job_ids
    assert len(result.warnings) == 1
