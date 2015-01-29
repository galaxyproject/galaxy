"""
Superclass Manager and Serializers for Sharable objects.

A sharable Galaxy object:
    has an owner/creator User
    is sharable with other, specific Users
    is importable (copyable) by users that have access
    has a slug which can be used as a link to view the resource
    can be published effectively making it available to all other Users
    can be rated
"""

import re

from galaxy import exceptions

from galaxy.managers import base
from galaxy.managers import taggable
from galaxy.managers import annotatable
from galaxy.managers import ratable
from galaxy.managers import users

import logging
log = logging.getLogger( __name__ )


class SharableModelManager( base.ModelManager, base.OwnableManagerMixin, base.AccessibleManagerMixin,
        taggable.TaggableManagerMixin, annotatable.AnnotatableManagerMixin, ratable.RatableManagerMixin ):
    # e.g. histories, pages, stored workflows, visualizations
    # base.DeleteableModelMixin? (all four are deletable)

    #: the model used for UserShareAssociations with this model
    user_share_model = None

    #: the single character abbreviation used in username_and_slug: e.g. 'h' for histories: u/user/h/slug
    SINGLE_CHAR_ABBR = None

    def __init__( self, app ):
        super( SharableModelManager, self ).__init__( app )
        # user manager is needed to check access/ownership/admin
        self.user_manager = users.UserManager( app )

    # .... has a user
    def by_user( self, trans, user, filters=None, **kwargs ):
        """
        Return list for all items (of model_class type) associated with the given
        `user`.
        """
        user_filter = self.model_class.user_id == user.id
        filters=self._munge_filters( user_filter, filters )
        return self.list( trans, filters=filters, **kwargs )

    # .... owned model interface
    def is_owner( self, trans, item, user ):
        """
        Return true if this sharable belongs to `user` (or `user` is an admin).
        """
        if self.user_manager.is_anonymous( user ):
            # note: this needs to be overridden in the case of anon users and session.current_history
            return False
        # ... effectively a good fit to have this here, but not semantically
        if self.user_manager.is_admin( trans, user ):
            return True
        return item.user == user

    # .... accessible interface
    def is_accessible( self, trans, item, user ):
        """
        If the item is importable, is owned by `user`, or (the valid) `user`
        is in 'users shared with' list for the item: return True.
        """
        if item.importable:
            return True
        # note: owners always have access - checking for accessible implicitly checks for ownership
        if self.is_owner( trans, item, user ):
            return True
        if self.user_manager.is_anonymous( user ):
            return False
        if user in item.users_shared_with_dot_users:
            return True
        return False

    # .... importable
    def make_importable( self, trans, item, flush=True ):
        """
        Makes item accessible--viewable and importable--and sets item's slug.
        Does not flush/commit changes, however. Item must have name, user,
        importable, and slug attributes.
        """
        self.app.model.context.add( item )
        item.importable = True
        self.create_unique_slug( trans, item, flush=False )
        if flush:
            self.app.model.context.flush()
        return item

    def make_non_importable( self, trans, item, flush=True ):
        """
        Makes item accessible--viewable and importable--and sets item's slug.
        Does not flush/commit changes, however. Item must have name, user,
        importable, and slug attributes.
        """
        # item must be unpublished if non-importable
        self.app.model.context.add( item )
        if item.published:
            self.unpublish( trans, item, flush=False )
        item.importable = False
        if flush:
            self.app.model.context.flush()
        return item

    #def _query_importable( self, trans, filters=None, **kwargs ):
    #    """
    #    """
    #    importable_filter = self.model_class.importable == True
    #    filters = self._munge_filters( importable_filter, filters )
    #    return self.list( trans, filters=filters, **kwargs )
    #
    #def list_importable( self, trans, **kwargs ):
    #    """
    #    """
    #    query = self._query_importable( trans, user, **kwargs )
    #    return self.list( trans, query=query, **kwargs )

    # .... published
    def publish( self, trans, item, flush=True ):
        """
        Set both the importable and published flags on `item` to True.
        """
        # item must be importable to be published
        if not item.importable:
            self.make_importable( trans, item, flush=False )
        self.app.model.context.add( item )
        item.published = True
        if flush:
            self.app.model.context.flush()
        return item

    def unpublish( self, trans, item, flush=True ):
        """
        Set the published flag on `item` to False.
        """
        self.app.model.context.add( item )
        item.published = False
        if flush:
            self.app.model.context.flush()
        return item

    #def _query_published( self, trans, filters=None, **kwargs ):
    #    """
    #    """
    #    published_filter = self.model_class.published == True
    #    filters = self._munge_filters( published_filter, filters )
    #    return self.list( trans, filters=filters, **kwargs )
    #
    #def list_published( self, trans, **kwargs ):
    #    """
    #    """
    #    query = self._query_published( trans, user, **kwargs )
    #    return self.list( trans, query=query, **kwargs )

    # .... user sharing
    # sharing is often done via a 3rd table btwn a User and an item -> a <Item>UserShareAssociation
    def get_share_assocs( self, trans, item, user=None ):
        """
        Get the UserShareAssociations for the `item`.

        Optionally send in `user` to test for a single match.
        """
        query = self.query_associated( trans, self.user_share_model, item )
        if user is not None:
            query = query.filter_by( user=user )
        return query.all()

    def share_with( self, trans, item, user, flush=True ):
        """
        Get or create a share for the given user (or users if `user` is a list).
        """
        # allow user to be a list and call recursivly
        if isinstance( user, list ):
            return map( lambda user: self.share_with( trans, item, user, flush=False ), user )
        # get or create
        existing = self.get_share_assocs( trans, item, user=user )
        if existing:
            return existing.pop( 0 )
        return self._create_user_share_assoc( trans, item, user, flush=flush )

    def _create_user_share_assoc( self, trans, item, user, flush=True ):
        """
        Create a share for the given user.
        """
        user_share_assoc = self.user_share_model()
        self.app.model.context.add( user_share_assoc )
        self.associate( trans, user_share_assoc, item )
        user_share_assoc.user = user

        # ensure an item slug so shared users can access
        if not item.slug:
            self.create_unique_slug( trans, item )

        if flush:
            self.app.model.context.flush()
        return user_share_assoc

    def unshare_with( self, trans, item, user, flush=True ):
        """
        Delete a user share (or list of shares) from the database.
        """
        if isinstance( user, list ):
            return map( lambda user: self.unshare_with( trans, item, user, flush=False ), user )
        # Look for and delete sharing relation for user.
        user_share_assoc = self.get_share_assocs( trans, item, user=user )[0]
        self.app.model.context.delete( user_share_assoc )
        if flush:
            self.app.model.context.flush()
        return user_share_assoc

    #def _query_shared_with( self, trans, user, filters=None, **kwargs ):
    ##TODO:
    #    """
    #    """
    #    pass

    #def list_shared_with( self, trans, user, **kwargs ):
    #    """
    #    """
    #    query = self._query_shared_with( trans, user, **kwargs )
    #    return self.list( trans, query=query, **kwargs )

    # .... slugs
    # slugs are human readable strings often used to link to sharable resources (replacing ids)
    #TODO: as validator, deserializer, etc. (maybe another object entirely?)
    def set_slug( self, trans, item, new_slug, flush=True ):
        """
        Validate and set the new slug for `item`.
        """
        # precondition: has been validated
        if not self.is_valid_slug( new_slug ):
            raise exceptions.RequestParameterInvalidException( "Invalid slug", slug=new_slug )

        # error if slug is already in use
        if self._slug_exists( trans, trans.user, new_slug ):
            raise exceptions.Conflict( "Slug already exists", slug=new_slug )

        item.slug = new_slug
        if flush:
            self.app.model.context.flush()
        return item

    def is_valid_slug( self, slug ):
        """
        Returns true if `slug` is valid.
        """
        VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )
        return VALID_SLUG_RE.match( slug )

    def _existing_set_of_slugs( self, trans, user ):
        query = ( self.app.model.context.query( self.model_class.slug )
                    .filter_by( user=user ) )
        return set( query.all() )

    def _slug_exists( self, trans, user, slug ):
        query = ( self.app.model.context.query( self.model_class.slug )
                    .filter_by( user=user, slug=slug ) )
        return query.count() != 0

    def _slugify( self, start_with ):
        # Replace whitespace with '-'
        slug_base = re.sub( "\s+", "-", start_with )
        # Remove all non-alphanumeric characters.
        slug_base = re.sub( "[^a-zA-Z0-9\-]", "", slug_base )
        # Remove trailing '-'.
        if slug_base.endswith('-'):
            slug_base = slug_base[:-1]
        return slug_base

    def _default_slug_base( self, trans, item ):
        # override in subclasses
        if hasattr( item, 'title' ):
            return item.title.lower()
        return item.name.lower()

    def get_unique_slug( self, trans, item ):
        """
        Returns a slug that is unique among user's importable items
        for item's class.
        """
        cur_slug = item.slug

        # Setup slug base.
        if cur_slug is None or cur_slug == "":
            slug_base = self._slugify( self._default_slug_base( trans, item ) )
        else:
            slug_base = cur_slug

        # Using slug base, find a slug that is not taken. If slug is taken,
        # add integer to end.
        new_slug = slug_base
        count = 1
        while ( self.app.model.context.query( item.__class__ )
                    .filter_by( user=item.user, slug=new_slug, importable=True )
                    .count() != 0 ):
            # Slug taken; choose a new slug based on count. This approach can
            # handle numerous items with the same name gracefully.
            new_slug = '%s-%i' % ( slug_base, count )
            count += 1

        return new_slug

    def create_unique_slug( self, trans, item, flush=True ):
        """
        Set a new, unique slug on the item.
        """
        item.slug = self.get_unique_slug( trans, item )
        self.app.model.context.add( item )
        if flush:
            self.app.model.context.flush()
        return item

    #def by_slug( self, trans, user, **kwargs ):
    #    """
    #    """
    #    pass

    # .... display
    #def display_by_username_and_slug( self, trans, username, slug ):
    #    """ Display item by username and slug. """

    #def set_public_username( self, trans, id, username, **kwargs ):
    #    """ Set user's public username and delegate to sharing() """
    #def sharing( self, trans, id, **kwargs ):
    #    """ Handle item sharing. """


class SharableModelSerializer( base.ModelSerializer,
        taggable.TaggableSerializerMixin, annotatable.AnnotatableSerializerMixin, ratable.RatableSerializerMixin ):
#TODO: stub
    SINGLE_CHAR_ABBR = None

    def add_serializers( self ):
        super( SharableModelSerializer, self ).add_serializers()
        taggable.TaggableSerializerMixin.add_serializers( self )
        annotatable.AnnotatableSerializerMixin.add_serializers( self )
        ratable.RatableSerializerMixin.add_serializers( self )

        self.serializers.update({
            'user_id'           : self.serialize_id,
            'username_and_slug' : self.serialize_username_and_slug
        })
        self.serializable_keys.extend([
            'importable', 'published', 'slug'
        ])

    def serialize_username_and_slug( self, trans, item, key ):
        if not ( item.user and item.slug and self.SINGLE_CHAR_ABBR ):
            return None
        return ( '/' ).join(( 'u', item.user.username, self.SINGLE_CHAR_ABBR, item.slug ) )

    # the only ones that needs any fns:
    #   user/user_id
    #   user_shares?
    #   username_and_slug?
    #def get_name_and_link_async( self, trans, id=None ):
    #def published_url( self, trans, item, key ):
    #    """
    #    """
    #    url = url_for(controller='history', action="display_by_username_and_slug",
    #        username=item.user.username, slug=item.slug )
    #    return url


class SharableModelDeserializer( base.ModelDeserializer,
        taggable.TaggableDeserializerMixin, annotatable.AnnotatableDeserializerMixin, ratable.RatableDeserializerMixin ):

    def add_deserializers( self ):
        super( SharableModelDeserializer, self ).add_deserializers()
        taggable.TaggableDeserializerMixin.add_deserializers( self )
        annotatable.AnnotatableDeserializerMixin.add_deserializers( self )
        ratable.RatableDeserializerMixin.add_deserializers( self )

        self.deserializers.update({
            'published'     : self.deserialize_published,
            'importable'    : self.deserialize_importable,
        })

    def deserialize_published( self, trans, item, key, val ):
        """
        """
        val = self.validate.bool( key, val )
        if item.published == val:
            return val

        if val:
            self.manager.publish( trans, item, flush=False )
        else:
            self.manager.unpublish( trans, item, flush=False )
        return item.published

    def deserialize_importable( self, trans, item, key, val ):
        """
        """
        val = self.validate.bool( key, val )
        if item.importable == val:
            return val

        if val:
            self.manager.make_importable( trans, item, flush=False )
        else:
            self.manager.make_non_importable( trans, item, flush=False )
        return item.published

    #def deserialize_slug( self, trans, item, val ):
    #    """
    #    """
    #    #TODO: call manager.set_slug
    #    pass

    #def deserialize_user_shares():


class SharableModelFilters( base.ModelFilterParser ):

    def _add_parsers( self ):
        super( SharableModelFilters, self )._add_parsers()
        self.orm_filter_parsers.update({
            'importable'    : { 'op': ( 'eq' ), 'val': self.parse_bool },
            'published'     : { 'op': ( 'eq' ), 'val': self.parse_bool },
            'slug'          : { 'op': ( 'eq', 'contains', 'like' ) },
            # chose by user should prob. only be available for admin? (most often we'll only need trans.user)
            #'user'          : { 'op': ( 'eq' ), 'val': self.parse_id_list },
        })
