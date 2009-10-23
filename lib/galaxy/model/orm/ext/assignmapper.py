"""
This is similar to the assignmapper extensions in SQLAclhemy 0.3 and 0.4 but
with some compatibility fixes. It assumes that the session is a ScopedSession,
and thus has the "mapper" method to attach contextual mappers to a class. It
adds additional query and session methods to the class to support the
SQLAlchemy 0.3 style of access.

The following Session methods, which normally accept an instance
or list of instances, are available directly through the objects, e.g.
"Session.flush( [instance] )" can be performed as "instance.flush()":

"""

__all__ = [ 'assign_mapper' ]

from sqlalchemy import util, exceptions
import types
from sqlalchemy.orm import mapper, Query

def _monkeypatch_session_method(name, session, class_, make_list=False):
    def do(self, *args, **kwargs):
        if make_list:
            self = [ self ]
        return getattr(session, name)( self, *args, **kwargs )
    try:
        do.__name__ = name
    except:
        pass
    if not hasattr(class_, name):
        setattr(class_, name, do)

def assign_mapper( session, class_, *args, **kwargs ):
    m = class_.mapper = session.mapper( class_, *args, **kwargs )
    for name in ( 'flush', ):
        _monkeypatch_session_method( name, session, class_, make_list=True )
    return m
