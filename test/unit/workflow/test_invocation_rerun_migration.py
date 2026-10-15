"""Exercise the lineage migration against pre-existing invocation rows."""

from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import (
    create_engine,
    inspect,
    text,
)
from sqlalchemy.exc import IntegrityError

from galaxy.model.migrations import util


def test_invocation_rerun_migration_round_trip(monkeypatch):
    migration = import_module("galaxy.model.migrations.alembic.versions_gxy.6f9a3b2c1d80_add_invocation_rerun_lineage")
    monkeypatch.setattr(util.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(util.DDLOperation, "_is_repair_mode", lambda self: False)
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        connection.execute(text("CREATE TABLE workflow_invocation (id INTEGER PRIMARY KEY, state TEXT)"))
        connection.execute(text("INSERT INTO workflow_invocation VALUES (1, 'scheduled'), (2, 'new')"))
        connection.commit()
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        connection.commit()
        inspector = inspect(connection)
        columns = {column["name"]: column for column in inspector.get_columns("workflow_invocation")}
        assert columns["rerun_of_invocation_id"]["nullable"]
        assert inspector.get_indexes("workflow_invocation")[0]["column_names"] == ["rerun_of_invocation_id"]
        foreign_key = inspector.get_foreign_keys("workflow_invocation")[0]
        assert foreign_key["referred_table"] == "workflow_invocation"
        assert foreign_key["options"]["ondelete"] == "SET NULL"
        assert connection.execute(text("SELECT rerun_of_invocation_id FROM workflow_invocation")).all() == [
            (None,),
            (None,),
        ]
        connection.commit()
        connection.execute(text("PRAGMA foreign_keys=ON"))
        connection.execute(text("UPDATE workflow_invocation SET rerun_of_invocation_id=1 WHERE id=2"))
        connection.commit()
        with pytest.raises(IntegrityError):
            connection.execute(text("UPDATE workflow_invocation SET rerun_of_invocation_id=99 WHERE id=2"))
        connection.rollback()
        connection.execute(text("DELETE FROM workflow_invocation WHERE id=1"))
        assert (
            connection.execute(text("SELECT rerun_of_invocation_id FROM workflow_invocation WHERE id=2")).scalar()
            is None
        )
        connection.commit()
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert [column["name"] for column in inspect(connection).get_columns("workflow_invocation")] == ["id", "state"]
        assert connection.execute(text("SELECT * FROM workflow_invocation")).all() == [(2, "new")]
    engine.dispose()
