"""
"""
import datetime
import inspect
import os
import hashlib
import random
import socket
import string
import time
import urlparse
from Cookie import CookieError
from importlib import import_module

from Cheetah.Template import Template
import mako.runtime
import mako.lookup
from babel.support import Translations
from babel import Locale
from six import string_types
from sqlalchemy import and_, true
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import joinedload

from galaxy.exceptions import MessageException

from galaxy import util
from galaxy.util import asbool
from galaxy.util import safe_str_cmp
from galaxy.util.sanitize_html import sanitize_html

from galaxy.managers import context
from galaxy.web.framework import url_for
from galaxy.web.framework import base
from galaxy.web.framework import helpers
from galaxy.web.framework import formbuilder

import logging
log = logging.getLogger( __name__ )


UCSC_SERVERS = (
    'hgw1.cse.ucsc.edu',
    'hgw2.cse.ucsc.edu',
    'hgw3.cse.ucsc.edu',
    'hgw4.cse.ucsc.edu',
    'hgw5.cse.ucsc.edu',
    'hgw6.cse.ucsc.edu',
    'hgw7.cse.ucsc.edu',
    'hgw8.cse.ucsc.edu',
    'hgw1.soe.ucsc.edu',
    'hgw2.soe.ucsc.edu',
    'hgw3.soe.ucsc.edu',
    'hgw4.soe.ucsc.edu',
    'hgw5.soe.ucsc.edu',
    'hgw6.soe.ucsc.edu',
    'hgw7.soe.ucsc.edu',
    'hgw8.soe.ucsc.edu',
)


class WebApplication( base.WebApplication ):
    """
    Base WSGI application instantiated for all Galaxy webapps.

    A web application that:
        * adds API and UI controllers by scanning given directories and
        importing all modules found there.
        * has a security object.
        * builds mako template lookups.
        * generates GalaxyWebTransactions.
    """
    def __init__( self, galaxy_app, session_cookie='galaxysession', name=None ):
        self.name = name
        base.WebApplication.__init__( self )
        self.set_transaction_factory( lambda e: self.transaction_chooser( e, galaxy_app, session_cookie ) )
        # Mako support
        self.mako_template_lookup = self.create_mako_template_lookup( galaxy_app, name )
        # Security helper
        self.security = galaxy_app.security

    def create_mako_template_lookup( self, galaxy_app, name ):
        paths = []
        # First look in webapp specific directory
        if name is not None:
            paths.append( os.path.join( galaxy_app.config.template_path, 'webapps', name ) )
        # Then look in root directory
        paths.append( galaxy_app.config.template_path )
        # Create TemplateLookup with a small cache
        return mako.lookup.TemplateLookup(directories=paths,
                                          module_directory=galaxy_app.config.template_cache,
                                          collection_size=500,
                                          output_encoding='utf-8' )

    def handle_controller_exception( self, e, trans, **kwargs ):
        if isinstance( e, MessageException ):
            # In the case of a controller exception, sanitize to make sure
            # unsafe html input isn't reflected back to the user
            return trans.show_message( sanitize_html(e.err_msg), e.type )

    def make_body_iterable( self, trans, body ):
        if isinstance( body, formbuilder.FormBuilder ):
            body = trans.show_form( body )
        return base.WebApplication.make_body_iterable( self, trans, body )

    def transaction_chooser( self, environ, galaxy_app, session_cookie ):
        return GalaxyWebTransaction( environ, galaxy_app, self, session_cookie )

    def add_ui_controllers( self, package_name, app ):
        """
        Search for UI controllers in `package_name` and add
        them to the webapp.
        """
        from galaxy.web.base.controller import BaseUIController
        from galaxy.web.base.controller import ControllerUnavailable
        package = import_module( package_name )
        controller_dir = package.__path__[0]
        for fname in os.listdir( controller_dir ):
            if not( fname.startswith( "_" ) ) and fname.endswith( ".py" ):
                name = fname[:-3]
                module_name = package_name + "." + name
                try:
                    module = import_module( module_name )
                except ControllerUnavailable as exc:
                    log.debug("%s could not be loaded: %s" % (module_name, str(exc)))
                    continue
                # Look for a controller inside the modules
                for key in dir( module ):
                    T = getattr( module, key )
                    if inspect.isclass( T ) and T is not BaseUIController and issubclass( T, BaseUIController ):
                        controller = self._instantiate_controller( T, app )
                        self.add_ui_controller( name, controller )

    def add_api_controllers( self, package_name, app ):
        """
        Search for UI controllers in `package_name` and add
        them to the webapp.
        """
        from galaxy.web.base.controller import BaseAPIController
        from galaxy.web.base.controller import ControllerUnavailable
        package = import_module( package_name )
        controller_dir = package.__path__[0]
        for fname in os.listdir( controller_dir ):
            if not( fname.startswith( "_" ) ) and fname.endswith( ".py" ):
                name = fname[:-3]
                module_name = package_name + "." + name
                try:
                    module = import_module( module_name )
                except ControllerUnavailable as exc:
                    log.debug("%s could not be loaded: %s" % (module_name, str(exc)))
                    continue
                for key in dir( module ):
                    T = getattr( module, key )
                    # Exclude classes such as BaseAPIController and BaseTagItemsController
                    if inspect.isclass( T ) and not key.startswith("Base") and issubclass( T, BaseAPIController ):
                        # By default use module_name, but allow controller to override name
                        controller_name = getattr( T, "controller_name", name )
                        controller = self._instantiate_controller( T, app )
                        self.add_api_controller( controller_name, controller )

    def _instantiate_controller( self, T, app ):
        """ Extension point, allow apps to contstruct controllers differently,
        really just used to stub out actual controllers for routes testing.
        """
        return T( app )


class GalaxyWebTransaction( base.DefaultWebTransaction,
                            context.ProvidesAppContext, context.ProvidesUserContext, context.ProvidesHistoryContext ):
    """
    Encapsulates web transaction specific state for the Galaxy application
    (specifically the user's "cookie" session and history)
    """

    def __init__( self, environ, app, webapp, session_cookie=None):
        self.app = app
        self.webapp = webapp
        self.security = webapp.security
        base.DefaultWebTransaction.__init__( self, environ )
        self.setup_i18n()
        self.expunge_all()
        config = self.app.config
        self.debug = asbool( config.get( 'debug', False ) )
        x_frame_options = getattr( config, 'x_frame_options', None )
        if x_frame_options:
            self.response.headers['X-Frame-Options'] = x_frame_options
        # Flag indicating whether we are in workflow building mode (means
        # that the current history should not be used for parameter values
        # and such).
        self.workflow_building_mode = False
        # Flag indicating whether this is an API call and the API key user is an administrator
        self.api_inherit_admin = False
        self.__user = None
        self.galaxy_session = None
        self.error_message = None

        # set any cross origin resource sharing headers if configured to do so
        self.set_cors_headers()

        if self.environ.get('is_api_request', False):
            # With API requests, if there's a key, use it and associate the
            # user with the transaction.
            # If not, check for an active session but do not create one.
            # If an error message is set here, it's sent back using
            # trans.show_error in the response -- in expose_api.
            self.error_message = self._authenticate_api( session_cookie )
        elif self.app.name == "reports":
            self.galaxy_session = None
        else:
            # This is a web request, get or create session.
            self._ensure_valid_session( session_cookie )
        if self.galaxy_session:
            # When we've authenticated by session, we have to check the
            # following.
            # Prevent deleted users from accessing Galaxy
            if config.use_remote_user and self.galaxy_session.user.deleted:
                self.response.send_redirect( url_for( '/static/user_disabled.html' ) )
            if config.require_login:
                self._ensure_logged_in_user( environ, session_cookie )
            if config.session_duration:
                # TODO DBTODO All ajax calls from the client need to go through
                # a single point of control where we can do things like
                # redirect/etc.  This is API calls as well as something like 40
                # @web.json requests that might not get handled well on the
                # clientside.
                #
                # Make sure we're not past the duration, and either log out or
                # update timestamp.
                now = datetime.datetime.now()
                if self.galaxy_session.last_action:
                    expiration_time = self.galaxy_session.last_action + datetime.timedelta(minutes=config.session_duration)
                else:
                    expiration_time = now
                    self.galaxy_session.last_action = now - datetime.timedelta(seconds=1)
                    self.sa_session.add(self.galaxy_session)
                    self.sa_session.flush()
                if expiration_time < now:
                    # Expiration time has passed.
                    self.handle_user_logout()
                    if self.environ.get('is_api_request', False):
                        self.response.status = 401
                        self.user = None
                        self.galaxy_session = None
                    else:
                        self.response.send_redirect( url_for( controller='user',
                                                     action='login',
                                                     message="You have been logged out due to inactivity.  Please log in again to continue using Galaxy.",
                                                     status='info',
                                                     use_panels=True ) )
                else:
                    self.galaxy_session.last_action = now
                    self.sa_session.add(self.galaxy_session)
                    self.sa_session.flush()

    def setup_i18n( self ):
        locales = []
        if 'HTTP_ACCEPT_LANGUAGE' in self.environ:
            # locales looks something like: ['en', 'en-us;q=0.7', 'ja;q=0.3']
            client_locales = self.environ['HTTP_ACCEPT_LANGUAGE'].split( ',' )
            for locale in client_locales:
                try:
                    locales.append( Locale.parse( locale.split( ';' )[0].strip(), sep='-' ).language )
                except Exception as e:
                    log.debug( "Error parsing locale '%s'. %s: %s", locale, type( e ), e )
        if not locales:
            # Default to English
            locales = 'en'
        t = Translations.load( dirname='locale', locales=locales, domain='ginga' )
        self.template_context.update( dict( _=t.ugettext, n_=t.ugettext, N_=t.ungettext ) )

    def set_cors_headers( self ):
        """Allow CORS requests if configured to do so by echoing back the request's
        'Origin' header (if any) as the response header 'Access-Control-Allow-Origin'
        """
        # TODO: in order to use these, we need preflight to work, and to do that we
        # need the OPTIONS method on all api calls (or everywhere we can POST/PUT)
        # ALLOWED_METHODS = ( 'POST', 'PUT' )

        # do not set any access control headers if not configured for it (common case)
        if not self.app.config.get( 'allowed_origin_hostnames', None ):
            return
        # do not set any access control headers if there's no origin header on the request
        origin_header = self.request.headers.get( "Origin", None )
        if not origin_header:
            return

        # singular match
        def matches_allowed_origin( origin, allowed_origin ):
            if isinstance( allowed_origin, string_types ):
                return origin == allowed_origin
            match = allowed_origin.match( origin )
            return match and match.group() == origin

        # check for '*' or compare to list of allowed
        def is_allowed_origin( origin ):
            # localhost uses no origin header (== null)
            if not origin:
                return False
            for allowed_origin in self.app.config.allowed_origin_hostnames:
                if allowed_origin == '*' or matches_allowed_origin( origin, allowed_origin ):
                    return True
            return False

        # boil origin header down to hostname
        origin = urlparse.urlparse( origin_header ).hostname
        # check against the list of allowed strings/regexp hostnames, echo original if cleared
        if is_allowed_origin( origin ):
            self.response.headers[ 'Access-Control-Allow-Origin' ] = origin_header
            # TODO: see the to do on ALLOWED_METHODS above
            # self.response.headers[ 'Access-Control-Allow-Methods' ] = ', '.join( ALLOWED_METHODS )

        # NOTE: raising some errors (such as httpexceptions), will remove the header
        # (e.g. client will get both cors error and 404 inside that)

    def get_user( self ):
        """Return the current user if logged in or None."""
        if self.galaxy_session:
            return self.galaxy_session.user
        else:
            return self.__user

    def set_user( self, user ):
        """Set the current user."""
        if self.galaxy_session:
            self.galaxy_session.user = user
            self.sa_session.add( self.galaxy_session )
            self.sa_session.flush()
        self.__user = user

    user = property( get_user, set_user )

    def get_cookie( self, name='galaxysession' ):
        """Convenience method for getting a session cookie"""
        try:
            # If we've changed the cookie during the request return the new value
            if name in self.response.cookies:
                return self.response.cookies[name].value
            else:
                return self.request.cookies[name].value
        except:
            return None

    def set_cookie( self, value, name='galaxysession', path='/', age=90, version='1' ):
        """Convenience method for setting a session cookie"""
        # The galaxysession cookie value must be a high entropy 128 bit random number encrypted
        # using a server secret key.  Any other value is invalid and could pose security issues.
        self.response.cookies[name] = value
        self.response.cookies[name]['path'] = path
        self.response.cookies[name]['max-age'] = 3600 * 24 * age  # 90 days
        tstamp = time.localtime( time.time() + 3600 * 24 * age )
        self.response.cookies[name]['expires'] = time.strftime( '%a, %d-%b-%Y %H:%M:%S GMT', tstamp )
        self.response.cookies[name]['version'] = version
        https = self.request.environ[ "wsgi.url_scheme" ] == "https"
        if https:
            self.response.cookies[name]['secure'] = True
        try:
            self.response.cookies[name]['httponly'] = True
        except CookieError as e:
            log.warning( "Error setting httponly attribute in cookie '%s': %s" % ( name, e ) )

    def _authenticate_api( self, session_cookie ):
        """
        Authenticate for the API via key or session (if available).
        """
        api_key = self.request.params.get('key', None)
        secure_id = self.get_cookie( name=session_cookie )
        api_key_supplied = self.environ.get('is_api_request', False) and api_key
        if api_key_supplied and self._check_master_api_key( api_key ):
            self.api_inherit_admin = True
            log.info( "Session authenticated using Galaxy master api key" )
            self.user = None
            self.galaxy_session = None
        elif api_key_supplied:
            # Sessionless API transaction, we just need to associate a user.
            try:
                provided_key = self.sa_session.query( self.app.model.APIKeys ).filter( self.app.model.APIKeys.table.c.key == api_key ).one()
            except NoResultFound:
                return 'Provided API key is not valid.'
            if provided_key.user.deleted:
                return 'User account is deactivated, please contact an administrator.'
            newest_key = provided_key.user.api_keys[0]
            if newest_key.key != provided_key.key:
                return 'Provided API key has expired.'
            self.set_user( provided_key.user )
        elif secure_id:
            # API authentication via active session
            # Associate user using existing session
            self._ensure_valid_session( session_cookie )
        else:
            # Anonymous API interaction -- anything but @expose_api_anonymous will fail past here.
            self.user = None
            self.galaxy_session = None

    def _check_master_api_key( self, api_key ):
        master_api_key = getattr( self.app.config, 'master_api_key', None )
        if not master_api_key:
            return False
        # Hash keys to make them the same size, so we can do safe comparison.
        master_hash = hashlib.sha256( master_api_key ).hexdigest()
        provided_hash = hashlib.sha256( api_key ).hexdigest()
        return safe_str_cmp( master_hash, provided_hash )

    def _ensure_valid_session( self, session_cookie, create=True):
        """
        Ensure that a valid Galaxy session exists and is available as
        trans.session (part of initialization)

        Support for universe_session and universe_user cookies has been
        removed as of 31 Oct 2008.
        """
        # Try to load an existing session
        secure_id = self.get_cookie( name=session_cookie )
        galaxy_session = None
        prev_galaxy_session = None
        user_for_new_session = None
        invalidate_existing_session = False
        # Track whether the session has changed so we can avoid calling flush
        # in the most common case (session exists and is valid).
        galaxy_session_requires_flush = False
        if secure_id:
            # Decode the cookie value to get the session_key
            session_key = self.security.decode_guid( secure_id )
            try:
                # Make sure we have a valid UTF-8 string
                session_key = session_key.encode( 'utf8' )
            except UnicodeDecodeError:
                # We'll end up creating a new galaxy_session
                session_key = None
            if session_key:
                # Retrieve the galaxy_session id via the unique session_key
                galaxy_session = self.sa_session.query( self.app.model.GalaxySession ) \
                                                .filter( and_( self.app.model.GalaxySession.table.c.session_key == session_key,
                                                               self.app.model.GalaxySession.table.c.is_valid == true() ) ).options( joinedload( "user" ) ).first()
        # If remote user is in use it can invalidate the session and in some
        # cases won't have a cookie set above, so we need to to check some
        # things now.
        if self.app.config.use_remote_user:
            # If this is an api request, and they've passed a key, we let this go.
            assert self.app.config.remote_user_header in self.environ, \
                "use_remote_user is set but %s header was not provided" % self.app.config.remote_user_header
            remote_user_email = self.environ[ self.app.config.remote_user_header ]
            if galaxy_session:
                # An existing session, make sure correct association exists
                if galaxy_session.user is None:
                    # No user, associate
                    galaxy_session.user = self.get_or_create_remote_user( remote_user_email )
                    galaxy_session_requires_flush = True
                elif (not remote_user_email.startswith('(null)') and  # Apache does this, see remoteuser.py
                      (galaxy_session.user.email != remote_user_email) and
                      ((not self.app.config.allow_user_impersonation) or
                       (remote_user_email not in self.app.config.admin_users_list))):
                    # Session exists but is not associated with the correct
                    # remote user, and the currently set remote_user is not a
                    # potentially impersonating admin.
                    invalidate_existing_session = True
                    user_for_new_session = self.get_or_create_remote_user( remote_user_email )
                    log.warning( "User logged in as '%s' externally, but has a cookie as '%s' invalidating session",
                                 remote_user_email, galaxy_session.user.email )
            else:
                # No session exists, get/create user for new session
                user_for_new_session = self.get_or_create_remote_user( remote_user_email )
        else:
            if galaxy_session is not None and galaxy_session.user and galaxy_session.user.external:
                # Remote user support is not enabled, but there is an existing
                # session with an external user, invalidate
                invalidate_existing_session = True
                log.warning( "User '%s' is an external user with an existing session, invalidating session since external auth is disabled",
                             galaxy_session.user.email )
            elif galaxy_session is not None and galaxy_session.user is not None and galaxy_session.user.deleted:
                invalidate_existing_session = True
                log.warning( "User '%s' is marked deleted, invalidating session" % galaxy_session.user.email )
        # Do we need to invalidate the session for some reason?
        if invalidate_existing_session:
            prev_galaxy_session = galaxy_session
            prev_galaxy_session.is_valid = False
            galaxy_session = None
        # No relevant cookies, or couldn't find, or invalid, so create a new session
        if galaxy_session is None:
            galaxy_session = self.__create_new_session( prev_galaxy_session, user_for_new_session )
            galaxy_session_requires_flush = True
            self.galaxy_session = galaxy_session
            self.__update_session_cookie( name=session_cookie )
        else:
            self.galaxy_session = galaxy_session
        # Do we need to flush the session?
        if galaxy_session_requires_flush:
            self.sa_session.add( galaxy_session )
            # FIXME: If prev_session is a proper relation this would not
            #        be needed.
            if prev_galaxy_session:
                self.sa_session.add( prev_galaxy_session )
            self.sa_session.flush()
        # If the old session was invalid, get a new (or existing default,
        # unused) history with our new session
        if invalidate_existing_session:
            self.get_or_create_default_history()

    def _ensure_logged_in_user( self, environ, session_cookie ):
        # The value of session_cookie can be one of
        # 'galaxysession' or 'galaxycommunitysession'
        # Currently this method does nothing unless session_cookie is 'galaxysession'
        if session_cookie == 'galaxysession' and self.galaxy_session.user is None:
            # TODO: re-engineer to eliminate the use of allowed_paths
            # as maintenance overhead is far too high.
            allowed_paths = [
                # client app route
                # TODO: might be better as '/:username/login', '/:username/logout'
                url_for( controller='root', action='login' ),
                # mako app routes
                url_for( controller='user', action='login' ),
                url_for( controller='user', action='logout' ),
                url_for( controller='user', action='reset_password' ),
                url_for( controller='user', action='change_password' ),
                # required to log in w/ openid
                url_for( controller='user', action='openid_auth' ),
                url_for( controller='user', action='openid_process' ),
                url_for( controller='user', action='openid_associate' ),
                # TODO: do any of these still need to bypass require login?
                url_for( controller='user', action='api_keys' ),
                url_for( controller='user', action='create' ),
                url_for( controller='user', action='index' ),
                url_for( controller='user', action='manage_user_info' ),
                url_for( controller='user', action='set_default_permissions' ),
            ]
            # append the welcome url to allowed paths if we'll show it at the login screen
            if self.app.config.show_welcome_with_login:
                allowed_paths.append( url_for( controller='root', action='welcome' ) )

            # prevent redirect when UCSC server attempts to get dataset contents as 'anon' user
            display_as = url_for( controller='root', action='display_as' )
            if self.app.datatypes_registry.get_display_sites('ucsc') and self.request.path == display_as:
                try:
                    host = socket.gethostbyaddr( self.environ[ 'REMOTE_ADDR' ] )[0]
                except( socket.error, socket.herror, socket.gaierror, socket.timeout ):
                    host = None
                if host in UCSC_SERVERS:
                    return
            # prevent redirect for external, enabled display applications getting dataset contents
            external_display_path = url_for( controller='', action='display_application' )
            if self.request.path.startswith( external_display_path ):
                request_path_split = self.request.path.split( '/' )
                try:
                    if (self.app.datatypes_registry.display_applications.get( request_path_split[-5] ) and
                            request_path_split[-4] in self.app.datatypes_registry.display_applications.get( request_path_split[-5] ).links and
                            request_path_split[-3] != 'None'):
                        return
                except IndexError:
                    pass
            # redirect to root if the path is not in the list above
            if self.request.path not in allowed_paths:
                login_url = url_for( controller='root', action='login', redirect=self.request.path )
                self.response.send_redirect( login_url )

    def __create_new_session( self, prev_galaxy_session=None, user_for_new_session=None ):
        """
        Create a new GalaxySession for this request, possibly with a connection
        to a previous session (in `prev_galaxy_session`) and an existing user
        (in `user_for_new_session`).

        Caller is responsible for flushing the returned session.
        """
        session_key = self.security.get_new_guid()
        galaxy_session = self.app.model.GalaxySession(
            session_key=session_key,
            is_valid=True,
            remote_host=self.request.remote_host,
            remote_addr=self.request.remote_addr,
            referer=self.request.headers.get( 'Referer', None ) )
        if prev_galaxy_session:
            # Invalidated an existing session for some reason, keep track
            galaxy_session.prev_session_id = prev_galaxy_session.id
        if user_for_new_session:
            # The new session should be associated with the user
            galaxy_session.user = user_for_new_session
        return galaxy_session

    def get_or_create_remote_user( self, remote_user_email ):
        """
        Create a remote user with the email remote_user_email and return it
        """
        if not self.app.config.use_remote_user:
            return None
        if getattr( self.app.config, "normalize_remote_user_email", False ):
            remote_user_email = remote_user_email.lower()
        user = self.sa_session.query( self.app.model.User).filter( self.app.model.User.table.c.email == remote_user_email ).first()
        if user:
            # GVK: June 29, 2009 - This is to correct the behavior of a previous bug where a private
            # role and default user / history permissions were not set for remote users.  When a
            # remote user authenticates, we'll look for this information, and if missing, create it.
            if not self.app.security_agent.get_private_user_role( user ):
                self.app.security_agent.create_private_user_role( user )
            if 'webapp' not in self.environ or self.environ['webapp'] != 'tool_shed':
                if not user.default_permissions:
                    self.app.security_agent.user_set_default_permissions( user )
                    self.app.security_agent.user_set_default_permissions( user, history=True, dataset=True )
        elif user is None:
            username = remote_user_email.split( '@', 1 )[0].lower()
            random.seed()
            user = self.app.model.User( email=remote_user_email )
            user.set_password_cleartext( ''.join( random.sample( string.letters + string.digits, 12 ) ) )
            user.external = True
            # Replace invalid characters in the username
            for char in filter( lambda x: x not in string.ascii_lowercase + string.digits + '-', username ):
                username = username.replace( char, '-' )
            # Find a unique username - user can change it later
            if self.sa_session.query( self.app.model.User ).filter_by( username=username ).first():
                i = 1
                while self.sa_session.query( self.app.model.User ).filter_by( username=(username + '-' + str(i) ) ).first():
                    i += 1
                username += '-' + str(i)
            user.username = username
            self.sa_session.add( user )
            self.sa_session.flush()
            self.app.security_agent.create_private_user_role( user )
            # We set default user permissions, before we log in and set the default history permissions
            if 'webapp' not in self.environ or self.environ['webapp'] != 'tool_shed':
                self.app.security_agent.user_set_default_permissions( user )
            # self.log_event( "Automatically created account '%s'", user.email )
        return user

    def __update_session_cookie( self, name='galaxysession' ):
        """
        Update the session cookie to match the current session.
        """
        self.set_cookie( self.security.encode_guid(self.galaxy_session.session_key ),
                         name=name, path=self.app.config.cookie_path )

    def handle_user_login( self, user ):
        """
        Login a new user (possibly newly created)

           - create a new session
           - associate new session with user
           - if old session had a history and it was not associated with a user, associate it with the new session,
             otherwise associate the current session's history with the user
           - add the disk usage of the current session to the user's total disk usage
        """
        # Set the previous session
        prev_galaxy_session = self.galaxy_session
        prev_galaxy_session.is_valid = False
        # Define a new current_session
        self.galaxy_session = self.__create_new_session( prev_galaxy_session, user )
        if self.webapp.name == 'galaxy':
            cookie_name = 'galaxysession'
            # Associated the current user's last accessed history (if exists) with their new session
            history = None
            try:
                users_last_session = user.galaxy_sessions[0]
                last_accessed = True
            except:
                users_last_session = None
                last_accessed = False
            if (prev_galaxy_session.current_history and not
                    prev_galaxy_session.current_history.deleted and
                    prev_galaxy_session.current_history.datasets):
                if prev_galaxy_session.current_history.user is None or prev_galaxy_session.current_history.user == user:
                    # If the previous galaxy session had a history, associate it with the new
                    # session, but only if it didn't belong to a different user.
                    history = prev_galaxy_session.current_history
                    if prev_galaxy_session.user is None:
                        # Increase the user's disk usage by the amount of the previous history's datasets if they didn't already own it.
                        for hda in history.datasets:
                            user.adjust_total_disk_usage(hda.quota_amount(user))
            elif self.galaxy_session.current_history:
                history = self.galaxy_session.current_history
            if (not history and users_last_session and
                    users_last_session.current_history and not
                    users_last_session.current_history.deleted):
                history = users_last_session.current_history
            elif not history:
                history = self.get_history( create=True, most_recent=True )
            if history not in self.galaxy_session.histories:
                self.galaxy_session.add_history( history )
            if history.user is None:
                history.user = user
            self.galaxy_session.current_history = history
            if not last_accessed:
                # Only set default history permissions if current history is not from a previous session
                self.app.security_agent.history_set_default_permissions( history, dataset=True, bypass_manage_permission=True )
            self.sa_session.add_all( ( prev_galaxy_session, self.galaxy_session, history ) )
        else:
            cookie_name = 'galaxycommunitysession'
            self.sa_session.add_all( ( prev_galaxy_session, self.galaxy_session ) )
        self.sa_session.flush()
        # This method is not called from the Galaxy reports, so the cookie will always be galaxysession
        self.__update_session_cookie( name=cookie_name )

    def handle_user_logout( self, logout_all=False ):
        """
        Logout the current user:
           - invalidate the current session
           - create a new session with no user associated
        """
        prev_galaxy_session = self.galaxy_session
        prev_galaxy_session.is_valid = False
        self.galaxy_session = self.__create_new_session( prev_galaxy_session )
        self.sa_session.add_all( ( prev_galaxy_session, self.galaxy_session ) )
        galaxy_user_id = prev_galaxy_session.user_id
        if logout_all and galaxy_user_id is not None:
            for other_galaxy_session in ( self.sa_session.query(self.app.model.GalaxySession)
                                          .filter( and_( self.app.model.GalaxySession.table.c.user_id == galaxy_user_id,
                                                         self.app.model.GalaxySession.table.c.is_valid == true(),
                                                         self.app.model.GalaxySession.table.c.id != prev_galaxy_session.id ) ) ):
                other_galaxy_session.is_valid = False
                self.sa_session.add( other_galaxy_session )
        self.sa_session.flush()
        if self.webapp.name == 'galaxy':
            # This method is not called from the Galaxy reports, so the cookie will always be galaxysession
            self.__update_session_cookie( name='galaxysession' )
        elif self.webapp.name == 'tool_shed':
            self.__update_session_cookie( name='galaxycommunitysession' )

    def get_galaxy_session( self ):
        """
        Return the current galaxy session
        """
        return self.galaxy_session

    def get_history( self, create=False, most_recent=False ):
        """
        Load the current history.
            - If that isn't available, we find the most recently updated history.
            - If *that* isn't available, we get or create the default history.
        Transactions will not always have an active history (API requests), so
        None is a valid response.
        """
        history = None
        if self.galaxy_session:
            if hasattr( self.galaxy_session, 'current_history' ):
                history = self.galaxy_session.current_history
        if not history and most_recent:
            history = self.get_most_recent_history()
        if not history and util.string_as_bool( create ):
            history = self.get_or_create_default_history()
        return history

    def set_history( self, history ):
        if history and not history.deleted:
            self.galaxy_session.current_history = history
        self.sa_session.add( self.galaxy_session )
        self.sa_session.flush()

    history = property( get_history, set_history )

    def get_or_create_default_history( self ):
        """
        Gets or creates a default history and associates it with the current
        session.
        """

        # There must be a user to fetch a default history.
        if not self.galaxy_session.user:
            return self.new_history()

        # Look for default history that (a) has default name + is not deleted and
        # (b) has no datasets. If suitable history found, use it; otherwise, create
        # new history.
        unnamed_histories = self.sa_session.query( self.app.model.History ).filter_by(
            user=self.galaxy_session.user,
            name=self.app.model.History.default_name,
            deleted=False )
        default_history = None
        for history in unnamed_histories:
            if len( history.datasets ) == 0:
                # Found suitable default history.
                default_history = history
                break

        # Set or create hsitory.
        if default_history:
            history = default_history
            self.set_history( history )
        else:
            history = self.new_history()

        return history

    def get_most_recent_history( self ):
        """
        Gets the most recently updated history.
        """
        # There must be a user to fetch histories, and without a user we have
        # no recent history.
        if not self.galaxy_session.user:
            return None
        try:
            recent_history = self.sa_session.query( self.app.model.History ).filter_by(
                user=self.galaxy_session.user,
                deleted=False ).order_by(self.app.model.History.update_time.desc()).first()
        except NoResultFound:
            return None
        self.set_history(recent_history)
        return recent_history

    def new_history( self, name=None ):
        """
        Create a new history and associate it with the current session and
        its associated user (if set).
        """
        # Create new history
        history = self.app.model.History()
        if name:
            history.name = name
        # Associate with session
        history.add_galaxy_session( self.galaxy_session )
        # Make it the session's current history
        self.galaxy_session.current_history = history
        # Associate with user
        if self.galaxy_session.user:
            history.user = self.galaxy_session.user
        # Track genome_build with history
        history.genome_build = self.app.genome_builds.default_value
        # Set the user's default history permissions
        self.app.security_agent.history_set_default_permissions( history )
        # Save
        self.sa_session.add_all( ( self.galaxy_session, history ) )
        self.sa_session.flush()
        return history

    @base.lazy_property
    def template_context( self ):
        return dict()

    def set_message( self, message, type=None ):
        """
        Convenience method for setting the 'message' and 'message_type'
        element of the template context.
        """
        self.template_context['message'] = message
        if type:
            self.template_context['status'] = type

    def get_message( self ):
        """
        Convenience method for getting the 'message' element of the template
        context.
        """
        return self.template_context['message']

    def show_message( self, message, type='info', refresh_frames=[], cont=None, use_panels=False, active_view="" ):
        """
        Convenience method for displaying a simple page with a single message.

        `type`: one of "error", "warning", "info", or "done"; determines the
                type of dialog box and icon displayed with the message

        `refresh_frames`: names of frames in the interface that should be
                          refreshed when the message is displayed
        """
        return self.fill_template( "message.mako", status=type, message=message, refresh_frames=refresh_frames, cont=cont, use_panels=use_panels, active_view=active_view )

    def show_error_message( self, message, refresh_frames=[], use_panels=False, active_view="" ):
        """
        Convenience method for displaying an error message. See `show_message`.
        """
        return self.show_message( message, 'error', refresh_frames, use_panels=use_panels, active_view=active_view )

    def show_ok_message( self, message, refresh_frames=[], use_panels=False, active_view="" ):
        """
        Convenience method for displaying an ok message. See `show_message`.
        """
        return self.show_message( message, 'done', refresh_frames, use_panels=use_panels, active_view=active_view )

    def show_warn_message( self, message, refresh_frames=[], use_panels=False, active_view="" ):
        """
        Convenience method for displaying an warn message. See `show_message`.
        """
        return self.show_message( message, 'warning', refresh_frames, use_panels=use_panels, active_view=active_view )

    def show_form( self, form, header=None, template="form.mako", use_panels=False, active_view="" ):
        """
        Convenience method for displaying a simple page with a single HTML
        form.
        """
        return self.fill_template( template, form=form, header=header,
                                   use_panels=( form.use_panels or use_panels ),
                                   active_view=active_view )

    def fill_template(self, filename, **kwargs):
        """
        Fill in a template, putting any keyword arguments on the context.
        """
        # call get_user so we can invalidate sessions from external users,
        # if external auth has been disabled.
        self.get_user()
        if filename.endswith( ".mako" ):
            return self.fill_template_mako( filename, **kwargs )
        else:
            template = Template( file=os.path.join(self.app.config.template_path, filename),
                                 searchList=[kwargs, self.template_context, dict(caller=self, t=self, h=helpers, util=util, request=self.request, response=self.response, app=self.app)] )
            return str( template )

    def fill_template_mako( self, filename, template_lookup=None, **kwargs ):
        template_lookup = template_lookup or self.webapp.mako_template_lookup
        template = template_lookup.get_template( filename )
        template.output_encoding = 'utf-8'

        data = dict( caller=self, t=self, trans=self, h=helpers, util=util, request=self.request, response=self.response, app=self.app )
        data.update( self.template_context )
        data.update( kwargs )
        return template.render( **data )

    def stream_template_mako( self, filename, **kwargs ):
        template = self.webapp.mako_template_lookup.get_template( filename )
        template.output_encoding = 'utf-8'
        data = dict( caller=self, t=self, trans=self, h=helpers, util=util, request=self.request, response=self.response, app=self.app )
        data.update( self.template_context )
        data.update( kwargs )

        def render( environ, start_response ):
            response_write = start_response( self.response.wsgi_status(), self.response.wsgi_headeritems() )

            class StreamBuffer( object ):
                def write( self, d ):
                    response_write( d.encode( 'utf-8' ) )
            buffer = StreamBuffer()
            context = mako.runtime.Context( buffer, **data )
            template.render_context( context )
            return []
        return render

    def fill_template_string(self, template_string, context=None, **kwargs):
        """
        Fill in a template, putting any keyword arguments on the context.
        """
        template = Template( source=template_string,
                             searchList=[context or kwargs, dict(caller=self)] )
        return str(template)


def build_url_map( app, global_conf, local_conf ):
    from paste.urlmap import URLMap
    from galaxy.web.framework.middleware.static import CacheableStaticURLParser as Static
    urlmap = URLMap()
    # Merge the global and local configurations
    conf = global_conf.copy()
    conf.update(local_conf)
    # Get cache time in seconds
    cache_time = conf.get( "static_cache_time", None )
    if cache_time is not None:
        cache_time = int( cache_time )
    # Send to dynamic app by default
    urlmap["/"] = app
    # Define static mappings from config
    urlmap["/static"] = Static( conf.get( "static_dir", "./static/" ), cache_time )
    urlmap["/images"] = Static( conf.get( "static_images_dir", "./static/images" ), cache_time )
    urlmap["/static/scripts"] = Static( conf.get( "static_scripts_dir", "./static/scripts/" ), cache_time )
    urlmap["/static/style"] = Static( conf.get( "static_style_dir", "./static/style/blue" ), cache_time )
    urlmap["/favicon.ico"] = Static( conf.get( "static_favicon_dir", "./static/favicon.ico" ), cache_time )
    urlmap["/robots.txt"] = Static( conf.get( "static_robots_txt", "./static/robots.txt" ), cache_time )
    return urlmap, cache_time
