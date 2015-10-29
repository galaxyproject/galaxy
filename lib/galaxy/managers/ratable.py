"""
Mixins for Ratable model managers and serializers.
"""

import logging
log = logging.getLogger( __name__ )


# TODO: stub
class RatableManagerMixin( object ):
    #: class of RatingAssociation (e.g. HistoryRatingAssociation)
    rating_assoc = None

    # TODO: most of this seems to be covered by item_attrs.UsesItemRatings

    # def by_user( self, trans, user, **kwargs ):
    #    pass


class RatableSerializerMixin( object ):

    def add_serializers( self ):
        self.serializers[ 'user_rating' ] = self.serialize_user_rating
        self.serializers[ 'community_rating' ] = self.serialize_community_rating

    def serialize_user_rating( self, item, key, user=None, **context ):
        """
        """
        pass

    def serialize_community_rating( self, item, key, **context ):
        """
        """
        pass


class RatableDeserializerMixin( object ):

    def add_deserializers( self ):
        pass
        # self.deserializers[ 'user_rating' ] = self.deserialize_rating

    # def deserialize_rating( self, trans, item, key, val ):
    #    val = self.validate.int_range( key, val, 0, 5 )
    #    return self.set_rating...( trans, item, val, user=trans.user )
