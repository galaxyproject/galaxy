"""Replace triggers

Revision ID: c716ee82337b
Revises: a91ea1d97111
Create Date: 2025-06-16 12:43:36.193648

"""

from alembic import op

from galaxy.model.migrations.util import (
    _is_sqlite,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "c716ee82337b"
down_revision = "a91ea1d97111"
branch_labels = None
depends_on = None


def upgrade():
    if not _is_sqlite():
        create_functions_and_triggers()


def downgrade():
    """This revision is a fix for the previous migration, so no downgrade is necessary."""


def create_functions_and_triggers():
    version_info = op.get_bind().engine.dialect.server_version_info
    # For offline mode (version_info is None), we assume that version > 10
    if version_info and version_info[0] > 10 or not version_info:
        trigger_def = statement_trigger_def
        trigger_fn = statement_trigger_fn
        function_keyword = "FUNCTION"
    else:
        trigger_def = row_trigger_def
        trigger_fn = row_trigger_fn
        function_keyword = "PROCEDURE"

    with transaction():
        drop_triggers()
        create_functions(trigger_fn)
        create_triggers(trigger_def, function_keyword)


def drop_triggers():
    # Unlike sqlite, postgres triggers were only named with an "s" suffix (i.e., "*_aus" and never "*_aur").
    op.execute("DROP TRIGGER IF EXISTS trigger_history_audit_by_id_aus ON history;")
    op.execute("DROP TRIGGER IF EXISTS trigger_history_audit_by_id_ais ON history;")
    op.execute("DROP TRIGGER IF EXISTS trigger_history_audit_by_history_id_aus ON history_dataset_association;")
    op.execute("DROP TRIGGER IF EXISTS trigger_history_audit_by_history_id_ais ON history_dataset_association;")
    op.execute(
        "DROP TRIGGER IF EXISTS trigger_history_audit_by_history_id_aus ON history_dataset_collection_association;"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trigger_history_audit_by_history_id_ais ON history_dataset_collection_association;"
    )


def create_functions(trigger_fn):
    for id_field in ["history_id", "id"]:
        function_name = get_function_name(id_field)
        stmt = trigger_fn(function_name, id_field, "clock_timestamp()")
        op.execute(stmt)


def create_triggers(trigger_def, function_keyword):
    op.execute(trigger_def("trigger_history_audit_by_id_aus", "UPDATE", "history", function_keyword, "id"))
    op.execute(trigger_def("trigger_history_audit_by_id_ais", "INSERT", "history", function_keyword, "id"))
    op.execute(
        trigger_def(
            "trigger_history_audit_by_history_id_aus",
            "UPDATE",
            "history_dataset_association",
            function_keyword,
            "history_id",
        )
    )
    op.execute(
        trigger_def(
            "trigger_history_audit_by_history_id_ais",
            "INSERT",
            "history_dataset_association",
            function_keyword,
            "history_id",
        )
    )
    op.execute(
        trigger_def(
            "trigger_history_audit_by_history_id_aus",
            "UPDATE",
            "history_dataset_collection_association",
            function_keyword,
            "history_id",
        )
    )
    op.execute(
        trigger_def(
            "trigger_history_audit_by_history_id_ais",
            "INSERT",
            "history_dataset_collection_association",
            function_keyword,
            "history_id",
        )
    )


def get_function_name(id_field):
    return f"fn_audit_history_by_{id_field}"


def statement_trigger_def(trigger_name, operation, table, function_keyword, id_field):
    function_name = get_function_name(id_field)
    return f"""
        CREATE TRIGGER {trigger_name}
        AFTER {operation} ON {table}
        REFERENCING NEW TABLE AS new_table
        FOR EACH STATEMENT EXECUTE {function_keyword} {function_name}();
    """


def row_trigger_def(trigger_name, operation, table, function_keyword, id_field):
    function_name = get_function_name(id_field)
    return f"""
        CREATE TRIGGER {trigger_name}
        AFTER {operation} ON {table}
        FOR EACH ROW
        WHEN (NEW.{id_field} IS NOT NULL)
        EXECUTE {function_keyword} {function_name}();
    """


def statement_trigger_fn(function_name, id_field, timestamp):
    # This function is identical to same function in down revision a91ea1d97111
    return f"""
        CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER
            LANGUAGE 'plpgsql'
        AS $BODY$
            BEGIN
                INSERT INTO history_audit (history_id, update_time)
                SELECT DISTINCT {id_field}, {timestamp} AT TIME ZONE 'UTC'
                FROM new_table
                WHERE {id_field} IS NOT NULL
                ON CONFLICT DO NOTHING;
                RETURN NULL;
            END;
        $BODY$
    """


def row_trigger_fn(function_name, id_field, timestamp):
    # This function is identical to same function in down revision a91ea1d97111
    return f"""
        CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER
            LANGUAGE 'plpgsql'
        AS $BODY$
            BEGIN
                INSERT INTO history_audit (history_id, update_time)
                VALUES (NEW.{id_field}, {timestamp} AT TIME ZONE 'UTC')
                ON CONFLICT DO NOTHING;
                RETURN NULL;
            END;
        $BODY$
    """
