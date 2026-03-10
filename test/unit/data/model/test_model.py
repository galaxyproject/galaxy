from uuid import (
    UUID,
    uuid4,
)

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

    When a tool with an explicit collection output is mapped over a list,
    each job gets a JobToImplicitOutputDatasetCollectionAssociation pointing
    to a DatasetCollection with precreated (unpopulated) elements.
    io_dicts(exclude_implicit_outputs=True) must exclude these to avoid
    crashes during metadata serialization on unpopulated elements.
    """
    job = model.Job()
    dc = model.DatasetCollection(collection_type="paired")
    assoc = model.JobToImplicitOutputDatasetCollectionAssociation(name="paired_output", dataset_collection=dc)
    job.output_dataset_collections.append(assoc)

    # With exclude_implicit_outputs=True, output_dataset_collections must be excluded
    io = job.io_dicts(exclude_implicit_outputs=True)
    assert "paired_output" not in io.out_collections

    # With exclude_implicit_outputs=False (default), they should be included
    io = job.io_dicts(exclude_implicit_outputs=False)
    assert "paired_output" in io.out_collections
    assert io.out_collections["paired_output"] is dc
