import logging

from . import DefaultToolAction

log = logging.getLogger( __name__ )


class DataManagerToolAction( DefaultToolAction ):
    """Tool action used for Data Manager Tools"""

    def execute( self, tool, trans, **kwds ):
        rval = super( DataManagerToolAction, self ).execute( tool, trans, **kwds )
        if isinstance( rval, tuple ) and len( rval ) == 2 and isinstance( rval[0], trans.app.model.Job ):
            assoc = trans.app.model.DataManagerJobAssociation( job=rval[0], data_manager_id=tool.data_manager_id  )
            trans.sa_session.add( assoc )
            trans.sa_session.flush()
        else:
            log.error( "Got bad return value from DefaultToolAction.execute(): %s" % ( rval ) )
        return rval
