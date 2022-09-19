"""Galaxy Quotas"""
import logging

import galaxy.util

log = logging.getLogger(__name__)


class QuotaAgent:  # metaclass=abc.ABCMeta
    """Abstraction around querying Galaxy for quota available and used.

    Certain parts of the app that deal directly with modifying the quota assume more than
    this interface - they assume the availability of the methods on DatabaseQuotaAgent that
    implements this interface. But for read-only quota operations - such as checking available
    quota or reporting it to users - methods defined on this interface should be sufficient
    and the NoQuotaAgent should be a valid choice.

    Sticking to well annotated methods on this interface should make it clean and
    possible to implement other backends for quota setting in the future such as managing
    the quota in other apps (LDAP maybe?) or via configuration files.
    """

    # TODO: make abstractmethod after they work better with mypy
    def get_quota(self, user):
        """Return quota in bytes or None if no quota is set."""

    def get_quota_nice_size(self, user):
        """Return quota as a human-readable string or 'unlimited' if no quota is set."""
        quota_bytes = self.get_quota(user)
        if quota_bytes is not None:
            quota_str = galaxy.util.nice_size(quota_bytes)
        else:
            quota_str = "unlimited"
        return quota_str

    # TODO: make abstractmethod after they work better with mypy
    def get_percent(self, trans=None, user=False, history=False, usage=False, quota=False):
        """Return the percentage of any storage quota applicable to the user/transaction."""

    def get_usage(self, trans=None, user=False, history=False):
        if trans:
            user = trans.user
            history = trans.history
        assert user is not False, "Could not determine user."
        if not user:
            assert history, "Could not determine anonymous user's history."
            usage = history.disk_size
        else:
            usage = user.total_disk_usage
        return usage

    def is_over_quota(self, app, job, job_destination):
        """Return True if the user or history is over quota for specified job.

        job_destination unused currently but an important future application will
        be admins and/or users dynamically specifying which object stores to use
        and that will likely come in through the job destination.
        """


class NoQuotaAgent(QuotaAgent):
    """Base quota agent, always returns no quota"""

    def __init__(self):
        pass

    def get_quota(self, user):
        return None

    @property
    def default_quota(self):
        return None

    def get_percent(self, trans=None, user=False, history=False, usage=False, quota=False):
        return None

    def is_over_quota(self, app, job, job_destination):
        return False


class DatabaseQuotaAgent(QuotaAgent):
    """Class that handles galaxy quotas"""

    def __init__(self, model):
        self.model = model
        self.sa_session = model.context

    def get_quota(self, user):
        """
        Calculated like so:

            1. Anonymous users get the default quota.
            2. Logged in users start with the highest of their associated '='
               quotas or the default quota, if there are no associated '='
               quotas.  If an '=' unlimited (-1 in the database) quota is found
               during this process, the user has no quota (aka unlimited).
            3. Quota is increased or decreased by any corresponding '+' or '-'
               quotas.
        """
        if not user:
            return self.default_unregistered_quota
        quotas = []
        for group in [uga.group for uga in user.groups]:
            for quota in [gqa.quota for gqa in group.quotas]:
                if quota not in quotas:
                    quotas.append(quota)
        for quota in [uqa.quota for uqa in user.quotas]:
            if quota not in quotas:
                quotas.append(quota)
        use_default = True
        max = 0
        adjustment = 0
        rval = 0
        for quota in quotas:
            if quota.deleted:
                continue
            if quota.operation == "=" and quota.bytes == -1:
                rval = None
                break
            elif quota.operation == "=":
                use_default = False
                if quota.bytes > max:
                    max = quota.bytes
            elif quota.operation == "+":
                adjustment += quota.bytes
            elif quota.operation == "-":
                adjustment -= quota.bytes
        if use_default:
            max = self.default_registered_quota
            if max is None:
                rval = None
        if rval is not None:
            rval = max + adjustment
            if rval <= 0:
                rval = 0
        return rval

    @property
    def default_unregistered_quota(self):
        return self._default_quota(self.model.DefaultQuotaAssociation.types.UNREGISTERED)

    @property
    def default_registered_quota(self):
        return self._default_quota(self.model.DefaultQuotaAssociation.types.REGISTERED)

    def _default_quota(self, default_type):
        dqa = (
            self.sa_session.query(self.model.DefaultQuotaAssociation)
            .filter(self.model.DefaultQuotaAssociation.type == default_type)
            .first()
        )
        if not dqa:
            return None
        if dqa.quota.bytes < 0:
            return None
        return dqa.quota.bytes

    def set_default_quota(self, default_type, quota):
        # Unset the current default(s) associated with this quota, if there are any
        for dqa in quota.default:
            self.sa_session.delete(dqa)
        # Unset the current users/groups associated with this quota
        for uqa in quota.users:
            self.sa_session.delete(uqa)
        for gqa in quota.groups:
            self.sa_session.delete(gqa)
        # Find the old default, assign the new quota if it exists
        dqa = (
            self.sa_session.query(self.model.DefaultQuotaAssociation)
            .filter(self.model.DefaultQuotaAssociation.type == default_type)
            .first()
        )
        if dqa:
            dqa.quota = quota
        # Or create if necessary
        else:
            dqa = self.model.DefaultQuotaAssociation(default_type, quota)
        self.sa_session.add(dqa)
        self.sa_session.flush()

    def get_percent(self, trans=None, user=False, history=False, usage=False, quota=False):
        """
        Return the percentage of any storage quota applicable to the user/transaction.
        """
        # if trans passed, use it to get the user, history (instead of/override vals passed)
        if trans:
            user = trans.user
            history = trans.history
        # if quota wasn't passed, attempt to get the quota
        if quota is False:
            quota = self.get_quota(user)
        # return none if no applicable quotas or quotas disabled
        if quota is None:
            return None
        # get the usage, if it wasn't passed
        if usage is False:
            usage = self.get_usage(trans, user, history)
        try:
            return min((int(float(usage) / quota * 100), 100))
        except ZeroDivisionError:
            return 100

    def set_entity_quota_associations(self, quotas=None, users=None, groups=None, delete_existing_assocs=True):
        if quotas is None:
            quotas = []
        if users is None:
            users = []
        if groups is None:
            groups = []
        for quota in quotas:
            if delete_existing_assocs:
                flush_needed = False
                for a in quota.users + quota.groups:
                    self.sa_session.delete(a)
                    flush_needed = True
                if flush_needed:
                    self.sa_session.flush()
            for user in users:
                uqa = self.model.UserQuotaAssociation(user, quota)
                self.sa_session.add(uqa)
            for group in groups:
                gqa = self.model.GroupQuotaAssociation(group, quota)
                self.sa_session.add(gqa)
            self.sa_session.flush()

    def is_over_quota(self, app, job, job_destination):
        quota = self.get_quota(job.user)
        if quota is not None:
            try:
                usage = self.get_usage(user=job.user, history=job.history)
                if usage > quota:
                    return True
            except AssertionError:
                pass  # No history, should not happen with an anon user
        return False


def get_quota_agent(config, model) -> QuotaAgent:
    quota_agent: QuotaAgent
    if config.enable_quotas:
        quota_agent = galaxy.quota.DatabaseQuotaAgent(model)
    else:
        quota_agent = galaxy.quota.NoQuotaAgent()
    return quota_agent


__all__ = ("get_quota_agent", "NoQuotaAgent")
