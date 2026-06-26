"""Add tool_request.request_state + tool_source identity columns + tightened UQ.

Three coordinated changes:

1. ``tool_request.request_state`` records the validity of the captured request
   payload (``not_validated`` / ``validated`` / ``validation_failed``). Distinct
   from ``tool_request.state``, which tracks the async-submission lifecycle.
   Set whenever a ToolRequest is minted (async API or workflow tool step).

2. ``tool_source`` gains per-execution tool identity columns (``tool_id``,
   ``tool_version``, ``dynamic_tool_id``) plus an ``identity_hash`` derived
   from them. Tool identity now hangs off the row itself rather than being
   recovered from the referencing ``ToolRequest``.

3. ``tool_source`` UNIQUE is ``(hash, source_class, identity_hash)``. Distinct
   dynamic-tool rows can therefore carry identical source text without sharing
   a row, while content-identical static tools still dedupe.

Existing dev DBs accumulated many ``tool_source`` rows from the async
tool-request mint path with ``hash="TODO"`` (literal placeholder, never filled
in). Those rows lack identity data; backfill writes the degenerate
``identity_hash`` for ``("static", "", "")`` for them, the dedupe step
collapses them onto the minimum-id survivor (``tool_request.tool_source_id``
references are repointed first), and only then the UNIQUE is added.

Downgrade drops the UNIQUE and the new columns; it does not un-dedupe.

Revision ID: 28885b317f78
Revises: 6925fe4c8a17
Create Date: 2026-05-21 12:30:00.000000

"""

import hashlib

import sqlalchemy as sa
from alembic import op

from galaxy.model.database_object_names import (
    build_foreign_key_name,
    build_index_name,
)
from galaxy.model.migrations.util import (
    add_column,
    alter_column,
    create_foreign_key,
    create_index,
    create_unique_constraint,
    drop_column,
    drop_constraint,
    drop_index,
    transaction,
)

# revision identifiers, used by Alembic.
revision = "28885b317f78"
down_revision = "6925fe4c8a17"
branch_labels = None
depends_on = None

table_name = "tool_source"
tool_id_index_name = build_index_name(table_name, "tool_id")
dynamic_tool_id_index_name = build_index_name(table_name, "dynamic_tool_id")
dynamic_tool_id_fk_name = build_foreign_key_name(table_name, "dynamic_tool_id")
# Matches what the model's naming convention (`%(table_name)s_%(column_0_name)s_key`)
# auto-generates for the ToolSource UniqueConstraint at definition time, so an
# init-from-model schema and a migration-built schema name the constraint the
# same way and downgrade can locate it. Widening the UQ from (hash, source_class)
# to (hash, source_class, identity_hash) does not change the auto-name because the
# convention only uses column 0.
tool_source_unique_constraint_name = "tool_source_hash_key"


def upgrade():
    with transaction():
        add_column("tool_request", sa.Column("request_state", sa.String(32)))
        _add_identity_columns()
        add_column(table_name, sa.Column("identity_hash", sa.String(255), nullable=True))
        _backfill_identity_hash()
        alter_column(table_name, "identity_hash", nullable=False)
        _dedupe_tool_source()
        create_unique_constraint(
            tool_source_unique_constraint_name,
            table_name,
            ["hash", "source_class", "identity_hash"],
        )


def downgrade():
    with transaction():
        drop_constraint(tool_source_unique_constraint_name, table_name)
        drop_column(table_name, "identity_hash")
        _drop_identity_columns()
        drop_column("tool_request", "request_state")


def _add_identity_columns():
    add_column(table_name, sa.Column("tool_id", sa.String(255), nullable=True, default=None))
    create_index(tool_id_index_name, table_name, ["tool_id"])
    add_column(table_name, sa.Column("tool_version", sa.String(255), nullable=True, default=None))
    add_column(table_name, sa.Column("dynamic_tool_id", sa.Integer, nullable=True, default=None))
    create_index(dynamic_tool_id_index_name, table_name, ["dynamic_tool_id"])
    create_foreign_key(dynamic_tool_id_fk_name, table_name, "dynamic_tool", ["dynamic_tool_id"], ["id"])


def _drop_identity_columns():
    drop_constraint(dynamic_tool_id_fk_name, table_name)
    drop_index(dynamic_tool_id_index_name, table_name)
    drop_column(table_name, "dynamic_tool_id")
    drop_column(table_name, "tool_version")
    drop_index(tool_id_index_name, table_name)
    drop_column(table_name, "tool_id")


def _backfill_identity_hash() -> None:
    conn = op.get_bind()
    rows = list(
        conn.execute(
            sa.text(f"SELECT id, tool_id, tool_version, dynamic_tool_id FROM {table_name} ORDER BY id")
        ).mappings()
    )
    for row in rows:
        conn.execute(
            sa.text(f"UPDATE {table_name} SET identity_hash = :identity_hash WHERE id = :id"),
            {"identity_hash": _identity_hash_for_row(row), "id": row["id"]},
        )


def _identity_hash_for_row(row) -> str:
    identity: tuple[str, ...]
    if (dynamic_tool_id := row["dynamic_tool_id"]) is not None:
        identity = ("dynamic", str(dynamic_tool_id))
    else:
        identity = ("static", row["tool_id"] or "", row["tool_version"] or "")
    return hashlib.sha256("\0".join(identity).encode("utf-8")).hexdigest()


def _dedupe_tool_source() -> None:
    """Repoint ``tool_request.tool_source_id`` at the minimum-id row per
    (hash, source_class, identity_hash) group, then delete loser rows.

    Pre-rollout DBs typically carry many ``hash="TODO"`` rows from the async
    mint path; they collapse onto one survivor here. SQL is written to work
    on both PostgreSQL and SQLite (correlated subqueries only — no
    UPDATE...FROM, no window functions in DELETE).
    """
    op.execute("""
        UPDATE tool_request
        SET tool_source_id = (
            SELECT MIN(ts2.id) FROM tool_source ts2
            WHERE ts2.hash = (
                SELECT ts1.hash FROM tool_source ts1
                WHERE ts1.id = tool_request.tool_source_id
            )
            AND ts2.source_class = (
                SELECT ts1.source_class FROM tool_source ts1
                WHERE ts1.id = tool_request.tool_source_id
            )
            AND ts2.identity_hash = (
                SELECT ts1.identity_hash FROM tool_source ts1
                WHERE ts1.id = tool_request.tool_source_id
            )
        )
        WHERE tool_source_id IN (
            SELECT id FROM tool_source ts
            WHERE EXISTS (
                SELECT 1 FROM tool_source ts2
                WHERE ts2.hash = ts.hash
                  AND ts2.source_class = ts.source_class
                  AND ts2.identity_hash = ts.identity_hash
                  AND ts2.id < ts.id
            )
        )
    """)
    op.execute("""
        DELETE FROM tool_source
        WHERE id IN (
            SELECT id FROM tool_source ts
            WHERE EXISTS (
                SELECT 1 FROM tool_source ts2
                WHERE ts2.hash = ts.hash
                  AND ts2.source_class = ts.source_class
                  AND ts2.identity_hash = ts.identity_hash
                  AND ts2.id < ts.id
            )
        )
    """)
