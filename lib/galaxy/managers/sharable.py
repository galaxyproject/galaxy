"""
"""
import re

from galaxy import exceptions

import base
import users

import logging
log = logging.getLogger( __name__ )


# =============================================================================
class SharableModelManager( base.ModelManager, base.OwnableModelInterface, base.AccessibleModelInterface ):
    """
    Superclass for managers of a model that:
        has an owner/creator User
        is sharable with other, specific Users
        is importable (copyable) by users that have access
        has a slug which can be used as a link to view the resource
        can be published effectively making it available to all other Users
        can be rated
    """
    # e.g. histories, pages, stored workflows, visualizations

    # the model used for UserShareAssociations with this model
    user_share_model = None

    def __init__( self, app ):
        super( SharableModelManager, self ).__init__( app )
        # user manager is needed to check access/ownership/admin
        self.user_mgr = users.UserManager( app )

    # ......................................................................... has a user
    def _query_by_user( self, trans, user, filters=None, **kwargs ):
        """
        Return query for all items (of model_class type) associated with the given
        `user`.
        """
        user_filter = self.model_class.user_id == user.id
        filters=self._munge_filters( user_filter, filters )
        return self.query( trans, filters=filters, **kwargs )

    def by_user( self, trans, user, **kwargs ):
        """
        Return list for all items (of model_class type) associated with the given
        `user`.
        """
        query = self._query_by_user( trans, user, **kwargs )
        return self.list( trans, query=query, **kwargs )

    # ......................................................................... owned model interface
    def is_owner( self, trans, item, user ):
        """
        Return true if this sharable belongs to `user` (or `user` is an admin).
        """
        if self.user_mgr.is_anonymous( user ):
            # note: this needs to be overridden in the case of anon users and session.current_history
            return False
        # ... effectively a good fit to have this here, but not semantically
        if self.user_mgr.is_admin( trans, user ):
            return True
        return item.user == user

    # ......................................................................... accessible interface
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
        if self.user_mgr.is_anonymous( user ):
            return False
        if user in item.users_shared_with_dot_users:
            return True
        return False

    # ......................................................................... importable
#TODO: the relationship between importable and published is ill defined
#??: can a published item be non-importable?
    def make_importable( self, trans, item, flush=True ):
        """
        Makes item accessible--viewable and importable--and sets item's slug.
        Does not flush/commit changes, however. Item must have name, user,
        importable, and slug attributes.
        """
        trans.sa_session.add( item )
        item.importable = True
        self.create_unique_slug( trans, item, flush=False )
        if flush:
            trans.sa_session.flush()
        return item

    def make_non_importable( self, trans, item, flush=True ):
        """
        Makes item accessible--viewable and importable--and sets item's slug.
        Does not flush/commit changes, however. Item must have name, user,
        importable, and slug attributes.
        """
        #if item.published:
        #    if unpublish:
        #        self.unpublish( trans, item, flush=False )
        #    else:
        #        raise exceptions.BadRequest( 'Item must be non-published to be inaccessible', item=item )
        trans.sa_session.add( item )
        item.importable = False
        if flush:
            trans.sa_session.flush()
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

    # ......................................................................... published
#TODO: the relationship between importable and published is ill defined
    #def publish( self, trans, item, make_accessible=True, flush=True ):
    #    if not item.importable:
    #        if make_accessible:
    #            self.make_accessible( trans, item, flush=False )
    #        else:
    #            raise exceptions.RequestParameterInvalidException( 'Item must be importable to be published',
    #                                                               item=str( item ) )
    # a published item is also/already importable(=True) implicitly
    def publish( self, trans, item, flush=True ):
        """
        Set both the importable and published flags on `item` to True.
        """
        if not item.importable:
            self.make_importable( trans, item, flush=False )
        trans.sa_session.add( item )
        item.published = True
        if flush:
            trans.sa_session.flush()
        return item

    def unpublish( self, trans, item, flush=True ):
        """
        Set the published flag on `item` to False.
        """
        trans.sa_session.add( item )
        item.published = False
        if flush:
            trans.sa_session.flush()
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

    # ......................................................................... user sharing
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
        trans.sa_session.add( user_share_assoc )
        self.associate( trans, user_share_assoc, item )
        user_share_assoc.user = user

        # waat?
        self.create_unique_slug( trans, item )

        if flush:
            trans.sa_session.flush()
        return user_share_assoc

    def unshare_with( self, trans, item, user, flush=True ):
        """
        Delete a user share (or list of shares) from the database.
        """
        if isinstance( user, list ):
            return map( lambda user: self.unshare_with( trans, item, user, flush=False ), user )
        # Look for and delete sharing relation for user.
        user_share_assoc = self.get_share_assocs( trans, item, user=user )[0]
        trans.sa_session.delete( user_share_assoc )
        if flush:
            trans.sa_session.flush()
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

    # ......................................................................... slugs
    # slugs are human readable strings often used to link to sharable resources (replacing ids)
    #TODO: as validator, deserializer, etc. (maybe another object entirely?)
    def is_valid_slug( self, slug ):
        """
        Returns true if `slug` is valid.
        """
        VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )
        return VALID_SLUG_RE.match( slug )

    def set_slug( self, trans, item, new_slug, flush=True ):
        """
        Validate and set the new slug for `item`.
        """
        if not self.is_valid_slug( new_slug ):
            raise exceptions.RequestParameterInvalidException( "Invalid slug", slug=new_slug )

        # error if slug is already in use
        existing_match = ( trans.sa_session.query( self.model_class )
            .filter_by( user=item.user, slug=new_slug, importable=True ) )
        if( existing_match.count() != 0 ):
            raise exceptions.BadRequest( "Slug already exists", slug=new_slug )

        item.slug = new_slug
        if flush:
            trans.sa_session.flush()
        return item

    def get_unique_slug( self, trans, item ):
        """
        Returns a slug that is unique among user's importable items
        for item's class.
        """
        cur_slug = item.slug

        # Setup slug base.
        if cur_slug is None or cur_slug == "":
            # Item can have either a name or a title.
#TODO: this depends on the model having name or title
            if hasattr( item, 'name' ):
                item_name = item.name
            elif hasattr( item, 'title' ):
                item_name = item.title
            # Replace whitespace with '-'
            slug_base = re.sub( "\s+", "-", item_name.lower() )
            # Remove all non-alphanumeric characters.
            slug_base = re.sub( "[^a-zA-Z0-9\-]", "", slug_base )
            # Remove trailing '-'.
            if slug_base.endswith('-'):
                slug_base = slug_base[:-1]
        else:
            slug_base = cur_slug

        # Using slug base, find a slug that is not taken. If slug is taken,
        # add integer to end.
        new_slug = slug_base
        count = 1
        while ( trans.sa_session.query( item.__class__ )
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
        trans.sa_session.add( item )
        if flush:
            trans.sa_session.flush()
        return item

    #def by_slug( self, trans, user, **kwargs ):
    #    """
    #    """
    #    pass

    # ......................................................................... display
    #def display_by_username_and_slug( self, trans, username, slug ):
    #    """ Display item by username and slug. """

    #def set_public_username( self, trans, id, username, **kwargs ):
    #    """ Set user's public username and delegate to sharing() """
    #def sharing( self, trans, id, **kwargs ):
    #    """ Handle item sharing. """
    #def get_name_and_link_async( self, trans, id=None ):
    #    """ Returns item's name and link. """


# =============================================================================
class SharableModelSerializer( base.ModelSerializer ):
    pass

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


# =============================================================================
class SharableModelDeserializer( base.ModelDeserializer ):

    def deserialize_published( self, trans, item, val ):
        """
        """
        #TODO: call manager.publish/unpublish
        pass

    def deserialize_importable( self, trans, item, val ):
        """
        """
        #TODO: call manager.make_importable/non_importable
        pass

    def deserialize_slug( self, trans, item, val ):
        """
        """
        #TODO: call manager.set_slug
        pass

    #def deserialize_user_shares():
