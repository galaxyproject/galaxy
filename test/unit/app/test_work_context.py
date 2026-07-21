from unittest import mock

from galaxy.work.context import SessionRequestContext


def _make_context(galaxy_session=None):
    return SessionRequestContext(
        app=mock.MagicMock(),
        request=mock.MagicMock(),
        response=mock.MagicMock(),
        galaxy_session=galaxy_session,
    )


def test_set_history_without_galaxy_session_does_not_raise():
    """Regression test for https://github.com/galaxyproject/galaxy/issues/23148.

    API requests authenticated via API key have no galaxy_session, so set_history
    must not unconditionally add/commit a None session to the sa_session.
    """
    trans = _make_context(galaxy_session=None)
    history = mock.MagicMock(deleted=False)

    trans.set_history(history)

    trans.sa_session.add.assert_not_called()
    trans.sa_session.commit.assert_not_called()


def test_set_history_with_galaxy_session_updates_and_commits():
    galaxy_session = mock.MagicMock()
    trans = _make_context(galaxy_session=galaxy_session)
    history = mock.MagicMock(deleted=False)

    trans.set_history(history)

    assert galaxy_session.current_history == history
    trans.sa_session.add.assert_called_once_with(galaxy_session)
    trans.sa_session.commit.assert_called_once()
