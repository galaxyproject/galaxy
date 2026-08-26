from uuid import (
    UUID,
    uuid4,
)

import pytest

from galaxy import model


def test_get_uuid():
    my_uuid = uuid4()
    rval = model.get_uuid(my_uuid)
    assert rval == UUID(str(my_uuid))

    rval = model.get_uuid()
    assert isinstance(rval, UUID)


def test_permitted_actions():
    actions = model.Dataset.permitted_actions
    assert actions and len(actions.values()) == 2


def test_io_dicts_excludes_implicit_output_collections():
    """Regression test for https://github.com/galaxyproject/galaxy/issues/22015

    When a tool with a dataset output is mapped over a list, each job gets
    both a JobToOutputDatasetAssociation and a
    JobToImplicitOutputDatasetCollectionAssociation with the same name.
    The implicit DC has precreated (unpopulated) elements; only the current
    job's element is initialized. io_dicts(exclude_implicit_outputs=True)
    must exclude these shared DCs (name in out_data) to avoid crashes
    during metadata serialization, but must include implicit DCs for
    collection outputs (name not in out_data) so set_metadata.py can
    discover and populate them.
    """
    job = model.Job()
    dc = model.DatasetCollection(collection_type="paired")
    assoc = model.JobToImplicitOutputDatasetCollectionAssociation(name="paired_output", dataset_collection=dc)
    job.output_dataset_collections.append(assoc)

    # When the name is NOT in out_data (collection output), the implicit DC
    # should be included even with exclude_implicit_outputs=True
    io = job.io_dicts(exclude_implicit_outputs=True)
    assert "paired_output" in io.out_collections
    assert io.out_collections["paired_output"] is dc

    # Now simulate a mapped dataset output: same name in both out_data and
    # output_dataset_collections. The shared DC must be excluded.
    hda = model.HistoryDatasetAssociation()
    out_assoc = model.JobToOutputDatasetAssociation(name="paired_output", dataset=hda)
    job.output_datasets.append(out_assoc)

    io = job.io_dicts(exclude_implicit_outputs=True)
    assert "paired_output" not in io.out_collections

    # With exclude_implicit_outputs=False (default), they should be included
    io = job.io_dicts(exclude_implicit_outputs=False)
    assert "paired_output" in io.out_collections


def _record_state(job, state):
    job.state = state
    job.state_history.append(model.JobStateHistory(job))


def test_resubmission_count_counts_resubmitted_state_history_entries():
    job = model.Job()
    assert job.resubmission_count == 0

    _record_state(job, model.Job.states.QUEUED)
    _record_state(job, model.Job.states.RUNNING)
    assert job.resubmission_count == 0

    _record_state(job, model.Job.states.RESUBMITTED)
    _record_state(job, model.Job.states.QUEUED)
    _record_state(job, model.Job.states.RUNNING)
    assert job.resubmission_count == 1

    _record_state(job, model.Job.states.RESUBMITTED)
    _record_state(job, model.Job.states.OK)
    assert job.resubmission_count == 2


@pytest.fixture(scope="module")
def init_model(engine):
    """Create model objects in the engine's database."""
    model.mapper_registry.metadata.create_all(engine)


def _job_with_output_dataset(session, make_job, make_hda):
    """A persisted job whose single output dataset is linked back via Dataset.job_id.

    ``update_output_states`` finds outputs through ``dataset.job_id``, so that column -
    not just the JobToOutputDatasetAssociation - has to be set for the update to bite.
    """
    job = make_job()
    dataset = model.Dataset()
    dataset.job_id = job.id
    session.add(dataset)
    session.commit()
    hda = make_hda(dataset=dataset, name="output1")
    assoc = model.JobToOutputDatasetAssociation(name="out_file1", dataset=hda)
    job.output_datasets.append(assoc)
    session.add(assoc)
    session.commit()
    return job, dataset


def _updated_dataset_state(session, job, dataset, job_state):
    job.state = job_state
    session.commit()
    job.update_output_states(supports_skip_locked=False)
    session.expire_all()
    return session.get(model.Dataset, dataset.id).state


def test_update_output_states_maps_finishing_to_setting_metadata(session, make_job, make_hda):
    """Regression test: "finishing" is a Job state but not a Dataset state.

    Persisting it verbatim leaves an invalid dataset state behind, which blows up the
    history state-count serializers and makes the history read as errored.
    """
    job, dataset = _job_with_output_dataset(session, make_job, make_hda)
    state = _updated_dataset_state(session, job, dataset, model.Job.states.FINISHING)
    assert state == model.Dataset.states.SETTING_METADATA
    assert state != model.Job.states.FINISHING


def test_update_output_states_passes_through_unmapped_states(session, make_job, make_hda):
    """States shared by both vocabularies must still propagate verbatim."""
    job, dataset = _job_with_output_dataset(session, make_job, make_hda)
    state = _updated_dataset_state(session, job, dataset, model.Job.states.RUNNING)
    assert state == model.Dataset.states.RUNNING
