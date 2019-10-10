"""
Mixins for Taggable model managers and serializers.
"""

# from galaxy import exceptions as galaxy_exceptions

import logging

from sqlalchemy import sql

from galaxy import model
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

    # TODO: most of this can be done by delegating to the GalaxyTagHandler?
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
    # TODO: here or GalaxyTagHandler
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

    valid_ops = ('eq', 'contains', 'has')

    def create_tag_filter(self, attr, op, val):

        def _create_tag_filter(model_class=None):
            if op not in TaggableFilterMixin.valid_ops:
                self.raise_filter_err(attr, op, val, 'bad op in filter')
            if model_class is None:
                return True
            class_name = model_class.__name__
            if class_name == 'HistoryDatasetCollectionAssociation':
                # Unfortunately we were a little inconsistent with out naming scheme
                class_name = 'HistoryDatasetCollection'
            target_model = getattr(model, "%sTagAssociation" % class_name)
            id_column = "%s_id" % target_model.table.name.rsplit('_tag_association')[0]
            column = target_model.table.c.user_tname + ":" + target_model.table.c.user_value
            if op == 'eq':
                if ':' not in val:
                    # We require an exact match and the tag to look for has no user_value,
                    # so we can't just concatenate user_tname, ':' and user_vale
                    cond = target_model.table.c.user_tname == val
                else:
                    cond = column == val
            else:
                cond = column.contains(val, autoescape=True)
            return sql.expression.and_(
                model_class.table.c.id == getattr(target_model.table.c, id_column),
                cond
            )
        return _create_tag_filter

    def _add_parsers(self):
        self.orm_filter_parsers.update({
            'tag': self.create_tag_filter
        })
