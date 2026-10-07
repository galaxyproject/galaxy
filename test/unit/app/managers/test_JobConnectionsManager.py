from typing import TYPE_CHECKING

import pytest
from sqlalchemy import union

from galaxy.managers.job_connections import JobConnectionsManager
from galaxy.model import (
    DatasetCollection,
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


def setup_connected_history(sa_session: "scoped_session"):
    history = History()
    sa_session.add(history)
    sa_session.commit()

    def new_hda():
        hda = HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True)
        history.add_dataset(hda)
        return hda

    def new_hdca():
        hdca = HistoryDatasetCollectionAssociation(collection=DatasetCollection(collection_type="list"))
        history.add_dataset_collection(hdca)
        return hdca

    input_hda, output_hda, input_hdca, output_hdca = new_hda(), new_hda(), new_hdca(), new_hdca()
    unrelated_hda, unrelated_hdca = new_hda(), new_hdca()
    dataset_job = Job()
    dataset_job.add_input_dataset("input", input_hda)
    dataset_job.add_input_dataset_collection("input_collection", input_hdca)
    dataset_job.add_output_dataset("output", output_hda)
    collection_job = Job()
    collection_job.add_input_dataset_collection("input", input_hdca)
    collection_job.add_output_dataset_collection("output", output_hdca)
    sa_session.add_all([dataset_job, collection_job])
    sa_session.commit()
    hids = [input_hda.hid, output_hda.hid, input_hdca.hid, output_hdca.hid, unrelated_hda.hid, unrelated_hdca.hid]
    assert hids == [1, 2, 3, 4, 5, 6]
    return history


# related hids by hid for the history built by setup_connected_history
EXPECTED_RELATED_HIDS = {1: [1, 2], 2: [1, 2, 3], 3: [2, 3, 4], 4: [3, 4], 5: [5], 6: [6]}


def assert_related_hids(manager: JobConnectionsManager, history_id: int, expected: dict[int, list[int]]):
    for hid, related in expected.items():
        assert sorted(manager.get_related_hids(history_id, hid)) == related, hid


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


def test_related_hids(job_connections_manager: JobConnectionsManager):
    history = setup_connected_history(job_connections_manager.sa_session)
    assert_related_hids(job_connections_manager, history.id, EXPECTED_RELATED_HIDS)
    # jobs reference the original items, not the copies made on import
    copied_history = history.copy()
    assert_related_hids(job_connections_manager, copied_history.id, EXPECTED_RELATED_HIDS)


def test_related_hids_copied_items_new_hids(job_connections_manager: JobConnectionsManager):
    sa_session = job_connections_manager.sa_session
    history = setup_connected_history(sa_session)
    target = History()
    sa_session.add(target)
    target.add_dataset(HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True))
    target.add_dataset(HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True))
    # copy items into another history so they get different hids than their originals
    hid_map = {}
    for hda in sorted(history.datasets, key=lambda hda: hda.hid, reverse=True):
        copied_hda = hda.copy(copy_hid=False, flush=False)
        target.add_dataset(copied_hda)
        hid_map[hda.hid] = copied_hda.hid
    for hdca in sorted(history.dataset_collections, key=lambda hdca: hdca.hid, reverse=True):
        copied_hdca = hdca.copy(flush=False, set_hid=False)
        target.add_dataset_collection(copied_hdca)
        hid_map[hdca.hid] = copied_hdca.hid
    sa_session.commit()
    assert hid_map == {5: 3, 2: 4, 1: 5, 6: 6, 4: 7, 3: 8}
    expected = {hid_map[hid]: sorted(hid_map[r] for r in related) for hid, related in EXPECTED_RELATED_HIDS.items()}
    assert_related_hids(job_connections_manager, target.id, expected)


def test_related_hids_jobs_on_copies(job_connections_manager: JobConnectionsManager):
    sa_session = job_connections_manager.sa_session
    history = setup_connected_history(sa_session)
    copied_history = history.copy()
    copied_input = next(hda for hda in copied_history.datasets if hda.hid == 1)
    new_output = HistoryDatasetAssociation(sa_session=sa_session, create_dataset=True)
    copied_history.add_dataset(new_output)
    job = Job()
    job.add_input_dataset("input", copied_input)
    job.add_output_dataset("output", new_output)
    sa_session.add(job)
    sa_session.commit()
    assert new_output.hid == 7
    expected = {**EXPECTED_RELATED_HIDS, 1: [1, 2, 7], 7: [1, 7]}
    assert_related_hids(job_connections_manager, copied_history.id, expected)
    # copy chains of depth two
    assert_related_hids(job_connections_manager, copied_history.copy().id, expected)
    # the original history is unaffected by jobs run on its copies
    assert_related_hids(job_connections_manager, history.id, EXPECTED_RELATED_HIDS)
