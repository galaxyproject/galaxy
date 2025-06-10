"""Update postgresql trigger to use clock_timestamp function

NOTE: This migration will not be applied on SQLIte.

Revision ID: a91ea1d97111
Revises: f070559879f1
Create Date: 2025-06-09 12:21:53.427419

"""

from alembic import op

from galaxy.model.migrations.util import _is_sqlite

# revision identifiers, used by Alembic.
revision = "a91ea1d97111"
down_revision = "f070559879f1"
branch_labels = None
depends_on = None


def upgrade():
    if not _is_sqlite():
        drop_functions_and_triggers()
        create_functions_and_triggers("clock_timestamp()")


def downgrade():
    if not _is_sqlite():
        drop_functions_and_triggers()
        create_functions_and_triggers("CURRENT_TIMESTAMP")


def drop_functions_and_triggers():
    op.execute("DROP FUNCTION IF EXISTS fn_audit_history_by_id CASCADE")
    op.execute("DROP FUNCTION IF EXISTS fn_audit_history_by_history_id CASCADE")


def create_functions_and_triggers(timestamp):
    version = op.get_bind().engine.dialect.server_version_info[0]
    if version > 10:
        trigger_fn = statement_trigger_fn
        trigger_def = statement_trigger_def
        function_keyword = "FUNCTION"
    else:
        trigger_fn = row_trigger_fn
        trigger_def = row_trigger_def
        function_keyword = "PROCEDURE"

    sql = []

    for id_field in ["history_id", "id"]:
        function_name = f"fn_audit_history_by_{id_field}"
        sql.append(trigger_fn(function_name, id_field, timestamp))

    trigger_config = {
        "history_dataset_association": "history_id",
        "history_dataset_collection_association": "history_id",
        "history": "id",
    }
    for table, id_field in trigger_config.items():
        function_name = f"fn_audit_history_by_{id_field}"
        for operation in ["UPDATE", "INSERT"]:
            sql.append(trigger_def(table, id_field, operation, function_keyword, function_name))

    for stmt in sql:
        op.execute(stmt)


def statement_trigger_fn(function_name, id_field, timestamp):
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


def statement_trigger_def(table, id_field, operation, function_keyword, function_name):
    trigger_name = get_trigger_name(id_field, operation)
    return f"""
        CREATE TRIGGER {trigger_name}
        AFTER {operation} ON {table}
        REFERENCING NEW TABLE AS new_table
        FOR EACH STATEMENT EXECUTE {function_keyword} {function_name}();
    """


def row_trigger_def(table, id_field, operation, function_keyword, function_name):
    trigger_name = get_trigger_name(id_field, operation)
    return f"""
        CREATE TRIGGER {trigger_name}
        AFTER {operation} ON {table}
        FOR EACH ROW
        WHEN (NEW.{id_field} IS NOT NULL)
        EXECUTE {function_keyword} {function_name}();
    """


def get_trigger_name(id_field, operation):
    # We always use the "s" code that denotes STATEMENT-type trigger. We do not use "r" for ROW-type
    # to stay consistent with preexisting instances ("r" was only used for sqlite triggers).
    operation = operation.lower()[0]  # INSERT -> i, UPDATE -> u
    code = f"a{operation}s"  # a is AFTER, s is STATEMENT
    return f"trigger_history_audit_by_{id_field}_{code}"
