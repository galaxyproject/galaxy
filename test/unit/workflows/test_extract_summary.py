from typing import (
    Any,
    cast,
)

from galaxy import model
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.util.unittest import TestCase
from galaxy.workflow import extract

UNDEFINED_JOB = object()


class TestWorkflowExtractSummary(TestCase):
    def setUp(self):
        self.history = MockHistory()
        self.trans = MockTrans(self.history)

    def _summarize(self) -> tuple[dict[Any, Any], set[str]]:
        """Helper to call summarize with mock trans, isolating the type cast."""
        return extract.summarize(trans=cast(ProvidesHistoryContext, self.trans))

    def test_empty_history(self):
        job_dict, warnings = self._summarize()
        assert not warnings
        assert not job_dict

    def test_summarize_returns_name_and_dataset_list(self):
        # Create two jobs and three datasets, test they are groupped
        # by job correctly with correct output names.
        hda1 = MockHda()
        self.history.active_datasets.append(hda1)
        hda2 = MockHda(job=hda1.job, output_name="out2")
        self.history.active_datasets.append(hda2)
        hda3 = MockHda(output_name="out3")
        self.history.active_datasets.append(hda3)

        job_dict, warnings = self._summarize()
        assert len(job_dict) == 2
        assert not warnings
        assert job_dict[hda1.job] == [("out1", hda1), ("out2", hda2)]
        assert job_dict[hda3.job] == [("out3", hda3)]

    def test_finds_original_job_if_copied(self):
        # Passive copies (no creating job of their own) normalize back to the
        # source, so the output is attributed to the source's creating job.
        hda = MockHda()
        derived_hda_1 = MockHda(job=UNDEFINED_JOB)
        derived_hda_1.copied_from_history_dataset_association = hda
        derived_hda_2 = MockHda(job=UNDEFINED_JOB)
        derived_hda_2.copied_from_history_dataset_association = derived_hda_1
        self.history.active_datasets.append(derived_hda_2)
        job_dict, warnings = self._summarize()
        assert not warnings
        assert len(job_dict) == 1
        assert job_dict[hda.job] == [("out1", derived_hda_2)]

    def test_keeps_copy_with_own_creating_job(self):
        # A copy that records its own creating job (e.g. Extract Dataset output)
        # is a real step and must not normalize past copied_from to the source.
        hda = MockHda()
        derived_hda = MockHda()
        derived_hda.copied_from_history_dataset_association = hda
        self.history.active_datasets.append(derived_hda)
        job_dict, warnings = self._summarize()
        assert not warnings
        assert len(job_dict) == 1
        assert job_dict[derived_hda.job] == [("out1", derived_hda)]
        assert hda.job not in job_dict

    def test_fake_job_hda(self):
        """Fakes job if creating_job_associations is empty."""
        hda = MockHda(job=UNDEFINED_JOB)
        self.history.active_datasets.append(hda)
        job_dict, warnings = self._summarize()
        assert not warnings
        assert len(job_dict) == 1
        fake_job = next(iter(job_dict.keys()))
        assert fake_job.id.startswith("fake_")
        datasets = next(iter(job_dict.values()))
        assert datasets == [(None, hda)]

    def test_fake_job_hda_name_guess(self):
        hda_from_history = MockHda(job=UNDEFINED_JOB)
        hda_from_history.copied_from_history_dataset_association = MockHda(job=UNDEFINED_JOB)
        self.history.active_datasets.append(hda_from_history)
        job_dict, warnings = self._summarize()
        assert not warnings
        assert len(job_dict) == 1
        fake_job = next(iter(job_dict.keys()))
        assert "History" in fake_job.name
        self.history.active_datasets.remove(hda_from_history)

        hda_from_library = MockHda(job=UNDEFINED_JOB)
        hda_from_library.copied_from_library_dataset_dataset_association = MockHda(job=UNDEFINED_JOB)
        self.history.active_datasets.append(hda_from_library)
        job_dict, warnings = self._summarize()
        assert not warnings
        assert len(job_dict) == 1
        fake_job = next(iter(job_dict.keys()))
        assert "Library" in fake_job.name

    def test_fake_job_hdca(self):
        hdca = MockHdca()
        self.history.active_datasets.append(hdca)
        job_dict, warnings = self._summarize()
        assert not warnings
        assert len(job_dict) == 1
        fake_job = next(iter(job_dict.keys()))
        assert fake_job.id.startswith("fake_")
        assert fake_job.is_fake
        content_instances = next(iter(job_dict.values()))
        assert content_instances == [(None, hdca)]

    def test_implicit_map_job_hdca(self):
        creating_job = model.Job()
        hdca = MockHdca(implicit_output_name="out1", job=creating_job)
        self.history.active_datasets.append(hdca)
        job_dict, warnings = self._summarize()
        assert not warnings
        assert len(job_dict) == 1
        job = next(iter(job_dict.keys()))
        assert job is creating_job

    def test_includes_hidden_standalone_intermediate(self):
        # A hidden dataset that is not a collection element (e.g. an intermediate
        # an IWC workflow hid) must still yield a job - the regression this fixes.
        hda = MockHda(visible=False)
        self.history.active_datasets.append(hda)
        job_dict, warnings = self._summarize()
        assert not warnings
        assert len(job_dict) == 1

    def test_skips_hidden_collection_element(self):
        # A hidden dataset that IS a collection element is represented by its
        # collection, so it must not become a standalone job.
        element = MockHda(visible=False, id=555)
        self.history.active_datasets.append(element)
        self.trans.sa_session.collection_element_hda_ids = [element.id]
        job_dict, warnings = self._summarize()
        assert not warnings
        assert len(job_dict) == 0

    def test_warns_and_skips_datasets_if_not_finished(self):
        hda = MockHda(state="queued")
        self.history.active_datasets.append(hda)
        job_dict, warnings = self._summarize()
        assert warnings
        assert len(job_dict) == 0


class MockJobToOutputDatasetAssociation:
    job = None

    def __init__(self, name, dataset):
        self.name = name
        self.dataset = dataset


class MockHistory:
    def __init__(self):
        self.id = 1
        self.active_datasets = []

    @property
    def active_contents(self):
        return self.active_datasets

    @property
    def visible_contents(self):
        return self.active_contents

    @property
    def all_contents(self):
        return self.active_contents


class MockScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class MockSession:
    def __init__(self):
        self.collection_element_hda_ids: list[int] = []

    def scalars(self, statement):
        return MockScalarResult(self.collection_element_hda_ids)


class MockTrans:
    def __init__(self, history):
        self.history = history
        self.sa_session = MockSession()

    def get_history(self):
        return self.history


class MockHda:
    def __init__(self, state="ok", output_name="out1", job=None, visible=True, id=123):
        self.hid = 1
        self.id = id
        self.visible = visible
        self.state = state
        self.copied_from_history_dataset_association = None
        self.copied_from_library_dataset_dataset_association = None
        self.history_content_type = "dataset"
        if job is not UNDEFINED_JOB:
            if not job:
                job = model.Job()
            self.job = job
            assoc = MockJobToOutputDatasetAssociation(output_name, self)
            assoc.job = job
            self.creating_job_associations = [assoc]
        else:
            self.creating_job_associations = []


class MockHdca:
    def __init__(self, implicit_output_name=None, job=None, hid=1):
        self.id = 124
        self.copied_from_history_dataset_collection_association = None
        self.history_content_type = "dataset_collection"
        self.implicit_output_name = implicit_output_name
        self.hid = 1
        self.collection = model.DatasetCollection()
        self.creating_job_associations = []
        element = model.DatasetCollectionElement(
            collection=self.collection,
            element=model.HistoryDatasetAssociation(),
            element_index=0,
            element_identifier="moocow",
        )
        element.dataset_instance.dataset = model.Dataset()
        element.dataset_instance.dataset.state = "ok"
        creating = model.JobToOutputDatasetAssociation(
            implicit_output_name,
            element.dataset_instance,
        )
        creating.job = job
        element.dataset_instance.creating_job_associations = [
            creating,
        ]
