from typing import cast, TYPE_CHECKING

from galaxy.jobs import JobWrapper
from galaxy.model import (
    Dataset,
    HistoryDatasetAssociation,
    Job,
    JobToOutputDatasetAssociation,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session

class MockRecordingSession:
    def __init__(self):
        self.added = []

    def add(self, dataset_instance):
        self.added.append(dataset_instance)


def _hda(dataset_id, state):
    hda = HistoryDatasetAssociation(id=dataset_id, extension="txt")
    hda._state = state
    return hda


def _dataset_assoc_with_instances(*instances):
    dataset = Dataset(id=42)
    dataset.history_associations = list(instances)
    dataset.library_associations = []
    dataset_instance = HistoryDatasetAssociation(dataset=dataset, extension="txt")
    return JobToOutputDatasetAssociation(name="out", dataset=dataset_instance)


def test_normalize_successful_output_association_states_marks_pending_instances_ok():
    wrapper = JobWrapper.__new__(JobWrapper)
    session = MockRecordingSession()
    wrapper.sa_session = cast('scoped_session', session)

    running_instance = _hda(dataset_id=3, state=Dataset.states.RUNNING)
    queued_instance = _hda(dataset_id=4, state=Dataset.states.QUEUED)
    ok_instance = _hda(dataset_id=5, state=Dataset.states.OK)
    association = _dataset_assoc_with_instances(running_instance, queued_instance, ok_instance)

    job = Job()
    job.id = 9
    wrapper._normalize_successful_output_association_states(job, [association])

    assert running_instance.state == Dataset.states.OK
    assert queued_instance.state == Dataset.states.OK
    assert ok_instance.state == Dataset.states.OK
    assert session.added == [running_instance, queued_instance]


def test_normalize_successful_output_association_states_leaves_non_pending_unchanged():
    wrapper = JobWrapper.__new__(JobWrapper)
    session = MockRecordingSession()
    wrapper.sa_session = cast('scoped_session', session)

    ok_instance = _hda(dataset_id=11, state=Dataset.states.OK)
    failed_meta_instance = _hda(dataset_id=12, state=Dataset.states.FAILED_METADATA)
    association = _dataset_assoc_with_instances(ok_instance, failed_meta_instance)

    job = Job()
    job.id = 12
    wrapper._normalize_successful_output_association_states(job, [association])

    assert ok_instance.state == Dataset.states.OK
    assert failed_meta_instance.state == Dataset.states.FAILED_METADATA
    assert session.added == []
