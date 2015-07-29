"""
Mixins for Annotatable model managers and serializers.
"""

import logging
log = logging.getLogger( __name__ )


class AnnotatableManagerMixin( object ):
    #: class of AnnotationAssociation (e.g. HistoryAnnotationAssociation)
    annotation_assoc = None

    def annotation( self, item ):
        """
        Return the annotation string made by the `item`'s owner or `None` if there
        is no annotation.
        """
        # NOTE: only works with sharable (.user)
        return self._user_annotation( item, item.user )

    # TODO: should/do we support multiple, non-owner annotation of items?
    def annotate( self, item, annotation, user=None, flush=True ):
        """
        Create a new annotation on `item` or delete the existing if annotation
        is `None`.
        """
        if not user:
            return None
        if annotation is None:
            self._delete_annotation( item, user, flush=flush )
            return None

        annotation_obj = item.add_item_annotation( self.session(), user, item, annotation )
        if flush:
            self.session().flush()
        return annotation_obj

    def _user_annotation( self, item, user ):
        return item.get_item_annotation_str( self.session(), user, item )

    def _delete_annotation( self, item, user, flush=True ):
        returned = item.delete_item_annotation( self.session(), user, item )
        if flush:
            self.session().flush()
        return returned


class AnnotatableSerializerMixin( object ):

    def add_serializers( self ):
        self.serializers[ 'annotation' ] = self.serialize_annotation

    def serialize_annotation( self, item, key, user=None, **context ):
        """
        Get and serialize an `item`'s annotation.
        """
        # user = item.user
        sa_session = self.app.model.context
        returned = item.get_item_annotation_str( sa_session, user, item )
        return returned


class AnnotatableDeserializerMixin( object ):

    def add_deserializers( self ):
        self.deserializers[ 'annotation' ] = self.deserialize_annotation

    def deserialize_annotation( self, item, key, val, user=None, **context ):
        """
        Make sure `val` is a valid annotation and assign it, deleting any existing
        if `val` is None.
        """
        val = self.validate.nullable_basestring( key, val )
        return self.manager.annotate( item, val, user=user, flush=False )


# TODO: I'm not entirely convinced this (or tags) are a good idea for filters since they involve a/the user
class AnnotatableFilterMixin( object ):

    def _owner_annotation( self, item ):
        """
        Get the annotation by the item's owner.
        """
        if not item.user:
            return None
        for annotation in item.annotations:
            if annotation.user == item.user:
                return annotation.annotation
        return None

    def filter_annotation_contains( self, item, val ):
        """
        Test whether `val` is in the owner's annotation.
        """
        owner_annotation = self._owner_annotation( item )
        if owner_annotation is None:
            return False
        return val in owner_annotation

    def _add_parsers( self ):
        self.fn_filter_parsers.update({
            'annotation'    : { 'op': { 'has': self.filter_annotation_contains, } },
        })
