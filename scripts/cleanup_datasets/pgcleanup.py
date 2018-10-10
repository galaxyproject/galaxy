#!/usr/bin/env python
"""
pgcleanup.py - A script for cleaning up datasets in Galaxy efficiently, by
    bypassing the Galaxy model and operating directly on the database.
    PostgreSQL 9.1 or greater is required.
"""
from __future__ import print_function

import argparse
import datetime
import inspect
import logging
import os
import shutil
import sys

import psycopg2
from six import string_types
from sqlalchemy.engine.url import make_url

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(1, os.path.join(galaxy_root, 'lib'))

import galaxy.config
from galaxy.exceptions import ObjectNotFound
from galaxy.objectstore import build_object_store_from_config
from galaxy.util.bunch import Bunch
from galaxy.util.script import app_properties_from_args, populate_config_args

log = logging.getLogger()


class MetadataFile(Bunch):
    pass


class Dataset(Bunch):
    pass


class Cleanup(object):
    def __init__(self):
        self.args = None
        self.config = None
        self.conn = None
        self.action_names = []
        self.logs = {}
        self.disk_accounting_user_ids = []
        self.object_store = None

        self.__cache_action_names()
        self.__parse_args()
        self.__setup_logging()
        self.__load_config()
        self.__connect_db()
        self.__load_object_store()

    def __cache_action_names(self):
        for name, value in inspect.getmembers(self):
            if not name.startswith('_') and inspect.ismethod(value):
                self.action_names.append(name)

    def __parse_args(self):
        parser = argparse.ArgumentParser()
        populate_config_args(parser)
        parser.add_argument('-d', '--debug', action='store_true', dest='debug', help='Enable debug logging', default=False)
        parser.add_argument('--dry-run', action='store_true', dest='dry_run', help="Dry run (rollback all transactions)", default=False)
        parser.add_argument('--force-retry', action='store_true', dest='force_retry', help="Retry file removals (on applicable actions)", default=False)
        parser.add_argument('-o', '--older-than', type=int, dest='days', help='Only perform action(s) on objects that have not been updated since the specified number of days', default=14)
        parser.add_argument('-U', '--no-update-time', action='store_false', dest='update_time', help="Don't set update_time on updated objects", default=True)
        parser.add_argument('-s', '--sequence', dest='sequence', help='Comma-separated sequence of actions, chosen from: %s' % self.action_names, default='')
        parser.add_argument('-w', '--work-mem', dest='work_mem', help='Set PostgreSQL work_mem for this connection', default=None)
        parser.add_argument('-l', '--log-dir', dest='log_dir', help='Log file directory', default=os.path.join(galaxy_root, 'scripts', 'cleanup_datasets'))
        self.args = parser.parse_args()

        self.args.sequence = [x.strip() for x in self.args.sequence.split(',')]

        if self.args.sequence == ['']:
            print("Error: At least one action must be specified in the action sequence\n")
            parser.print_help()
            sys.exit(0)

    def __setup_logging(self):
        format = "%(funcName)s %(levelname)s %(asctime)s %(message)s"
        if self.args.debug:
            logging.basicConfig(level=logging.DEBUG, format=format)
        else:
            logging.basicConfig(level=logging.INFO, format=format)

    def __load_config(self):
        app_properties = app_properties_from_args(self.args)
        self.config = galaxy.config.Configuration(**app_properties)

    def __connect_db(self):
        url = make_url(galaxy.config.get_database_url(self.config))

        log.info('Connecting to database with URL: %s' % url)
        args = url.translate_connect_args(username='user')
        args.update(url.query)

        assert url.get_dialect().name == 'postgresql', 'This script can only be used with PostgreSQL.'

        self.conn = psycopg2.connect(**args)

    def __load_object_store(self):
        self.object_store = build_object_store_from_config(self.config)

    def _open_logfile(self):
        action_name = inspect.stack()[1][3]
        logname = os.path.join(self.args.log_dir, action_name + '.log')

        if self.args.dry_run:
            log.debug('--dry-run specified, logging changes to stdout instead of log file: %s' % logname)
            self.logs[action_name] = sys.stdout
        else:
            log.debug('Opening log file: %s' % logname)
            self.logs[action_name] = open(logname, 'a')

        message = '==== Log opened: %s ' % datetime.datetime.now().isoformat()
        self.logs[action_name].write(message.ljust(72, '='))
        self.logs[action_name].write('\n')

    def _log(self, message, action_name=None):
        if action_name is None:
            action_name = inspect.stack()[1][3]
        if not message.endswith('\n'):
            message += '\n'
        self.logs[action_name].write(message)

    def _close_logfile(self):
        action_name = inspect.stack()[1][3]

        message = '==== Log closed: %s ' % datetime.datetime.now().isoformat()
        self.logs[action_name].write(message.ljust(72, '='))
        self.logs[action_name].write('\n')

        if self.args.dry_run:
            log.debug('--dry-run specified, changes were logged to stdout insted of log file')
        else:
            log.debug('Closing log file: %s' % self.logs[action_name].name)
            self.logs[action_name].close()

        del self.logs[action_name]

    def _run(self):
        ok = True
        for name in self.args.sequence:
            if name not in self.action_names:
                log.error('Unknown action in sequence: %s' % name)
                ok = False
        if not ok:
            log.critical('Exiting due to previous error(s)')
            sys.exit(1)
        for name in self.args.sequence:
            log.info('Calling %s' % name)
            self.__getattribute__(name)()
            log.info('Finished %s' % name)

    def _create_event(self, message=None):
        """
        Create a new event in the cleanup_event table.
        """

        if message is None:
            message = inspect.stack()[2][3]

        sql = """
            INSERT INTO cleanup_event
                        (create_time, message)
                 VALUES (NOW(), %(message)s)
              RETURNING id;
        """

        args = {'message': message}

        log.debug("SQL is: %s", sql % args_for_print(args))

        cur = self.conn.cursor()

        if self.args.dry_run:
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
                log.info("Not executing event creation (increments sequence even when rolling back), using an old event ID (%i) for dry run" % max_id)
            return max_id

        log.info("Executing SQL")
        cur.execute(sql, args)
        log.info('Database status: %s' % cur.statusmessage)

        return cur.fetchone()[0]

    @property
    def _update_time_sql(self):
        # only update time if not doing force retry (otherwise a lot of things would have their update times reset that were actually purged a long time ago)
        if self.args.update_time and not self.args.force_retry:
            return ", update_time = NOW()"
        return ""

    @property
    def _force_retry_sql(self):
        if not self.args.force_retry:
            return " AND NOT purged"""
        return ""

    def _format_sql(self, sql):
        return sql.format(
            update_time_sql=self._update_time_sql,
            force_retry_sql=self._force_retry_sql,
        )

    def _add_default_args(self, args):
        if isinstance(args, dict):
            if 'days' not in args:
                args['days'] = self.args.days

    def _update(self, sql, args, add_event=True, event_message=None):
        sql = self._format_sql(sql)
        if add_event and isinstance(args, dict) and 'event_id' not in args:
            args['event_id'] = self._create_event(message=event_message)
        self._add_default_args(args)

        if args is not None:
            log.debug('SQL is: %s', sql % args_for_print(args))
        else:
            log.debug('SQL is: %s', sql)

        cur = self.conn.cursor()

        if self.args.work_mem is not None:
            log.info('Setting work_mem to %s' % self.args.work_mem)
            cur.execute('SET work_mem TO %s', (self.args.work_mem,))

        log.info('Executing SQL')
        cur.execute(sql, args)
        log.info('Database status: %s' % cur.statusmessage)

        return cur

    def _flush(self):
        if self.args.dry_run:
            self.conn.rollback()
            log.info("--dry-run specified, all changes rolled back")
        else:
            self.conn.commit()
            log.info("All changes committed")

    def _remove_metadata_file(self, id, object_store_id, action_name):
        metadata_file = MetadataFile(id=id, object_store_id=object_store_id)

        try:
            filename = self.object_store.get_filename(metadata_file, extra_dir='_metadata_files', extra_dir_at_root=True, alt_name="metadata_%d.dat" % id)
            self._log('Removing from disk: %s' % filename, action_name)
        except (ObjectNotFound, AttributeError) as e:
            log.error('Unable to get MetadataFile %s filename: %s' % (id, e))
            return

        if not self.args.dry_run:
            try:
                os.unlink(filename)
            except Exception as e:
                self._log('Removal of %s failed with error: %s' % (filename, e), action_name)

    def _update_user_disk_usage(self):
        """
        Any operation that purges a HistoryDatasetAssociation may require
        updating a user's disk usage.  Rather than attempt to resolve dataset
        copies at purge-time, simply maintain a list of users that have had
        HDAs purged, and update their usages once all updates are complete.

        This could probably be done more efficiently.
        """
        log.info('Recalculating disk usage for users whose HistoryDatasetAssociations were purged')

        for user_id in self.disk_accounting_user_ids:

            # TODO: h.purged = false should be unnecessary once all hdas in purged histories are purged.
            sql = """
                   UPDATE galaxy_user
                      SET disk_usage = (SELECT COALESCE(SUM(total_size), 0)
                                          FROM (  SELECT d.total_size
                                                    FROM history_dataset_association hda
                                                         JOIN history h ON h.id = hda.history_id
                                                         JOIN dataset d ON hda.dataset_id = d.id
                                                   WHERE h.user_id = %(user_id)s
                                                         AND h.purged = false
                                                         AND hda.purged = false
                                                         AND d.purged = false
                                                         AND d.id NOT IN (SELECT dataset_id
                                                                            FROM library_dataset_dataset_association)
                                                GROUP BY d.id) sizes)
                    WHERE id = %(user_id)s
                RETURNING disk_usage;
            """

            args = {'user_id': user_id}
            cur = self._update(sql, args, add_event=False)
            self._flush()

            for tup in cur:
                # disk_usage might be None (e.g. user has purged all data)
                log.debug('Updated disk usage for user id %i to %s bytes' % (user_id, tup[0]))

    def _shutdown(self):
        self.object_store.shutdown()
        self.conn.close()
        for handle in self.logs.values():
            message = '==== Log closed at shutdown: %s ' % datetime.datetime.now().isoformat()
            handle.write(message.ljust(72, '='))
            handle.write('\n')
            handle.close()

    #
    # actions
    #

    # the _update method automatically:
    #   - calls the sql argument's (string) format() method to replace '{update_time_sql}' and '{force_retry_sql}'
    #   - creates an event and adds its id to args with key `event_id` (if args is a dict)
    #   - adds `days` to args (if args is a dict)

    def update_hda_purged_flag(self):
        """
        The old cleanup script does not mark HistoryDatasetAssociations as purged when deleted Histories are purged.  This method can be used to rectify that situation.
        """
        log.info('Marking purged all HistoryDatasetAssociations associated with purged Datasets')

        # update_time is intentionally left unmodified.
        sql = """
                WITH purged_hda_ids
                  AS (     UPDATE history_dataset_association
                              SET purged = true
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
              SELECT id
                FROM purged_hda_ids
            ORDER BY id;
        """

        cur = self._update(sql, {})
        self._flush()

        self._open_logfile()
        for tup in cur:
            self._log('Marked HistoryDatasetAssociation purged: %s' % tup[0])
        self._close_logfile()

    def delete_userless_histories(self):
        """
        Mark deleted all "anonymous" Histories (not owned by a registered user) that are older than the specified number of days.
        """
        log.info('Marking deleted all userless Histories older than %i days' % self.args.days)

        sql = """
                WITH deleted_history_ids
                  AS (     UPDATE history
                              SET deleted = true{update_time_sql}
                            WHERE user_id is null
                                  AND NOT deleted
                                  AND update_time < (NOW() - interval '%(days)s days')
                        RETURNING id),
                     history_events
                  AS (INSERT INTO cleanup_event_history_association
                                  (create_time, cleanup_event_id, history_id)
                           SELECT NOW(), %(event_id)s, id
                             FROM deleted_history_ids)
              SELECT id
                FROM deleted_history_ids
            ORDER BY id
        """

        cur = self._update(sql, {})
        self._flush()

        self._open_logfile()
        for tup in cur:
            self._log('Marked userless History deleted: %s' % tup[0])
        self._close_logfile()

    def purge_error_hdas(self):
        """
        Mark purged all HistoryDatasetAssociations whose dataset_id is state = 'error' that are older than the specified
        number of days.
        """
        log.info('Marking purged all error state HistoryDatasetAssociations older than %i days' % self.args.days)

        sql = """
              WITH purged_hda_ids
                AS (     UPDATE history_dataset_association
                            SET purged = true{update_time_sql}
                           FROM dataset
                          WHERE history_dataset_association.dataset_id = dataset.id
                                AND dataset.state = 'error'
                                AND history_dataset_association.update_time < (NOW() - interval '%(days)s days')
                      RETURNING history_dataset_association.id as id,
                                history_dataset_association.history_id as history_id),
                   hda_events
                AS (INSERT INTO cleanup_event_hda_association
                                (create_time, cleanup_event_id, hda_id)
                         SELECT NOW(), %(event_id)s, id
                           FROM purged_hda_ids)
            SELECT purged_hda_ids.id,
                   history.user_id
              FROM purged_hda_ids
                   LEFT OUTER JOIN history
                                   ON purged_hda_ids.history_id = history.id
          ORDER BY purged_hda_ids.id
        """

        cur = self._update(sql, {})
        self._flush()

        self._open_logfile()
        for tup in cur:
            self._log('Marked HistoryDatasetAssociations purged: %s' % tup[0])
            if tup[1] is not None and tup[1] not in self.disk_accounting_user_ids:
                self.disk_accounting_user_ids.append(int(tup[1]))
        self._close_logfile()

    def purge_hdas_of_purged_histories(self):
        """
        Mark purged all HistoryDatasetAssociations in histories that are purged and older than the specified number of days.
        """
        log.info('Marking purged all HistoryDatasetAssociations in purged Histories older than %i days' % self.args.days)

        sql = """
              WITH purged_hda_ids
                AS (     UPDATE history_dataset_association
                            SET purged = true{update_time_sql}
                           FROM history
                          WHERE history_dataset_association.history_id = history.id
                                AND NOT history_dataset_association.purged
                                AND history.purged
                                AND history.update_time < (NOW() - interval '%(days)s days')
                      RETURNING history_dataset_association.id as id,
                                history_dataset_association.history_id as history_id),
                   hda_events
                AS (INSERT INTO cleanup_event_hda_association
                                (create_time, cleanup_event_id, hda_id)
                         SELECT NOW(), %(event_id)s, id
                           FROM purged_hda_ids)
            SELECT purged_hda_ids.id,
                   history.user_id
              FROM purged_hda_ids
                   LEFT OUTER JOIN history
                                   ON purged_hda_ids.history_id = history.id
          ORDER BY purged_hda_ids.id
        """

        cur = self._update(sql, {})
        self._flush()

        self._open_logfile()
        for tup in cur:
            self._log('Marked HistoryDatasetAssociations purged: %s' % tup[0])
            if tup[1] is not None and tup[1] not in self.disk_accounting_user_ids:
                self.disk_accounting_user_ids.append(int(tup[1]))
        self._close_logfile()

    def purge_deleted_hdas(self):
        """
        Mark purged all HistoryDatasetAssociations currently marked deleted that are older than the specified number of days.
        Mark deleted all MetadataFiles whose hda_id is purged in this step.
        Mark deleted all ImplicitlyConvertedDatasetAssociations whose hda_parent_id is purged in this step.
        Mark purged all HistoryDatasetAssociations for which an ImplicitlyConvertedDatasetAssociation with matching hda_id is deleted in this step.
        """
        log.info('Marking purged all deleted HistoryDatasetAssociations older than %i days' % self.args.days)

        sql = """
              WITH purged_hda_ids
                AS (     UPDATE history_dataset_association
                            SET purged = true{update_time_sql}
                          WHERE deleted{force_retry_sql}
                                AND update_time < (NOW() - interval '%(days)s days')
                      RETURNING id,
                                history_id),
                   deleted_metadata_file_ids
                AS (     UPDATE metadata_file
                            SET deleted = true{update_time_sql}
                           FROM purged_hda_ids
                          WHERE purged_hda_ids.id = metadata_file.hda_id
                      RETURNING metadata_file.hda_id AS hda_id,
                                metadata_file.id AS id,
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
                            SET purged = true{update_time_sql}
                           FROM deleted_icda_ids
                          WHERE deleted_icda_ids.hda_id = history_dataset_association.id),
                   hda_events
                AS (INSERT INTO cleanup_event_hda_association
                                (create_time, cleanup_event_id, hda_id)
                         SELECT NOW(), %(event_id)s, id
                           FROM purged_hda_ids),
                   metadata_file_events
                AS (INSERT INTO cleanup_event_metadata_file_association
                                (create_time, cleanup_event_id, metadata_file_id)
                         SELECT NOW(), %(event_id)s, id
                           FROM deleted_metadata_file_ids),
                   icda_events
                AS (INSERT INTO cleanup_event_icda_association
                                (create_time, cleanup_event_id, icda_id)
                         SELECT NOW(), %(event_id)s, id
                           FROM deleted_icda_ids),
                   icda_hda_events
                AS (INSERT INTO cleanup_event_hda_association
                                (create_time, cleanup_event_id, hda_id)
                         SELECT NOW(), %(event_id)s, hda_id
                           FROM deleted_icda_ids)
            SELECT purged_hda_ids.id,
                   history.user_id,
                   deleted_metadata_file_ids.id,
                   deleted_metadata_file_ids.object_store_id,
                   deleted_icda_ids.id,
                   deleted_icda_ids.hda_id
              FROM purged_hda_ids
                   LEFT OUTER JOIN deleted_metadata_file_ids
                                   ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
                   LEFT OUTER JOIN deleted_icda_ids
                                   ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
                   LEFT OUTER JOIN history
                                   ON purged_hda_ids.history_id = history.id
        """

        cur = self._update(sql, {})
        self._flush()

        self._open_logfile()
        for tup in cur:
            self._log('Marked HistoryDatasetAssociations purged: %s' % tup[0])
            if tup[1] is not None and tup[1] not in self.disk_accounting_user_ids:
                self.disk_accounting_user_ids.append(int(tup[1]))
            if tup[2] is not None:
                self._log('Purge of HDA %s caused deletion of MetadataFile: %s in Object Store: %s' % (tup[0], tup[2], tup[3]))
                self._remove_metadata_file(tup[2], tup[3], inspect.stack()[0][3])
            if tup[4] is not None:
                self._log('Purge of HDA %s caused deletion of ImplicitlyConvertedDatasetAssociation: %s and converted HistoryDatasetAssociation: %s' % (tup[0], tup[4], tup[5]))
        self._close_logfile()

    def purge_deleted_histories(self):
        """
        Mark purged all Histories marked deleted that are older than the specified number of days.
        Mark purged all HistoryDatasetAssociations in Histories marked purged in this step (if not already purged).
        """
        log.info('Marking purged all deleted histories that are older than the specified number of days.')

        sql = """
              WITH purged_history_ids
                AS (     UPDATE history
                            SET purged = true{update_time_sql}
                          WHERE deleted{force_retry_sql}
                                AND update_time < (NOW() - interval '%(days)s days')
                      RETURNING id,
                                user_id),
                   purged_hda_ids
                AS (     UPDATE history_dataset_association
                            SET purged = true{update_time_sql}
                           FROM purged_history_ids
                          WHERE purged_history_ids.id = history_dataset_association.history_id
                                AND NOT history_dataset_association.purged
                      RETURNING history_dataset_association.history_id AS history_id,
                                history_dataset_association.id AS id),
                   deleted_metadata_file_ids
                AS (     UPDATE metadata_file
                            SET deleted = true{update_time_sql}
                           FROM purged_hda_ids
                          WHERE purged_hda_ids.id = metadata_file.hda_id
                      RETURNING metadata_file.hda_id AS hda_id,
                                metadata_file.id AS id,
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
                            SET purged = true{update_time_sql}
                           FROM deleted_icda_ids
                          WHERE deleted_icda_ids.hda_id = history_dataset_association.id),
                   history_events
                AS (INSERT INTO cleanup_event_history_association
                                (create_time, cleanup_event_id, history_id)
                         SELECT NOW(), %(event_id)s, id
                           FROM purged_history_ids),
                   hda_events
                AS (INSERT INTO cleanup_event_hda_association
                                (create_time, cleanup_event_id, hda_id)
                         SELECT NOW(), %(event_id)s, id
                           FROM purged_hda_ids),
                   metadata_file_events
                AS (INSERT INTO cleanup_event_metadata_file_association
                                (create_time, cleanup_event_id, metadata_file_id)
                         SELECT NOW(), %(event_id)s, id
                           FROM deleted_metadata_file_ids),
                   icda_events
                AS (INSERT INTO cleanup_event_icda_association
                                (create_time, cleanup_event_id, icda_id)
                         SELECT NOW(), %(event_id)s, id
                           FROM deleted_icda_ids),
                   icda_hda_events
                AS (INSERT INTO cleanup_event_hda_association
                                (create_time, cleanup_event_id, hda_id)
                         SELECT NOW(), %(event_id)s, hda_id
                           FROM deleted_icda_ids)
            SELECT purged_history_ids.id,
                   purged_history_ids.user_id,
                   purged_hda_ids.id,
                   deleted_metadata_file_ids.id,
                   deleted_metadata_file_ids.object_store_id,
                   deleted_icda_ids.id,
                   deleted_icda_ids.hda_id
              FROM purged_history_ids
                   LEFT OUTER JOIN purged_hda_ids
                                   ON purged_history_ids.id = purged_hda_ids.history_id
                   LEFT OUTER JOIN deleted_metadata_file_ids
                                   ON deleted_metadata_file_ids.hda_id = purged_hda_ids.id
                   LEFT OUTER JOIN deleted_icda_ids
                                   ON deleted_icda_ids.hda_parent_id = purged_hda_ids.id
          ORDER BY purged_history_ids.id
        """

        cur = self._update(sql, {})
        self._flush()

        self._open_logfile()
        for tup in cur:
            self._log('Marked History purged: %s' % tup[0])
            if tup[1] is not None and tup[1] not in self.disk_accounting_user_ids:
                self.disk_accounting_user_ids.append(int(tup[1]))
            if tup[2] is not None:
                self._log('Purge of History %s caused deletion of HistoryDatasetAssociation: %s' % (tup[0], tup[2]))
            if tup[3] is not None:
                self._log('Purge of HDA %s caused deletion of MetadataFile: %s in Object Store: %s' % (tup[1], tup[3], tup[4]))
                self._remove_metadata_file(tup[3], tup[4], inspect.stack()[0][3])
            if tup[5] is not None:
                self._log('Purge of HDA %s caused deletion of ImplicitlyConvertedDatasetAssociation: %s and converted HistoryDatasetAssociation: %s' % (tup[1], tup[5], tup[6]))
        self._close_logfile()

    def delete_exported_histories(self):
        """
        Mark deleted all Datasets that are derivative of JobExportHistoryArchives that are older than the specified number of days.
        """
        log.info('Marking deleted all Datasets that are derivative of JobExportHistoryArchives that are older than the specified number of days.')

        sql = """
                WITH deleted_dataset_ids
                  AS (     UPDATE dataset
                              SET deleted = true{update_time_sql}
                             FROM job_export_history_archive
                            WHERE job_export_history_archive.dataset_id = dataset.id
                                  AND NOT deleted
                                  AND dataset.update_time <= (NOW() - interval '%(days)s days')
                        RETURNING dataset.id),
                     dataset_events
                  AS (INSERT INTO cleanup_event_dataset_association
                                  (create_time, cleanup_event_id, dataset_id)
                           SELECT NOW(), %(event_id)s, id
                             FROM deleted_dataset_ids)
              SELECT id
                FROM deleted_dataset_ids
            ORDER BY id
        """

        cur = self._update(sql, {})
        self._flush()

        self._open_logfile()
        for tup in cur:
            self._log('Marked Dataset deleted: %s' % tup[0])
        self._close_logfile()

    def delete_datasets(self):
        """
        Mark deleted all Datasets whose associations are all marked as deleted (LDDA) or purged (HDA) that are older than the specified number of days.
        """
        log.info('Marking deleted all Datasets whose associations are all marked as deleted/purged that are older than the specified number of days.')

        sql = """
                WITH deleted_dataset_ids
                  AS (     UPDATE dataset
                              SET deleted = true{update_time_sql}
                            WHERE NOT deleted
                                  AND NOT EXISTS (SELECT true
                                                    FROM library_dataset_dataset_association
                                                   WHERE (NOT deleted
                                                          OR update_time >= (NOW() - interval '%(days)s days'))
                                                         AND dataset.id = dataset_id)
                                  AND NOT EXISTS (SELECT true
                                                    FROM history_dataset_association
                                                   WHERE (NOT purged
                                                          OR update_time >= (NOW() - interval '%(days)s days'))
                                                         AND dataset.id = dataset_id)
                        RETURNING id),
                     dataset_events
                  AS (INSERT INTO cleanup_event_dataset_association
                                  (create_time, cleanup_event_id, dataset_id)
                           SELECT NOW(), %(event_id)s, id
                             FROM deleted_dataset_ids)
              SELECT id
                FROM deleted_dataset_ids
            ORDER BY id
        """

        cur = self._update(sql, {})
        self._flush()

        self._open_logfile()
        for tup in cur:
            self._log('Marked Dataset deleted: %s' % tup[0])
        self._close_logfile()

    def purge_datasets(self):
        """
        Mark purged all Datasets marked deleted that are older than the specified number of days.
        """
        log.info('Marking purged all Datasets marked deleted that are older than the specified number of days.')

        sql = """
                WITH purged_dataset_ids
                  AS (     UPDATE dataset
                              SET purged = true{update_time_sql}
                            WHERE deleted{force_retry_sql}
                                  AND update_time < (NOW() - interval '%(days)s days')
                        RETURNING id,
                                  object_store_id),
                     dataset_events
                  AS (INSERT INTO cleanup_event_dataset_association
                                  (create_time, cleanup_event_id, dataset_id)
                           SELECT NOW(), %(event_id)s, id
                             FROM purged_dataset_ids)
              SELECT id,
                     object_store_id
                FROM purged_dataset_ids
            ORDER BY id
        """

        cur = self._update(sql, {})
        self._flush()

        self._open_logfile()
        for tup in cur:
            self._log('Marked Dataset purged: %s in Object Store: %s' % (tup[0], tup[1]))

            # always try to remove the "object store path" - if it's at an external_filename, that file will be untouched anyway (which is what we want)
            dataset = Dataset(id=tup[0], object_store_id=tup[1])
            try:
                filename = self.object_store.get_filename(dataset)
            except (ObjectNotFound, AttributeError) as e:
                log.error('Unable to get Dataset %s filename: %s' % (tup[0], e))
                continue

            try:
                extra_files_dir = self.object_store.get_filename(dataset, dir_only=True, extra_dir="dataset_%d_files" % tup[0])
            except (ObjectNotFound, AttributeError):
                extra_files_dir = None

            # don't check for existence of the dataset, it should exist
            self._log('Removing from disk: %s' % filename)
            if not self.args.dry_run:
                try:
                    os.unlink(filename)
                except Exception as e:
                    self._log('Removal of %s failed with error: %s' % (filename, e))

            # extra_files_dir is optional so it's checked first
            if extra_files_dir is not None and os.path.exists(extra_files_dir):
                self._log('Removing from disk: %s' % extra_files_dir)
                if not self.args.dry_run:
                    try:
                        shutil.rmtree(extra_files_dir)
                    except Exception as e:
                        self._log('Removal of %s failed with error: %s' % (extra_files_dir, e))

        self._close_logfile()


def quote_for_print(v):
    if isinstance(v, string_types):
        return "'" + v.replace("'", "\\'") + "'"
    else:
        return v


def args_for_print(args):
    if isinstance(args, dict):
        r = {}
        for k, v in args.items():
            r[k] = quote_for_print(v)
    elif isinstance(args, (tuple, list)):
        r = []
        for v in args:
            r.append(quote_for_print(v))
        if isinstance(args, tuple):
            r = tuple(r)
    else:
        r = args
    return r


if __name__ == '__main__':
    cleanup = Cleanup()
    try:
        cleanup._run()
        if cleanup.disk_accounting_user_ids:
            cleanup._update_user_disk_usage()
    except Exception:
        log.exception('Caught exception in run sequence:')
    cleanup._shutdown()
