from galaxy import model
from galaxy.quota import DatabaseQuotaAgent
from .test_galaxy_mapping import BaseModelTestCase


class CalculateUsageTestCase(BaseModelTestCase):
    def test_calculate_usage(self):
        u = model.User(email="calc_usage@example.com", password="password")
        self.persist(u)

        h = model.History(name="History for Usage", user=u)
        self.persist(h)

        d1 = model.HistoryDatasetAssociation(
            extension="txt", history=h, create_dataset=True, sa_session=self.model.session
        )
        d1.dataset.total_size = 10
        self.persist(d1)

        assert u.calculate_disk_usage() == 10
        assert u.disk_usage is None
        u.calculate_and_set_disk_usage()
        assert u.disk_usage == 10

        # Test dataset being in another history doesn't duplicate usage cost.
        h2 = model.History(name="Second usage history", user=u)
        self.persist(h2)
        d2 = model.HistoryDatasetAssociation(extension="txt", history=h2, dataset=d1.dataset)
        self.persist(d2)

        # duplicating dataset within a history also doesn't duplicate usage cost
        d3 = model.HistoryDatasetAssociation(extension="txt", history=h, dataset=d1.dataset)
        self.persist(d3)

        assert u.calculate_disk_usage() == 10


class QuotaTestCase(BaseModelTestCase):
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

    def _add_group_quota(self, user, quota):
        group = model.Group()
        uga = model.UserGroupAssociation(user, group)
        gqa = model.GroupQuotaAssociation(group=group, quota=quota)
        self.persist(group, uga, quota, gqa, user)

    def _add_user_quota(self, user, quota):
        uqa = model.UserQuotaAssociation(user=user, quota=quota)
        user.quotas.append(uqa)
        self.persist(quota, uqa, user)

    def _assert_user_quota_is(self, user, amount):
        assert amount == self.quota_agent.get_quota(user)
        if amount is None:
            user.total_disk_usage = 1000
            job = model.Job()
            job.user = user
            assert not self.quota_agent.is_over_quota(None, job, None)
        else:
            job = model.Job()
            job.user = user
            user.total_disk_usage = amount - 1
            assert not self.quota_agent.is_over_quota(None, job, None)
            user.total_disk_usage = amount + 1
            assert self.quota_agent.is_over_quota(None, job, None)
