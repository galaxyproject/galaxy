"""
Mixins for Taggable model managers and serializers.
"""

import logging
log = logging.getLogger( __name__ )


class TaggableManagerMixin( object ):
    #: class of TagAssociation (e.g. HistoryTagAssociation)
    tag_assoc = None

    # TODO: most of this can be done by delegating to the TagManager?

    # def by_user( self, user, **kwargs ):
    #    pass


class TaggableSerializerMixin( object ):

    def add_serializers( self ):
        self.serializers[ 'tags' ] = self.serialize_tags

    def serialize_tags( self, item, key, **context ):
        """
        Return tags as a list of strings.
        """
        if not hasattr( item, 'tags' ):
            return None

        tags_str_list = []
        for tag in item.tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += ":" + tag.user_value
            tags_str_list.append( tag_str )
        return tags_str_list


class TaggableDeserializerMixin( object ):

    def add_deserializers( self ):
        self.deserializers[ 'tags' ] = self.deserialize_tags

    def deserialize_tags( self, item, key, val, user=None, **context ):
        """
        Make sure `val` is a valid list of tag strings and assign them.

        Note: this will erase any previous tags.
        """
        new_tags_list = self.validate.basestring_list( key, val )
        # TODO: have to assume trans.user here...
        # TODO: duped from tags manager - de-dupe when moved to taggable mixin
        tag_handler = self.app.tag_handler
        tag_handler.delete_item_tags( user, item )
        new_tags_str = ','.join( new_tags_list )
        tag_handler.apply_item_tags( user, item, unicode( new_tags_str.encode( 'utf-8' ), 'utf-8' ) )

        # TODO:!! does the creation of new_tags_list mean there are now more and more unused tag rows in the db?
        return item.tags


class TaggableFilterMixin( object ):

    def _tag_str_gen( self, item ):
        """
        Return a list of strings built from the item's tags.
        """
        # TODO: which user is this? all?
        for tag in item.tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += ":" + tag.user_value
            yield tag_str

    def filter_has_partial_tag( self, item, val ):
        """
        Return True if any tag partially contains `val`.
        """
        for tag_str in self._tag_str_gen( item ):
            if val in tag_str:
                return True
        return False

    def filter_has_tag( self, item, val ):
        """
        Return True if any tag exactly equals `val`.
        """
        for tag_str in self._tag_str_gen( item ):
            if val == tag_str:
                return True
        return False

    def _add_parsers( self ):
        self.fn_filter_parsers.update({
            'tag': {
                'op': {
                    'eq'    : self.filter_has_tag,
                    'has'   : self.filter_has_partial_tag,
                }
            }
        })
