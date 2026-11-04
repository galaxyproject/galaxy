import uuid
from decimal import Decimal
from typing import cast
from unittest import mock

import pytest
from sqlalchemy import (
    create_engine,
    text,
    update,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.celery.tasks import (
    DISK_USAGE_RUNNING_LOCK,
    DISK_USAGE_WAITING_LOCK,
    recalculate_disk_usage_deduplicated,
)
from galaxy.model.unittest_utils.utils import random_email
from galaxy.objectstore import (
    BaseObjectStore,
    build_object_store_from_config,
    QuotaSourceInfo,
    QuotaSourceMap,
    serialize_static_object_store_config,
)
from galaxy.objectstore.unittest_utils import (
    Config,
)
from galaxy.quota import DatabaseQuotaAgent
from .test_galaxy_mapping import (
    BaseModelTestCase,
    create_postgres_test_database,
    MockObjectStore,
    skip_if_not_postgres_base,
)


class TestPurgeUsage(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        u = model.User(email=random_email(), password="password")
        u.disk_usage = Decimal(25)
        self.persist(u)

        h = model.History(name="History for Purging", user=u)
        self.persist(h)
        self.u = u
        self.h = h

    def _setup_dataset(self):
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=self.h, create_dataset=True, sa_session=self.model.session
        )
        assert d1.dataset is not None
        d1.dataset.total_size = Decimal(10)
        d1.dataset.state = model.Dataset.states.OK
        self.persist(d1)
        return d1

    def test_calculate_usage(self):
        d1 = self._setup_dataset()
        quota_source_info = QuotaSourceInfo(None, True)
        d1.purge_usage_from_quota(self.u, quota_source_info)
        self.persist(self.u)
        assert self.u.disk_usage == Decimal(15)

    def test_calculate_usage_running_job_output(self):
        # outputs of running jobs are only charged once the job finishes
        d1 = self._setup_dataset()
        d1.dataset.state = model.Dataset.states.RUNNING
        quota_source_info = QuotaSourceInfo(None, True)
        d1.purge_usage_from_quota(self.u, quota_source_info)
        self.persist(self.u)
        assert self.u.disk_usage == Decimal(25)

    def test_read_usage_with_pending_adjustments(self):
        # adjustments are written when the user is flushed, reading the usage before that applies them first
        self.u.adjust_total_disk_usage(10, None)
        self.u.adjust_total_disk_usage(5, None)
        assert self.u.get_disk_usage() == Decimal(40)
        self.u.adjust_total_disk_usage(-20, None)
        assert self.u.dictify_usage_for(None).total_disk_usage == 20
        self.u.adjust_total_disk_usage(-5, None)
        assert self.u.dictify_usage()[0].total_disk_usage == 15
        self.persist(self.u)
        assert self.u.disk_usage == Decimal(15)

    def test_adjust_usage_keeps_concurrent_adjustments(self):
        # the usage loaded in this session is 25
        assert self.u.disk_usage == Decimal(25)
        # another transaction adds 10 meanwhile, leaving the loaded value stale
        self.model.session.execute(
            update(model.User).where(model.User.id == self.u.id).values(disk_usage=model.User.disk_usage + 10),
            execution_options={"synchronize_session": False},
        )
        self.u.adjust_total_disk_usage(5, None)
        self.persist(self.u)
        assert self.u.disk_usage == Decimal(40)

    def test_adjust_usage_of_unsaved_user(self):
        # added to the session but not flushed, so not in the database yet
        u = model.User(email=random_email(), password="password")
        self.model.session.add(u)
        u.adjust_total_disk_usage(10, None)
        self.persist(u)
        assert u.disk_usage == Decimal(10)

    def test_calculate_usage_untracked(self):
        # test quota tracking off on the objectstore
        d1 = self._setup_dataset()
        quota_source_info = QuotaSourceInfo(None, False)
        d1.purge_usage_from_quota(self.u, quota_source_info)
        self.persist(self.u)
        assert self.u.disk_usage == Decimal(25)

    def test_calculate_usage_per_source(self):
        self.u.adjust_total_disk_usage(124, "myquotalabel")

        # test quota tracking with a non-default quota label
        d1 = self._setup_dataset()
        quota_source_info = QuotaSourceInfo("myquotalabel", True)
        d1.purge_usage_from_quota(self.u, quota_source_info)
        self.persist(self.u)
        assert self.u.disk_usage == Decimal(25)

        usages = self.u.dictify_usage()
        assert len(usages) == 2
        assert usages[1].quota_source_label == "myquotalabel"
        assert usages[1].total_disk_usage == 114


class TestCalculateUsage(BaseModelTestCase):
    def setUp(self):
        self.object_store = cast(BaseObjectStore, MockObjectStore())
        u = model.User(email=f"calc_usage{uuid.uuid1()}@example.com", password="password")
        self.persist(u)
        h = model.History(name="History for Calculated Usage", user=u)
        self.persist(h)
        self.u = u
        self.h = h

    def _add_dataset(self, total_size, object_store_id=None, history=None):
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=history or self.h, create_dataset=True, sa_session=self.model.session
        )
        assert d1.dataset is not None
        d1.dataset.total_size = total_size
        d1.dataset.object_store_id = object_store_id
        d1.dataset.state = model.Dataset.states.OK
        self.persist(d1)
        return d1

    def _copy_to_history(self, hda, history):
        copy = model.HistoryDatasetAssociation(extension="txt", history=history, dataset=hda.dataset)
        self.persist(copy)
        return copy

    def _add_to_library(self, hda):
        ldda = model.LibraryDatasetDatasetAssociation(extension="txt", dataset=hda.dataset)
        self.persist(ldda)
        return ldda

    def _alt_source_object_store(self):
        quota_source_map = QuotaSourceMap()
        alt_source = QuotaSourceMap()
        alt_source.default_quota_source = "alt_source"
        quota_source_map.backends["alt_source_store"] = alt_source
        return cast(BaseObjectStore, MockObjectStore(quota_source_map))

    def test_calculate_usage(self):
        u = self.u
        h = self.h

        d1 = self._add_dataset(10)

        assert u.calculate_disk_usage_default_source(self.object_store) == 10
        assert u.disk_usage is None
        u.calculate_and_set_disk_usage(self.object_store)
        assert u.calculate_disk_usage_default_source(self.object_store) == 10
        # method no longer updates user object
        # assert u.disk_usage == 10

        # Test dataset being in another history doesn't duplicate usage cost.
        h2 = model.History(name="Second usage history", user=u)
        self.persist(h2)
        d2 = model.HistoryDatasetAssociation(extension="txt", history=h2, dataset=d1.dataset)
        self.persist(d2)

        # duplicating dataset within a history also doesn't duplicate usage cost
        d3 = model.HistoryDatasetAssociation(extension="txt", history=h, dataset=d1.dataset)
        self.persist(d3)

        assert u.calculate_disk_usage_default_source(self.object_store) == 10

    def test_calculate_usage_with_user_provided_storage(self):
        u = self.u

        self._add_dataset(10)
        # This dataset should not be counted towards the user's disk usage
        self._add_dataset(30, object_store_id="user_objects://user/provided/storage")

        assert u.calculate_disk_usage_default_source(self.object_store) == 10
        assert u.disk_usage is None
        u.calculate_and_set_disk_usage(self.object_store)
        assert u.calculate_disk_usage_default_source(self.object_store) == 10

        self._refresh_user_and_assert_disk_usage_is(10)

    def test_calculate_usage_readjusts_incorrect_quota(self):
        u = self.u

        self._add_dataset(10)

        assert u.calculate_disk_usage_default_source(self.object_store) == 10
        assert u.disk_usage is None
        u.calculate_and_set_disk_usage(self.object_store)
        assert u.calculate_disk_usage_default_source(self.object_store) == 10

        self._refresh_user_and_assert_disk_usage_is(10)

        # lets break this to simulate the actual bugs we observe in Galaxy.
        u.disk_usage = Decimal(-10)
        self.persist(u)
        self._refresh_user_and_assert_disk_usage_is(-10)

        # recalculate and verify it is fixed
        u.calculate_and_set_disk_usage(self.object_store)
        self._refresh_user_and_assert_disk_usage_is(10)

        # break it again
        u.disk_usage = Decimal(1000)
        self.persist(u)
        self._refresh_user_and_assert_disk_usage_is(1000)

        # recalculate and verify it is fixed
        u.calculate_and_set_disk_usage(self.object_store)
        self._refresh_user_and_assert_disk_usage_is(10)

    def test_calculate_objectstore_usage(self):
        # not strictly a quota check but such similar code and ideas...
        u = self.u

        self._add_dataset(10, "not_tracked")
        self._add_dataset(15, "tracked")

        usage = u.dictify_objectstore_usage()
        assert len(usage) == 2

        usage_dict = {u.object_store_id: u.total_disk_usage for u in usage}
        assert int(usage_dict["not_tracked"]) == 10
        assert int(usage_dict["tracked"]) == 15

    def test_calculate_usage_disabled_quota(self):
        u = self.u

        self._add_dataset(10, "not_tracked")
        self._add_dataset(15, "tracked")

        quota_source_map = QuotaSourceMap()
        not_tracked = QuotaSourceMap()
        not_tracked.default_quota_enabled = False
        quota_source_map.backends["not_tracked"] = not_tracked

        object_store = cast(BaseObjectStore, MockObjectStore(quota_source_map))

        assert u.calculate_disk_usage_default_source(object_store) == 15

    def test_calculate_usage_alt_quota(self):
        u = self.u

        self._add_dataset(10)
        self._add_dataset(15, "alt_source_store")

        quota_source_map = QuotaSourceMap()
        alt_source = QuotaSourceMap()
        alt_source.default_quota_source = "alt_source"
        quota_source_map.backends["alt_source_store"] = alt_source

        object_store = cast(BaseObjectStore, MockObjectStore(quota_source_map))

        u.calculate_and_set_disk_usage(object_store)
        self.model.context.refresh(u)
        usages = u.dictify_usage(object_store)
        assert len(usages) == 2
        assert usages[0].quota_source_label is None
        assert usages[0].total_disk_usage == 10

        assert usages[1].quota_source_label == "alt_source"
        assert usages[1].total_disk_usage == 15

        usage = u.dictify_usage_for(None)
        assert usage.quota_source_label is None
        assert usage.total_disk_usage == 10

        usage = u.dictify_usage_for("alt_source")
        assert usage.quota_source_label == "alt_source"
        assert usage.total_disk_usage == 15

        usage = u.dictify_usage_for("unused_source")
        assert usage.quota_source_label == "unused_source"
        assert usage.total_disk_usage == 0

    def test_calculate_usage_removes_unused_quota_labels(self):
        u = self.u

        d = self._add_dataset(10)
        self._add_dataset(15, "alt_source_store")

        quota_source_map = QuotaSourceMap()
        alt_source = QuotaSourceMap()
        alt_source.default_quota_source = "alt_source"
        quota_source_map.backends["alt_source_store"] = alt_source

        object_store = cast(BaseObjectStore, MockObjectStore(quota_source_map))

        u.calculate_and_set_disk_usage(object_store)
        self.model.context.refresh(u)
        usages = u.dictify_usage()
        assert len(usages) == 2
        assert usages[0].quota_source_label is None
        assert usages[0].total_disk_usage == 10

        assert usages[1].quota_source_label == "alt_source"
        assert usages[1].total_disk_usage == 15

        alt_source.default_quota_source = "new_alt_source"
        u.calculate_and_set_disk_usage(object_store)
        self.model.context.refresh(u)
        usages = u.dictify_usage()
        assert len(usages) == 2
        assert usages[0].quota_source_label is None
        assert usages[0].total_disk_usage == 10

        assert usages[1].quota_source_label == "new_alt_source"
        assert usages[1].total_disk_usage == 15

        d.dataset.deleted = True
        d.purge_usage_from_quota(u, quota_source_map.info)
        self.model.session.add(d)
        self.model.session.flush()
        self.model.context.refresh(u)

        usages = u.dictify_usage()
        assert len(usages) == 2
        assert usages[0].quota_source_label is None
        assert usages[0].total_disk_usage == 0

    def test_dictify_usage_unused_quota_labels(self):
        u = self.u

        self._add_dataset(10)
        self._add_dataset(15, "alt_source_store")

        quota_source_map = QuotaSourceMap()
        alt_source = QuotaSourceMap()
        alt_source.default_quota_source = "alt_source"
        quota_source_map.backends["alt_source_store"] = alt_source

        unused_source = QuotaSourceMap()
        unused_source.default_quota_source = "unused_source"
        quota_source_map.backends["unused_source_store"] = unused_source

        object_store = cast(BaseObjectStore, MockObjectStore(quota_source_map))
        u.calculate_and_set_disk_usage(object_store)
        self.model.context.refresh(u)
        usages = u.dictify_usage(object_store)
        assert len(usages) == 3

    def test_calculate_usage_default_storage_disabled(self):
        u = self.u

        self._add_dataset(10)
        self._add_dataset(15, "alt_source_store")

        quota_source_map = QuotaSourceMap(None, False)
        alt_source = QuotaSourceMap("alt_source", True)
        quota_source_map.backends["alt_source_store"] = alt_source

        object_store = cast(BaseObjectStore, MockObjectStore(quota_source_map))

        u.calculate_and_set_disk_usage(object_store)
        self.model.context.refresh(u)
        usages = u.dictify_usage(object_store)
        assert len(usages) == 2
        assert usages[0].quota_source_label is None
        assert usages[0].total_disk_usage == 0

        assert usages[1].quota_source_label == "alt_source"
        assert usages[1].total_disk_usage == 15

    def test_update_usage_from_labeled_to_unlabeled(self):
        quota_agent = DatabaseQuotaAgent(self.model)
        u = self.u

        self._add_dataset(10)
        alt_d = self._add_dataset(15, "alt_source_store")
        self.model.session.flush()
        assert quota_agent

        quota_source_map = QuotaSourceMap(None, True)
        alt_source = QuotaSourceMap("alt_source", True)
        quota_source_map.backends["alt_source_store"] = alt_source

        object_store = cast(BaseObjectStore, MockObjectStore(quota_source_map))
        u.calculate_and_set_disk_usage(object_store)
        self._refresh_user_and_assert_disk_usage_is(10)
        quota_agent.relabel_quota_for_dataset(alt_d.dataset, "alt_source", None)
        self._refresh_user_and_assert_disk_usage_is(25)
        self._refresh_user_and_assert_disk_usage_is(0, "alt_source")

    def test_update_usage_from_unlabeled_to_labeled(self):
        quota_agent = DatabaseQuotaAgent(self.model)
        u = self.u

        d = self._add_dataset(10)
        self._add_dataset(15, "alt_source_store")
        self.model.session.flush()
        assert quota_agent

        quota_source_map = QuotaSourceMap(None, True)
        alt_source = QuotaSourceMap("alt_source", True)
        quota_source_map.backends["alt_source_store"] = alt_source

        object_store = cast(BaseObjectStore, MockObjectStore(quota_source_map))
        u.calculate_and_set_disk_usage(object_store)
        self._refresh_user_and_assert_disk_usage_is(15, "alt_source")
        quota_agent.relabel_quota_for_dataset(d.dataset, None, "alt_source")
        self._refresh_user_and_assert_disk_usage_is(25, "alt_source")
        self._refresh_user_and_assert_disk_usage_is(0, None)

    def test_update_usage_skips_users_holding_only_purged_copies(self):
        moved = self._add_dataset(10)
        moved.purged = True
        self._assert_moving_dataset_keeps_usage(moved.dataset)

    def test_update_usage_skips_copies_in_purged_histories(self):
        purged_history = model.History(name="Purged history", user=self.u)
        purged_history.purged = True
        self.persist(purged_history)
        moved = self._add_dataset(10)
        moved.history = purged_history
        self._assert_moving_dataset_keeps_usage(moved.dataset)

    def test_update_usage_skips_datasets_in_libraries(self):
        moved = self._add_dataset(10)
        self.persist(model.LibraryDatasetDatasetAssociation(dataset=moved.dataset))
        self._assert_moving_dataset_keeps_usage(moved.dataset)

    def _assert_moving_dataset_keeps_usage(self, moved_dataset):
        """Moving a dataset the user's usage doesn't count, next to one of 15 bytes, leaves the usage unchanged."""
        u = self.u
        self._add_dataset(15)
        self.model.session.flush()
        quota_source_map = QuotaSourceMap(None, True)
        quota_source_map.backends["alt_source_store"] = QuotaSourceMap("alt_source", True)
        u.calculate_and_set_disk_usage(cast(BaseObjectStore, MockObjectStore(quota_source_map)))
        expected_usage = {None: 15, "alt_source": 0}
        assert self._usage_by_quota_source() == expected_usage

        DatabaseQuotaAgent(self.model).relabel_quota_for_dataset(moved_dataset, None, "alt_source")
        assert self._usage_by_quota_source() == expected_usage

    def _usage_by_quota_source(self):
        self.model.context.refresh(self.u)
        return {usage.quota_source_label: int(usage.total_disk_usage) for usage in self.u.dictify_usage()}

    def test_calculate_usage_excludes_library_datasets(self):
        u = self.u
        self._add_dataset(10, "files")
        in_library = self._add_dataset(20, "files")
        self._add_to_library(in_library)
        in_two_libraries = self._add_dataset(40, "files")
        self._add_to_library(in_two_libraries)
        self._add_to_library(in_two_libraries)

        assert u.calculate_disk_usage_default_source(self.object_store) == 10
        u.calculate_and_set_disk_usage(self.object_store)
        self._refresh_user_and_assert_disk_usage_is(10)
        assert {r.object_store_id: int(r.total_disk_usage) for r in u.dictify_objectstore_usage()} == {"files": 10}

    def test_calculate_usage_excludes_purged_hdas_and_histories(self):
        u = self.u
        self._add_dataset(10)
        deleted = self._add_dataset(20)
        deleted.deleted = True
        self.persist(deleted)
        purged = self._add_dataset(40)
        purged.deleted = True
        purged.purged = True
        self.persist(purged)
        purged_history = model.History(name="Purged history", user=u)
        purged_history.deleted = True
        purged_history.purged = True
        self.persist(purged_history)
        self._add_dataset(80, history=purged_history)
        # a purged copy does not hide the dataset while another copy is unpurged
        kept = self._add_dataset(160)
        purged_copy = self._copy_to_history(kept, self.h)
        purged_copy.purged = True
        self.persist(purged_copy)

        assert u.calculate_disk_usage_default_source(self.object_store) == 190
        u.calculate_and_set_disk_usage(self.object_store)
        self._refresh_user_and_assert_disk_usage_is(190)

    def test_calculate_usage_dataset_shared_with_other_user(self):
        u = self.u
        other_user = model.User(email=f"calc_usage_other{uuid.uuid1()}@example.com", password="password")
        other_history = model.History(name="Other user history", user=other_user)
        self.persist(other_user, other_history)
        shared = self._add_dataset(10)
        self._copy_to_history(shared, other_history)
        self._add_dataset(20, history=other_history)

        assert u.calculate_disk_usage_default_source(self.object_store) == 10
        assert other_user.calculate_disk_usage_default_source(self.object_store) == 30
        u.calculate_and_set_disk_usage(self.object_store)
        other_user.calculate_and_set_disk_usage(self.object_store)
        self._refresh_user_and_assert_disk_usage_is(10)
        self.model.context.refresh(other_user)
        assert other_user.disk_usage == 30

    def test_calculate_usage_falls_back_to_file_size(self):
        u = self.u
        d = self._add_dataset(None)
        d.dataset.file_size = 7
        self.persist(d)
        self._add_dataset(None)

        assert u.calculate_disk_usage_default_source(self.object_store) == 7
        u.calculate_and_set_disk_usage(self.object_store)
        self._refresh_user_and_assert_disk_usage_is(7)

    def test_calculate_usage_alt_quota_excludes_library_purged_and_user_objects(self):
        u = self.u
        self._add_dataset(10)
        self._add_to_library(self._add_dataset(20))
        self._add_dataset(40, "alt_source_store")
        self._add_to_library(self._add_dataset(80, "alt_source_store"))
        purged = self._add_dataset(160, "alt_source_store")
        purged.purged = True
        self.persist(purged)
        self._add_dataset(320, "user_objects://user/provided/storage")
        object_store = self._alt_source_object_store()

        u.calculate_and_set_disk_usage(object_store)
        self._refresh_user_and_assert_disk_usage_is(10)
        self._refresh_user_and_assert_disk_usage_is(40, "alt_source")
        assert {r.object_store_id: int(r.total_disk_usage) for r in u.dictify_objectstore_usage()} == {
            "alt_source_store": 40,
            "user_objects://user/provided/storage": 320,
        }

    def test_calculate_usage_alt_quota_without_datasets(self):
        u = self.u
        self._add_dataset(10)
        object_store = self._alt_source_object_store()

        u.calculate_and_set_disk_usage(object_store)
        self.model.context.refresh(u)
        usages = u.dictify_usage()
        assert [(usage.quota_source_label, usage.total_disk_usage) for usage in usages] == [
            (None, 10),
            ("alt_source", 0),
        ]

    def _refresh_user_and_assert_disk_usage_is(self, usage, label=None):
        u = self.u
        self.model.context.refresh(u)
        if label is None:
            assert u.disk_usage == usage
        else:
            usages = u.dictify_usage()
            for uqbu in usages:
                if uqbu.quota_source_label == label:
                    assert int(uqbu.total_disk_usage) == int(usage)


@skip_if_not_postgres_base
class TestCalculateUsagePostgres(TestCalculateUsage):
    @classmethod
    def _db_uri(cls):
        return create_postgres_test_database()


@skip_if_not_postgres_base
class TestRecalculateDiskUsageDeduplicatedPostgres(BaseModelTestCase):
    @classmethod
    def _db_uri(cls):
        return create_postgres_test_database()

    def setUp(self):
        self.object_store = cast(BaseObjectStore, MockObjectStore())
        self.u = model.User(email=random_email(), password="password")
        h = model.History(name="History for deduplicated usage", user=self.u)
        d = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        assert d.dataset is not None
        d.dataset.total_size = Decimal(10)
        self.persist(self.u, h, d)
        self.lock_params = {"user_id": self.u.id}

    def test_recalculates_usage(self):
        assert recalculate_disk_usage_deduplicated(self.model.session(), self.u, self.object_store)
        self.model.context.refresh(self.u)
        assert self.u.disk_usage == 10

    def test_skips_while_another_recalculation_is_waiting(self):
        waiting_lock = {"lock": DISK_USAGE_WAITING_LOCK, **self.lock_params}
        with self.model.engine.connect() as waiting:
            waiting.execute(text("SELECT pg_advisory_lock(:lock, :user_id)"), waiting_lock)
            assert not recalculate_disk_usage_deduplicated(self.model.session(), self.u, self.object_store)
            waiting.execute(text("SELECT pg_advisory_unlock(:lock, :user_id)"), waiting_lock)
        self.model.context.refresh(self.u)
        assert self.u.disk_usage is None

    def test_recalculates_with_a_single_pooled_connection(self):
        engine = create_engine(self.model.engine.url, pool_size=1, max_overflow=0, pool_timeout=1)
        try:
            with Session(engine) as session:
                user = session.get(model.User, self.u.id)
                assert user
                assert recalculate_disk_usage_deduplicated(session, user, self.object_store)
        finally:
            engine.dispose()
        self.model.context.refresh(self.u)
        assert self.u.disk_usage == 10

    def test_waits_for_running_recalculation_within_time_limit(self):
        with self.model.engine.connect() as running:
            running.execute(
                text("SELECT pg_advisory_xact_lock(:lock, :user_id)"),
                {"lock": DISK_USAGE_RUNNING_LOCK, **self.lock_params},
            )
            with mock.patch("galaxy.celery.tasks.RECALCULATE_DISK_USAGE_TIME_LIMIT", 1):
                with pytest.raises(OperationalError, match="statement timeout"):
                    recalculate_disk_usage_deduplicated(self.model.session(), self.u, self.object_store)
            self.model.session.rollback()
            # the waiting slot is free again for the next recalculation
            waiting_lock = {"lock": DISK_USAGE_WAITING_LOCK, **self.lock_params}
            assert running.scalar(text("SELECT pg_try_advisory_lock(:lock, :user_id)"), waiting_lock)
            running.execute(text("SELECT pg_advisory_unlock(:lock, :user_id)"), waiting_lock)
            running.rollback()
        assert recalculate_disk_usage_deduplicated(self.model.session(), self.u, self.object_store)
        self.model.context.refresh(self.u)
        assert self.u.disk_usage == 10


class TestQuota(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        self.quota_agent = DatabaseQuotaAgent(self.model)

    def test_quota(self):
        u = model.User(email="quota@example.com", password="password")
        self.persist(u)

        self._assert_user_quota_is(u, None)

        quota = model.Quota(name="default registered", amount=20)
        self.quota_agent.set_default_quota(
            model.DefaultQuotaAssociation.types.REGISTERED,
            quota,
        )

        self._assert_user_quota_is(u, 20)

        quota = model.Quota(name="user quota add", amount=30, operation="+")
        self._add_user_quota(u, quota)

        self._assert_user_quota_is(u, 50)

        quota = model.Quota(name="user quota bigger base", amount=70, operation="=")
        self._add_user_quota(u, quota)

        self._assert_user_quota_is(u, 100)

        quota = model.Quota(name="user quota del", amount=10, operation="-")
        self._add_user_quota(u, quota)

        self._assert_user_quota_is(u, 90)

        quota = model.Quota(name="group quota add", amount=7, operation="+")
        self._add_group_quota(u, quota)
        self._assert_user_quota_is(u, 97)

        quota = model.Quota(name="group quota bigger base", amount=100, operation="=")
        self._add_group_quota(u, quota)
        self._assert_user_quota_is(u, 127)

        quota.deleted = True
        self.persist(quota)
        self._assert_user_quota_is(u, 97)

        quota = model.Quota(name="group quota unlimited", amount=-1, operation="=")
        self._add_group_quota(u, quota)
        self._assert_user_quota_is(u, None)

    def test_labeled_quota(self):
        u = model.User(email="labeled_quota@example.com", password="password")
        self.persist(u)

        label1 = "coollabel1"
        self._assert_user_quota_is(u, None, label1)

        quota = model.Quota(name="default registered labeled", amount=21, quota_source_label=label1)
        self.quota_agent.set_default_quota(
            model.DefaultQuotaAssociation.types.REGISTERED,
            quota,
        )

        self._assert_user_quota_is(u, 21, label1)

        quota = model.Quota(name="user quota add labeled", amount=31, operation="+", quota_source_label=label1)
        self._add_user_quota(u, quota)

        self._assert_user_quota_is(u, 52, label1)

    def _add_group_quota(self, user, quota):
        group = model.Group()
        uga = model.UserGroupAssociation(user, group)
        gqa = model.GroupQuotaAssociation(group=group, quota=quota)
        self.persist(group, uga, quota, gqa, user)

    def _add_user_quota(self, user, quota):
        uqa = model.UserQuotaAssociation(user=user, quota=quota)
        user.quotas.append(uqa)
        self.persist(quota, uqa, user)

    def _assert_user_quota_is(self, user, amount, quota_source_label=None):
        actual_quota = self.quota_agent.get_quota(user, quota_source_label=quota_source_label)
        assert amount == actual_quota, f"Expected quota [{amount}], got [{actual_quota}]"
        quota_source_map = QuotaSourceMap()
        if quota_source_label is None:
            if amount is None:
                user.total_disk_usage = 1000
                job = model.Job()
                job.user = user
                assert not self.quota_agent.is_over_quota(quota_source_map, job)
            else:
                job = model.Job()
                job.user = user
                user.total_disk_usage = amount - 1
                assert not self.quota_agent.is_over_quota(quota_source_map, job)
                user.total_disk_usage = amount + 1
                assert self.quota_agent.is_over_quota(quota_source_map, job)


class TestQuotaObjectStore(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        u = model.User(email=f"calc_usage{uuid.uuid1()}@example.com", password="password")
        self.persist(u)
        h = model.History(name="History for Calculated Usage", user=u)
        self.persist(h)
        self.u = u
        self.h = h

        self.quota_agent = DatabaseQuotaAgent(self.model)

    def test_labeled_quota_objectstore(self):
        """
        setup an object store with 3 backends with 2 quota sources
        - backends "files" and "legacy" count for a quota source "permanent"
        - backend "files-scratch"
        setup corresponding default quotas for the quota sources

        - add datasets to each of the backends such that the default quotas are (just) not violated
        - assert that jobs targeting files / files-scratch pass the quota check

        - add datasets such that quotas are violated
        - assert that jobs targeting files / files-scratch violate the quota check
        """

        DISTRIBUTED_TEST_CONFIG_YAML = """
type: distributed
search_for_missing: true
backends:
  - id: "files"
    type: disk
    device: "files"
    weight: 1
    store_by: uuid
    allow_selection: true
    private: false
    quota:
      source: permanent
    name: "Permanent Storage"
    description: Data in Permanent Storage is not deleted automatically.  Default quota is X.
    files_dir: database/files_24.1/
    badges:
      - type: not_backed_up
  - id: "files-scratch"
    type: disk
    device: "files"
    weight: 0
    store_by: uuid
    allow_selection: true
    private: true
    quota:
      source: scratch
    name: "Scratch storage"
    description: "Data in scratch storage is scheduled for automatic removal after Y days. Default quota is Z."
    files_dir: database/files_24.1/
    badges:
      - type: not_backed_up
      - type: short_term
        message: "Data stored here is scheduled for removal after 30 days"
  - id: legacy
    type: disk
    store_by: id
    quota:
      source: permanent
    weight: 0
    files_dir: database/files/
"""
        with Config(DISTRIBUTED_TEST_CONFIG_YAML) as (directory, object_store):
            as_dict = serialize_static_object_store_config(object_store, set())
            self.object_store = build_object_store_from_config(None, config_dict=as_dict)

        quota = model.Quota(name="default permanent quota", amount=20, quota_source_label="permanent")
        self.quota_agent.set_default_quota(
            model.DefaultQuotaAssociation.types.REGISTERED,
            quota,
        )

        quota = model.Quota(name="default scratch quota", amount=100, quota_source_label="scratch")
        self.quota_agent.set_default_quota(
            model.DefaultQuotaAssociation.types.REGISTERED,
            quota,
        )

        self._add_dataset(10, "legacy")
        self._add_dataset(10, "files")
        self._add_dataset(100, "files-scratch")
        self.u.calculate_and_set_disk_usage(self.object_store)

        self._run_job("files", False)
        self._run_job("files-scratch", False)

        self._add_dataset(1, "files")
        self._add_dataset(1, "files-scratch")
        self.u.calculate_and_set_disk_usage(self.object_store)

        self._run_job("files", True)
        self._run_job("files-scratch", True)

    def _add_dataset(self, total_size, object_store_id=None):
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=self.h, create_dataset=True, sa_session=self.model.session
        )
        assert d1.dataset is not None
        d1.dataset.total_size = total_size
        d1.dataset.object_store_id = object_store_id
        self.persist(d1)
        return d1

    def _run_job(self, object_store_id, over_quota):
        """
        check if a job targeting object_store_id is over_quota
        """
        job = model.Job()
        job.user = self.u
        job.object_store_id = object_store_id
        assert over_quota is self.quota_agent.is_over_quota(self.object_store.get_quota_source_map(), job)


class TestUsage(BaseModelTestCase):
    def test_usage(self):
        u = model.User(email="usage@example.com", password="password")
        self.persist(u)

        u.adjust_total_disk_usage(123, None)
        self.persist(u)

        assert u.get_disk_usage() == 123

    def test_labeled_usage(self):
        u = model.User(email="labeled.usage@example.com", password="password")
        self.persist(u)
        assert len(u.quota_source_usages) == 0

        u.adjust_total_disk_usage(123, "foobar")
        usages = u.dictify_usage()
        assert len(usages) == 1

        assert u.get_disk_usage() == 0
        assert u.get_disk_usage(quota_source_label="foobar") == 123
        self.model.context.refresh(u)

        usages = u.dictify_usage()
        assert len(usages) == 2

        u.adjust_total_disk_usage(124, "foobar")
        self.model.context.refresh(u)

        usages = u.dictify_usage()
        assert len(usages) == 2
        assert usages[1].quota_source_label == "foobar"
        assert usages[1].total_disk_usage == 247
