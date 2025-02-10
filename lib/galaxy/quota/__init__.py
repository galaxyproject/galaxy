"""Galaxy Quotas"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.sql import text

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

    def relabel_quota_for_dataset(self, dataset, from_label: Optional[str], to_label: Optional[str]):
        """Update the quota source label for dataset and adjust relevant quotas.

        Subtract quota for labels from users using old label and quota for new label
        for these users.
        """

    # TODO: make abstractmethod after they work better with mypy
    def get_quota(self, user, quota_source_label=None) -> Optional[int]:
        """Return quota in bytes or None if no quota is set."""

    def get_quota_nice_size(self, user, quota_source_label=None) -> Optional[str]:
        """Return quota as a human-readable string or 'unlimited' if no quota is set."""
        quota_bytes = self.get_quota(user, quota_source_label=quota_source_label)
        if quota_bytes is not None:
            quota_str = galaxy.util.nice_size(quota_bytes)
        else:
            quota_str = "unlimited"
        return quota_str

    # TODO: make abstractmethod after they work better with mypy
    def get_percent(
        self, trans=None, user=False, history=False, usage=False, quota=False, quota_source_label=None
    ) -> Optional[int]:
        """Return the percentage of any storage quota applicable to the user/transaction."""

    def get_usage(self, trans=None, user=False, history=False, quota_source_label=None) -> Optional[float]:
        if trans:
            user = trans.user
            history = trans.history
        assert user is not False, "Could not determine user."
        if not user:
            assert history, "Could not determine anonymous user's history."
            usage = history.disk_size
        else:
            if quota_source_label is None:
                usage = user.total_disk_usage
            else:
                quota_source_usage = user.quota_source_usage_for(quota_source_label)
                if not quota_source_usage or quota_source_usage.disk_usage is None:
                    usage = 0.0
                else:
                    usage = quota_source_usage.disk_usage
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

    def get_quota(self, user, quota_source_label=None) -> Optional[int]:
        return None

    def relabel_quota_for_dataset(self, dataset, from_label: Optional[str], to_label: Optional[str]):
        return None

    @property
    def default_quota(self):
        return None

    def get_percent(
        self, trans=None, user=False, history=False, usage=False, quota=False, quota_source_label=None
    ) -> Optional[int]:
        return None

    def is_over_quota(self, app, job, job_destination):
        return False


class DatabaseQuotaAgent(QuotaAgent):
    """Class that handles galaxy quotas"""

    def __init__(self, model):
        self.model = model
        self.sa_session = model.context

    def get_quota(self, user, quota_source_label=None) -> Optional[int]:
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
            return self._default_unregistered_quota(quota_source_label)
        query = text(
            """
SELECT (
        COALESCE(MAX(CASE WHEN union_quota.operation = '='
                          THEN union_quota.bytes
                          ELSE NULL
                          END),
                 (SELECT default_quota.bytes
                  FROM quota as default_quota
                      LEFT JOIN default_quota_association on default_quota.id = default_quota_association.quota_id
                      WHERE default_quota_association.type = 'registered'
                          AND default_quota.deleted != :is_true
                          AND default_quota.quota_source_label {label_cond}))
        +
        (CASE WHEN SUM(CASE WHEN union_quota.operation = '=' AND union_quota.bytes = -1
                            THEN 1 ELSE 0
                            END) > 0
              THEN NULL
              ELSE 0 END)
        +
        (COALESCE(SUM(
                CASE WHEN union_quota.operation = '+' THEN union_quota.bytes
                     WHEN union_quota.operation = '-' THEN -1 * union_quota.bytes
                     ELSE 0
                     END
              ), 0))
       )
FROM (
    SELECT user_quota.operation as operation, user_quota.bytes as bytes
    FROM galaxy_user as guser
        LEFT JOIN user_quota_association as uqa on guser.id = uqa.user_id
        LEFT JOIN quota as user_quota on user_quota.id = uqa.quota_id
    WHERE user_quota.deleted != :is_true
        AND user_quota.quota_source_label {label_cond}
        AND guser.id = :user_id
    UNION ALL
    SELECT group_quota.operation as operation, group_quota.bytes as bytes
    FROM galaxy_user as guser
        LEFT JOIN user_group_association as uga on guser.id = uga.user_id
        LEFT JOIN galaxy_group on galaxy_group.id = uga.group_id
        LEFT JOIN group_quota_association as gqa on galaxy_group.id = gqa.group_id
        LEFT JOIN quota as group_quota on group_quota.id = gqa.quota_id
    WHERE group_quota.deleted != :is_true
        AND group_quota.quota_source_label {label_cond}
        AND guser.id = :user_id
) as union_quota
""".format(
                label_cond="IS NULL" if quota_source_label is None else " = :label"
            )
        )
        engine = self.sa_session.get_bind()
        with engine.connect() as conn:
            res = conn.execute(query, {"is_true": True, "user_id": user.id, "label": quota_source_label}).fetchone()
            if res:
                return int(res[0]) if res[0] else None
            else:
                return None

    def relabel_quota_for_dataset(self, dataset, from_label: Optional[str], to_label: Optional[str]):
        adjust = dataset.get_total_size()
        with_quota_affected_users = """WITH quota_affected_users AS
(
    SELECT DISTINCT user_id
    FROM history
        INNER JOIN
            history_dataset_association on history_dataset_association.history_id = history.id
        INNER JOIN
            dataset on history_dataset_association.dataset_id = dataset.id
    WHERE
        dataset_id = :dataset_id
)"""
        engine = self.sa_session.get_bind()

        # Hack for older sqlite, would work on newer sqlite - 3.24.0
        for_sqlite = "sqlite" in engine.dialect.name

        if to_label == from_label:
            return
        if to_label is None:
            to_statement = f"""
{with_quota_affected_users}
UPDATE galaxy_user
SET disk_usage = coalesce(disk_usage, 0) + :adjust
WHERE id in (select user_id from quota_affected_users)
"""
        else:
            if for_sqlite:
                to_statement = f"""
{with_quota_affected_users},
new_quota_sources (user_id, disk_usage, quota_source_label) AS (
    SELECT user_id, :adjust as disk_usage, :to_label as quota_source_label
    FROM quota_affected_users
)
INSERT OR REPLACE INTO user_quota_source_usage (id, user_id, quota_source_label, disk_usage)
SELECT old.id, new.user_id, new.quota_source_label, COALESCE(old.disk_usage + :adjust, :adjust)
FROM new_quota_sources as new LEFT JOIN user_quota_source_usage AS old ON new.user_id = old.user_id AND NEW.quota_source_label = old.quota_source_label"""
            else:
                to_statement = f"""
{with_quota_affected_users},
new_quota_sources (user_id, disk_usage, quota_source_label) AS (
    SELECT user_id, :adjust as disk_usage, :to_label as quota_source_label
    FROM quota_affected_users
)
INSERT INTO user_quota_source_usage(user_id, disk_usage, quota_source_label)
SELECT * FROM new_quota_sources
ON CONFLICT
    ON constraint uqsu_unique_label_per_user
    DO UPDATE SET disk_usage = user_quota_source_usage.disk_usage + :adjust
"""

        if from_label is None:
            from_statement = f"""
{with_quota_affected_users}
UPDATE galaxy_user
SET disk_usage = coalesce(disk_usage - :adjust, 0)
WHERE id in (select user_id from quota_affected_users)
"""
        else:
            if for_sqlite:
                from_statement = f"""
{with_quota_affected_users},
new_quota_sources (user_id, disk_usage, quota_source_label) AS (
    SELECT user_id, :adjust as disk_usage, :from_label as quota_source_label
    FROM quota_affected_users
)
INSERT OR REPLACE INTO user_quota_source_usage (id, user_id, quota_source_label, disk_usage)
SELECT old.id, new.user_id, new.quota_source_label, COALESCE(old.disk_usage - :adjust, 0)
FROM new_quota_sources as new LEFT JOIN user_quota_source_usage AS old ON new.user_id = old.user_id AND NEW.quota_source_label = old.quota_source_label"""
            else:
                from_statement = f"""
{with_quota_affected_users},
new_quota_sources (user_id, disk_usage, quota_source_label) AS (
    SELECT user_id, 0 as disk_usage, :from_label as quota_source_label
    FROM quota_affected_users
)
INSERT INTO user_quota_source_usage(user_id, disk_usage, quota_source_label)
SELECT * FROM new_quota_sources
ON CONFLICT
    ON constraint uqsu_unique_label_per_user
    DO UPDATE SET disk_usage = user_quota_source_usage.disk_usage - :adjust
"""

        bind = {"dataset_id": dataset.id, "adjust": int(adjust), "to_label": to_label, "from_label": from_label}
        engine = self.sa_session.get_bind()
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text(from_statement), bind)
                conn.execute(text(to_statement), bind)

    def _default_unregistered_quota(self, quota_source_label):
        return self._default_quota(self.model.DefaultQuotaAssociation.types.UNREGISTERED, quota_source_label)

    def _default_quota(self, default_type, quota_source_label):
        label_condition = "IS NULL" if quota_source_label is None else "= :label"
        query = text(
            f"""
SELECT bytes
FROM quota as default_quota
LEFT JOIN default_quota_association on default_quota.id = default_quota_association.quota_id
WHERE default_quota_association.type = :default_type
    AND default_quota.deleted != :is_true
    AND default_quota.quota_source_label {label_condition}
"""
        )
        engine = self.sa_session.get_bind()
        with engine.connect() as conn:
            res = conn.execute(
                query, {"is_true": True, "label": quota_source_label, "default_type": default_type}
            ).fetchone()
            if res:
                return res[0]
            else:
                return None

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
        label = quota.quota_source_label
        stmt = select(self.model.DefaultQuotaAssociation).filter(
            self.model.DefaultQuotaAssociation.type == default_type
        )
        dqas = self.sa_session.scalars(stmt).all()
        target_default = None
        for dqa in dqas:
            if dqa.quota.quota_source_label == label and not dqa.quota.deleted:
                target_default = dqa
        if target_default:
            target_default.quota = quota
        # Or create if necessary
        else:
            target_default = self.model.DefaultQuotaAssociation(default_type, quota)
        self.sa_session.add(target_default)
        self.sa_session.commit()

    def get_percent(
        self, trans=None, user=False, history=False, usage=False, quota=False, quota_source_label=None
    ) -> Optional[int]:
        """
        Return the percentage of any storage quota applicable to the user/transaction.
        """
        # if trans passed, use it to get the user, history (instead of/override vals passed)
        if trans:
            user = trans.user
            history = trans.history
        # if quota wasn't passed, attempt to get the quota
        if quota is False:
            quota = self.get_quota(user, quota_source_label=quota_source_label)
        # return none if no applicable quotas or quotas disabled
        if quota is None:
            return None
        # get the usage, if it wasn't passed
        if usage is False:
            usage = self.get_usage(trans, user, history, quota_source_label=quota_source_label)
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
                    self.sa_session.commit()
            for user in users:
                uqa = self.model.UserQuotaAssociation(user, quota)
                self.sa_session.add(uqa)
            for group in groups:
                gqa = self.model.GroupQuotaAssociation(group, quota)
                self.sa_session.add(gqa)
            self.sa_session.commit()

    def is_over_quota(self, app, job, job_destination):
        # Doesn't work because job.object_store_id until inside handler :_(
        # quota_source_label = job.quota_source_label
        if job_destination is not None:
            object_store_id = job_destination.params.get("object_store_id", None)
            object_store = app.object_store
            quota_source_map = object_store.get_quota_source_map()
            quota_source_label = quota_source_map.get_quota_source_info(object_store_id).label
        else:
            quota_source_label = None
        quota = self.get_quota(job.user, quota_source_label=quota_source_label)
        if quota is not None:
            try:
                usage = self.get_usage(user=job.user, history=job.history, quota_source_label=quota_source_label)
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
