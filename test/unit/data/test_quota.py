from galaxy.quota import DatabaseQuotaAgent
from .test_galaxy_mapping import BaseModelTestCase


class QuotaTestCase(BaseModelTestCase):

    def setUp(self):
        super().setUp()
        model = self.model
        self.quota_agent = DatabaseQuotaAgent(model)

    def test_quota(self):
        model = self.model
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
        group = self.model.Group()
        uga = self.model.UserGroupAssociation(user, group)
        gqa = self.model.GroupQuotaAssociation(group=group, quota=quota)
        self.persist(group, uga, quota, gqa, user)

    def _add_user_quota(self, user, quota):
        uqa = self.model.UserQuotaAssociation(user=user, quota=quota)
        user.quotas.append(uqa)
        self.persist(quota, uqa, user)

    def _assert_user_quota_is(self, user, amount):
        assert amount == self.quota_agent.get_quota(user)
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
