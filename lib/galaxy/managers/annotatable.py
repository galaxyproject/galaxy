"""
Mixins for Annotatable model managers and serializers.
"""

import logging
log = logging.getLogger( __name__ )


class AnnotatableManagerMixin( object ):
    #: class of AnnotationAssociation (e.g. HistoryAnnotationAssociation)
    annotation_assoc = None

    # TODO: most of this seems to be covered by item_attrs.UsesAnnotations
    # TODO: use these below (serializer/deserializer)
    def user_annotation( self, trans, item, user ):
        return item.get_item_annotation_str( self.app.model.context, user, item )

    def owner_annotation( self, trans, item ):
        return self.user_annotation( trans, item, item.user )

    def delete_annotation( self, trans, item, user ):
        return item.delete_item_annotation( self.app.model.context, user, item )

    def annotate( self, trans, item, user, annotation ):
        if annotation is None:
            self.delete_annotation( self, trans, item, user )
            return None

        annotation_obj = item.add_item_annotation( self.app.model.context, user, item, annotation )
        return annotation_obj.annotation

    #def by_user( self, trans, user, **kwargs ):
    #    pass


class AnnotatableSerializerMixin( object ):

    def add_serializers( self ):
        self.serializers[ 'annotation' ] = self.serialize_annotation

    def serialize_annotation( self, trans, item, key ):
        """
        Get and serialize an `item`'s annotation.
        """
        # user = item.user
        #TODO: trans
        user = trans.user
        sa_session = self.app.model.context
        returned = item.get_item_annotation_str( sa_session, user, item )
        return returned


class AnnotatableDeserializerMixin( object ):

    def add_deserializers( self ):
        self.deserializers[ 'annotation' ] = self.deserialize_annotation

    def deserialize_annotation( self, trans, item, key, val ):
        """
        Make sure `val` is a valid annotation and assign it, deleting any existing
        if `val` is None.
        """
        val = self.validate.nullable_basestring( key, val )

        sa_session = self.app.model.context
        #TODO: trans
        user = trans.user
        if val is None:
            item.delete_item_annotation( sa_session, user, item )
            return None

        annotated_item = item.add_item_annotation( sa_session, user, item, val )
        return annotated_item.annotation
