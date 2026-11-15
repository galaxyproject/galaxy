import contextlib
import os
import shutil
import threading
from typing import Union
from unittest.mock import patch

from sqlalchemy import (
    event,
    func,
    select,
)
from sqlalchemy.orm.scoping import scoped_session

import galaxy.datatypes.registry
import galaxy.model
import galaxy.model.mapping as mapping
from galaxy.model import (
    History,
    HistoryDatasetAssociation,
    HistoryDatasetAssociationHistory,
    MetadataFile,
    setup_global_object_store_for_models,
    User,
)
from galaxy.model.base import get_before_flush_handler
from galaxy.model.metadata import MetadataTempFile
from galaxy.objectstore.s3_boto3 import S3ObjectStore as Boto3ObjectStore
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


def test_copy_from_gives_target_and_its_copies_their_own_metadata_files():
    with _setup_mapping_and_user() as (test_config, object_store, model, history):
        session = model.context
        source = _create_hda(
            model, object_store, history, test_config.write("moo", "source"), include_metadata_file=True
        )
        # A queued output that a job cache hit fills in, and a copy of it made while it was queued.
        target = _create_hda(model, object_store, history, test_config.write("cow", "target"))
        target_copy = target.copy(flush=False)
        history.add_dataset(target_copy)
        session.commit()

        target.copy_from(source, include_metadata=True)
        session.commit()

        index_ids = set()
        for hda in (source, target, target_copy):
            index = hda.metadata.bam_index
            assert index.history_dataset is hda
            with open(index.get_file_name()) as f:
                assert f.read() == "moo"
            index_ids.add(index.id)
        assert len(index_ids) == 3


def test_copy_from_the_same_source_twice_copies_metadata_files_once():
    # A cached job's structured collection output is copied as a job output and again as a collection element.
    with _setup_mapping_and_user() as (test_config, object_store, model, history):
        session = model.context
        source = _create_hda(
            model, object_store, history, test_config.write("moo", "source"), include_metadata_file=True
        )
        target = _create_hda(model, object_store, history, test_config.write("cow", "target"))
        session.commit()

        target.copy_from(source, include_metadata=True)
        target.copy_from(source, include_metadata=True)
        session.commit()

        owned = session.scalars(select(MetadataFile).where(MetadataFile.hda_id == target.id)).all()
        assert owned == [target.metadata.bam_index]


def test_copy_from_leaves_the_transaction_to_the_caller():
    # Job.copy_from_job holds row locks until it commits; the default disk object store stores by id.
    with _setup_mapping_and_user() as (test_config, object_store, model, history):
        session = model.context
        source = _create_hda(
            model, object_store, history, test_config.write("moo", "source"), include_metadata_file=True
        )
        target = _create_hda(model, object_store, history, test_config.write("cow", "target"))
        session.commit()

        target.copy_from(source, include_metadata=True)
        assert target.metadata.bam_index.id != source.metadata.bam_index.id
        session.rollback()

        assert session.scalar(select(func.count(MetadataFile.id))) == 1


def test_copy_from_inserts_each_metadata_file_row_once():
    # A job cache hit over a mapped collection copies a metadata file per element; insert each row complete.
    with _setup_mapping_and_user() as (test_config, object_store, model, history):
        session = model.context
        source = _create_hda(
            model, object_store, history, test_config.write("moo", "source"), include_metadata_file=True
        )
        target = _create_hda(model, object_store, history, test_config.write("cow", "target"))
        session.commit()

        statements = []

        def record(conn, cursor, statement, *args):
            statements.append(statement)

        engine = session.get_bind()
        event.listen(engine, "before_cursor_execute", record)
        try:
            target.copy_from(source, include_metadata=True)
            session.commit()
        finally:
            event.remove(engine, "before_cursor_execute", record)

        assert len([s for s in statements if s.startswith("INSERT INTO metadata_file")]) == 1
        assert not [s for s in statements if s.startswith("UPDATE metadata_file")]
        assert target.metadata.bam_index.object_store_id == target.dataset.object_store_id


class InMemoryRemoteBoto3ObjectStore(Boto3ObjectStore):
    """A boto3 object store whose bucket is a dict; records downloads and existence checks."""

    def _initialize(self):
        self.remote: dict[str, bytes] = {}
        self.downloads: list[str] = []
        self.existence_checks: list[str] = []

    def _exists_remotely(self, rel_path: str) -> bool:
        self.existence_checks.append(rel_path)
        return rel_path in self.remote

    def _get_remote_size(self, rel_path: str) -> int:
        return len(self.remote[rel_path])

    def _download(self, rel_path: str) -> bool:
        self.downloads.append(rel_path)
        cache_path = self._get_cache_path(rel_path)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "wb") as fh:
            fh.write(self.remote[rel_path])
        return True

    def _push_string_to_path(self, rel_path: str, from_string: str) -> bool:
        self.remote[rel_path] = from_string.encode()
        return True

    def _push_file_to_path(self, rel_path: str, source_file: str) -> bool:
        with open(source_file, "rb") as fh:
            self.remote[rel_path] = fh.read()
        return True

    def _delete_existing_remote(self, rel_path: str) -> bool:
        return self.remote.pop(rel_path, None) is not None


BOTO3_TEST_CONFIG = """
type: boto3
auth:
  access_key: access_moo
  secret_key: secret_cow
bucket:
  name: unique_bucket_name_all_lowercase
cache:
  path: "${temp_directory}/object_store_cache"
  size: 1000
extra_dirs:
- type: job_work
  path: "${temp_directory}/job_working_directory"
- type: temp
  path: "${temp_directory}/tmp"
"""


@patch("galaxy.objectstore.s3_boto3.S3ObjectStore", InMemoryRemoteBoto3ObjectStore)
def test_copy_from_writes_metadata_files_without_downloading_them():
    # A synced get_filename() would download the new, empty object only for update_from_file to replace it.
    with _setup_mapping_and_user(BOTO3_TEST_CONFIG) as (test_config, object_store, model, history):
        session = model.context
        source = _create_hda(
            model, object_store, history, test_config.write("moo", "source"), include_metadata_file=True
        )
        target = _create_hda(model, object_store, history, test_config.write("cow", "target"))
        session.commit()

        target.copy_from(source, include_metadata=True)
        session.commit()
        assert not object_store.downloads
        # Each remote existence check is a request; a job cache hit over a mapped collection copies a file per element.
        copied = target.metadata.bam_index
        copied_checks = [p for p in object_store.existence_checks if p.endswith(f"metadata_{copied.id}.dat")]
        assert len(copied_checks) == 1

        # Re-set metadata on a node whose cache lacks the copied file's directory.
        cache_path = copied.get_file_name(sync_cache=False)
        shutil.rmtree(os.path.dirname(cache_path))
        copied.update_from_file(test_config.write("oink", "regenerated_index"))

        assert not object_store.downloads
        assert os.path.exists(cache_path)
        with open(cache_path) as fh:
            assert fh.read() == "oink"


@patch("galaxy.objectstore.s3_boto3.S3ObjectStore", InMemoryRemoteBoto3ObjectStore)
def test_update_from_file_without_a_file_name_uploads_the_stored_file():
    with _setup_mapping_and_user(BOTO3_TEST_CONFIG, store_by="uuid") as (test_config, object_store, model, history):
        hda = _create_hda(model, object_store, history, test_config.write("moo", "source"))
        index = hda.datatype.metadata_spec["bam_index"].param.new_file(dataset=hda)
        with open(index.get_file_name(), "w") as fh:
            fh.write("index")
        checks_before = len(object_store.existence_checks)

        index.update_from_file(None)

        (remote_path,) = (p for p in object_store.remote if p.endswith(f"metadata_{index.uuid}.dat"))
        assert object_store.remote[remote_path] == b"index"
        assert len(object_store.existence_checks) == checks_before + 1


class RegisteringRucioBroker:
    def __init__(self, object_store):
        self.registrations: list[tuple[str, str]] = []

    def data_object_exists(self, rel_path):
        return False

    def get_size(self, rel_path):
        return 0

    def register(self, rel_path, source):
        self.registrations.append((rel_path, source))


RUCIO_REGISTER_ONLY_TEST_CONFIG = """
type: rucio
register_only: true
enable_cache_monitor: false
cache:
  path: "${temp_directory}/cache"
"""


@patch("galaxy.objectstore.rucio.RucioBroker", RegisteringRucioBroker)
def test_update_from_file_without_a_file_name_registers_the_stored_file():
    with _setup_mapping_and_user(RUCIO_REGISTER_ONLY_TEST_CONFIG, store_by="uuid") as (_, object_store, model, history):
        hda = HistoryDatasetAssociation(extension="bam", create_dataset=True, sa_session=model.context)
        history.add_dataset(hda)
        index = hda.datatype.metadata_spec["bam_index"].param.new_file(dataset=hda)
        path = index.get_file_name()
        with open(path, "w") as fh:
            fh.write("index")

        index.update_from_file(None)

        assert [source for _, source in object_store.rucio_broker.registrations] == [path]


HIERARCHICAL_TEST_CONFIG = """
type: hierarchical
backends:
- type: disk
  files_dir: "${temp_directory}/files1"
  extra_dirs:
  - type: temp
    path: "${temp_directory}/tmp1"
  - type: job_work
    path: "${temp_directory}/job_working_directory1"
- type: disk
  files_dir: "${temp_directory}/files2"
  extra_dirs:
  - type: temp
    path: "${temp_directory}/tmp2"
  - type: job_work
    path: "${temp_directory}/job_working_directory2"
"""


def test_updating_a_metadata_file_keeps_it_in_its_hierarchical_backend():
    with _setup_mapping_and_user(HIERARCHICAL_TEST_CONFIG) as (test_config, object_store, model, history):
        hda = _create_hda(model, object_store, history, test_config.write("moo", "source"), include_metadata_file=True)
        index = hda.metadata.bam_index
        primary_path = index.get_file_name()
        primary_root = os.path.join(test_config.temp_directory, "files1")
        secondary_path = primary_path.replace(primary_root, os.path.join(test_config.temp_directory, "files2"))
        os.makedirs(os.path.dirname(secondary_path))
        shutil.move(primary_path, secondary_path)

        index.update_from_file(test_config.write("oink", "regenerated_index"))

        assert not os.path.exists(primary_path)
        with open(secondary_path) as fh:
            assert fh.read() == "oink"


def test_copying_metadata_files_onto_an_output_not_yet_in_a_history(monkeypatch):
    # A job cache hit at submission fills the output before it joins the history; Galaxy's tests reject flushing it.
    with _setup_mapping_and_user(store_by="uuid") as (test_config, object_store, model, history):
        session = model.context
        source = _create_hda(
            model, object_store, history, test_config.write("moo", "source"), include_metadata_file=True
        )
        session.commit()
        monkeypatch.setenv("GALAXY_TEST_RAISE_EXCEPTION_ON_HISTORYLESS_HDA", "1")
        event.listen(session, "before_flush", get_before_flush_handler())

        output = HistoryDatasetAssociation(extension="bam", dataset=source.dataset, sa_session=session, flush=False)
        session.add(output)
        output.metadata = source.metadata
        history.add_dataset(output)
        session.commit()

        assert output.metadata.bam_index.id != source.metadata.bam_index.id
        with open(output.metadata.bam_index.get_file_name()) as fh:
            assert fh.read() == "moo"


def test_output_flushed_before_joining_its_history_gets_no_version():
    # Under store_by id, copying a metadata file flushes the output of a job cache hit at submission.
    with _setup_mapping_and_user() as (test_config, object_store, model, history):
        session = model.context
        source = _create_hda(
            model, object_store, history, test_config.write("moo", "source"), include_metadata_file=True
        )
        source.dataset.state = "ok"
        session.commit()

        output = HistoryDatasetAssociation(extension="bam", dataset=source.dataset, sa_session=session, flush=False)
        session.add(output)
        output.metadata = source.metadata
        assert output.id is not None
        output.name = "cached output"
        history.add_dataset(output)
        session.commit()

        assert output.version == 1
        versions = select(func.count(HistoryDatasetAssociationHistory.id)).where(
            HistoryDatasetAssociationHistory.history_dataset_association_id == output.id
        )
        assert session.scalar(versions) == 0

        output.name = "renamed"
        session.commit()
        assert output.version == 2
        assert session.scalar(versions) == 1


@contextlib.contextmanager
def _setup_mapping_and_user(config_str=DISK_TEST_CONFIG, store_by="id"):
    with TestConfig(config_str, store_by=store_by) as (test_config, object_store):
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
    object_store.update_from_file(hda.dataset, file_name=path, create=True)
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
    store_by = hda.dataset.object_store.get_store_by(hda.dataset)
    assert copied_index.endswith(f"metadata_{getattr(hda.metadata.bam_index, store_by)}.dat")
