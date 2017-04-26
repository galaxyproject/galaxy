from galaxy import model
from galaxy.managers import context
from galaxy.model import mapping
from galaxy.util import bunch


class TestTransaction( context.ProvidesAppContext ):

    def __init__( self ):
        self.app = TestApp()


def test_logging_events_off():
    trans = TestTransaction()
    trans.log_event( "test event 123" )
    assert len( trans.sa_session.query( model.Event ).all() ) == 0


def test_logging_events_on():
    trans = TestTransaction()
    trans.app.config.log_events = True
    trans.log_event( "test event 123" )
    events = trans.sa_session.query( model.Event ).all()
    assert len( events ) == 1
    assert events[ 0 ].message == "test event 123"


def test_logging_actions_off():
    trans = TestTransaction()
    trans.log_action( "test action 123" )
    assert len( trans.sa_session.query( model.Event ).all() ) == 0


def test_logging_actions_on():
    trans = TestTransaction()
    trans.app.config.log_actions = True
    trans.log_action( None, "test action 123", context="the context", params=dict(foo="bar") )
    actions = trans.sa_session.query( model.UserAction ).all()
    assert len( actions ) == 1
    assert actions[ 0 ].action == "test action 123"


def test_expunge_all():
    trans = TestTransaction()

    user = model.User( "foo", "bar1" )
    trans.sa_session.add( user )

    user.password = "bar2"
    trans.sa_session.flush()

    assert trans.sa_session.query( model.User ).first().password == "bar2"

    trans.sa_session.expunge_all()

    user.password = "bar3"
    trans.sa_session.flush()

    # Password unchange because not attached to session/context.
    assert trans.sa_session.query( model.User ).first().password == "bar2"


class TestApp( object ):

    def __init__( self ):
        self.config = bunch.Bunch(
            log_events=False,
            log_actions=False,
        )
        self.model = mapping.init(
            "/tmp",
            "sqlite:///:memory:",
            create_tables=True
        )
