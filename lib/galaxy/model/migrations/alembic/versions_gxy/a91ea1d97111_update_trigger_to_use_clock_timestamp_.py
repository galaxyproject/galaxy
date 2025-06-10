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
        create_functions_and_triggers("clock_timestamp()")


def downgrade():
    if not _is_sqlite():
        create_functions_and_triggers("CURRENT_TIMESTAMP")


def create_functions_and_triggers(timestamp):
    version = op.get_bind().engine.dialect.server_version_info[0]
    if version > 10:
        trigger_fn = statement_trigger_fn
    else:
        trigger_fn = row_trigger_fn

    for id_field in ["history_id", "id"]:
        function_name = f"fn_audit_history_by_{id_field}"
        stmt = trigger_fn(function_name, id_field, timestamp)
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
