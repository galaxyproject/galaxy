"""
This is similar to the assignmapper extensions in SQLAclhemy 0.3 and 0.4 but
with some compatibility fixes. It assumes that the session is a ScopedSession,
and thus has the "mapper" method to attach contextual mappers to a class. It
adds additional query and session methods to the class to support the
SQLAlchemy 0.3 style of access. The following methods which would normally be
accessed through "Object.query().method()" are available directly through the
object:

    'get', 'filter', 'filter_by', 'select', 'select_by',
    'selectfirst', 'selectfirst_by', 'selectone', 'selectone_by',
    'get_by', 'join_to', 'join_via', 'count', 'count_by',
    'options', 'instances'

Additionally, the following Session methods, which normally accept an instance
or list of instances, are available directly through the objects, e.g.
"Session.flush( [instance] )" can be performed as "instance.flush()":

    'refresh', 'expire', 'delete', 'expunge', 'update'
"""

__all__ = [ 'assign_mapper' ]

from sqlalchemy import util, exceptions
import types
from sqlalchemy.orm import mapper, Query

def _monkeypatch_query_method( name, session, class_ ):
    def do(self, *args, **kwargs):
        ## util.warn_deprecated('Query methods on the class are deprecated; use %s.query.%s instead' % (class_.__name__, name))
        return getattr( class_.query, name)(*args, **kwargs)
    try:
        do.__name__ = name
    except:
        pass
    if not hasattr(class_, name):
        setattr(class_, name, classmethod(do))

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
    for name in ('get', 'filter', 'filter_by', 'select', 'select_by',
                 'selectfirst', 'selectfirst_by', 'selectone', 'selectone_by',
                 'get_by', 'join_to', 'join_via', 'count', 'count_by',
                 'options', 'instances'):
        _monkeypatch_query_method(name, session, class_)
    for name in ('refresh', 'expire', 'delete', 'expunge', 'update'):
        _monkeypatch_session_method(name, session, class_)
    for name in ( 'flush', ):
        _monkeypatch_session_method( name, session, class_, make_list=True )
    return m
