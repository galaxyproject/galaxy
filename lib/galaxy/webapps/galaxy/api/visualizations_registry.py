"""
"""

from galaxy.web.base.controller import BaseAPIController
from galaxy.managers import hdas
from galaxy.web import _future_expose_api as expose_api

import logging
log = logging.getLogger( __name__ )


class VisualizationsRegistryController( BaseAPIController ):

    def __init__( self, app ):
        super( VisualizationsRegistryController, self ).__init__( app )
        self.hda_manager = hdas.HDAManager( app )

    @expose_api
    def index( self, trans, **kwargs ):
        """
        GET /api/visualizations:
        """
        print 'VisReg.index:', kwargs
        # parse target object into actual object
        target = self._deserialize_target( trans, **kwargs )
        if not target:
            return []
        return trans.app.visualizations_registry.get_visualizations( trans, target )

    def _deserialize_target( self, trans, **kwargs ):
        if 'model_class' not in kwargs:
            return None
        model_class_str = kwargs.get( 'model_class' )

        if model_class_str == 'HistoryDatasetAssociation':
            return self._deserialize_hda( trans, **kwargs )
        return None

    def _deserialize_hda( self, trans, **kwargs ):
        if 'id' in kwargs:
            decoded_id = self.decode_id( kwargs.get( 'id' ) )
            hda = self.hda_manager.get_accessible( decoded_id, trans.user )
            return hda
        if 'ids' in kwargs:
            encoded_ids = kwargs.get( 'ids' ).split( ',' )
            decoded_ids = [ self.decode_id( id_ ) for id_ in encoded_ids ]
            # TODO: list_accessible
            hdas = [ self.hda_manager.get_accessible( id_, trans.user ) for id_ in decoded_ids ]
            return hdas
        return None
