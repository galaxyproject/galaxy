#!/usr/bin/env python
"""
pgcleanup.py - A script for cleaning up datasets in Galaxy efficiently, by
    bypassing the Galaxy model and operating directly on the database.
    PostgreSQL 9.1 or greater is required.
"""

import argparse
import datetime
import inspect
import logging
import os
import re
import string
import sys
import time
import uuid
from collections import namedtuple
from functools import partial

import psycopg2
from psycopg2.extras import NamedTupleCursor
from sqlalchemy.engine.url import make_url

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(1, os.path.join(galaxy_root, "lib"))

import galaxy.config
from galaxy.exceptions import ObjectNotFound
from galaxy.model import calculate_user_disk_usage_statements
from galaxy.objectstore import build_object_store_from_config
from galaxy.util.script import (
    app_properties_from_args,
    populate_config_args,
    set_log_handler,
)

DEFAULT_LOG_DIR = os.path.join(galaxy_root, "scripts", "cleanup_datasets")

log = logging.getLogger(__name__)


#
# BASE CLASSES, etc.
#


class LevelFormatter(logging.Formatter):
    warn_fmt = "%(levelname)-5s %(funcName)s(): %(message)s"
    def_fmt = "%(message)s"

    def format(self, record):
        if record.levelno > logging.INFO:
            fmt = self.warn_fmt
        else:
            fmt = self.def_fmt
        if hasattr(self, "_style"):  # py3
            self._style._fmt = fmt
        else:
            self._fmt = fmt
        return logging.Formatter.format(self, record)


class Action:
    """Base class for all actions.

    When writing new actions, the following things happen automatically:
    - _action_sql's format() method is used to replace ``{update_time_sql}`` and ``{force_retry_sql}``
    - an event is created and its id is added to the sql args with key ``event_id``
    - ``days`` is added to the sql args
    - ``causals`` (see examples) allow logging what events triggered what other events

    The first column in the result set is considered the "primary" column upon which actions are being performed.

    See the mixins for additional features.

    Generally you should set at least ``_action_sql`` in subclasses (although it's possible to just override ``sql``
    directly.)
    """

    requires_objectstore = True
    update_time_sql = ", update_time = NOW() AT TIME ZONE 'utc'"
    force_retry_sql = " AND NOT purged"
    primary_key = None
    causals = ()
    _action_sql = ""
    _action_sql_args = {}

    # these shouldn't be overridden by subclasses

    @classmethod
    def name_c(cls):
        # special case - for more complex stuff you can always implement name_c() on subclasses
        clsname = cls.__name__.replace("HDA", "Hda")
        actname = [clsname[0].lower()]
        for c in clsname[1:]:
            if c in string.ascii_uppercase:
                c = "_" + c.lower()
            actname.append(c)
        return "".join(actname)

    @classmethod
    def doc_iter(cls):
        for line in cls.__doc__.splitlines():
            yield line.replace(" ", "", 4)

    def __init__(self, app):
        self._log_dir = app.args.log_dir
        self._log_file = app.args.log_file
        self._dry_run = app.args.dry_run
        self._debug = app.args.debug
        self._update_time = app.args.update_time
        self._force_retry = app.args.force_retry
        if app.args.object_store_id:
            self._object_store_id_sql = f" AND dataset.object_store_id = '{app.args.object_store_id}'"
        else:
            self._object_store_id_sql = ""
        self._epoch_time = str(int(time.time()))
        self._days = app.args.days
        self._config = app.config
        self._update = app._update
        self.__log = None
        self.__row_methods = []
        self.__post_methods = []
        self.__exit_methods = []
        if self.requires_objectstore:
            self.object_store = build_object_store_from_config(self._config)
            self._register_exit_method(self.object_store.shutdown)
        self._init()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for method in self.__exit_methods:
            method()
        if self.__log is not None:
            self.__close_log()

    def __open_log(self):
        if self._log_file:
            logf = os.path.join(self._log_dir, self._log_file)
        else:
            logf = os.path.join(self._log_dir, self.name + ".log")
        if self._dry_run:
            log.info("--dry-run specified, logging changes to stderr instead of log file: %s", logf)
            h = set_log_handler()
        else:
            log.info("Opening log file: %s", logf)
            h = set_log_handler(filename=logf)
        h.setLevel(logging.DEBUG if self._debug else logging.INFO)
        h.setFormatter(LevelFormatter())
        self.__log = logging.getLogger(self.name)
        self.__log.addHandler(h)
        self.__log.propagate = False
        m = (f"==== Log opened: {datetime.datetime.now().isoformat()} ").ljust(72, "=")
        self.__log.info(m)
        self.__log.info("Epoch time for this action: %s", self._epoch_time)

    def __close_log(self):
        m = (f"==== Log closed: {datetime.datetime.now().isoformat()} ").ljust(72, "=")
        self.log.info(m)
        self.__log = None

    def _register_row_method(self, method):
        self.__row_methods.append(method)

    def _register_post_method(self, method):
        self.__post_methods.append(method)

    def _register_exit_method(self, method):
        self.__exit_methods.append(method)

    @property
    def log(self):
        if self.__log is None:
            self.__open_log()
        return self.__log

    @property
    def name(self):
        return self.__class__.name_c()

    # subclasses can override these as needed

    @property
    def _update_time_sql(self):
        # only update time if not doing force retry (otherwise a lot of things would have their update times reset that
        # were actually purged a long time ago)
        if self._update_time and not self._force_retry:
            return self.update_time_sql
        return ""

    @property
    def _force_retry_sql(self):
        # a misnomer, the value of force_retry_sql is actually the SQL that should be used if *not* forcibly retrying
        if not self._force_retry:
            return self.force_retry_sql
        return ""

    @property
    def sql(self):
        return self._action_sql.format(
            update_time_sql=self._update_time_sql,
            force_retry_sql=self._force_retry_sql,
            epoch_time=self._epoch_time,
            object_store_id_sql=self._object_store_id_sql,
        )

    @property
    def sql_args(self):
        args = self._action_sql_args.copy()
        if "days" not in args:
            args["days"] = self._days
        return args

    def _collect_row_results(self, row, results, primary_key):
        primary_key = row._fields[0]
        primary = getattr(row, primary_key)
        if primary not in results:
            results[primary] = [set() for x in range(len(self.causals))]
        rowgetter = partial(getattr, row)
        for i, causal in enumerate(self.causals):
            vals = tuple(map(rowgetter, causal))
            if any(vals[1:]):
                results[primary][i].add(vals)

    def _log_results(self, results, primary_key):
        for primary in sorted(results.keys()):
            self.log.info(f"{primary_key}: {primary}")
            for causal, s in zip(self.causals, results[primary]):
                for r in sorted(s):
                    secondaries = ", ".join(f"{x[0]}: {x[1]}" for x in zip(causal[1:], r[1:]))
                    self.log.info(f"{causal[0]} {r[0]} caused {secondaries}")

    def handle_results(self, cur):
        results = {}
        primary_key = self.primary_key
        for row in cur:
            if primary_key is None:
                primary_key = row._fields[0]
            self._collect_row_results(row, results, primary_key)
            for method in self.__row_methods:
                method(row)
        self._log_results(results, primary_key)
        for method in self.__post_methods:
            method()

    # subclasses can implement these

    def _init(self):
        """Action initialization routines.

        Subclasses that implement ``_init()`` should call ``super()`` in it.
        """
        pass


class RemovesObjects:
    """Base class for mixins that remove objects from object stores."""

    requires_objectstore = True

    def _init(self):
        super()._init()
        self.objects_to_remove = set()
        log.info("Initializing object store for action %s", self.name)
        self._register_row_method(self.collect_removed_object_info)
        self._register_post_method(self.remove_objects)

    def collect_removed_object_info(self, row):
        object_id = getattr(row, self.id_column, None)
        object_uuid = getattr(row, self.uuid_column, None)
        if object_uuid:
            object_uuid = str(uuid.UUID(object_uuid))
        if object_id:
            self.objects_to_remove.add(self.object_class(object_id, row.object_store_id, object_uuid))

    def remove_objects(self):
        for object_to_remove in sorted(self.objects_to_remove):
            self.remove_object(object_to_remove)

    def remove_from_object_store(self, object_to_remove, object_store_kwargs, entire_dir=False, check_exists=False):
        # only remove the "object store path" - if it's at an external_filename, that file will be untouched anyway
        # (which is what we want)
        loggers = (self.log, log)
        try:
            # TODO: get_filename() can do stuff like cache locally from S3, but we want the filename for logging
            # purposes; this isn't ideal, object stores should probably have a noop way to get the "object store native
            # identifier" which in the case of Disk would be the path
            if not check_exists or self.object_store.exists(object_to_remove, **object_store_kwargs):
                filename = self.object_store.get_filename(object_to_remove, **object_store_kwargs)
                self.log.info("removing %s at: %s", object_to_remove, filename)
                if not self._dry_run:
                    self.object_store.delete(object_to_remove, entire_dir=entire_dir, **object_store_kwargs)
        except ObjectNotFound as e:
            [log_.warning("object store failure: %s: %s", object_to_remove, e) for log_ in loggers]
        except Exception as e:
            [log_.error("delete failure: %s: %s", object_to_remove, e) for log_ in loggers]

    def remove_object(self, object_to_remove):
        raise NotImplementedError()


#
# MIXINS
#


class PurgesHDAs:
    """Avoid repetition in queries that purge HDAs, since they must also delete MetadataFiles and ICDAs.

    To use, place ``{purge_hda_dependencies_sql}`` somewhere in your CTEs after a ``purged_hda_ids`` CTE returning HDA
    ids. If you have additional CTEs after the template point, be sure to append a ``,``.
    """

    _purge_hda_dependencies_sql = """deleted_metadata_file_ids
          AS (     UPDATE metadata_file
                      SET deleted = true{update_time_sql}
                     FROM purged_hda_ids
                    WHERE purged_hda_ids.id = metadata_file.hda_id
                RETURNING metadata_file.hda_id AS hda_id,
                          metadata_file.id AS id,
                          metadata_file.uuid AS uuid,
                          metadata_file.object_store_id AS object_store_id),
             deleted_icda_ids
          AS (     UPDATE implicitly_converted_dataset_association
                      SET deleted = true{update_time_sql}
                     FROM purged_hda_ids
                    WHERE purged_hda_ids.id = implicitly_converted_dataset_association.hda_parent_id
                RETURNING implicitly_converted_dataset_association.hda_id AS hda_id,
                          implicitly_converted_dataset_association.hda_parent_id AS hda_parent_id,
                          implicitly_converted_dataset_association.id AS id),
             deleted_icda_purged_child_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true{update_time_sql}
                     FROM deleted_icda_ids
                    WHERE deleted_icda_ids.hda_id = history_dataset_association.id),
             metadata_file_events
          AS (INSERT INTO cleanup_event_metadata_file_association
                          (create_time, cleanup_event_id, metadata_file_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM deleted_metadata_file_ids),
             icda_events
          AS (INSERT INTO cleanup_event_icda_association
                          (create_time, cleanup_event_id, icda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM deleted_icda_ids),
             icda_hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, hda_id
                     FROM deleted_icda_ids)"""

    @property
    def sql(self):
        _purge_hda_dependencies_sql = self._purge_hda_dependencies_sql.format(
            update_time_sql=self._update_time_sql,
            force_retry_sql=self._force_retry_sql,
            epoch_time=self._epoch_time,
        )
        return self._action_sql.format(
            purge_hda_dependencies_sql=_purge_hda_dependencies_sql,
            update_time_sql=self._update_time_sql,
            force_retry_sql=self._force_retry_sql,
            epoch_time=self._epoch_time,
            object_store_id_sql=self._object_store_id_sql,
        )


class RequiresDiskUsageRecalculation:
    """Causes disk usage to be recalculated for affected users.

    To use, ensure your query returns a ``recalculate_disk_usage_user_id`` column.
    """

    requires_objectstore = True

    def _init(self):
        super()._init()
        self.__recalculate_disk_usage_user_ids = set()
        self._register_row_method(self.collect_recalculate_disk_usage_user_id)
        self._register_post_method(self.recalculate_disk_usage)

    def collect_recalculate_disk_usage_user_id(self, row):
        if row.recalculate_disk_usage_user_id:
            self.__recalculate_disk_usage_user_ids.add(row.recalculate_disk_usage_user_id)

    def recalculate_disk_usage(self):
        """
        Any operation that purges a HistoryDatasetAssociation may require
        updating a user's disk usage.  Rather than attempt to resolve dataset
        copies at purge-time, simply maintain a list of users that have had
        HDAs purged, and update their usages once all updates are complete.

        This could probably be done more efficiently.
        """
        log.info("Recalculating disk usage for users whose data were purged")
        for user_id in sorted(self.__recalculate_disk_usage_user_ids):
            quota_source_map = self.object_store.get_quota_source_map()
            statements = calculate_user_disk_usage_statements(user_id, quota_source_map)

            for sql, args in statements:
                sql = sql.replace("%", "%%")
                sql = re.sub(r"\:([\w]+)", r"%(\1)s", sql)
                new_args = {}
                for key, val in args.items():
                    if isinstance(val, list):
                        val = tuple(val)
                    new_args[key] = val
                self._update(sql, new_args, add_event=False)

            self.log.info("recalculate_disk_usage user_id %i", user_id)


class RemovesMetadataFiles(RemovesObjects):
    """Causes MetadataFiles to be removed from the object store.

    To use, ensure your query returns ``deleted_metadata_file_id``, ``object_store_id``, and
    ``deleted_metadata_file_uuid`` columns.
    """

    object_class = namedtuple("MetadataFile", ["id", "object_store_id", "uuid"])
    id_column = "deleted_metadata_file_id"
    uuid_column = "deleted_metadata_file_uuid"

    def remove_object(self, metadata_file):
        store_by = self.object_store.get_store_by(metadata_file)
        if store_by == "uuid":
            alt_name = f"metadata_{metadata_file.uuid}.dat"
        else:
            alt_name = f"metadata_{metadata_file.id}.dat"
        self.remove_from_object_store(
            metadata_file, dict(extra_dir="_metadata_files", extra_dir_at_root=True, alt_name=alt_name)
        )


class RemovesDatasets(RemovesObjects):
    """Causes Datasets to be removed from the object store.

    To use, ensure your query returns ``purged_dataset_id``, ``object_store_id``, and ``purged_dataset_uuid`` columns.
    """

    object_class = namedtuple("Dataset", ["id", "object_store_id", "uuid"])
    id_column = "purged_dataset_id"
    uuid_column = "purged_dataset_uuid"

    def remove_object(self, dataset):
        store_by = self.object_store.get_store_by(dataset)
        if store_by == "uuid":
            extra_dir = f"dataset_{dataset.uuid}_files"
        else:
            extra_dir = f"dataset_{dataset.id}_files"
        self.remove_from_object_store(dataset, {})
        self.remove_from_object_store(
            dataset, dict(dir_only=True, extra_dir=extra_dir), entire_dir=True, check_exists=True
        )


#
# ACTIONS
#


class UpdateHDAPurgedFlag(Action):
    """
    The old cleanup script does not mark HistoryDatasetAssociations as purged when deleted Histories
    are purged.  This action can be used to rectify that situation.
    """

    # update_time is intentionally left unmodified.
    _action_sql = """
        WITH purged_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true
                     FROM dataset
                        WHERE history_dataset_association.dataset_id = dataset.id
                          AND dataset.purged
                          AND NOT history_dataset_association.purged
                RETURNING history_dataset_association.id),
             hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW(), %(event_id)s, id
                     FROM purged_hda_ids)
      SELECT id AS purged_hda_id
        FROM purged_hda_ids
    ORDER BY id;
    """


class DeleteUserlessHistories(Action):
    """
    - Mark deleted all "anonymous" Histories (not owned by a registered user) that are older than
      the specified number of days.
    """

    _action_sql = """
        WITH deleted_history_ids
          AS (     UPDATE history
                      SET deleted = true{update_time_sql}
                    WHERE user_id is null
                          AND NOT deleted
                          AND update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING id),
             history_events
          AS (INSERT INTO cleanup_event_history_association
                          (create_time, cleanup_event_id, history_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM deleted_history_ids)
      SELECT id AS deleted_history_id
        FROM deleted_history_ids
    ORDER BY id
    """


class DeleteInactiveUsers(Action):
    """
    - Mark deleted all users that are older than the specified number of days.
    - Mark deleted (state = 'deleted') all Jobs whose user_ids are deleted in this step.
    """

    force_retry_sql = " AND NOT deleted"
    _action_sql = """
        WITH deleted_user_ids
          AS (     UPDATE galaxy_user
                      SET deleted = true{update_time_sql}
                    WHERE NOT active{force_retry_sql}
                          AND update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING id),
             deleted_job_ids
          AS (     UPDATE job
                      SET state = 'deleted'{update_time_sql}
                     FROM deleted_user_ids
                    WHERE deleted_user_ids.id = job.user_id
                          AND job.state = 'new'
                RETURNING job.user_id AS user_id,
                          job.id AS id),
             user_events
          AS (INSERT INTO cleanup_event_user_association
                          (create_time, cleanup_event_id, user_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM deleted_user_ids)
      SELECT deleted_user_ids.id AS deleted_user_id,
             deleted_job_ids.id AS deleted_job_id
        FROM deleted_user_ids
             LEFT OUTER JOIN deleted_job_ids
                             ON deleted_job_ids.user_id = deleted_user_ids.id
    ORDER BY deleted_user_ids.id
    """
    causals = (("purged_user_id", "purged_job_id"),)


class PurgeDeletedUsers(PurgesHDAs, RemovesMetadataFiles, Action):
    """
    - Mark purged all users that are older than the specified number of days.
    - Set User.disk_usage = 0 for all users purged in this step.
    - Mark purged all Histories whose user_ids are purged in this step.
    - Mark purged all HistoryDatasetAssociations whose history_ids are purged in this step.
    - Delete all UserGroupAssociations whose user_ids are purged in this step.
    - Delete all UserRoleAssociations whose user_ids are purged in this step EXCEPT FOR THE PRIVATE
      ROLE.
    - Delete all UserAddresses whose user_ids are purged in this step.
    """

    _action_sql = """
        WITH purged_user_ids
          AS (     UPDATE galaxy_user
                      SET purged = true{update_time_sql}
                    WHERE deleted{force_retry_sql}
                          AND update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING id),
             deleted_uga_ids
          AS (DELETE FROM user_group_association
                    USING purged_user_ids
                    WHERE user_group_association.user_id = purged_user_ids.id
                RETURNING user_group_association.user_id AS user_id,
                          user_group_association.id AS id),
             deleted_ura_ids
          AS (DELETE FROM user_role_association
                    USING role
                    WHERE role.id = user_role_association.role_id
                          AND role.type != 'private'
                          AND user_role_association.user_id IN
                            (SELECT id
                               FROM purged_user_ids)
                RETURNING user_role_association.user_id AS user_id,
                          user_role_association.id AS id),
             deleted_ua_ids
          AS (DELETE FROM user_address
                    USING purged_user_ids
                    WHERE user_address.user_id = purged_user_ids.id
                RETURNING user_address.user_id AS user_id,
                          user_address.id AS id),
             user_events
          AS (INSERT INTO cleanup_event_user_association
                          (create_time, cleanup_event_id, user_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_user_ids),
             purged_history_ids
          AS (     UPDATE history
                      SET purged = true{update_time_sql}
                     FROM purged_user_ids
                    WHERE purged_user_ids.id = history.user_id
                          AND NOT history.purged
                RETURNING history.user_id AS user_id,
                          history.id AS id),
             history_events
          AS (INSERT INTO cleanup_event_history_association
                          (create_time, cleanup_event_id, history_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_history_ids),
             purged_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true{update_time_sql}
                     FROM purged_history_ids
                    WHERE purged_history_ids.id = history_dataset_association.history_id
                          AND NOT history_dataset_association.purged
                RETURNING history_dataset_association.history_id AS history_id,
                          history_dataset_association.id AS id),
             hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_hda_ids),
             {purge_hda_dependencies_sql}
      SELECT purged_user_ids.id AS purged_user_id,
             purged_user_ids.id AS zero_disk_usage_user_id,
             purged_history_ids.id AS purged_history_id,
             purged_hda_ids.id AS purged_hda_id,
             deleted_metadata_file_ids.id AS deleted_metadata_file_id,
             deleted_metadata_file_ids.uuid AS deleted_metadata_file_uuid,
             deleted_metadata_file_ids.object_store_id AS object_store_id,
             deleted_icda_ids.id AS deleted_icda_id,
             deleted_icda_ids.hda_id AS deleted_icda_hda_id,
             deleted_uga_ids.id AS deleted_uga_id,
             deleted_ura_ids.id AS deleted_ura_id,
             deleted_ua_ids.id AS deleted_ua_id
        FROM purged_user_ids
             LEFT OUTER JOIN purged_history_ids
                             ON purged_user_ids.id = purged_history_ids.user_id
             LEFT OUTER JOIN purged_hda_ids
                             ON purged_history_ids.id = purged_hda_ids.history_id
             LEFT OUTER JOIN deleted_metadata_file_ids
                             ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_icda_ids
                             ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_uga_ids
                             ON purged_user_ids.id = deleted_uga_ids.user_id
             LEFT OUTER JOIN deleted_ura_ids
                             ON purged_user_ids.id = deleted_ura_ids.user_id
             LEFT OUTER JOIN deleted_ua_ids
                             ON purged_user_ids.id = deleted_ua_ids.user_id
    ORDER BY purged_user_ids.id
    """
    causals = (
        ("purged_user_id", "purged_history_id"),
        ("purged_history_id", "purged_hda_id"),
        ("purged_hda_id", "deleted_metadata_file_id", "object_store_id"),
        ("purged_hda_id", "deleted_icda_id", "deleted_icda_hda_id"),
        ("purged_user_id", "deleted_uga_id"),
        ("purged_user_id", "deleted_ura_id"),
        ("purged_user_id", "deleted_ua_id"),
    )

    def _init(self):
        super()._init()
        self.__zero_disk_usage_user_ids = set()
        self._register_row_method(self.collect_zero_disk_usage_user_id)
        self._register_post_method(self.zero_disk_usage)

    def collect_zero_disk_usage_user_id(self, row):
        self.__zero_disk_usage_user_ids.add(row.zero_disk_usage_user_id)

    def zero_disk_usage(self):
        if not self.__zero_disk_usage_user_ids:
            return
        log.info("Zeroing disk usage for users who were purged")
        sql = """
            UPDATE galaxy_user
               SET disk_usage = 0
             WHERE id IN %(user_ids)s
        """
        user_ids = sorted(self.__zero_disk_usage_user_ids)
        args = {"user_ids": tuple(user_ids)}
        self._update(sql, args, add_event=False)
        self.log.info("zero_disk_usage user_ids: %s", " ".join(str(i) for i in user_ids))


class PurgeDeletedUsersGDPR(PurgesHDAs, RemovesMetadataFiles, Action):
    """
    - Perform all steps in the PurgeDeletedUsers/purge_deleted_users action
    - Obfuscate User.email and User.username for all users purged in this step.

    NOTE: Your database must have the pgcrypto extension installed e.g. with:
      CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """

    _action_sql = """
        WITH purged_user_ids
          AS (     UPDATE galaxy_user
                      SET purged = true,
                          disk_usage = 0,
                          email = encode(digest(email || '{epoch_time}', 'sha1'), 'hex'),
                          username = encode(digest(username || '{epoch_time}', 'sha1'), 'hex'){update_time_sql}
                    WHERE deleted{force_retry_sql}
                          AND update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING id),
             deleted_uga_ids
          AS (DELETE FROM user_group_association
                    USING purged_user_ids
                    WHERE user_group_association.user_id = purged_user_ids.id
                RETURNING user_group_association.user_id AS user_id,
                          user_group_association.id AS id),
             deleted_ura_ids
          AS (DELETE FROM user_role_association
                    USING role
                    WHERE role.id = user_role_association.role_id
                          AND role.type != 'private'
                          AND user_role_association.user_id IN
                            (SELECT id
                               FROM purged_user_ids)
                RETURNING user_role_association.user_id AS user_id,
                          user_role_association.id AS id),
             deleted_ua_ids
          AS (DELETE FROM user_address
                    USING purged_user_ids
                    WHERE user_address.user_id = purged_user_ids.id
                RETURNING user_address.user_id AS user_id,
                          user_address.id AS id),
             user_events
          AS (INSERT INTO cleanup_event_user_association
                          (create_time, cleanup_event_id, user_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_user_ids),
             purged_history_ids
          AS (     UPDATE history
                      SET purged = true{update_time_sql}
                     FROM purged_user_ids
                    WHERE purged_user_ids.id = history.user_id
                          AND NOT history.purged
                RETURNING history.user_id AS user_id,
                          history.id AS id),
             history_events
          AS (INSERT INTO cleanup_event_history_association
                          (create_time, cleanup_event_id, history_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_history_ids),
             purged_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true{update_time_sql}
                     FROM purged_history_ids
                    WHERE purged_history_ids.id = history_dataset_association.history_id
                          AND NOT history_dataset_association.purged
                RETURNING history_dataset_association.history_id AS history_id,
                          history_dataset_association.id AS id),
             hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_hda_ids),
             {purge_hda_dependencies_sql}
      SELECT purged_user_ids.id AS purged_user_id,
             purged_user_ids.id AS zero_disk_usage_user_id,
             purged_history_ids.id AS purged_history_id,
             purged_hda_ids.id AS purged_hda_id,
             deleted_metadata_file_ids.id AS deleted_metadata_file_id,
             deleted_metadata_file_ids.uuid AS deleted_metadata_file_uuid,
             deleted_metadata_file_ids.object_store_id AS object_store_id,
             deleted_icda_ids.id AS deleted_icda_id,
             deleted_icda_ids.hda_id AS deleted_icda_hda_id,
             deleted_uga_ids.id AS deleted_uga_id,
             deleted_ura_ids.id AS deleted_ura_id,
             deleted_ua_ids.id AS deleted_ua_id
        FROM purged_user_ids
             LEFT OUTER JOIN purged_history_ids
                             ON purged_user_ids.id = purged_history_ids.user_id
             LEFT OUTER JOIN purged_hda_ids
                             ON purged_history_ids.id = purged_hda_ids.history_id
             LEFT OUTER JOIN deleted_metadata_file_ids
                             ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_icda_ids
                             ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_uga_ids
                             ON purged_user_ids.id = deleted_uga_ids.user_id
             LEFT OUTER JOIN deleted_ura_ids
                             ON purged_user_ids.id = deleted_ura_ids.user_id
             LEFT OUTER JOIN deleted_ua_ids
                             ON purged_user_ids.id = deleted_ua_ids.user_id
    ORDER BY purged_user_ids.id
    """
    causals = (
        ("purged_user_id", "purged_history_id"),
        ("purged_history_id", "purged_hda_id"),
        ("purged_hda_id", "deleted_metadata_file_id", "object_store_id"),
        ("purged_hda_id", "deleted_icda_id", "deleted_icda_hda_id"),
        ("purged_user_id", "deleted_uga_id"),
        ("purged_user_id", "deleted_ura_id"),
        ("purged_user_id", "deleted_ua_id"),
    )

    @classmethod
    def name_c(cls):
        return "purge_deleted_users_gdpr"


class PurgeDeletedHDAs(PurgesHDAs, RemovesMetadataFiles, RequiresDiskUsageRecalculation, Action):
    """
    - Mark purged all HistoryDatasetAssociations currently marked deleted that are older than the
      specified number of days.
    - Mark deleted all MetadataFiles whose hda_id is purged in this step.
    - Mark deleted all ImplicitlyConvertedDatasetAssociations whose hda_parent_id is purged in this
      step.
    - Mark purged all HistoryDatasetAssociations for which an ImplicitlyConvertedDatasetAssociation
      with matching hda_id is deleted in this step.
    """

    _action_sql = """
        WITH purged_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true{update_time_sql}
                    WHERE deleted{force_retry_sql}
                          AND update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING id,
                          history_id),
             hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_hda_ids),
             {purge_hda_dependencies_sql}
      SELECT purged_hda_ids.id AS purged_hda_id,
             history.user_id AS recalculate_disk_usage_user_id,
             deleted_metadata_file_ids.id AS deleted_metadata_file_id,
             deleted_metadata_file_ids.uuid AS deleted_metadata_file_uuid,
             deleted_metadata_file_ids.object_store_id AS object_store_id,
             deleted_icda_ids.id AS deleted_icda_id,
             deleted_icda_ids.hda_id AS deleted_icda_hda_id
        FROM purged_hda_ids
             LEFT OUTER JOIN history
                             ON purged_hda_ids.history_id = history.id
             LEFT OUTER JOIN deleted_metadata_file_ids
                             ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_icda_ids
                             ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
    ORDER BY purged_hda_ids.id
    """
    causals = (
        ("purged_hda_id", "deleted_metadata_file_id", "object_store_id"),
        ("purged_hda_id", "deleted_icda_id", "deleted_icda_hda_id"),
    )


class PurgeOldHDAs(PurgesHDAs, RemovesMetadataFiles, RequiresDiskUsageRecalculation, Action):
    """
    - Mark purged all HistoryDatasetAssociations that are older than the specified number of days.
    - Mark deleted all MetadataFiles whose hda_id is purged in this step.
    - Mark deleted all ImplicitlyConvertedDatasetAssociations whose hda_parent_id is purged in this
      step.
    - Mark purged all HistoryDatasetAssociations for which an ImplicitlyConvertedDatasetAssociation
      with matching hda_id is deleted in this step.
    """

    force_retry_sql = " AND NOT history_dataset_association.purged"
    _action_sql = """
        WITH purged_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true{update_time_sql}
                    FROM dataset
                    WHERE history_dataset_association.dataset_id = dataset.id AND
                          dataset.create_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                          {force_retry_sql} {object_store_id_sql}
                RETURNING history_dataset_association.id,
                          history_id),
             hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_hda_ids),
             {purge_hda_dependencies_sql}
      SELECT purged_hda_ids.id AS purged_hda_id,
             history.user_id AS recalculate_disk_usage_user_id,
             deleted_metadata_file_ids.id AS deleted_metadata_file_id,
             deleted_metadata_file_ids.uuid AS deleted_metadata_file_uuid,
             deleted_metadata_file_ids.object_store_id AS object_store_id,
             deleted_icda_ids.id AS deleted_icda_id,
             deleted_icda_ids.hda_id AS deleted_icda_hda_id
        FROM purged_hda_ids
             LEFT OUTER JOIN history
                             ON purged_hda_ids.history_id = history.id
             LEFT OUTER JOIN deleted_metadata_file_ids
                             ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_icda_ids
                             ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
    ORDER BY purged_hda_ids.id
    """
    causals = (
        ("purged_hda_id", "deleted_metadata_file_id", "object_store_id"),
        ("purged_hda_id", "deleted_icda_id", "deleted_icda_hda_id"),
    )


class PurgeHistorylessHDAs(PurgesHDAs, RemovesMetadataFiles, RequiresDiskUsageRecalculation, Action):
    """
    - Mark purged all HistoryDatasetAssociations whose history_id is null.
    """

    force_retry_sql = " AND NOT history_dataset_association.purged"
    _action_sql = """
        WITH purged_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true{update_time_sql}
                     FROM dataset
                    WHERE history_id IS NULL{force_retry_sql}{object_store_id_sql}
                          AND history_dataset_association.update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING history_dataset_association.id as id,
                          history_dataset_association.history_id as history_id),
             hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_hda_ids),
             {purge_hda_dependencies_sql}
      SELECT purged_hda_ids.id AS purged_hda_id,
             history.user_id AS recalculate_disk_usage_user_id,
             deleted_metadata_file_ids.id AS deleted_metadata_file_id,
             deleted_metadata_file_ids.uuid AS deleted_metadata_file_uuid,
             deleted_metadata_file_ids.object_store_id AS object_store_id,
             deleted_icda_ids.id AS deleted_icda_id,
             deleted_icda_ids.hda_id AS deleted_icda_hda_id
        FROM purged_hda_ids
             LEFT OUTER JOIN history
                             ON purged_hda_ids.history_id = history.id
             LEFT OUTER JOIN deleted_metadata_file_ids
                             ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_icda_ids
                             ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
    ORDER BY purged_hda_ids.id
    """
    causals = (
        ("purged_hda_id", "deleted_metadata_file_id", "object_store_id"),
        ("purged_hda_id", "deleted_icda_id", "deleted_icda_hda_id"),
    )


class PurgeErrorHDAs(PurgesHDAs, RemovesMetadataFiles, RequiresDiskUsageRecalculation, Action):
    """
    - Mark purged all HistoryDatasetAssociations whose dataset_id is state = 'error' that are older
      than the specified number of days.
    """

    force_retry_sql = " AND NOT history_dataset_association.purged"
    _action_sql = """
        WITH purged_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true{update_time_sql}
                     FROM dataset
                    WHERE history_dataset_association.dataset_id = dataset.id{force_retry_sql}{object_store_id_sql}
                          AND dataset.state = 'error'
                          AND history_dataset_association.update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING history_dataset_association.id as id,
                          history_dataset_association.history_id as history_id),
             hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_hda_ids),
             {purge_hda_dependencies_sql}
      SELECT purged_hda_ids.id AS purged_hda_id,
             history.user_id AS recalculate_disk_usage_user_id,
             deleted_metadata_file_ids.id AS deleted_metadata_file_id,
             deleted_metadata_file_ids.uuid AS deleted_metadata_file_uuid,
             deleted_metadata_file_ids.object_store_id AS object_store_id,
             deleted_icda_ids.id AS deleted_icda_id,
             deleted_icda_ids.hda_id AS deleted_icda_hda_id
        FROM purged_hda_ids
             LEFT OUTER JOIN history
                             ON purged_hda_ids.history_id = history.id
             LEFT OUTER JOIN deleted_metadata_file_ids
                             ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_icda_ids
                             ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
    ORDER BY purged_hda_ids.id
    """
    causals = (
        ("purged_hda_id", "deleted_metadata_file_id", "object_store_id"),
        ("purged_hda_id", "deleted_icda_id", "deleted_icda_hda_id"),
    )


class PurgeHDAsOfPurgedHistories(PurgesHDAs, RequiresDiskUsageRecalculation, Action):
    """
    - Mark purged all HistoryDatasetAssociations in histories that are purged and older than the
      specified number of days.
    """

    force_retry_sql = " AND NOT history_dataset_association.purged"
    _action_sql = """
        WITH purged_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true{update_time_sql}
                     FROM history
                    WHERE history_dataset_association.history_id = history.id{force_retry_sql}
                          AND history.purged
                          AND history.update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING history_dataset_association.id as id,
                          history_dataset_association.history_id as history_id),
             hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_hda_ids),
             {purge_hda_dependencies_sql}
      SELECT purged_hda_ids.id AS purged_hda_id,
             history.user_id AS recalculate_disk_usage_user_id,
             deleted_metadata_file_ids.id AS deleted_metadata_file_id,
             deleted_metadata_file_ids.uuid AS deleted_metadata_file_uuid,
             deleted_metadata_file_ids.object_store_id AS object_store_id,
             deleted_icda_ids.id AS deleted_icda_id,
             deleted_icda_ids.hda_id AS deleted_icda_hda_id
        FROM purged_hda_ids
             LEFT OUTER JOIN history
                             ON purged_hda_ids.history_id = history.id
             LEFT OUTER JOIN deleted_metadata_file_ids
                             ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_icda_ids
                             ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
    ORDER BY purged_hda_ids.id
    """


class PurgeDeletedHistories(PurgesHDAs, RequiresDiskUsageRecalculation, Action):
    """
    - Mark purged all Histories marked deleted that are older than the specified number of days.
    - Mark purged all HistoryDatasetAssociations in Histories marked purged in this step (if not
      already purged).
    """

    _action_sql = """
        WITH purged_history_ids
          AS (     UPDATE history
                      SET purged = true{update_time_sql}
                    WHERE deleted{force_retry_sql}
                          AND update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING id,
                          user_id),
             history_events
          AS (INSERT INTO cleanup_event_history_association
                          (create_time, cleanup_event_id, history_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_history_ids),
             purged_hda_ids
          AS (     UPDATE history_dataset_association
                      SET purged = true, deleted = true{update_time_sql}
                     FROM purged_history_ids
                    WHERE purged_history_ids.id = history_dataset_association.history_id
                          AND NOT history_dataset_association.purged
                RETURNING history_dataset_association.history_id AS history_id,
                          history_dataset_association.id AS id),
             hda_events
          AS (INSERT INTO cleanup_event_hda_association
                          (create_time, cleanup_event_id, hda_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_hda_ids),
             {purge_hda_dependencies_sql}
      SELECT purged_history_ids.id AS purged_history_id,
             purged_history_ids.user_id AS recalculate_disk_usage_user_id,
             purged_hda_ids.id AS purged_hda_id,
             deleted_metadata_file_ids.id AS deleted_metadata_file_id,
             deleted_metadata_file_ids.uuid AS deleted_metadata_file_uuid,
             deleted_metadata_file_ids.object_store_id AS object_store_id,
             deleted_icda_ids.id AS deleted_icda_id,
             deleted_icda_ids.hda_id AS deleted_icda_hda_id
        FROM purged_history_ids
             LEFT OUTER JOIN purged_hda_ids
                             ON purged_history_ids.id = purged_hda_ids.history_id
             LEFT OUTER JOIN deleted_metadata_file_ids
                             ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
             LEFT OUTER JOIN deleted_icda_ids
                             ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
    ORDER BY purged_history_ids.id
    """
    causals = (
        ("purged_history_id", "purged_hda_id"),
        ("purged_hda_id", "deleted_metadata_file_id", "object_store_id"),
        ("purged_hda_id", "deleted_icda_id", "deleted_icda_hda_id"),
    )


class DeleteExportedHistories(Action):
    """
    - Mark deleted all Datasets that are derivative of JobExportHistoryArchives that are older than
      the specified number of days.
    """

    _action_sql = """
        WITH deleted_dataset_ids
          AS (     UPDATE dataset
                      SET deleted = true{update_time_sql}
                     FROM job_export_history_archive
                    WHERE job_export_history_archive.dataset_id = dataset.id
                          AND NOT deleted {object_store_id_sql}
                          AND dataset.update_time <= (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING dataset.id),
             dataset_events
          AS (INSERT INTO cleanup_event_dataset_association
                          (create_time, cleanup_event_id, dataset_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM deleted_dataset_ids)
      SELECT id AS deleted_dataset_id
        FROM deleted_dataset_ids
    ORDER BY id
    """


class DeleteDatasets(Action):
    """
    - Mark deleted all Datasets whose associations are all marked as deleted (LDDA) or purged (HDA)
      that are older than the specified number of days.
    - JobExportHistoryArchives have no deleted column, so the datasets for these will simply be
      deleted after the specified number of days
    """

    _action_sql = """
        WITH deleted_dataset_ids
          AS (     UPDATE dataset
                      SET deleted = true{update_time_sql}
                    WHERE NOT deleted {object_store_id_sql}
                          AND NOT EXISTS
                            (SELECT true
                               FROM library_dataset_dataset_association
                              WHERE (NOT deleted
                                     OR update_time >= (NOW() AT TIME ZONE 'utc' - interval '%(days)s days'))
                                    AND dataset.id = dataset_id)
                          AND NOT EXISTS
                            (SELECT true
                               FROM history_dataset_association
                              WHERE (NOT purged
                                     OR update_time >= (NOW() AT TIME ZONE 'utc' - interval '%(days)s days'))
                                    AND dataset.id = dataset_id)
                RETURNING id),
             dataset_events
          AS (INSERT INTO cleanup_event_dataset_association
                          (create_time, cleanup_event_id, dataset_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM deleted_dataset_ids)
      SELECT id
        FROM deleted_dataset_ids
    ORDER BY id
    """


class PurgeDatasets(RemovesDatasets, Action):
    """
    - Mark purged all Datasets marked deleted that are older than the specified number of days.
    """

    _action_sql = """
        WITH purged_dataset_ids
          AS (     UPDATE dataset
                      SET purged = true{update_time_sql}
                    WHERE deleted{force_retry_sql}{object_store_id_sql}
                          AND update_time < (NOW() AT TIME ZONE 'utc' - interval '%(days)s days')
                RETURNING id,
                          uuid,
                          object_store_id),
             dataset_events
          AS (INSERT INTO cleanup_event_dataset_association
                          (create_time, cleanup_event_id, dataset_id)
                   SELECT NOW() AT TIME ZONE 'utc', %(event_id)s, id
                     FROM purged_dataset_ids)
      SELECT id AS purged_dataset_id,
             uuid AS purged_dataset_uuid,
             object_store_id AS object_store_id
        FROM purged_dataset_ids
    ORDER BY id
    """


class Cleanup:
    def __init__(self):
        self.args = None
        self.config = None
        self.__conn = None
        self.__actions = None
        self.__current_action = None

        self.__parse_args()
        self.__setup_logging()
        self.__validate_actions()
        self.__load_config()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__conn is not None:
            self.__conn.close()

    @property
    def actions(self):
        if self.__actions is None:
            self.__actions = {}
            for name, value in inspect.getmembers(sys.modules[__name__]):
                if (
                    not name.startswith("_")
                    and inspect.isclass(value)
                    and value != Action
                    and issubclass(value, Action)
                ):
                    self.__actions[value.name_c()] = value
        return self.__actions

    @property
    def conn(self):
        if self.__conn is None:
            url = make_url(self.config.database_connection)
            log.info(f"Connecting to database with URL: {url}")
            args = url.translate_connect_args(username="user")
            args.update(url.query)
            assert url.get_dialect().name == "postgresql", "This script can only be used with PostgreSQL."
            self.__conn = psycopg2.connect(cursor_factory=NamedTupleCursor, **args)
            # TODO: is this per session or cursor?
            if self.args.work_mem is not None:
                log.info("Setting work_mem to %s", self.args.work_mem)
                self.__conn.cursor().execute("SET work_mem TO %s", (self.args.work_mem,))
        return self.__conn

    def __parse_args(self):
        parser = argparse.ArgumentParser()
        populate_config_args(parser)
        parser.add_argument(
            "-d", "--debug", action="store_true", default=False, help="Enable debug logging (SQL queries)"
        )
        parser.add_argument("--dry-run", action="store_true", default=False, help="Dry run (rollback all transactions)")
        parser.add_argument(
            "--force-retry", action="store_true", default=False, help="Retry file removals (on applicable actions)"
        )
        parser.add_argument(
            "-o",
            "--older-than",
            dest="days",
            type=int,
            default=14,
            help="Only perform action(s) on objects that have not been updated since the specified number of days",
        )
        parser.add_argument(
            "--object-store-id",
            dest="object_store_id",
            type=str,
            default=None,
            help="Only perform action(s) on objects stored in the target object store (for dataset operations - ignored by user/history centric operations)",
        )
        parser.add_argument(
            "-U",
            "--no-update-time",
            action="store_false",
            dest="update_time",
            default=True,
            help="Don't set update_time on updated objects",
        )
        parser.add_argument(
            "-s", "--sequence", dest="sequence", default="", help="DEPRECATED: Comma-separated sequence of actions"
        )
        parser.add_argument(
            "-w", "--work-mem", dest="work_mem", default=None, help="Set PostgreSQL work_mem for this connection"
        )
        parser.add_argument("-l", "--log-dir", default=DEFAULT_LOG_DIR, help="Log file directory")
        parser.add_argument("-g", "--log-file", default=None, help="Log file name")
        parser.add_argument(
            "actions",
            nargs="*",
            metavar="ACTION",
            default=[],
            help="Action(s) to perform, chosen from: {}".format(", ".join(sorted(self.actions.keys()))),
        )
        self.args = parser.parse_args()

        # add deprecated sequence arg to actions
        self.args.sequence = [x.strip() for x in self.args.sequence.split(",")]
        if self.args.sequence != [""]:
            self.args.actions.extend(self.args.sequence)
        if not self.args.actions:
            parser.error("Please specify one or more actions")

    def __setup_logging(self):
        logging.basicConfig(
            level=logging.DEBUG if self.args.debug else logging.INFO,
            format="%(asctime)s %(levelname)-5s %(funcName)s(): %(message)s",
        )

    def __validate_actions(self):
        ok = True
        for name in self.args.actions:
            if name not in self.actions.keys():
                log.error("Unknown action in sequence: %s", name)
                ok = False
        if not ok:
            log.critical("Exiting due to previous error(s)")
            sys.exit(1)

    def __load_config(self):
        app_properties = app_properties_from_args(self.args)
        self.config = galaxy.config.Configuration(**app_properties)

    def _dry_run_event(self):
        cur = self.conn.cursor()
        sql = "SELECT MAX(id) FROM cleanup_event;"
        cur.execute(sql)
        max_id = cur.fetchone()[0]
        if max_id is None:
            # there has to be at least one event in the table, if there are none just create a fake one.
            sql = "INSERT INTO cleanup_event (create_time, message) VALUES (NOW(), 'dry_run_event') RETURNING id;"
            cur.execute(sql)
            max_id = cur.fetchone()[0]
            self.conn.commit()
            log.info("An event must exist for the subsequent query to succeed, so a dummy event has been created")
        else:
            log.info(
                "Not executing event creation (increments sequence even when rolling back), using an old "
                "event ID (%i) for dry run",
                max_id,
            )
        return max_id

    def _execute(self, sql, args):
        cur = self.conn.cursor()
        sql_str = cur.mogrify(sql, args).decode("utf-8")
        log.debug(f"SQL is: {sql_str}")
        log.info("Executing SQL")
        cur.execute(sql, args)
        log.info("Database status: %s", cur.statusmessage)
        return cur

    def _create_event(self, message=None):
        """
        Create a new event in the cleanup_event table.
        """
        if self.args.dry_run:
            return self._dry_run_event()

        sql = """
            INSERT INTO cleanup_event
                        (create_time, message)
                 VALUES (NOW() AT TIME ZONE 'utc', %(message)s)
              RETURNING id;
        """
        message = message or self.__current_action
        args = {"message": message}
        event_id = self._execute(sql, args).fetchone()[0]
        log.info("Created event %s for action: %s", event_id, self.__current_action)
        return event_id

    def _update(self, sql, args, add_event=True, event_message=None):
        if add_event and "event_id" not in args:
            args["event_id"] = self._create_event(message=event_message)
        cur = self._execute(sql, args)
        if cur.rowcount <= 0:
            log.info("Update resulted in no changes, rolling back transaction")
            self.conn.rollback()
        else:
            log.info("Flushing transaction")
            self._flush()
        return cur

    def _flush(self):
        if self.args.dry_run:
            self.conn.rollback()
            log.info("--dry-run specified, all changes rolled back")
        else:
            self.conn.commit()
            log.info("All changes committed")

    def _run_action(self, action):
        cur = self._update(action.sql, action.sql_args)
        action.handle_results(cur)

    def run(self):
        for name in self.args.actions:
            cls = self.actions[name]
            log.info("Running action '%s':", name)
            map(log.info, cls.doc_iter())
            self.__current_action = name
            with cls(self) as action:
                self._run_action(action)
            log.info("Finished %s", name)


if __name__ == "__main__":
    with Cleanup() as app:
        try:
            app.run()
        except Exception:
            log.exception("Caught exception in run sequence:")
