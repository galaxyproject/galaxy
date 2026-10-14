from datetime import (
    date,
    datetime,
    timedelta,
)

import pytest
from sqlalchemy import (
    select,
    update,
)

from galaxy import model as m
from galaxy.model.scripts.delete_galaxy_sessions import (
    _get_default_max_update_time,
    run,
)

CUTOFF = datetime(2026, 1, 15)
OLD = CUTOFF - timedelta(days=60)
OLDER = CUTOFF - timedelta(days=90)
RECENT = CUTOFF + timedelta(days=1)


def test_run_keeps_each_users_current_session(session, engine, make_user, make_galaxy_session):
    inactive_user = make_user()
    inactive_current = make_galaxy_session(user=inactive_user, update_time=OLD)
    inactive_stale = make_galaxy_session(user=inactive_user, update_time=OLDER)

    active_user = make_user()
    active_current = make_galaxy_session(user=active_user, update_time=RECENT)
    active_stale = make_galaxy_session(user=active_user, update_time=OLD)

    tied_user = make_user()
    tied_first = make_galaxy_session(user=tied_user, update_time=OLD)
    tied_second = make_galaxy_session(user=tied_user, update_time=OLD)

    null_time_user = make_user()
    null_time_dated = make_galaxy_session(user=null_time_user, update_time=OLD)
    null_time_undated = make_galaxy_session(user=null_time_user)

    anonymous_stale = make_galaxy_session(update_time=OLD)
    anonymous_recent = make_galaxy_session(update_time=RECENT)
    session.commit()
    # The ORM applies the column default for None, so NULL can only come from outside it.
    session.execute(update(m.GalaxySession).where(m.GalaxySession.id == null_time_undated.id).values(update_time=None))
    session.commit()

    assert null_time_undated.update_time is None
    assert null_time_user.current_galaxy_session.id == null_time_dated.id

    users = (inactive_user, active_user, tied_user, null_time_user)
    current_before = {user.id: user.current_galaxy_session.id for user in users}
    kept = {
        inactive_current.id,
        active_current.id,
        tied_second.id,
        null_time_dated.id,
        null_time_undated.id,
        anonymous_recent.id,
    }
    deleted = {inactive_stale.id, active_stale.id, tied_first.id, anonymous_stale.id}

    run(engine=engine, max_update_time=CUTOFF)

    session.expire_all()
    remaining = set(session.scalars(select(m.GalaxySession.id)))
    assert kept <= remaining
    assert not remaining & deleted
    for user in users:
        assert user.current_galaxy_session.id == current_before[user.id]


@pytest.mark.parametrize(
    "today, expected",
    [
        (date(2026, 1, 15), date(2025, 12, 16)),
        (date(2026, 3, 31), date(2026, 3, 1)),
    ],
)
def test_default_max_update_time(today, expected):
    assert _get_default_max_update_time(today) == expected
