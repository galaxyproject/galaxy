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
from sqlalchemy.orm import Query
from sqlalchemy.orm import mapper as sqla_mapper

def _monkeypatch_query_method( name, session, class_ ):
    # TODO: eliminate this method by fixing the single query in ~/datatypes/metadata.py ( line 396 )
    def do(self, *args, **kwargs):
        return getattr( class_.query, name)(*args, **kwargs)
    try:
        do.__name__ = name
    except:
        pass
    if not hasattr(class_, name):
        setattr(class_, name, classmethod(do))
def _monkeypatch_session_method( name, session, class_ ):
    # TODO: eliminate this method by fixing the session flushes in ~/model/__init__.py ( 20 of them )
    # and ~/datatypes/metadata.py ( 4 of them ).  The affected objects have no known hook into mapping.context
    # ( i.e., sqlalchemy session ).
    def do( self, *args, **kwargs ):
        if self not in session.deleted:
            session.add( self )
        return session.flush() 
    try:
        do.__name__ = name
    except:
        pass
    if not hasattr( class_, name ):
        setattr( class_, name, do )
def session_mapper( scoped_session, class_, *args, **kwargs ):
    def mapper( cls, *arg, **kw ):
        validate = kw.pop( 'validate', False )
        if cls.__init__ is object.__init__:
            def __init__( self, **kwargs ):
                for key, value in kwargs.items():
                    if validate:
                        if not cls_mapper.has_property( key ):
                            raise TypeError( "Invalid __init__ argument: '%s'" % key )
                    setattr( self, key, value )
            cls.__init__ = __init__
        cls.query = scoped_session.query_property()
        _monkeypatch_query_method( 'get', scoped_session, cls )
        _monkeypatch_session_method( 'flush', scoped_session, cls )
        return sqla_mapper( cls, *arg, **kw )
    return mapper( class_, *args, **kwargs )
def assign_mapper( session, class_, *args, **kwargs ):
    m = class_.mapper = session_mapper( session, class_, *args, **kwargs )
    return m
