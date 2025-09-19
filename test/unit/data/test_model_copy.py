import contextlib
import os
import threading
from typing import Union

from sqlalchemy.orm.scoping import scoped_session

import galaxy.datatypes.registry
import galaxy.model
import galaxy.model.mapping as mapping
from galaxy.model import (
    History,
    HistoryDatasetAssociation,
    setup_global_object_store_for_models,
    User,
)
from galaxy.model.metadata import MetadataTempFile
from galaxy.objectstore.unittest_utils import (
    Config as TestConfig,
    DISK_TEST_CONFIG,
)
from galaxy.util import ExecutionTimer

datatypes_registry = galaxy.datatypes.registry.Registry()
datatypes_registry.load_datatypes()
galaxy.model.set_datatypes_registry(datatypes_registry)

NUM_DATASETS = 3
NUM_COLLECTIONS = 1
SLOW_QUERY_LOG_THRESHOLD = 1000
INCLUDE_METADATA_FILE = True
THREAD_LOCAL_LOG = threading.local()


def test_history_dataset_copy(num_datasets=NUM_DATASETS, include_metadata_file=INCLUDE_METADATA_FILE):
    with _setup_mapping_and_user() as (test_config, object_store, model, old_history):
        for i in range(num_datasets):
            hda_path = test_config.write("moo", f"test_metadata_original_{i}")
            _create_hda(model, object_store, old_history, hda_path, include_metadata_file=include_metadata_file)

        session = model.context
        session.commit()

        history_copy_timer = ExecutionTimer()
        original_update_time = old_history.update_time
        assert original_update_time
        new_history = old_history.copy(name="new name", target_user=old_history.user, all_datasets=True)
        session.add(new_history)
        session.add(old_history)
        session.commit()
        session.refresh(old_history)
        new_update_time = session.get(model.History, old_history.id).update_time
        assert original_update_time == new_update_time
        print(f"history copied {history_copy_timer}")
        assert new_history.name == "new name"
        assert new_history.user == old_history.user
        for hda in new_history.active_datasets:
            assert hda.get_size() == 3
            if include_metadata_file:
                _check_metadata_file(hda)
            annotation_str = hda.get_item_annotation_str(model.context, old_history.user, hda)
            assert annotation_str == f"annotation #{hda.hid}", annotation_str


def test_history_collection_copy(list_size=NUM_DATASETS):
    with _setup_mapping_and_user() as (test_config, object_store, model, old_history):
        for i in range(NUM_COLLECTIONS):
            hdas = []
            for i in range(list_size * 2):
                hda_path = test_config.write("moo", f"test_metadata_original_{i}")
                hda = _create_hda(
                    model, object_store, old_history, hda_path, visible=False, include_metadata_file=False
                )
                hdas.append(hda)

            session = model.context
            list_elements = []
            list_collection = model.DatasetCollection(collection_type="list:paired")
            for j in range(list_size):
                paired_collection = model.DatasetCollection(collection_type="paired")
                forward_dce = model.DatasetCollectionElement(collection=paired_collection, element=hdas[j * 2])
                reverse_dce = model.DatasetCollectionElement(collection=paired_collection, element=hdas[j * 2 + 1])
                paired_collection_element = model.DatasetCollectionElement(
                    collection=list_collection, element=paired_collection
                )
                list_elements.append(paired_collection_element)
                session.add_all([forward_dce, reverse_dce, paired_collection_element])
            history_dataset_collection = model.HistoryDatasetCollectionAssociation(collection=list_collection)
            history_dataset_collection.user = old_history.user
            session.add(history_dataset_collection)
            session.commit()

            old_history.add_dataset_collection(history_dataset_collection)
            history_dataset_collection.add_item_annotation(
                session,
                old_history.user,
                history_dataset_collection,
                f"annotation #{history_dataset_collection.hid}",
            )

        session.commit()

        annotation_str = history_dataset_collection.get_item_annotation_str(
            session, old_history.user, history_dataset_collection
        )

        # Saving magic SA invocations for detecting full flushes that may harm performance.
        # from sqlalchemy import event
        # @event.listens_for(model.context, "before_flush")
        # def track_instances_before_flush(session, context, instances):
        #     if not instances:
        #         print("FULL FLUSH...")
        #     else:
        #         print(f"Flushing just {instances}")

        history_copy_timer = ExecutionTimer()
        new_history = old_history.copy(target_user=old_history.user)
        print(f"history copied {history_copy_timer}")

        for hda in new_history.active_datasets:
            assert hda.get_size() == 3
            annotation_str = hda.get_item_annotation_str(session, old_history.user, hda)
            assert annotation_str == f"annotation #{hda.hid}", annotation_str

        assert len(new_history.active_dataset_collections) == NUM_COLLECTIONS
        for hdca in new_history.active_dataset_collections:
            annotation_str = hdca.get_item_annotation_str(session, old_history.user, hdca)
            assert annotation_str == f"annotation #{hdca.hid}", annotation_str


@contextlib.contextmanager
def _setup_mapping_and_user():
    with TestConfig(DISK_TEST_CONFIG) as (test_config, object_store):
        # Start the database and connect the mapping
        model = mapping.init(
            "/tmp",
            "sqlite:///:memory:",
            create_tables=True,
            slow_query_log_threshold=SLOW_QUERY_LOG_THRESHOLD,
            thread_local_log=THREAD_LOCAL_LOG,
        )
        setup_global_object_store_for_models(object_store)

        u = User(email="historycopy@example.com", password="password")
        h1 = History(name="HistoryCopyHistory1", user=u)
        session = model.context
        session.add_all([u, h1])
        session.commit()
        yield test_config, object_store, model, h1


def _create_hda(
    has_session: Union[mapping.GalaxyModelMapping, scoped_session],
    object_store,
    history,
    path,
    visible=True,
    include_metadata_file=False,
):
    if hasattr(has_session, "context"):
        sa_session = has_session.context
    else:
        sa_session = has_session
    hda = HistoryDatasetAssociation(extension="bam", create_dataset=True, sa_session=sa_session)
    hda.visible = visible
    sa_session.add(hda)
    sa_session.commit()
    object_store.update_from_file(hda, file_name=path, create=True)
    if include_metadata_file:
        hda.metadata.from_JSON_dict(json_dict={"bam_index": MetadataTempFile.from_JSON({"kwds": {}, "filename": path})})
        _check_metadata_file(hda)
    hda.set_size()
    history.add_dataset(hda)
    hda.add_item_annotation(sa_session, history.user, hda, f"annotation #{hda.hid}")
    return hda


def _check_metadata_file(hda):
    assert hda.metadata.bam_index.id
    copied_index = hda.metadata.bam_index.get_file_name()
    assert os.path.exists(copied_index)
    with open(copied_index) as f:
        assert f.read() == "moo"
    assert copied_index.endswith(f"metadata_{hda.id}.dat")
