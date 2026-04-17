"""Add pg_notify to history audit triggers

Revision ID: b8d5e2f9a1c7
Revises: f5e9e4bca542
Create Date: 2026-04-17 14:30:00.000000

The SSE-based history update pipeline (see `managers/history_audit_monitor.py`)
depends on a PostgreSQL LISTEN on the `galaxy_history_update` channel. For
existing installations, trigger functions installed by earlier migrations (most
recently `c716ee82337b_replace_triggers`) do not emit the corresponding
`pg_notify`, so the monitor wakes up only from the poll-timeout fallback and
per-history events are never dispatched in real time. This revision replaces
both audit trigger functions with versions that emit `pg_notify` for each
affected history id, matching `model/triggers/update_audit_table.py` used on
fresh installs.

SQLite installations use the poll-only path and require no change.
"""

from alembic import op

from galaxy.model.migrations.util import (
    _is_sqlite,
    transaction,
)

revision = "b8d5e2f9a1c7"
down_revision = "f5e9e4bca542"
branch_labels = None
depends_on = None


CHANNEL = "galaxy_history_update"


def upgrade():
    if _is_sqlite():
        return
    with transaction():
        _install_functions(with_notify=True)


def downgrade():
    if _is_sqlite():
        return
    with transaction():
        _install_functions(with_notify=False)


def _install_functions(with_notify: bool):
    version_info = op.get_bind().engine.dialect.server_version_info
    use_statement = version_info is None or version_info[0] >= 10
    builder = _statement_trigger_fn if use_statement else _row_trigger_fn
    for id_field in ("history_id", "id"):
        op.execute(builder(f"fn_audit_history_by_{id_field}", id_field, with_notify))


def _statement_trigger_fn(function_name: str, id_field: str, with_notify: bool) -> str:
    notify_block = (
        f"""
                FOR _history_id IN SELECT DISTINCT {id_field} FROM new_table WHERE {id_field} IS NOT NULL
                LOOP
                    PERFORM pg_notify('{CHANNEL}', _history_id::text);
                END LOOP;
        """
        if with_notify
        else ""
    )
    declare_block = "DECLARE _history_id integer;" if with_notify else ""
    return f"""
        CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER
            LANGUAGE 'plpgsql'
        AS $BODY$
            {declare_block}
            BEGIN
                INSERT INTO history_audit (history_id, update_time)
                SELECT DISTINCT {id_field}, clock_timestamp() AT TIME ZONE 'UTC'
                FROM new_table
                WHERE {id_field} IS NOT NULL
                ON CONFLICT DO NOTHING;
                {notify_block}
                RETURN NULL;
            END;
        $BODY$
    """


def _row_trigger_fn(function_name: str, id_field: str, with_notify: bool) -> str:
    notify_stmt = f"PERFORM pg_notify('{CHANNEL}', NEW.{id_field}::text);" if with_notify else ""
    return f"""
        CREATE OR REPLACE FUNCTION {function_name}()
            RETURNS TRIGGER
            LANGUAGE 'plpgsql'
        AS $BODY$
            BEGIN
                INSERT INTO history_audit (history_id, update_time)
                VALUES (NEW.{id_field}, clock_timestamp() AT TIME ZONE 'UTC')
                ON CONFLICT DO NOTHING;
                {notify_stmt}
                RETURN NULL;
            END;
        $BODY$
    """
