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
        #TODO: have to assume trans.user here...
        #user = item.user
        user = trans.user
        sa_session = self.app.model.context
        returned = item.get_item_annotation_str( sa_session, user, item )
        print 'annotation:', returned, type( returned )
        return returned


# =============================================================================
class AnnotatableDeserializer( object ):

    def add_deserializers( self ):
        self.deserializers[ 'annotation' ] = self.deserialize_annotation

    def deserialize_annotation( self, trans, item, key, val ):
        """
        Make sure `val` is a valid annotation and assign it, deleting any existing
        if `val` is None.
        """
        val = self.validate.nullable_basestring( key, val )

        sa_session = self.app.model.context
        #TODO: have to assume trans.user here...
        user = trans.user
        if val is None:
            item.delete_item_annotation( sa_session, user, item )
            return None

        model = item.add_item_annotation( sa_session, user, item, val )
        return model.annotation
