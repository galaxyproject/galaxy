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

The STATEMENT-vs-ROW decision must match the trigger DEFINITION installed by
`c716ee82337b` so the function body references the right context (`new_table`
vs `NEW`); both use `version > 10` (and treat offline mode as STATEMENT).

SQLite installations use the poll-only path and require no change.
"""

from alembic import op

from galaxy.model.migrations.util import (
    _is_sqlite,
    transaction,
)
from galaxy.model.triggers.update_audit_table import (
    build_trigger_fn,
    fn_prefix,
    use_statement_trigger,
)

revision = "b8d5e2f9a1c7"
down_revision = "f5e9e4bca542"
branch_labels = None
depends_on = None


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


def _install_functions(with_notify: bool) -> None:
    version_info = op.get_bind().engine.dialect.server_version_info
    # Offline mode (no live connection) matches c716ee82337b: assume STATEMENT.
    statement = version_info is None or use_statement_trigger(version_info[0])
    for id_field in ("history_id", "id"):
        fn_name = f"{fn_prefix}_{id_field}"
        op.execute(build_trigger_fn(fn_name, id_field, use_statement=statement, with_notify=with_notify))
