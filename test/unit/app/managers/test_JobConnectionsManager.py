from typing import TYPE_CHECKING

import pytest
from sqlalchemy import (
    event,
    union,
)

from galaxy.managers.job_connections import JobConnectionsManager
from galaxy.model import (
    DatasetCollection,
    DatasetCollectionElement,
    History,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    Job,
)
from galaxy.model.unittest_utils import GalaxyDataTestApp

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session


@pytest.fixture
def sa_session():
    return GalaxyDataTestApp().model.session


@pytest.fixture
def job_connections_manager(sa_session) -> JobConnectionsManager:
    gm = JobConnectionsManager(sa_session)
    return gm


# =============================================================================
def setup_connected_dataset(sa_session: "scoped_session"):
    center_hda = HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True)
    input_hda = HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True)
    input_hdca = HistoryDatasetCollectionAssociation()
    output_hda = HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True)
    output_hdca = HistoryDatasetCollectionAssociation()
    input_job = Job()
    output_job = Job()
    input_job.add_output_dataset("output_hda", center_hda)
    input_job.add_input_dataset("input_hda", input_hda)
    input_job.add_input_dataset_collection("input_hdca", input_hdca)
    output_job.add_input_dataset("input_hda", center_hda)
    output_job.add_output_dataset("output_hda", output_hda)
    output_job.add_output_dataset_collection("output_hdca", output_hdca)
    sa_session.add_all([center_hda, input_hda, input_hdca, output_hdca, input_job, output_job])
    sa_session.commit()
    expected_graph = {
        "inputs": [
            {"src": "HistoryDatasetAssociation", "id": input_hda.id},
            {"src": "HistoryDatasetCollectionAssociation", "id": input_hdca.id},
        ],
        "outputs": [
            {"src": "HistoryDatasetAssociation", "id": output_hda.id},
            {"src": "HistoryDatasetCollectionAssociation", "id": output_hdca.id},
        ],
    }
    return center_hda, expected_graph


def setup_connected_dataset_collection(sa_session: "scoped_session"):
    center_hdca = HistoryDatasetCollectionAssociation()
    input_hda1 = HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True)
    input_hda2 = HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True)
    input_hdca = HistoryDatasetCollectionAssociation()
    output_hda = HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True)
    output_hdca = HistoryDatasetCollectionAssociation()
    input_job = Job()
    output_job = Job()
    input_job.add_output_dataset_collection("output_hdca", center_hdca)
    input_job.add_input_dataset("input_hda", input_hda1)
    input_job.add_input_dataset("input_hda", input_hda2)
    input_job.add_input_dataset_collection("input_hdca", input_hdca)
    output_job.add_input_dataset_collection("input_hdca", center_hdca)
    output_job.add_output_dataset("output_hda", output_hda)
    output_job.add_output_dataset_collection("output_hdca", output_hdca)
    sa_session.add_all([center_hdca, input_hda1, input_hda2, input_hdca, output_hdca, input_job, output_job])
    sa_session.commit()
    expected_graph = {
        "inputs": [
            {"src": "HistoryDatasetAssociation", "id": input_hda1.id},
            {"src": "HistoryDatasetAssociation", "id": input_hda2.id},
            {"src": "HistoryDatasetCollectionAssociation", "id": input_hdca.id},
        ],
        "outputs": [
            {"src": "HistoryDatasetAssociation", "id": output_hda.id},
            {"src": "HistoryDatasetCollectionAssociation", "id": output_hdca.id},
        ],
    }
    return center_hdca, expected_graph


# =============================================================================
def test_graph_manager_inputs_for_hda(job_connections_manager: JobConnectionsManager):
    sa_session = job_connections_manager.sa_session
    center_hda, expected_graph = setup_connected_dataset(sa_session)
    s = job_connections_manager.inputs_for_hda(center_hda.id)
    assert len(sa_session.execute(union(*s)).all()) == 2


def test_graph_manager_outputs_for_hda(job_connections_manager: JobConnectionsManager):
    sa_session = job_connections_manager.sa_session
    center_hda, expected_graph = setup_connected_dataset(sa_session)
    s = job_connections_manager.outputs_derived_from_input_hda(center_hda.id)
    assert len(sa_session.execute(union(*s)).all()) == 2


def test_graph_manager_inputs_for_hdca(job_connections_manager: JobConnectionsManager):
    sa_session = job_connections_manager.sa_session
    center_hdca, expected_graph = setup_connected_dataset_collection(sa_session)
    s = job_connections_manager.inputs_for_hdca(center_hdca.id)
    assert len(sa_session.execute(union(*s)).all()) == 3


def test_graph_manager_outputs_for_hdca(job_connections_manager: JobConnectionsManager):
    sa_session = job_connections_manager.sa_session
    center_hdca, expected_graph = setup_connected_dataset_collection(sa_session)
    s = job_connections_manager.outputs_derived_from_input_hdca(center_hdca.id)
    assert len(sa_session.execute(union(*s)).all()) == 2


def test_graph_manager_hda(job_connections_manager: JobConnectionsManager):
    center_hda, expected_graph = setup_connected_dataset(job_connections_manager.sa_session)
    assert job_connections_manager.get_connections_graph(center_hda.id, "HistoryDatasetAssociation") == expected_graph


def test_graph_manager_hdca(job_connections_manager: JobConnectionsManager):
    center_hdca, expected_graph = setup_connected_dataset_collection(job_connections_manager.sa_session)
    assert (
        job_connections_manager.get_connections_graph(center_hdca.id, "HistoryDatasetCollectionAssociation")
        == expected_graph
    )


@pytest.fixture(params=["dataset", "collection"])
def related_items(sa_session, request):
    history = History()
    sa_session.add(history)
    is_dataset = request.param == "dataset"

    def item(hid, copied_from=None, creating_input=None, history=history):
        value: HistoryDatasetAssociation | HistoryDatasetCollectionAssociation
        if is_dataset:
            value = HistoryDatasetAssociation(sa_session=sa_session, history=history, hid=hid, create_dataset=True)
            if copied_from is not None:
                value.copy_from(copied_from)
        else:
            value = HistoryDatasetCollectionAssociation(
                history=history, hid=hid, collection=DatasetCollection(collection_type="list")
            )
            value.copied_from_history_dataset_collection_association = copied_from
        sa_session.add(value)
        if creating_input is not None:
            job = Job()
            job.history = history
            if isinstance(value, HistoryDatasetAssociation):
                job.add_input_dataset("input", creating_input)
                job.add_output_dataset("output", value)
            else:
                job.add_input_dataset_collection("input", creating_input)
                job.add_output_dataset_collection("output", value)
            sa_session.add(job)
        sa_session.flush()
        return value

    return history, item


def test_related_hids_job_output_copy_boundary(sa_session, related_items):
    history, item = related_items
    grandparent = item(1)
    parent = item(2, creating_input=grandparent)
    passthrough = item(3, copied_from=parent, creating_input=parent)
    item(4, creating_input=parent)
    sa_session.commit()
    manager = JobConnectionsManager(sa_session)
    assert sorted(manager.get_related_hids(history.id, passthrough.hid)) == [2, 3]
    # Mapping back must also distinguish a pass-through output from an ordinary copy.
    assert sorted(manager.get_related_hids(history.id, grandparent.hid)) == [1, 2]
    copied_history = History()
    sa_session.add(copied_history)
    item(12, copied_from=parent, history=copied_history)
    copy = item(13, copied_from=passthrough, history=copied_history)
    item(14, copied_from=copy, history=copied_history)
    sa_session.commit()
    assert sorted(manager.get_related_hids(copied_history.id, 14)) == [12, 14]


def test_related_hids_cached_job_output(sa_session, related_items):
    history, item = related_items
    input_item = item(1)
    original = item(2, creating_input=input_item)
    downstream = item(3, creating_input=original)
    cached = item(4, copied_from=original, creating_input=input_item)
    sa_session.commit()
    manager = JobConnectionsManager(sa_session)
    assert sorted(manager.get_related_hids(history.id, cached.hid)) == [1, 4]
    assert sorted(manager.get_related_hids(history.id, downstream.hid)) == [2, 3]


def test_related_hids_consumers_on_intermediate_copies(sa_session, related_items):
    original_history, item = related_items
    original_input = item(1)
    original_output = item(2, creating_input=original_input)
    imported_history = History()
    sa_session.add(imported_history)
    imported_input = item(11, copied_from=original_input, history=imported_history)
    imported_output = item(12, copied_from=original_output, history=imported_history)
    new_output = item(13, creating_input=imported_input, history=imported_history)
    final_history = History()
    sa_session.add(final_history)
    item(21, copied_from=imported_input, history=final_history)
    item(22, copied_from=imported_output, history=final_history)
    item(23, copied_from=new_output, history=final_history)
    sa_session.commit()
    manager = JobConnectionsManager(sa_session)
    assert sorted(manager.get_related_hids(final_history.id, 21)) == [21, 22, 23]
    assert sorted(manager.get_related_hids(final_history.id, 22)) == [21, 22]
    assert sorted(manager.get_related_hids(final_history.id, 23)) == [21, 23]
    assert sorted(manager.get_related_hids(original_history.id, 1)) == [1, 2]


@pytest.mark.parametrize("depth", [0, 20])
def test_related_hids_deep_copy_query_count(sa_session, related_items, depth):
    history, item = related_items
    source = item(1)
    item(2, creating_input=source)
    for hid in range(3, 3 + depth):
        source = item(hid, copied_from=source)
    sa_session.commit()
    history_id, hid = history.id, source.hid
    statements = []

    def record_statement(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = sa_session.get_bind()
    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        result = JobConnectionsManager(sa_session).get_related_hids(history_id, hid)
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)
    assert sorted(result) == sorted([2, hid])
    assert len(statements) == 2, f"A {depth}-deep copy chain required {len(statements)} statements"


def test_related_hids_shared_dataset_is_not_a_copy(sa_session):
    history = History()
    input_hda = HistoryDatasetAssociation(sa_session=sa_session, history=history, hid=1, create_dataset=True)
    output_hda = HistoryDatasetAssociation(sa_session=sa_session, history=history, hid=2, create_dataset=True)
    hidden_element = HistoryDatasetAssociation(history=history, hid=3, dataset=output_hda.dataset, visible=False)
    job = Job()
    job.add_input_dataset("input", input_hda)
    job.add_output_dataset("output", output_hda)
    sa_session.add_all([history, input_hda, output_hda, hidden_element, job])
    sa_session.commit()
    assert sorted(JobConnectionsManager(sa_session).get_related_hids(history.id, 1)) == [1, 2]


def test_related_hids_cyclic_copy_links(sa_session, related_items):
    history, item = related_items
    first = item(1)
    second = item(2, copied_from=first)
    if isinstance(first, HistoryDatasetAssociation):
        first.copied_from_history_dataset_association = second
    else:
        first.copied_from_history_dataset_collection_association = second
    sa_session.commit()
    assert JobConnectionsManager(sa_session).get_related_hids(history.id, 1) == [1]


@pytest.mark.parametrize("nested", [False, True])
def test_related_hids_hidden_collection_output_copy_boundary(sa_session, nested):
    history = History()
    source = HistoryDatasetAssociation(sa_session=sa_session, history=history, hid=1, create_dataset=True)
    output = HistoryDatasetAssociation(sa_session=sa_session, history=history, hid=2, create_dataset=True)
    hidden = HistoryDatasetAssociation(sa_session=sa_session, history=history, hid=3, create_dataset=True)
    hidden.copy_from(source)
    inner = DatasetCollection(collection_type="list")
    inner.elements = [DatasetCollectionElement(element=hidden, element_identifier="element", element_index=0)]
    if nested:
        outer = DatasetCollection(collection_type="list:list")
        outer.elements = [DatasetCollectionElement(element=inner, element_identifier="list", element_index=0)]
    else:
        outer = inner
    collection = HistoryDatasetCollectionAssociation(history=history, hid=4, collection=outer)
    dataset_job = Job()
    dataset_job.add_input_dataset("input", source)
    dataset_job.add_output_dataset("output", output)
    collection_job = Job()
    collection_job.add_input_dataset("input", source)
    collection_job.add_output_dataset_collection("output", collection)
    sa_session.add_all([history, source, output, hidden, collection, dataset_job, collection_job])
    sa_session.commit()
    manager = JobConnectionsManager(sa_session)
    assert sorted(manager.get_related_hids(history.id, 2)) == [1, 2]
    assert manager.get_related_hids(history.id, 3) == [3]
    copied_history = history.copy()
    sa_session.add(copied_history)
    sa_session.commit()
    assert sorted(manager.get_related_hids(copied_history.id, 2)) == [1, 2]
    assert manager.get_related_hids(copied_history.id, 3) == [3]


@pytest.mark.parametrize("collection_input", [False, True])
def test_related_hids_reused_collection_element_keeps_provenance(sa_session, collection_input):
    original_history = History()
    source = HistoryDatasetAssociation(sa_session=sa_session, history=original_history, hid=1, create_dataset=True)
    output = HistoryDatasetAssociation(sa_session=sa_session, history=original_history, hid=2, create_dataset=True)
    original_job = Job()
    original_job.add_input_dataset("input", source)
    original_job.add_output_dataset("output", output)
    sa_session.add_all([original_history, source, output, original_job])
    sa_session.flush()
    history = original_history.copy()
    sa_session.add(history)
    sa_session.flush()
    copied_source = history.datasets[0]
    collection = DatasetCollection(collection_type="list")
    collection.elements = [
        DatasetCollectionElement(element=copied_source, element_identifier="element", element_index=0)
    ]
    hdca = HistoryDatasetCollectionAssociation(history=history, hid=3, collection=collection)
    job = Job()
    if collection_input:
        input_collection = DatasetCollection(collection_type="list")
        input_collection.elements = [
            DatasetCollectionElement(element=copied_source, element_identifier="element", element_index=0)
        ]
        input_hdca = HistoryDatasetCollectionAssociation(history=history, hid=4, collection=input_collection)
        job.add_input_dataset_collection("input", input_hdca)
        sa_session.add(input_hdca)
    else:
        job.add_input_dataset("input", copied_source)
    job.add_output_dataset_collection("output", hdca)
    sa_session.add_all([hdca, job])
    sa_session.commit()
    expected = [1, 2] if collection_input else [1, 2, 3]
    assert sorted(JobConnectionsManager(sa_session).get_related_hids(history.id, 1)) == expected


def test_related_hids_empty_history(sa_session):
    history = History()
    sa_session.add(history)
    sa_session.commit()
    assert JobConnectionsManager(sa_session).get_related_hids(history.id, 99) == [99]


def test_related_hids_missing_item(sa_session, related_items):
    history, item = related_items
    source = item(1)
    item(2, creating_input=source)
    sa_session.commit()
    assert JobConnectionsManager(sa_session).get_related_hids(history.id, 99) == [99]


def test_related_hids_same_hid_across_item_types(sa_session):
    history = History()
    dataset_input = HistoryDatasetAssociation(sa_session=sa_session, history=history, hid=1, create_dataset=True)
    dataset_output = HistoryDatasetAssociation(sa_session=sa_session, history=history, hid=2, create_dataset=True)
    collection_input = HistoryDatasetCollectionAssociation(
        history=history, hid=1, collection=DatasetCollection(collection_type="list")
    )
    collection_output = HistoryDatasetCollectionAssociation(
        history=history, hid=3, collection=DatasetCollection(collection_type="list")
    )
    dataset_job = Job()
    dataset_job.add_input_dataset("input", dataset_input)
    dataset_job.add_output_dataset("output", dataset_output)
    collection_job = Job()
    collection_job.add_input_dataset_collection("input", collection_input)
    collection_job.add_output_dataset_collection("output", collection_output)
    sa_session.add_all(
        [history, dataset_input, dataset_output, collection_input, collection_output, dataset_job, collection_job]
    )
    sa_session.commit()
    assert sorted(JobConnectionsManager(sa_session).get_related_hids(history.id, 1)) == [1, 2, 3]
