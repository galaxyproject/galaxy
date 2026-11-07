"""Interactive callback retries must respect committed entry-point revocation."""

from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest

from galaxy import model


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"__engagequeue_attempt": "accepted-attempt"},
    ],
)
def test_retried_callback_refreshes_revocation_before_proxy_publication(tmp_path, params, monkeypatch):
    from sqlalchemy import (
        create_engine,
        Table,
        update,
    )
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Session

    from galaxy.managers.interactivetool import InteractiveToolManager

    engine = create_engine(f"sqlite:///{tmp_path / 'entry-points.sqlite'}")
    table = model.InteractiveToolEntryPoint.__table__
    assert isinstance(table, Table)
    table.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        entry_point = model.InteractiveToolEntryPoint(job_id=42, tool_port=8888, configured=False)
        session.add(entry_point)
        session.commit()
        initially_deleted = entry_point.deleted
        assert initially_deleted is False
        # Stop commits in another request, while callback's identity map still
        # holds the old object. Merely checking ep.deleted would be insufficient.
        with Session(engine) as stop_session:
            stop_session.execute(
                update(model.InteractiveToolEntryPoint)
                .where(model.InteractiveToolEntryPoint.id == entry_point.id)
                .values(deleted=True)
            )
            stop_session.commit()
        cached_deleted = entry_point.deleted
        assert cached_deleted is False
        manager = object.__new__(InteractiveToolManager)
        monkeypatch.setattr(manager, "sa_session", session, raising=False)
        manager.dispatcher = None
        save_entry_point = Mock()
        monkeypatch.setattr(manager, "save_entry_point", save_entry_point)
        job = cast(
            model.Job,
            SimpleNamespace(
                id=42,
                destination_params=params,
                interactivetool_entry_points=[entry_point],
            ),
        )
        recorded = []
        original_scalars = session.scalars

        def locked_scalars(statement):
            recorded.append(str(statement.compile(dialect=postgresql.dialect())))
            return original_scalars(statement)

        monkeypatch.setattr(session, "scalars", locked_scalars)
        result = manager.configure_entry_points(job, {"8888": {"host": "127.0.0.1", "port": 12345, "protocol": "http"}})
        assert result == {"configured": [], "not_configured": [entry_point]}
        assert entry_point.deleted is True
        assert entry_point.configured is False
        save_entry_point.assert_not_called()
        assert "FOR UPDATE" in recorded[0]
    engine.dispose()
