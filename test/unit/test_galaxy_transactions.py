import pytest

from galaxy import model
from galaxy.managers import context
from galaxy.model import mapping
from galaxy.util import bunch


class App:
    def __init__(self):
        self.config = bunch.Bunch(
            log_events=False,
            log_actions=False,
        )
        self.model = mapping.init("/tmp", "sqlite:///:memory:", create_tables=True)


class Transaction(context.ProvidesAppContext):
    def __init__(self):
        self._app = App()

    @property
    def app(self):
        return self._app

    @property
    def url_builder(self):
        return None


@pytest.fixture
def transaction():
    return Transaction()


def test_logging_events_off(transaction):
    transaction.log_event("test event 123")
    assert len(transaction.sa_session.query(model.Event).all()) == 0


def test_logging_events_on(transaction):
    transaction.app.config.log_events = True
    transaction.log_event("test event 123")
    events = transaction.sa_session.query(model.Event).all()
    assert len(events) == 1
    assert events[0].message == "test event 123"


def test_logging_actions_off(transaction):
    transaction.log_action("test action 123")
    assert len(transaction.sa_session.query(model.Event).all()) == 0


def test_logging_actions_on(transaction):
    transaction.app.config.log_actions = True
    transaction.log_action(None, "test action 123", context="the context", params=dict(foo="bar"))
    actions = transaction.sa_session.query(model.UserAction).all()
    assert len(actions) == 1
    assert actions[0].action == "test action 123"


def test_expunge_all(transaction):
    user = model.User("foo", "bar1")
    transaction.sa_session.add(user)

    user.password = "bar2"
    transaction.sa_session.flush()

    assert transaction.sa_session.query(model.User).first().password == "bar2"

    transaction.sa_session.expunge_all()

    user.password = "bar3"
    transaction.sa_session.flush()

    # Password unchange because not attached to session/context.
    assert transaction.sa_session.query(model.User).first().password == "bar2"
