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

from sqlalchemy import true
import re
from galaxy import exceptions

from galaxy.managers import base
from galaxy.managers import secured
from galaxy.managers import taggable
from galaxy.managers import annotatable
from galaxy.managers import ratable
from galaxy.managers import users

import logging
log = logging.getLogger( __name__ )


class SharableModelManager( base.ModelManager, secured.OwnableManagerMixin, secured.AccessibleManagerMixin,
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
    def by_user( self, user, filters=None, **kwargs ):
        """
        Return list for all items (of model_class type) associated with the given
        `user`.
        """
        user_filter = self.model_class.user_id == user.id
        filters = self._munge_filters( user_filter, filters )
        return self.list( filters=filters, **kwargs )

    # .... owned/accessible interfaces
    def is_owner( self, item, user, **kwargs ):
        """
        Return true if this sharable belongs to `user` (or `user` is an admin).
        """
        # ... effectively a good fit to have this here, but not semantically
        if self.user_manager.is_admin( user ):
            return True
        return item.user == user

    def is_accessible( self, item, user, **kwargs ):
        """
        If the item is importable, is owned by `user`, or (the valid) `user`
        is in 'users shared with' list for the item: return True.
        """
        if item.importable:
            return True
        # note: owners always have access - checking for accessible implicitly checks for ownership
        if self.is_owner( item, user, **kwargs ):
            return True
        if self.user_manager.is_anonymous( user ):
            return False
        if user in item.users_shared_with_dot_users:
            return True
        return False

    # .... importable
    def make_importable( self, item, flush=True ):
        """
        Makes item accessible--viewable and importable--and sets item's slug.
        Does not flush/commit changes, however. Item must have name, user,
        importable, and slug attributes.
        """
        self.create_unique_slug( item, flush=False )
        return self._session_setattr( item, 'importable', True, flush=flush )

    def make_non_importable( self, item, flush=True ):
        """
        Makes item accessible--viewable and importable--and sets item's slug.
        Does not flush/commit changes, however. Item must have name, user,
        importable, and slug attributes.
        """
        # item must be unpublished if non-importable
        if item.published:
            self.unpublish( item, flush=False )
        return self._session_setattr( item, 'importable', False, flush=flush )

    # .... published
    def publish( self, item, flush=True ):
        """
        Set both the importable and published flags on `item` to True.
        """
        # item must be importable to be published
        if not item.importable:
            self.make_importable( item, flush=False )
        return self._session_setattr( item, 'published', True, flush=flush )

    def unpublish( self, item, flush=True ):
        """
        Set the published flag on `item` to False.
        """
        return self._session_setattr( item, 'published', False, flush=flush )

    def _query_published( self, filters=None, **kwargs ):
        """
        Return a query for all published items.
        """
        published_filter = self.model_class.published == true()
        filters = self._munge_filters( published_filter, filters )
        return self.query( filters=filters, **kwargs )

    def list_published( self, filters=None, **kwargs ):
        """
        Return a list of all published items.
        """
        published_filter = self.model_class.published == true()
        filters = self._munge_filters( published_filter, filters )
        return self.list( filters=filters, **kwargs )

    # .... user sharing
    # sharing is often done via a 3rd table btwn a User and an item -> a <Item>UserShareAssociation
    def get_share_assocs( self, item, user=None ):
        """
        Get the UserShareAssociations for the `item`.

        Optionally send in `user` to test for a single match.
        """
        query = self.query_associated( self.user_share_model, item )
        if user is not None:
            query = query.filter_by( user=user )
        return query.all()

    def share_with( self, item, user, flush=True ):
        """
        Get or create a share for the given user (or users if `user` is a list).
        """
        # precondition: user has been validated
        # allow user to be a list and call recursivly
        if isinstance( user, list ):
            return map( lambda user: self.share_with( item, user, flush=False ), user )
        # get or create
        existing = self.get_share_assocs( item, user=user )
        if existing:
            return existing.pop( 0 )
        return self._create_user_share_assoc( item, user, flush=flush )

    def _create_user_share_assoc( self, item, user, flush=True ):
        """
        Create a share for the given user.
        """
        user_share_assoc = self.user_share_model()
        self.session().add( user_share_assoc )
        self.associate( user_share_assoc, item )
        user_share_assoc.user = user

        # ensure an item slug so shared users can access
        if not item.slug:
            self.create_unique_slug( item )

        if flush:
            self.session().flush()
        return user_share_assoc

    def unshare_with( self, item, user, flush=True ):
        """
        Delete a user share (or list of shares) from the database.
        """
        if isinstance( user, list ):
            return map( lambda user: self.unshare_with( item, user, flush=False ), user )
        # Look for and delete sharing relation for user.
        user_share_assoc = self.get_share_assocs( item, user=user )[0]
        self.session().delete( user_share_assoc )
        if flush:
            self.session().flush()
        return user_share_assoc

    def _query_shared_with( self, user, eagerloads=True, **kwargs ):
        """
        Return a query for this model already filtered to models shared
        with a particular user.
        """
        query = self.session().query( self.model_class ).join( 'users_shared_with' )
        if eagerloads is False:
            query = query.enable_eagerloads( False )
        # TODO: as filter in FilterParser also
        query = query.filter( self.user_share_model.user == user )
        return self._filter_and_order_query( query, **kwargs )

    def list_shared_with( self, user, filters=None, order_by=None, limit=None, offset=None, **kwargs ):
        """
        Return a list of those models shared with a particular user.
        """
        # TODO: refactor out dupl-code btwn base.list
        orm_filters, fn_filters = self._split_filters( filters )
        if not fn_filters:
            # if no fn_filtering required, we can use the 'all orm' version with limit offset
            query = self._query_shared_with( user, filters=orm_filters,
                order_by=order_by, limit=limit, offset=offset, **kwargs )
            return self._orm_list( query=query, **kwargs )

        # fn filters will change the number of items returnable by limit/offset - remove them here from the orm query
        query = self._query_shared_with( user, filters=orm_filters,
            order_by=order_by, limit=None, offset=None, **kwargs )
        # apply limit and offset afterwards
        items = self._apply_fn_filters_gen( query.all(), fn_filters )
        return list( self._apply_fn_limit_offset_gen( items, limit, offset ) )

    # .... slugs
    # slugs are human readable strings often used to link to sharable resources (replacing ids)
    # TODO: as validator, deserializer, etc. (maybe another object entirely?)
    def set_slug( self, item, new_slug, user, flush=True ):
        """
        Validate and set the new slug for `item`.
        """
        # precondition: has been validated
        if not self.is_valid_slug( new_slug ):
            raise exceptions.RequestParameterInvalidException( "Invalid slug", slug=new_slug )

        # error if slug is already in use
        if self._slug_exists( user, new_slug ):
            raise exceptions.Conflict( "Slug already exists", slug=new_slug )

        item.slug = new_slug
        if flush:
            self.session().flush()
        return item

    def is_valid_slug( self, slug ):
        """
        Returns true if `slug` is valid.
        """
        VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )
        return VALID_SLUG_RE.match( slug )

    def _existing_set_of_slugs( self, user ):
        query = ( self.session().query( self.model_class.slug )
                  .filter_by( user=user ) )
        return list( set( query.all() ) )

    def _slug_exists( self, user, slug ):
        query = ( self.session().query( self.model_class.slug )
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

    def _default_slug_base( self, item ):
        # override in subclasses
        if hasattr( item, 'title' ):
            return item.title.lower()
        return item.name.lower()

    def get_unique_slug( self, item ):
        """
        Returns a slug that is unique among user's importable items
        for item's class.
        """
        cur_slug = item.slug

        # Setup slug base.
        if cur_slug is None or cur_slug == "":
            slug_base = self._slugify( self._default_slug_base( item ) )
        else:
            slug_base = cur_slug

        # Using slug base, find a slug that is not taken. If slug is taken,
        # add integer to end.
        new_slug = slug_base
        count = 1
        while ( self.session().query( item.__class__ )
                    .filter_by( user=item.user, slug=new_slug, importable=True )
                    .count() != 0 ):
            # Slug taken; choose a new slug based on count. This approach can
            # handle numerous items with the same name gracefully.
            new_slug = '%s-%i' % ( slug_base, count )
            count += 1

        return new_slug

    def create_unique_slug( self, item, flush=True ):
        """
        Set a new, unique slug on the item.
        """
        item.slug = self.get_unique_slug( item )
        self.session().add( item )
        if flush:
            self.session().flush()
        return item

    # TODO: def by_slug( self, user, **kwargs ):


class SharableModelSerializer( base.ModelSerializer,
       taggable.TaggableSerializerMixin, annotatable.AnnotatableSerializerMixin, ratable.RatableSerializerMixin ):
    # TODO: stub
    SINGLE_CHAR_ABBR = None

    def add_serializers( self ):
        super( SharableModelSerializer, self ).add_serializers()
        taggable.TaggableSerializerMixin.add_serializers( self )
        annotatable.AnnotatableSerializerMixin.add_serializers( self )
        ratable.RatableSerializerMixin.add_serializers( self )

        self.serializers.update({
            'user_id'           : self.serialize_id,
            'username_and_slug' : self.serialize_username_and_slug,
            'users_shared_with' : self.serialize_users_shared_with
        })
        # these use the default serializer but must still be white-listed
        self.serializable_keyset.update([
            'importable', 'published', 'slug'
        ])

    def serialize_username_and_slug( self, item, key, **context ):
        if not ( item.user and item.slug and self.SINGLE_CHAR_ABBR ):
            return None
        return ( '/' ).join(( 'u', item.user.username, self.SINGLE_CHAR_ABBR, item.slug ) )

    # the only ones that needs any fns:
    #   user/user_id
    #   username_and_slug?

    def serialize_users_shared_with( self, item, key, user=None, **context ):
        """
        Returns a list of encoded ids for users the item has been shared.

        Skipped if the requesting user is not the owner.
        """
        # TODO: still an open question as to whether key removal based on user
        # should be handled here or at a higher level (even if we didn't have to pass user (via thread context, etc.))
        if not self.manager.is_owner( item, user ):
            self.skip()

        share_assocs = self.manager.get_share_assocs( item )
        return [ self.serialize_id( share, 'user_id' ) for share in share_assocs ]


class SharableModelDeserializer( base.ModelDeserializer,
        taggable.TaggableDeserializerMixin, annotatable.AnnotatableDeserializerMixin, ratable.RatableDeserializerMixin ):

    def add_deserializers( self ):
        super( SharableModelDeserializer, self ).add_deserializers()
        taggable.TaggableDeserializerMixin.add_deserializers( self )
        annotatable.AnnotatableDeserializerMixin.add_deserializers( self )
        ratable.RatableDeserializerMixin.add_deserializers( self )

        self.deserializers.update({
            'published'         : self.deserialize_published,
            'importable'        : self.deserialize_importable,
            'users_shared_with' : self.deserialize_users_shared_with,
        })

    def deserialize_published( self, item, key, val, **context ):
        """
        """
        val = self.validate.bool( key, val )
        if item.published == val:
            return val

        if val:
            self.manager.publish( item, flush=False )
        else:
            self.manager.unpublish( item, flush=False )
        return item.published

    def deserialize_importable( self, item, key, val, **context ):
        """
        """
        val = self.validate.bool( key, val )
        if item.importable == val:
            return val

        if val:
            self.manager.make_importable( item, flush=False )
        else:
            self.manager.make_non_importable( item, flush=False )
        return item.importable

    # TODO: def deserialize_slug( self, item, val, **context ):

    def deserialize_users_shared_with( self, item, key, val, **context ):
        """
        Accept a list of encoded user_ids, validate them as users, and then
        add or remove user shares in order to update the users_shared_with to
        match the given list finally returning the new list of shares.
        """
        unencoded_ids = [ self.app.security.decode_id( id_ ) for id_ in val ]
        new_users_shared_with = set( self.manager.user_manager.by_ids( unencoded_ids ) )
        current_shares = self.manager.get_share_assocs( item )
        currently_shared_with = set([ share.user for share in current_shares ])

        needs_adding = new_users_shared_with - currently_shared_with
        for user in needs_adding:
            current_shares.append( self.manager.share_with( item, user, flush=False ) )

        needs_removing = currently_shared_with - new_users_shared_with
        for user in needs_removing:
            current_shares.remove( self.manager.unshare_with( item, user, flush=False ) )

        self.manager.session().flush()
        # TODO: or should this return the list of ids?
        return current_shares


class SharableModelFilters( base.ModelFilterParser,
        taggable.TaggableFilterMixin, annotatable.AnnotatableFilterMixin, ratable.RatableFilterMixin ):

    def _add_parsers( self ):
        super( SharableModelFilters, self )._add_parsers()
        taggable.TaggableFilterMixin._add_parsers( self )
        annotatable.AnnotatableFilterMixin._add_parsers( self )
        ratable.RatableFilterMixin._add_parsers( self )

        self.orm_filter_parsers.update({
            'importable'    : { 'op': ( 'eq' ), 'val': self.parse_bool },
            'published'     : { 'op': ( 'eq' ), 'val': self.parse_bool },
            'slug'          : { 'op': ( 'eq', 'contains', 'like' ) },
            # chose by user should prob. only be available for admin? (most often we'll only need trans.user)
            # 'user'          : { 'op': ( 'eq' ), 'val': self.parse_id_list },
        })
