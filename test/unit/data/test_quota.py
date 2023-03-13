import uuid

from galaxy import model
from galaxy.objectstore import (
    QuotaSourceInfo,
    QuotaSourceMap,
)
from galaxy.quota import DatabaseQuotaAgent
from .test_galaxy_mapping import (
    BaseModelTestCase,
    MockObjectStore,
)


class TestPurgeUsage(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        model = self.model
        u = model.User(email="purge_usage@example.com", password="password")
        u.disk_usage = 25
        self.persist(u)

        h = model.History(name="History for Purging", user=u)
        self.persist(h)
        self.u = u
        self.h = h

    def _setup_dataset(self):
        d1 = self.model.HistoryDatasetAssociation(
            extension="txt", history=self.h, create_dataset=True, sa_session=self.model.session
        )
        d1.dataset.total_size = 10
        self.persist(d1)
        return d1

    def test_calculate_usage(self):
        d1 = self._setup_dataset()
        quota_source_info = QuotaSourceInfo(None, True)
        d1.purge_usage_from_quota(self.u, quota_source_info)
        self.persist(self.u)
        assert int(self.u.disk_usage) == 15

    def test_calculate_usage_untracked(self):
        # test quota tracking off on the objectstore
        d1 = self._setup_dataset()
        quota_source_info = QuotaSourceInfo(None, False)
        d1.purge_usage_from_quota(self.u, quota_source_info)
        self.persist(self.u)
        assert int(self.u.disk_usage) == 25

    def test_calculate_usage_per_source(self):
        self.u.adjust_total_disk_usage(124, "myquotalabel")

        # test quota tracking with a non-default quota label
        d1 = self._setup_dataset()
        quota_source_info = QuotaSourceInfo("myquotalabel", True)
        d1.purge_usage_from_quota(self.u, quota_source_info)
        self.persist(self.u)
        assert int(self.u.disk_usage) == 25

        usages = self.u.dictify_usage()
        assert len(usages) == 2
        assert usages[1].quota_source_label == "myquotalabel"
        assert usages[1].total_disk_usage == 114


class TestCalculateUsage(BaseModelTestCase):
    def setUp(self):
        model = self.model
        u = model.User(email="calc_usage%s@example.com" % str(uuid.uuid1()), password="password")
        self.persist(u)
        h = model.History(name="History for Calculated Usage", user=u)
        self.persist(h)
        self.u = u
        self.h = h

    def _add_dataset(self, total_size, object_store_id=None):
        model = self.model
        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=self.h, create_dataset=True, sa_session=self.model.session
        )
        d1.dataset.total_size = total_size
        d1.dataset.object_store_id = object_store_id
        self.persist(d1)
        return d1

    def test_calculate_usage(self):
        model = self.model
        u = self.u
        h = self.h

        d1 = self._add_dataset(10)

        object_store = MockObjectStore()
        assert u.calculate_disk_usage_default_source(object_store) == 10
        assert u.disk_usage is None
        u.calculate_and_set_disk_usage(object_store)
        assert u.calculate_disk_usage_default_source(object_store) == 10
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

        assert u.calculate_disk_usage_default_source(object_store) == 10

    def test_calculate_usage_disabled_quota(self):
        u = self.u

        self._add_dataset(10, "not_tracked")
        self._add_dataset(15, "tracked")

        quota_source_map = QuotaSourceMap()
        not_tracked = QuotaSourceMap()
        not_tracked.default_quota_enabled = False
        quota_source_map.backends["not_tracked"] = not_tracked

        object_store = MockObjectStore(quota_source_map)

        assert u.calculate_disk_usage_default_source(object_store) == 15

    def test_calculate_usage_alt_quota(self):
        model = self.model
        u = self.u

        self._add_dataset(10)
        self._add_dataset(15, "alt_source_store")

        quota_source_map = QuotaSourceMap()
        alt_source = QuotaSourceMap()
        alt_source.default_quota_source = "alt_source"
        quota_source_map.backends["alt_source_store"] = alt_source

        object_store = MockObjectStore(quota_source_map)

        u.calculate_and_set_disk_usage(object_store)
        model.context.refresh(u)
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
        model = self.model
        u = self.u

        self._add_dataset(10)
        self._add_dataset(15, "alt_source_store")

        quota_source_map = QuotaSourceMap()
        alt_source = QuotaSourceMap()
        alt_source.default_quota_source = "alt_source"
        quota_source_map.backends["alt_source_store"] = alt_source

        object_store = MockObjectStore(quota_source_map)

        u.calculate_and_set_disk_usage(object_store)
        model.context.refresh(u)
        usages = u.dictify_usage()
        assert len(usages) == 2
        assert usages[0].quota_source_label is None
        assert usages[0].total_disk_usage == 10

        assert usages[1].quota_source_label == "alt_source"
        assert usages[1].total_disk_usage == 15

        alt_source.default_quota_source = "new_alt_source"
        u.calculate_and_set_disk_usage(object_store)
        model.context.refresh(u)
        usages = u.dictify_usage()
        assert len(usages) == 2
        assert usages[0].quota_source_label is None
        assert usages[0].total_disk_usage == 10

        assert usages[1].quota_source_label == "new_alt_source"
        assert usages[1].total_disk_usage == 15

    def test_dictify_usage_unused_quota_labels(self):
        model = self.model
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

        object_store = MockObjectStore(quota_source_map)
        u.calculate_and_set_disk_usage(object_store)
        model.context.refresh(u)
        usages = u.dictify_usage(object_store)
        assert len(usages) == 3

    def test_calculate_usage_default_storage_disabled(self):
        model = self.model
        u = self.u

        self._add_dataset(10)
        self._add_dataset(15, "alt_source_store")

        quota_source_map = QuotaSourceMap(None, False)
        alt_source = QuotaSourceMap("alt_source", True)
        quota_source_map.backends["alt_source_store"] = alt_source

        object_store = MockObjectStore(quota_source_map)

        u.calculate_and_set_disk_usage(object_store)
        model.context.refresh(u)
        usages = u.dictify_usage(object_store)
        assert len(usages) == 2
        assert usages[0].quota_source_label is None
        assert usages[0].total_disk_usage == 0

        assert usages[1].quota_source_label == "alt_source"
        assert usages[1].total_disk_usage == 15


class TestQuota(BaseModelTestCase):
    def setUp(self):
        super().setUp()
        model = self.model
        self.quota_agent = DatabaseQuotaAgent(model)

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
        model = self.model
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
        if quota_source_label is None:
            if amount is None:
                user.total_disk_usage = 1000
                job = self.model.Job()
                job.user = user
                assert not self.quota_agent.is_over_quota(None, job, None)
            else:
                job = self.model.Job()
                job.user = user
                user.total_disk_usage = amount - 1
                assert not self.quota_agent.is_over_quota(None, job, None)
                user.total_disk_usage = amount + 1
                assert self.quota_agent.is_over_quota(None, job, None)


class TestUsage(BaseModelTestCase):
    def test_usage(self):
        model = self.model
        u = model.User(email="usage@example.com", password="password")
        self.persist(u)

        u.adjust_total_disk_usage(123, None)
        self.persist(u)

        assert u.get_disk_usage() == 123

    def test_labeled_usage(self):
        model = self.model
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
