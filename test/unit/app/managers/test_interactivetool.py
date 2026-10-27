"""Interactive callback retries must respect committed entry-point revocation."""

from types import SimpleNamespace
from unittest.mock import Mock

from galaxy import model
from galaxy.jobs.runners.pulsar import DETACHED_LOCAL_CAPABILITIES


def test_retried_callback_refreshes_revocation_before_proxy_publication(tmp_path):
    from sqlalchemy import (
        create_engine,
        update,
    )
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Session

    from galaxy.managers.interactivetool import InteractiveToolManager

    engine = create_engine(f"sqlite:///{tmp_path / 'entry-points.sqlite'}")
    model.InteractiveToolEntryPoint.__table__.create(engine)
    with Session(engine, expire_on_commit=False) as session:
        entry_point = model.InteractiveToolEntryPoint(job_id=42, tool_port=8888, configured=False)
        session.add(entry_point)
        session.commit()
        assert entry_point.deleted is False
        # Stop commits in another request, while callback's identity map still
        # holds the old object. Merely checking ep.deleted would be insufficient.
        with Session(engine) as stop_session:
            stop_session.execute(
                update(model.InteractiveToolEntryPoint)
                .where(model.InteractiveToolEntryPoint.id == entry_point.id)
                .values(deleted=True)
            )
            stop_session.commit()
        assert entry_point.deleted is False
        manager = object.__new__(InteractiveToolManager)
        manager.sa_session = session
        manager.dispatcher = None
        manager.save_entry_point = Mock()
        job = SimpleNamespace(
            id=42,
            destination_params={DETACHED_LOCAL_CAPABILITIES: {"schema": 1}},
            interactivetool_entry_points=[entry_point],
        )
        recorded = []
        original_scalars = session.scalars

        def locked_scalars(statement):
            recorded.append(str(statement.compile(dialect=postgresql.dialect())))
            return original_scalars(statement)

        session.scalars = locked_scalars
        result = manager.configure_entry_points(job, {"8888": {"host": "127.0.0.1", "port": 12345, "protocol": "http"}})
        assert result == {"configured": [], "not_configured": [entry_point]}
        assert entry_point.deleted is True
        assert entry_point.configured is False
        manager.save_entry_point.assert_not_called()
        assert "FOR UPDATE" in recorded[0]
    engine.dispose()
