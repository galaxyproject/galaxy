"""make dataset uuids unique

Revision ID: 04288b6a5b25
Revises: c63848676caf
Create Date: 2024-07-24 10:43:48.162813

NOTE ON NAMING: In this script, the term "latest" refers to a dataset that has
the smallest primary key in a group of datasets with duplicate UUIDs and,
therefore, is the oldest/original dataset in this group.
"""

from alembic import op
from sqlalchemy.sql import text

from galaxy.model.migrations.util import (
    _is_sqlite,
    create_unique_constraint,
    drop_constraint,
    table_exists,
)

# revision identifiers, used by Alembic.
revision = "04288b6a5b25"
down_revision = "c63848676caf"
branch_labels = None
depends_on = None

dataset_table_name = "dataset"
uuid_column = "uuid"
unique_constraint_name = "uq_uuid_column"

DEBUG = False


# sqlite isn't production - ignore the fake uuid please
# https://stackoverflow.com/questions/17277735/using-uuids-in-sqlite
def new_uuid():
    return "lower(hex(randomblob(16)))" if _is_sqlite() else "REPLACE(gen_random_uuid()::text, '-', '')"


def upgrade():
    connection = op.get_bind()

    op.execute("DROP TABLE IF EXISTS duplicate_datasets_by_uuid")
    op.execute("DROP TABLE IF EXISTS temp_duplicates_counts")
    op.execute("DROP VIEW IF EXISTS temp_duplicate_datasets_purged")
    op.execute("DROP VIEW IF EXISTS temp_duplicate_datasets_active")
    op.execute("DROP TABLE IF EXISTS temp_latest_active_duplicate")
    op.execute("DROP TABLE IF EXISTS temp_active_mapping")
    op.execute("DROP TABLE IF EXISTS hda_dataset_mapping_pre_uuid_condense")
    op.execute("DROP TABLE IF EXISTS ldda_dataset_mapping_pre_uuid_condense")

    # Find and store duplicate UUIDs - create table temp_duplicates_counts
    _setup_duplicate_counts(connection)

    # Backup all dataset info for duplicated dataset table in
    # table duplicate_datasets_by_uuid
    _setup_backup_datasets_for_duplicated_uuids(connection)

    # create views temp_duplicate_datasets_purged and temp_duplicate_datasets_active to
    # join against in subsequent queries inspect this data
    _setup_duplicated_dataset_views_by_purged_status(connection)

    _find_latest_active_dataset_for_each_uuid(connection)  # and record in temp_latest_active_duplicate

    _map_active_uuids_to_latest(connection)  # in temp table temp_active_mapping

    _preserve_old_dataset_association_mappings(connection)

    _randomize_uuids_for_purged_datasets_with_duplicated_uuids(connection)
    _randomize_uuids_for_older_active_datasets_with_duplicated_uuids(connection)

    _update_dataset_associations_to_point_to_latest_active_datasets(connection)

    # cleanup all working tables except backups required to undo migration prcoess - these backups are
    # duplicate_datasets_by_uuid, ldda_dataset_mapping_pre_uuid_condense, hda_dataset_mapping_pre_uuid_condense
    op.execute("DROP VIEW IF EXISTS temp_duplicate_datasets_purged")
    op.execute("DROP VIEW IF EXISTS temp_duplicate_datasets_active")
    op.execute("DROP TABLE IF EXISTS temp_active_mapping")
    op.execute("DROP TABLE IF EXISTS temp_latest_active_duplicate")
    op.execute("DROP TABLE IF EXISTS temp_duplicates_counts")

    # Add a unique constraint to the UUID column
    create_unique_constraint(unique_constraint_name, dataset_table_name, [uuid_column])


def downgrade():
    connection = op.get_bind()

    drop_constraint(unique_constraint_name, dataset_table_name)

    # restoring the old uuids requires untracked tables left by previous upgrade
    # the unit tests do not set these up - so lets verify the tables we need exist
    # before restoring the UUIDs.
    if table_exists("hda_dataset_mapping_pre_uuid_condense", True):
        _restore_old_mappings(connection)
        _restore_dataset_uuids(connection)

    # cleanup left behind untracked tables duplicate_datasets_by_uuid, ldda_dataset_mapping_pre_uuid_condense, hda_dataset_mapping_pre_uuid_condense
    op.execute("DROP TABLE IF EXISTS duplicate_datasets_by_uuid")
    op.execute("DROP TABLE IF EXISTS ldda_dataset_mapping_pre_uuid_condense")
    op.execute("DROP TABLE IF EXISTS hda_dataset_mapping_pre_uuid_condense")


def _restore_old_mappings(connection):
    restore_hda_dataset_ids = text(
        """
        UPDATE history_dataset_association
        SET dataset_id=mapping.old_dataset_id
        FROM hda_dataset_mapping_pre_uuid_condense AS mapping
        WHERE mapping.id = history_dataset_association.id
        """
    )
    connection.execute(restore_hda_dataset_ids)
    restore_ldda_dataset_ids = text(
        """
        UPDATE library_dataset_dataset_association
        SET dataset_id=mapping.old_dataset_id
        FROM ldda_dataset_mapping_pre_uuid_condense as mapping
        WHERE mapping.id = library_dataset_dataset_association.id
        """
    )
    connection.execute(restore_ldda_dataset_ids)


def _restore_dataset_uuids(connection):
    restore_ldda_dataset_ids = text(
        f"""
        UPDATE {dataset_table_name}
        SET {uuid_column}=backup_datasets.{uuid_column}
        FROM duplicate_datasets_by_uuid as backup_datasets
        WHERE backup_datasets.id = {dataset_table_name}.id
        """
    )
    connection.execute(restore_ldda_dataset_ids)


def _setup_duplicate_counts(connection):
    duplicate_counts_query = text(
        f"""
        CREATE TEMP TABLE temp_duplicates_counts AS
        SELECT {uuid_column}, COUNT(*)
        FROM {dataset_table_name}
        GROUP BY {uuid_column}
        HAVING COUNT(*) > 1
        """
    )
    connection.execute(duplicate_counts_query)


def _setup_backup_datasets_for_duplicated_uuids(connection):
    duplicate_datasets = text(
        f"""
        CREATE TABLE duplicate_datasets_by_uuid AS
        SELECT *
        FROM {dataset_table_name}
        WHERE {uuid_column} IN (select {uuid_column} from temp_duplicates_counts)
        """
    )
    connection.execute(duplicate_datasets)


def _setup_duplicated_dataset_views_by_purged_status(connection):
    duplicate_purged_datasets_query = text(
        """
        CREATE TEMP VIEW temp_duplicate_datasets_purged AS
        SELECT *
        FROM duplicate_datasets_by_uuid
        WHERE purged = true
        """
    )
    connection.execute(duplicate_purged_datasets_query)

    duplicate_active_datasets_query = text(
        """
        CREATE TEMP VIEW temp_duplicate_datasets_active AS
        SELECT *
        FROM duplicate_datasets_by_uuid
        WHERE purged = false
        """
    )
    connection.execute(duplicate_active_datasets_query)
    _debug(connection, "purged duplicated", text("select count(*) from temp_duplicate_datasets_purged"))
    _debug(connection, "active duplicated", text("select count(*) from temp_duplicate_datasets_active"))


def _find_latest_active_dataset_for_each_uuid(connection):
    latest_active_duplicate_query = text(
        f"""
        CREATE TEMP TABLE temp_latest_active_duplicate AS
        SELECT {uuid_column}, MIN(id) as latest_dataset_id
        FROM temp_duplicate_datasets_active
        GROUP BY {uuid_column}
        """
    )
    connection.execute(latest_active_duplicate_query)
    debug_query = text("select * from temp_latest_active_duplicate")
    _debug(connection, "latest active table", debug_query)


def _map_active_uuids_to_latest(connection):
    active_mapping_query = text(
        f"""
        CREATE TEMP TABLE temp_active_mapping AS
        SELECT d.id as from_dataset_id, l.latest_dataset_id as to_dataset_id, l.{uuid_column} as uuid
        FROM temp_duplicate_datasets_active as d
        LEFT JOIN temp_latest_active_duplicate l ON d.{uuid_column} = l.{uuid_column}
        """
    )
    connection.execute(active_mapping_query)
    debug_query = text("select * from temp_active_mapping")
    _debug(connection, "temp active mapping", debug_query)
    debug_query = text("select * from temp_active_mapping as m where m.from_dataset_id != m.to_dataset_id")
    _debug(connection, "temp active mapping older...", debug_query)


def _randomize_uuids_for_purged_datasets_with_duplicated_uuids(connection):
    updated_purged_uuids = text(
        f"""
        UPDATE {dataset_table_name}
        SET uuid={new_uuid()}
        WHERE {uuid_column} IN (SELECT {uuid_column} FROM temp_duplicate_datasets_purged) AND purged = true
        """
    )
    connection.execute(updated_purged_uuids)


def _randomize_uuids_for_older_active_datasets_with_duplicated_uuids(connection):
    # sanity check...
    duplicate_datasets_with_uuid_of_latest_active_uuid = text(
        f"""
        SELECT COUNT(*)
        FROM {dataset_table_name} as d
        INNER JOIN temp_active_mapping AS a ON d.uuid = a.uuid
        GROUP BY d.{uuid_column}
        HAVING COUNT(*) > 1
        """
    )
    _debug(
        connection,
        "(before) duplicate_datasets_with_uuid_of_latest_active_uuid",
        duplicate_datasets_with_uuid_of_latest_active_uuid,
    )

    update_older_datasets = text(
        f"""
        UPDATE {dataset_table_name}
        SET uuid={new_uuid()}
        WHERE EXISTS
            (
                SELECT *
                FROM temp_active_mapping as m
                where m.from_dataset_id = {dataset_table_name}.id and m.from_dataset_id != m.to_dataset_id
            )
        """
    )
    connection.execute(update_older_datasets)

    _debug(
        connection,
        "(after) duplicate_datasets_with_uuid_of_latest_active_uuid",
        duplicate_datasets_with_uuid_of_latest_active_uuid,
    )

    duplicate_active_count = text(
        """
        SELECT COUNT(*)
        FROM temp_active_mapping
        """
    )
    _debug(connection, "(after) duplicate_active_count", duplicate_active_count)
    datasets_with_originally_duplicated_uuids = text(
        f"""
        SELECT COUNT(*)
        FROM {dataset_table_name} as d
        INNER JOIN temp_active_mapping AS a ON d.uuid = a.uuid
        """
    )
    _debug(connection, "(after) datasets_with_originally_duplicated_uuids", datasets_with_originally_duplicated_uuids)


def _update_dataset_associations_to_point_to_latest_active_datasets(connection):
    # for others select one dataset to represent the dataset in HDAs/LDDAs
    update_hda_links = text(
        """
        UPDATE history_dataset_association
        SET dataset_id=t.to_dataset_id
        FROM temp_active_mapping t
        WHERE t.from_dataset_id = dataset_id
        """
    )
    connection.execute(update_hda_links)
    update_ldda_links = text(
        """
        UPDATE library_dataset_dataset_association
        SET dataset_id=t.to_dataset_id
        FROM temp_active_mapping t
        WHERE t.from_dataset_id = dataset_id
        """
    )
    connection.execute(update_ldda_links)


def _preserve_old_dataset_association_mappings(connection):
    old_hda_mappings = text(
        f"""
        CREATE TABLE hda_dataset_mapping_pre_uuid_condense AS
        SELECT DISTINCT h.id as id, d.id as old_dataset_id
         FROM history_dataset_association AS h
         INNER JOIN dataset AS d ON h.dataset_id = d.id
         INNER JOIN duplicate_datasets_by_uuid AS duplicates ON d.{uuid_column} = duplicates.{uuid_column}
        """
    )
    connection.execute(old_hda_mappings)
    old_ldda_mappings = text(
        f"""
        CREATE TABLE ldda_dataset_mapping_pre_uuid_condense AS
         SELECT l.id as id, d.id as old_dataset_id
         FROM library_dataset_dataset_association aS l
         INNER JOIN dataset AS d ON l.dataset_id = d.id
         INNER JOIN duplicate_datasets_by_uuid AS duplicates ON d.{uuid_column} = duplicates.{uuid_column}
        """
    )
    connection.execute(old_ldda_mappings)


def _debug(connection, log_msg, query):
    if DEBUG:
        result = connection.execute(query)
        print(f"{log_msg} {result.all()}")
