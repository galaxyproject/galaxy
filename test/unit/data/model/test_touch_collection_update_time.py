"""
Unit tests for Dataset.touch_collection_update_time() functionality.

Tests both the recursive CTE approach and the Python fallback implementation
across different database backends and collection hierarchy scenarios.
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.model.unittest_utils.model_testing_utils import persist


@pytest.fixture(scope="module")
def engine():
    """Create test database engine."""
    db_uri = "sqlite:///:memory:"
    return create_engine(db_uri)


@pytest.fixture(scope="module")
def init_model(engine):
    """Create model objects in the engine's database."""
    model.mapper_registry.metadata.create_all(engine)


@pytest.fixture
def session(init_model, engine):
    """Create test database session with all Galaxy model tables."""
    with Session(engine) as s:
        yield s


@pytest.fixture
def user(session):
    """Create a test user."""
    unique_id = uuid.uuid4().hex[:8]
    user = model.User(username=f"test_user_{unique_id}", email=f"test_{unique_id}@example.com", password="password123")
    user_id = persist(session, user)
    return session.get(model.User, user_id)


@pytest.fixture
def history(session, user):
    """Create a test history."""
    history = model.History(name="Test History", user=user)
    history_id = persist(session, history)
    return session.get(model.History, history_id)


@pytest.fixture
def dataset(session):
    """Create a test dataset."""
    dataset = model.Dataset(state="ok")
    dataset_id = persist(session, dataset)
    return session.get(model.Dataset, dataset_id)


@pytest.fixture
def hda(session, history, dataset):
    """Create a test HistoryDatasetAssociation."""
    hda = model.HistoryDatasetAssociation(dataset=dataset, history=history, name="Test Dataset", hid=1)
    hda_id = persist(session, hda)
    return session.get(model.HistoryDatasetAssociation, hda_id)


def create_simple_collection_hierarchy(session, hda):
    """
    Create a simple collection hierarchy:
    HDCA -> Collection -> DCE -> HDA
    """
    # Create a collection
    collection = model.DatasetCollection(collection_type="list")
    collection_id = persist(session, collection)
    collection = session.get(model.DatasetCollection, collection_id)

    # Create collection element linking collection to HDA
    dce = model.DatasetCollectionElement(
        collection=collection, element=hda, element_identifier="item1", element_index=0
    )
    persist(session, dce)

    # Create HDCA
    hdca = model.HistoryDatasetCollectionAssociation(
        collection_id=collection.id, history_id=hda.history.id, name="Test Collection", hid=2
    )
    hdca_id = persist(session, hdca)
    return session.get(model.HistoryDatasetCollectionAssociation, hdca_id)


def create_nested_collection_hierarchy(session, hda):
    """
    Create a nested collection hierarchy:
    HDCA -> Collection1 -> DCE -> Collection2 -> DCE -> HDA
    """
    # Create inner collection (contains the HDA)
    inner_collection = model.DatasetCollection(collection_type="list")
    inner_collection_id = persist(session, inner_collection)
    inner_collection = session.get(model.DatasetCollection, inner_collection_id)

    # Create DCE linking inner collection to HDA
    inner_dce = model.DatasetCollectionElement(
        collection=inner_collection, element=hda, element_identifier="inner_item", element_index=0
    )
    persist(session, inner_dce)

    # Create outer collection
    outer_collection = model.DatasetCollection(collection_type="list:list")
    outer_collection_id = persist(session, outer_collection)
    outer_collection = session.get(model.DatasetCollection, outer_collection_id)

    # Create DCE linking outer collection to inner collection
    outer_dce = model.DatasetCollectionElement(
        collection=outer_collection, element=inner_collection, element_identifier="outer_item", element_index=0
    )
    persist(session, outer_dce)

    # Create HDCA for outer collection
    hdca = model.HistoryDatasetCollectionAssociation(
        collection_id=outer_collection.id, history_id=hda.history.id, name="Nested Collection", hid=3
    )
    hdca_id = persist(session, hdca)
    return session.get(model.HistoryDatasetCollectionAssociation, hdca_id)


def create_multiple_hdca_hierarchy(session, hda):
    """
    Create a hierarchy with multiple HDCAs referencing the same collection:
    HDCA1 -> Collection -> DCE -> HDA
    HDCA2 -> Collection (same as above)
    """
    # Create a collection
    collection = model.DatasetCollection(collection_type="list")
    collection_id = persist(session, collection)
    collection = session.get(model.DatasetCollection, collection_id)

    # Create collection element linking collection to HDA
    dce = model.DatasetCollectionElement(
        collection=collection, element=hda, element_identifier="shared_item", element_index=0
    )
    persist(session, dce)

    # Create first HDCA
    hdca1 = model.HistoryDatasetCollectionAssociation(
        collection_id=collection.id, history_id=hda.history.id, name="Shared Collection 1", hid=4
    )
    hdca1_id = persist(session, hdca1)

    # Create second HDCA referencing the same collection
    hdca2 = model.HistoryDatasetCollectionAssociation(
        collection_id=collection.id, history_id=hda.history.id, name="Shared Collection 2", hid=5
    )
    hdca2_id = persist(session, hdca2)

    return (
        session.get(model.HistoryDatasetCollectionAssociation, hdca1_id),
        session.get(model.HistoryDatasetCollectionAssociation, hdca2_id),
    )


class TestTouchCollectionUpdateTime:
    """Test cases for Dataset.touch_collection_update_time() method."""

    def test_no_collections(self, session, dataset):
        """Test that touch_collection_update_time works when dataset is not in any collections."""
        # Should not raise any errors
        dataset.touch_collection_update_time()
        session.commit()

    def test_simple_collection_hierarchy(self, session, hda):
        """Test updating a simple collection hierarchy."""
        hdca = create_simple_collection_hierarchy(session, hda)

        # Record original update time
        original_time = hdca.update_time

        # Touch collection update time
        hda.dataset.touch_collection_update_time()
        session.commit()

        # Refresh from database
        session.refresh(hdca)

        # Verify update time was changed
        assert hdca.update_time > original_time

    def test_nested_collection_hierarchy(self, session, hda):
        """Test updating a nested collection hierarchy."""
        hdca = create_nested_collection_hierarchy(session, hda)

        # Record original update time
        original_time = hdca.update_time

        # Touch collection update time
        hda.dataset.touch_collection_update_time()
        session.commit()

        # Refresh from database
        session.refresh(hdca)

        # Verify update time was changed
        assert hdca.update_time > original_time

    def test_multiple_hdcas_same_collection(self, session, hda):
        """Test updating multiple HDCAs that reference the same collection."""
        hdca1, hdca2 = create_multiple_hdca_hierarchy(session, hda)

        # Record original update times
        original_time1 = hdca1.update_time
        original_time2 = hdca2.update_time

        # Touch collection update time
        hda.dataset.touch_collection_update_time()
        session.commit()

        # Refresh from database
        session.refresh(hdca1)
        session.refresh(hdca2)

        # Verify both HDCAs were updated
        assert hdca1.update_time > original_time1
        assert hdca2.update_time > original_time2

    def test_multiple_hdas_same_dataset(self, session, dataset, history, user):
        """Test updating collections when dataset has multiple HDAs."""
        # Create two HDAs for the same dataset
        hda1 = model.HistoryDatasetAssociation(dataset=dataset, history=history, name="Test Dataset 1", hid=1)
        persist(session, hda1)

        hda2 = model.HistoryDatasetAssociation(dataset=dataset, history=history, name="Test Dataset 2", hid=2)
        persist(session, hda2)

        # Create collections for each HDA
        hdca1 = create_simple_collection_hierarchy(session, hda1)
        hdca2 = create_simple_collection_hierarchy(session, hda2)

        # Record original update times
        original_time1 = hdca1.update_time
        original_time2 = hdca2.update_time

        # Touch collection update time on the dataset
        dataset.touch_collection_update_time()
        session.commit()

        # Refresh from database
        session.refresh(hdca1)
        session.refresh(hdca2)

        # Verify both HDCAs were updated
        assert hdca1.update_time > original_time1
        assert hdca2.update_time > original_time2

    def test_cte_approach(self, session, hda):
        """Test CTE implementation."""
        hdca = create_simple_collection_hierarchy(session, hda)
        original_time = hdca.update_time
        # This should use the SQLite CTE path
        hda.dataset.touch_collection_update_time()
        session.commit()
        assert hdca.update_time > original_time

    def test_fallback_approach(self, session, hda):
        """Test Python fallback implementation updates HDCA properly."""
        hdca = create_simple_collection_hierarchy(session, hda)

        # Record original update time
        original_time = hdca.update_time

        # Create a second session to avoid the dialect mock interfering with refresh
        with Session(session.bind) as fallback_session:
            # Get the dataset and hda in the new session
            dataset = fallback_session.get(model.Dataset, hda.dataset.id)
            assert dataset

            # Mock the dialect on the fallback session to force Python fallback
            with patch.object(fallback_session.bind, "dialect") as mock_dialect:
                mock_dialect.name = "unknown_db"

                # This should use the Python fallback path
                dataset.touch_collection_update_time()
                fallback_session.commit()

        # Refresh the HDCA in the original session to see the updates
        session.refresh(hdca)

        # Verify update time was changed
        assert hdca.update_time > original_time

    def test_depth_limiting(self, session, hda):
        """Test that very deep hierarchies are handled with depth limiting."""
        # Create a deep hierarchy (this tests the depth limit logic)
        current_collection = None
        collections = []

        # Create 5 levels of nested collections
        for i in range(5):
            collection = model.DatasetCollection(collection_type=f"list{':list' * i}")
            collection_id = persist(session, collection)
            collection = session.get(model.DatasetCollection, collection_id)
            collections.append(collection)

            if i == 0:
                # First level: connect to HDA
                dce = model.DatasetCollectionElement(
                    collection=collection, element=hda, element_identifier=f"item_{i}", element_index=0
                )
            else:
                # Subsequent levels: connect to previous collection
                dce = model.DatasetCollectionElement(
                    collection=collection, element=current_collection, element_identifier=f"item_{i}", element_index=0
                )
            persist(session, dce)
            current_collection = collection

        # Create HDCA for the top-level collection
        hdca = model.HistoryDatasetCollectionAssociation(
            collection=current_collection, history=hda.history, name="Deep Collection", hid=10
        )
        hdca_id = persist(session, hdca)
        hdca = session.get(model.HistoryDatasetCollectionAssociation, hdca_id)

        original_time = hdca.update_time

        # Should handle deep hierarchy without issues
        hda.dataset.touch_collection_update_time()
        session.commit()

        session.refresh(hdca)
        assert hdca.update_time > original_time

    def test_empty_collections(self, session, history):
        """Test behavior with empty collections (no elements)."""
        # Create empty collection
        collection = model.DatasetCollection(collection_type="list")
        collection_id = persist(session, collection)
        collection = session.get(model.DatasetCollection, collection_id)

        # Create HDCA for empty collection
        hdca = model.HistoryDatasetCollectionAssociation(
            collection=collection, history=history, name="Empty Collection", hid=1
        )
        persist(session, hdca)

        # Create a dataset not in any collection and get it back from session
        dataset = model.Dataset(state="ok")
        dataset_id = persist(session, dataset)
        dataset = session.get(model.Dataset, dataset_id)

        # Should not affect empty collections
        dataset.touch_collection_update_time()
        session.commit()
