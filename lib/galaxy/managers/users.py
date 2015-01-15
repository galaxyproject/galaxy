"""
Manager and Serializer for Users.
"""

import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy

from galaxy import model
from galaxy import exceptions

from galaxy.managers import base
from galaxy.managers import api_keys


import logging
log = logging.getLogger( __name__ )


# =============================================================================
class UserManager( base.ModelManager ):
    model_class = model.User
    default_order_by = ( model.User.create_time, )
    foreign_key_name = 'user'

    #TODO: there is quite a bit of functionality around the user (authentication, permissions, quotas, groups/roles)
    #   most of which it may be unneccessary to have here

    #TODO: incorp BaseAPIController.validate_in_users_and_groups
    #TODO: incorp CreatesUsersMixin
    #TODO: incorp CreatesApiKeysMixin
    #TODO: incorporate security/validate_user_input.py
    #TODO: incorporate UsesFormDefinitionsMixin?

    def create( self, trans, **kwargs ):
        """
        Create a new user.
        """
        #TODO: deserialize and validate here
        email = kwargs[ 'email' ]
        username = kwargs[ 'username' ]
        password = kwargs[ 'password' ]
        self._error_on_duplicate_email( trans, email )

        user = model.User( email=email, password=password )
        user.username = username

        if self.app.config.user_activation_on:
            user.active = False
        else:
            # Activation is off, every new user is active by default.
            user.active = True

        self.app.model.context.add( user )
        try:
            self.app.model.context.flush()
            #TODO:?? flush needed for permissions below? If not, make optional
        except sqlalchemy.exceptions.IntegrityError, db_err:
            raise exceptions.Conflict( db_err.message )

        # can throw an sqlalx.IntegrityError if username not unique

        self.app.security_agent.create_private_user_role( user )
#TODO: any other route to webapp?
        if trans.webapp.name == 'galaxy':
            # We set default user permissions, before we log in and set the default history permissions
            permissions = self.app.config.new_user_dataset_access_role_default_private
            self.app.security_agent.user_set_default_permissions( user, default_access_private=permissions )
        return user

    def _error_on_duplicate_email( self, trans, email ):
        """
        Check for a duplicate email and raise if found.

        :raises exceptions.Conflict: if any are found
        """
        #TODO: remove this check when unique=True is added to the email column
        if self.by_email( trans, email ) is not None:
            raise exceptions.Conflict( 'Email must be unique', email=email )

    # ------------------------------------------------------------------------- filters
    def by_email( self, trans, email, filters=None, **kwargs ):
        """
        Find a user by their email.
        """
        filters = self._munge_filters( self.model_class.email == email, filters )
        try:
#TODO: use one_or_none
            return super( UserManager, self ).one( trans, filters=filters, **kwargs )
        except exceptions.ObjectNotFound, not_found:
            return None

    def by_email_like( self, trans, email_with_wildcards, filters=None, order_by=None, **kwargs ):
        """
        Find a user searching with SQL wildcards.
        """
        filters = self._munge_filters( self.model_class.email.like( email_with_wildcards ), filters )
        order_by = order_by or ( model.User.email, )
        return super( UserManager, self ).list( trans, filters=filters, order_by=order_by, **kwargs )

    # ------------------------------------------------------------------------- admin
    def is_admin( self, trans, user ):
        """
        Return True if this user is an admin.
        """
        admin_emails = self._admin_emails( trans )
        return user and admin_emails and user.email in admin_emails

    def _admin_emails( self, trans ):
        """
        Return a list of admin email addresses from the config file.
        """
        return [ x.strip() for x in self.app.config.get( "admin_users", "" ).split( "," ) ]

    def admins( self, trans, filters=None, **kwargs ):
        """
        Return a list of admin Users.
        """
        filters = self._munge_filters( self.model_class.email.in_( self._admin_emails( trans ) ), filters )
        return super( UserManager, self ).list( trans, filters=filters, **kwargs )

    def error_unless_admin( self, trans, user, msg="Administrators only", **kwargs ):
        """
        Raise an error if `user` is not an admin.

        :raises exceptions.AdminRequiredException: if `user` is not an admin.
        """
        # useful in admin only methods
        if not self.is_admin( trans, user ):
            raise exceptions.AdminRequiredException( msg, **kwargs )
        return user

    # ------------------------------------------------------------------------- anonymous
    def is_anonymous( self, user ):
        """
        Return True if `user` is anonymous.
        """
        # define here for single point of change and make more readable
        return user is None

    def error_if_anonymous( self, trans, user, msg="Log-in required", **kwargs ):
        """
        Raise an error if `user` is anonymous.
        """
        if user is None:
            #TODO: code is correct (403), but should be named AuthenticationRequired (401 and 403 are flipped)
            raise exceptions.AuthenticationFailed( msg, **kwargs )
        return user

    # ------------------------------------------------------------------------- current
    def is_current_user( self, trans, user ):
        """
        Return True if this user is the trans' current user.
        """
        # define here for single point of change and make more readable
        return user == trans.user

    def is_current_user_anonymous( self, trans ):
        """
        Return True if the current user is anonymous.
        """
        return self.is_anonymous( trans.user )

    def is_current_user_admin( self, trans ):
        """
        Return True if the current user is admin.
        """
        return self.is_admin( trans, trans.user )

    # ------------------------------------------------------------------------- ?
    #def tags( self, trans, user, **kwargs ):
    #    """
    #    Return all tags created by this user.
    #    """
    #    pass

    #def annotations( self, trans, user, **kwargs ):
    #    """
    #    Return all annotations created by this user.
    #    """
    #    pass

    # ------------------------------------------------------------------------- api keys
    def create_api_key( self, trans, user ):
        """
        Create and return an API key for `user`.
        """
        #TODO: seems like this should return the model
        return api_keys.ApiKeyManager( self.app ).create_api_key( user )

    #TODO: possibly move to ApiKeyManager
    def valid_api_key( self, trans, user ):
        """
        Return this most recent APIKey for this user or None if none have been created.
        """
        query = ( self.app.model.context.query( model.APIKeys )
                    .filter_by( user=user )
                    .order_by( sqlalchemy.desc( model.APIKeys.create_time ) ) )
        all = query.all()
        for a in all:
            print a.user.username, a.key, a.create_time
        print all
        if len( all ):
            return all[0]
        return None
        #return query.first()

    #TODO: possibly move to ApiKeyManager
    def get_or_create_valid_api_key( self, trans, user ):
        """
        Return this most recent APIKey for this user or create one if none have been
        created.
        """
        existing = self.valid_api_key( trans, user )
        if existing:
            return existing
        return self.create_api_key( self, trans, user )

    # ------------------------------------------------------------------------- roles
    def private_role( self, trans, user ):
        """
        Return the security agent's private role for `user`.
        """
        #TODO: not sure we need to go through sec agent... it's just the first role of type private
        return self.app.security_agent.get_private_user_role( user )


# =============================================================================
class UserSerializer( base.ModelSerializer ):

    def __init__( self ):
        """
        Convert a User and associated data to a dictionary representation.
        """
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
            #'tags', # all tags
            #'annotations' # all annotations
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
