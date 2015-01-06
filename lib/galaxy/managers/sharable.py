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
    # histories, pages, stored workflows, visualizations
    user_share_model = None

    def __init__( self, app ):
        """
        """
        super( SharableModelManager, self ).__init__( app )
        # user manager is needed to check access/ownership/admin
        self.user_mgr = users.UserManager( app )

    # ......................................................................... has a user
    def _query_by_user( self, trans, user, filters=None, **kwargs ):
        """
        """
        user_filter = self.model_class.user_id == user.id
        filters=self._munge_filters( user_filter, filters )
        return self.query( trans, filters=filters, **kwargs )

    def by_user( self, trans, user, filters=None, **kwargs ):
        """
        """
        user_filter = self.model_class.user_id == user.id
        filters=self._munge_filters( user_filter, filters )
        #note: no ownership check needed
        return self.list( trans, filters=filters, **kwargs )

    # ......................................................................... owned model interface
# this really is more of a 'check_*editable/write*' - in essence that's what check_ownership boils down to often
    def is_owner( self, trans, item, user ):
        """
        """
        if self.user_mgr.is_anonymous( user ):
            # note: this needs to be overridden in the case of anon users and session.current_history
            return False
        if self.user_mgr.is_admin( trans, user ):
            return True
        return item.user == user

    # ......................................................................... accessible interface
    def is_accessible( self, trans, item, user ):
        """
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
        #??: can a published item be non-importable?
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

    def list_importable( self, trans, **kwargs ):
#TODO:
        """
        """
        pass

    # ......................................................................... published
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
        """
        trans.sa_session.add( item )
        item.published = False
        if flush:
            trans.sa_session.flush()
        return item

    def list_published( self, trans, **kwargs ):
#TODO:
        """
        """
        pass

    # ......................................................................... user sharing
    # sharing is often done via a 3rd table btwn a User and an item -> a <Item>UserShareAssociation
    def get_share_assocs( self, trans, item, user=None ):
        """
        """
        query = self.query_associated( trans, self.user_share_model, item )
        if user is not None:
            query = query.filter_by( user=user )
        return query.all()

    def share_with( self, trans, item, user, flush=True ):
        """
        """
        # allow user to be a list and call recursivly
        if isinstance( user, list ):
            return map( lambda user: self.share_with( trans, item, user, flush=False ), user )

        share = self.user_share_model()
        trans.sa_session.add( share )
        self.associate( trans, share, item )
        share.user = user
        self.create_unique_slug( trans, item )
        if flush:
            trans.sa_session.flush()
        return item

    def unshare_with( self, trans, item, user, flush=True ):
        """
        """
        if isinstance( user, list ):
            return map( lambda user: self.unshare_with( trans, item, user, flush=False ), user )
        # Look for and delete sharing relation for history-user.
        for assoc in self.get_share_assocs( trans, item, user=user ):
            trans.sa_session.delete( assoc )
        if flush:
            trans.sa_session.flush()
        return item

    def list_shared_with( self, trans, item, user, **kwargs ):
#TODO:
        """
        """
        pass

    # ......................................................................... slugs
    # slugs are human readable strings often used to link to sharable resources (replacing ids)
    def is_valid_slug( self, slug ):
        """
        Returns true if slug is valid.
        """
        VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )
        return VALID_SLUG_RE.match( slug )

    def set_slug( self, trans, item, new_slug, flush=True ):
        """
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
        """
        item.slug = self.get_unique_slug( trans, item )
        trans.sa_session.add( item )
        if flush:
            trans.sa_session.flush()
        return item

    def by_slug( self, trans, user, **kwargs ):
        """
        """
        pass

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
