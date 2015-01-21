"""
Mixins for Annotatable model managers and serializers.
"""

from galaxy import exceptions
from galaxy import model

import logging
log = logging.getLogger( __name__ )


# =============================================================================
class AnnotatableManagerInterface( object ):
    annotation_assoc = None

    #TODO: most of this seems to be covered by item_attrs.UsesAnnotations


# =============================================================================
class AnnotatableSerializer( object ):

    def add_serializers( self ):
        self.serializers[ 'annotation' ] = self.serialize_annotation

    def serialize_annotation( self, trans, item, key ):
        """
        Get and serialize an `item`'s annotation.
        """
#TODO: which is correct here?
        #user = item.user
        user = trans.user
        sa_session = self.app.model.context
        return item.get_item_annotation_str( sa_session, user, item )


# =============================================================================
class AnnotatableDeserializer( object ):

    def add_deserializers( self ):
        self.deserializers[ 'annotation' ] = self.deserialize_annotation

    def deserialize_annotation( self, trans, item, key, val ):
        """
        Make sure `val` is a valid annotation and assign it.
        """
#TODO: no validate here...
        val = self.validate.nullable_basestring( key, val )
        #TODO: have to assume trans.user here...
        return item.add_item_annotation( trans.sa_session, trans.user, item, val )

