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
