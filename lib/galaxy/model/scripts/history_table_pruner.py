import datetime
import logging
import math

from sqlalchemy import text

TMP_TABLE = "tmp_unused_history"

ASSOC_TABLES = (
    "event",
    "history_audit",
    "history_tag_association",
    "history_annotation_association",
    "history_rating_association",
    "history_user_share_association",
    "default_history_permissions",
    "data_manager_history_association",
    "cleanup_event_history_association",
    "galaxy_session_to_history",
)

EXCLUDED_ASSOC_TABLES = (
    "job_import_history_archive",
    "job_export_history_archive",
    "workflow_invocation",
    "history_dataset_collection_association",
    "job",
    "history_dataset_association",
)

DEFAULT_BATCH_SIZE = 1000

logging.basicConfig()
log = logging.getLogger(__name__)


class HistoryTablePruner:
    """Removes unused histories (user is null, hid == 1)."""

    def __init__(self, engine, batch_size=None, max_create_time=None):
        self.engine = engine
        self.batch_size = batch_size or DEFAULT_BATCH_SIZE
        self.max_create_time = max_create_time or self._get_default_max_create_time()
        self.min_id, self.max_id = self._get_min_max_ids()
        self.batches = self._get_batch_count()

    def run(self):
        """
        Due to the very large size of some tables, we run operations in batches, using low/high history id as boundaries.
        """

        def get_high(low):
            return min(self.max_id + 1, low + self.batch_size)

        if self.min_id is None:
            log.info("No histories exist")
            return

        log.info(
            f"Total batches to run: {self.batches}, minimum history id: {self.min_id}, maximum history id: {self.max_id}"
        )

        low = self.min_id
        high = get_high(low)
        batch_counter = 1
        while low <= self.max_id:
            log.info(f"Running batch {batch_counter} of {self.batches}: history id range {low}-{high - 1}:")
            self._run_batch(low, high)
            low = high
            high = get_high(high)
            batch_counter += 1

    def _get_default_max_create_time(self):
        """By default, do not delete histories created less than a month ago."""
        today = datetime.date.today()
        return today.replace(month=today.month - 1)

    def _run_batch(self, low, high):
        empty_batch_msg = f" No histories to delete in id range {low}-{high - 1}"
        self._mark_histories_as_deleted_and_purged(low, high)
        histories = self._get_histories(low, high)
        if not histories:
            log.info(empty_batch_msg)
            return

        exclude = self._get_histories_to_exclude(low, high)

        # Calculate set of histories to delete.
        to_delete = set(histories) - exclude
        if not to_delete:
            log.info(empty_batch_msg)
            return

        self._create_tmp_table()
        try:
            self._populate_tmp_table(to_delete)
            self._delete_associations()
            self._set_references_to_null()
            self._delete_histories(low, high)
        except Exception as e:
            raise e
        finally:
            self._drop_tmp_table()

    def _get_min_max_ids(self):
        stmt = text(
            "SELECT min(id), max(id) FROM history WHERE user_id IS NULL AND hid_counter = 1 AND create_time < :create_time"
        )
        params = {"create_time": self.max_create_time}
        with self.engine.begin() as conn:
            minmax = conn.execute(stmt, params).all()
        # breakpoint()
        return minmax[0][0], minmax[0][1]

    def _get_batch_count(self):
        """Calculate number of batches to run."""
        return math.ceil((self.max_id - self.min_id) / self.batch_size)

    def _mark_histories_as_deleted_and_purged(self, low, high):
        """Mark target histories as deleted and purged to prevent their further usage."""
        log.info(" Marking histories as deleted and purged")
        stmt = text(
            """
            UPDATE history
            SET deleted = TRUE, purged = TRUE
            WHERE user_id IS NULL AND hid_counter = 1 AND create_time < :create_time AND id >= :low AND id < :high
        """
        )
        params = self._get_stmt_params(low, high)
        with self.engine.begin() as conn:
            return conn.execute(stmt, params)

    def _get_histories(self, low, high):
        """Return ids of histories to delete."""
        log.info(" Collecting history ids")
        stmt = text(
            "SELECT id FROM history WHERE user_id IS NULL AND hid_counter = 1 AND create_time < :create_time AND id >= :low AND id < :high"
        )
        params = self._get_stmt_params(low, high)
        with self.engine.begin() as conn:
            return conn.scalars(stmt, params).all()

    def _get_histories_to_exclude(self, low, high):
        """Retrieve histories that should NOT be deleted due to existence of associated records that should be preserved."""
        log.info(f" Collecting ids of histories to exclude based on {len(EXCLUDED_ASSOC_TABLES)} associated tables:")
        statements = []
        for table in EXCLUDED_ASSOC_TABLES:
            statements.append((table, text(f"SELECT history_id FROM {table} WHERE history_id >= :low AND id < :high")))

        params = self._get_stmt_params(low, high)
        ids = []
        for table, stmt in statements:
            with self.engine.begin() as conn:
                log.info(f"  Collecting history_id from {table}")
                ids += conn.scalars(stmt, params).all()

        excluded = set(ids)
        if None in excluded:
            excluded.remove(None)
        return excluded

    def _create_tmp_table(self):
        """Create temporary table to hold history ids."""
        stmt = text(f"CREATE TEMPORARY TABLE {TMP_TABLE} (id INT PRIMARY KEY)")
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def _drop_tmp_table(self):
        stmt = text(f"CREATE TEMPORARY TABLE {TMP_TABLE} (id INT PRIMARY KEY)")
        stmt = text(f"DROP TABLE {TMP_TABLE}")
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def _populate_tmp_table(self, to_delete):
        """Load ids of histories to delete into temporary table."""
        assert to_delete
        log.info(" Populating temporary table")
        sql_values = ",".join([f"({id})" for id in to_delete])
        stmt = text(f"INSERT INTO {TMP_TABLE} VALUES {sql_values}")
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def _delete_associations(self):
        """Delete records associated with histories to be deleted."""

        for table in ASSOC_TABLES:
            log.info(f" Deleting associated records from {table}")
            stmt = text(f"DELETE FROM {table} WHERE history_id IN (SELECT id FROM {TMP_TABLE})")
            with self.engine.begin() as conn:
                conn.execute(stmt)

    def _set_references_to_null(self):
        """Set history_id to null in galaxy_session table for records referring to histories to be deleted."""
        log.info(" Set history_id to null in galaxy_session")
        stmt = text(
            f"UPDATE galaxy_session SET current_history_id = NULL WHERE current_history_id IN (SELECT id FROM {TMP_TABLE})"
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def _delete_histories(self, low, high):
        """Last step: delete histories that are safe to delete."""
        log.info(f" Deleting histories in id range {low}-{high - 1}")
        stmt = text(f"DELETE FROM history WHERE id IN (SELECT id FROM {TMP_TABLE})")
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def _get_stmt_params(self, low, high):
        params = {
            "create_time": self.max_create_time,
            "low": low,
            "high": high,
        }
        return params
