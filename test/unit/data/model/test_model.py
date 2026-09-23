from uuid import (
    UUID,
    uuid4,
)

import pytest

from galaxy import model
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model.item_attrs import add_item_annotation
from galaxy.schema.schema import MAX_ANNOTATION_SIZE


@pytest.fixture(scope="module")
def init_model(engine):
    model.Base.metadata.create_all(engine)


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


ANNOTATION_MODELS = model.ItemAnnotationAssociation.__subclasses__()


@pytest.mark.parametrize("annotation_model", ANNOTATION_MODELS, ids=lambda cls: cls.__name__)
def test_annotation_size_limit(annotation_model):
    at_limit = "a" * MAX_ANNOTATION_SIZE
    assert annotation_model(annotation=None).annotation is None
    assert annotation_model(annotation=at_limit).annotation == at_limit
    with pytest.raises(RequestParameterInvalidException, match="Annotation too large"):
        annotation_model(annotation=at_limit + "a")


@pytest.mark.parametrize("item_class", [model.History, model.LibraryDatasetCollectionAssociation])
def test_update_item_annotation(session, item_class):
    first, second = item_class(), item_class()
    session.add_all([first, second])
    session.flush()
    original = add_item_annotation(session, None, first, "original")
    session.flush()
    other = add_item_annotation(session, None, second, "other")
    session.flush()
    assert original is not other
    with pytest.raises(RequestParameterInvalidException):
        add_item_annotation(session, None, first, "a" * (MAX_ANNOTATION_SIZE + 1))
    assert original.annotation == "original"
    assert add_item_annotation(session, None, first, "updated") is original
    assert original.annotation == "updated"
    assert other.annotation == "other"


def test_annotation_columns_are_not_indexed():
    tables = [table for table in model.Base.metadata.tables.values() if "annotation" in table.columns]
    assert len(tables) == len(ANNOTATION_MODELS)  # every annotated table carries the length validator
    for table in tables:
        assert not any(list(index.columns.keys()) == ["annotation"] for index in table.indexes)
