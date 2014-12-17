"""
"""
import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy

from galaxy import model
from galaxy import exceptions
import api_keys

import base

import logging
log = logging.getLogger( __name__ )


# =============================================================================
class UserManager( base.ModelManager ):
    model_class = model.User
    default_order_by = ( model.User.create_time, )
    foreign_key_name = 'user'

    def create( self, trans, **kwargs ):
        #TODO: deserialize and validate here
        email = kwargs[ 'email' ]
        username = kwargs[ 'username' ]
        password = kwargs[ 'password' ]
        self._error_on_duplicate_email( trans, email )

        user = model.User( email=email, password=password )
        user.username = username

        if trans.app.config.user_activation_on:
            user.active = False
        else:
            # Activation is off, every new user is active by default.
            user.active = True

        trans.sa_session.add( user )
        try:
            trans.sa_session.flush()
            #TODO:?? flush needed for permissions below? If not, make optional
        except sqlalchemy.exceptions.IntegrityError, db_err:
            raise exceptions.Conflict( db_err.message )

        # can throw an sqlalx.IntegrityError if username not unique

        trans.app.security_agent.create_private_user_role( user )
        if trans.webapp.name == 'galaxy':
            # We set default user permissions, before we log in and set the default history permissions
            permissions = trans.app.config.new_user_dataset_access_role_default_private
            trans.app.security_agent.user_set_default_permissions( user, default_access_private=permissions )
        return user

    #TODO: incorporate security/validate_user_input.py

    def _error_on_duplicate_email( self, trans, email ):
        #TODO: remove this check when unique=True is added to the email column
        if self.by_email( trans, email ) is not None:
            raise exceptions.Conflict( 'Email must be unique', email=email )

    # ------------------------------------------------------------------------- filters
    def by_email( self, trans, email, filters=None, **kwargs ):
        filters = self._munge_filters( self.model_class.email == email, filters )
        try:
            return super( UserManager, self ).one( trans, filters=filters, **kwargs )
        except exceptions.ObjectNotFound, not_found:
            return None

    def by_email_like( self, trans, email_with_wildcards, filters=None, order_by=None, **kwargs ):
        filters = self._munge_filters( self.model_class.email.like( email_with_wildcards ), filters )
        order_by = order_by or ( model.User.email, )
        return super( UserManager, self ).list( trans, filters=filters, order_by=order_by, **kwargs )

    # ------------------------------------------------------------------------- admin
    def is_admin( self, trans, user ):
        admin_emails = self._admin_emails( trans )
        return user and admin_emails and user.email in admin_emails

    def _admin_emails( self, trans ):
        return [ x.strip() for x in trans.app.config.get( "admin_users", "" ).split( "," ) ]

    def admins( self, trans, filters=None, **kwargs ):
        filters = self._munge_filters( self.model_class.email.in_( self._admin_emails( trans ) ), filters )
        return super( UserManager, self ).list( trans, filters=filters, **kwargs )

    def error_unless_admin( self, trans, user, msg="Administrators only", **kwargs ):
        if not self.is_admin( trans, user ):
            raise exceptions.AdminRequiredException( msg, **kwargs )
        return user

    # ------------------------------------------------------------------------- anonymous
    def is_anonymous( self, user ):
        # define here for single point of change
        return user is None

    def error_if_anonymous( self, trans, user, msg="Log-in required", **kwargs ):
        print 'error_if_anonymous', user
        if user is None:
            #TODO: code is correct (403), but should be named AuthenticationRequired (401 and 403 are flipped)
            raise exceptions.AuthenticationFailed( msg, **kwargs )
        return user

    # ------------------------------------------------------------------------- current
    def is_current_user( self, trans, user ):
        return user == trans.user

    def is_current_user_anonymous( self, trans ):
        return trans.user is None

    def is_current_user_admin( self, trans ):
        return self.is_admin( trans, trans.user )

    # ------------------------------------------------------------------------- ?
    #def tags( self, trans, **kwargs ):
    #    # return all tags from this user
    #    pass

    #def annotations( self, trans, **kwargs ):
    #    # return all annotations from this user
    #    pass

    # ------------------------------------------------------------------------- api keys
    def create_api_key( self, trans, user ):
        return api_keys.ApiKeyManager( trans.app ).create_api_key( user )

    # needed?
    def api_key( self, trans, user ):
        #TODO: catch NoResultFound
        return trans.sa_session.query( model.APIKeys ).filter_by( user=user ).one()

    #TODO: there is quite a bit of functionality around the user (authentication, quotas, groups/roles)
    #   most of which it may be unneccessary to have here

    # ------------------------------------------------------------------------- roles
    def private_role( self, trans, user ):
        #TODO: not sure we need to go through sec agent... it's just the first role of type private
        return trans.app.security_agent.get_private_user_role( user )


# =============================================================================
class UserSerializer( base.ModelSerializer ):

    def __init__( self ):
        super( UserSerializer, self ).__init__()

        summary_view = [
            'id', 'email', 'username'
        ]
        # in the Historys' case, each of these views includes the keys from the previous
        detailed_view = summary_view + [
            'update_time', 'create_time',
            'total_disk_usage', 'nice_total_disk_usage',
            'deleted', 'purged',
            'active'
        ]
        extended_view = detailed_view + [
            #'preferences',
            #'tags',
            #'annotations'
        ]
        self.serializable_keys = extended_view
        self.views = {
            'summary'   : summary_view,
            'detailed'  : detailed_view,
            'extended'  : extended_view,
        }
        self.default_view = 'summary'

    def add_serializers( self ):
        self.serializers.update({
            'id'            : self.serialize_id,
            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,
        })
