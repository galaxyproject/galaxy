"""
Mixins for Taggable model managers and serializers.
"""

# from galaxy import exceptions as galaxy_exceptions

import logging

from galaxy.util import unicodify

log = logging.getLogger(__name__)


# TODO: work out the relation between serializers and managers and then fold these into the parent of the two
def _tag_str_gen(item):
    # TODO: which user is this? all?
    for tag in item.tags:
        tag_str = tag.user_tname
        if tag.value is not None:
            tag_str += ":" + tag.user_value
        yield tag_str


def _tags_to_strings(item):
    if not hasattr(item, 'tags'):
        return None
    return sorted(list(_tag_str_gen(item)))


def _tags_from_strings(item, tag_handler, new_tags_list, user=None):
    # TODO: have to assume trans.user here...
    if not user:
        # raise galaxy_exceptions.RequestParameterMissingException( 'User required for tags on ' + str( item ) )
        # TODO: this becomes a 'silent failure' - no tags are set. This is a questionable approach but
        # I haven't found a better one for anon users copying items with tags
        return
    # TODO: duped from tags manager - de-dupe when moved to taggable mixin
    tag_handler.delete_item_tags(user, item)
    new_tags_str = ','.join(new_tags_list)
    tag_handler.apply_item_tags(user, item, unicodify(new_tags_str, 'utf-8'))
    # TODO:!! does the creation of new_tags_list mean there are now more and more unused tag rows in the db?


class TaggableManagerMixin(object):
    #: class of TagAssociation (e.g. HistoryTagAssociation)
    tag_assoc = None

    # TODO: most of this can be done by delegating to the TagManager?
    def get_tags(self, item):
        """
        Return a list of tag strings.
        """
        return _tags_to_strings(item)

    def set_tags(self, item, new_tags, user=None):
        """
        Set an `item`'s tags from a list of strings.
        """
        return _tags_from_strings(item, self.app.tag_handler, new_tags, user=user)

    # def tags_by_user( self, user, **kwargs ):
    # TODO: here or TagManager
    #    pass


class TaggableSerializerMixin(object):

    def add_serializers(self):
        self.serializers['tags'] = self.serialize_tags

    def serialize_tags(self, item, key, **context):
        """
        Return tags as a list of strings.
        """
        return _tags_to_strings(item)


class TaggableDeserializerMixin(object):

    def add_deserializers(self):
        self.deserializers['tags'] = self.deserialize_tags

    def deserialize_tags(self, item, key, val, user=None, **context):
        """
        Make sure `val` is a valid list of tag strings and assign them.

        Note: this will erase any previous tags.
        """
        new_tags_list = self.validate.basestring_list(key, val)
        _tags_from_strings(item, self.app.tag_handler, new_tags_list, user=user)
        return item.tags


class TaggableFilterMixin(object):

    def filter_has_partial_tag(self, item, val):
        """
        Return True if any tag partially contains `val`.
        """
        for tag_str in _tag_str_gen(item):
            if val in tag_str:
                return True
        return False

    def filter_has_tag(self, item, val):
        """
        Return True if any tag exactly equals `val`.
        """
        for tag_str in _tag_str_gen(item):
            if val == tag_str:
                return True
        return False

    def _add_parsers(self):
        self.fn_filter_parsers.update({
            'tag': {
                'op': {
                    'eq'    : self.filter_has_tag,
                    'has'   : self.filter_has_partial_tag,
                }
            }
        })
