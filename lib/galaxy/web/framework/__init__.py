"""
Galaxy web application framework
"""

import pkg_resources

import os, sys, time, socket, random, string
pkg_resources.require( "Cheetah" )
from Cheetah.Template import Template
import base
import pickle
from functools import wraps
from galaxy import util
from galaxy.exceptions import MessageException
from galaxy.util.json import to_json_string, from_json_string

pkg_resources.require( "simplejson" )
import simplejson

import helpers

pkg_resources.require( "PasteDeploy" )
from paste.deploy.converters import asbool
import paste.httpexceptions

pkg_resources.require( "Mako" )
import mako.template
import mako.lookup
import mako.runtime

pkg_resources.require( "Babel" )
from babel.support import Translations
from babel import Locale, UnknownLocaleError

pkg_resources.require( "SQLAlchemy >= 0.4" )
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound

pkg_resources.require( "pexpect" )
pkg_resources.require( "amqplib" )

import logging
log = logging.getLogger( __name__ )

url_for = base.routes.url_for

UCSC_SERVERS = (
    'hgw1.cse.ucsc.edu',
    'hgw2.cse.ucsc.edu',
    'hgw3.cse.ucsc.edu',
    'hgw4.cse.ucsc.edu',
    'hgw5.cse.ucsc.edu',
    'hgw6.cse.ucsc.edu',
    'hgw7.cse.ucsc.edu',
    'hgw8.cse.ucsc.edu',
)

def expose( func ):
    """
    Decorator: mark a function as 'exposed' and thus web accessible
    """
    func.exposed = True
    return func
    
def json( func ):
    @wraps(func)
    def decorator( self, trans, *args, **kwargs ):
        trans.response.set_content_type( "text/javascript" )
        return simplejson.dumps( func( self, trans, *args, **kwargs ) )
    if not hasattr(func, '_orig'):
        decorator._orig = func
    decorator.exposed = True
    return decorator

def json_pretty( func ):
    @wraps(func)
    def decorator( self, trans, *args, **kwargs ):
        trans.response.set_content_type( "text/javascript" )
        return simplejson.dumps( func( self, trans, *args, **kwargs ), indent=4, sort_keys=True )
    if not hasattr(func, '_orig'):
        decorator._orig = func
    decorator.exposed = True
    return decorator

def require_login( verb="perform this action", use_panels=False, webapp='galaxy' ):
    def argcatcher( func ):
        @wraps(func)
        def decorator( self, trans, *args, **kwargs ):
            if trans.get_user():
                return func( self, trans, *args, **kwargs )
            else:
                return trans.show_error_message(
                    'You must be <a target="galaxy_main" href="%s">logged in</a> to %s.'
                    % ( url_for( controller='user', action='login', webapp=webapp ), verb ), use_panels=use_panels )
        return decorator
    return argcatcher

def expose_api( func ):
    @wraps(func)
    def decorator( self, trans, *args, **kwargs ):
        def error( environ, start_response ):
            start_response( error_status, [('Content-type', 'text/plain')] )
            return error_message
        error_status = '403 Forbidden'
        ## If there is a user, we've authenticated a session.
        if not trans.user and isinstance(trans.galaxy_session, Bunch):
            # If trans.user is already set, don't check for a key.
            # This happens when we're authenticating using session instead of an API key.
            # The Bunch clause is used to prevent the case where there's no user, but there is a real session.
            # DBTODO: This needs to be fixed when merging transaction types.
            if 'key' not in kwargs:
                error_message = 'No API key provided with request, please consult the API documentation.'
                return error
            try:
                provided_key = trans.sa_session.query( trans.app.model.APIKeys ).filter( trans.app.model.APIKeys.table.c.key == kwargs['key'] ).one()
            except NoResultFound:
                error_message = 'Provided API key is not valid.'
                return error
            if provided_key.user.deleted:
                error_message = 'User account is deactivated, please contact an administrator.'
                return error
            newest_key = provided_key.user.api_keys[0]
            if newest_key.key != provided_key.key:
                error_message = 'Provided API key has expired.'
                return error
            trans.set_user( provided_key.user )
        if trans.request.body:
            try:
                payload = util.recursively_stringify_dictionary_keys( simplejson.loads( trans.request.body ) )
                kwargs['payload'] = payload
            except ValueError:
                error_status = '400 Bad Request'
                error_message = 'Your request did not appear to be valid JSON, please consult the API documentation'
                return error
        trans.response.set_content_type( "application/json" )
        # Perform api_run_as processing, possibly changing identity
        if 'run_as' in kwargs:
            if not trans.user_can_do_run_as():
                error_message = 'User does not have permissions to run jobs as another user'
                return error
            try:
                decoded_user_id = trans.security.decode_id( kwargs['run_as'] )
            except TypeError:
                trans.response.status = 400
                return "Malformed user id ( %s ) specified, unable to decode." % str( kwargs['run_as'] )
            try:
                user = trans.sa_session.query( trans.app.model.User ).get( decoded_user_id )
                trans.api_inherit_admin = trans.user_is_admin()
                trans.set_user(user)
            except:
                trans.response.status = 400
                return "That user does not exist."
        try:
            if trans.debug:
                return simplejson.dumps( func( self, trans, *args, **kwargs ), indent=4, sort_keys=True )
            else:
                return simplejson.dumps( func( self, trans, *args, **kwargs ) )
        except paste.httpexceptions.HTTPException:
            raise # handled
        except:
            log.exception( 'Uncaught exception in exposed API method:' )
            raise paste.httpexceptions.HTTPServerError()
    if not hasattr(func, '_orig'):
        decorator._orig = func
    decorator.exposed = True
    return decorator

def require_admin( func ):
    @wraps(func)
    def decorator( self, trans, *args, **kwargs ):
        if not trans.user_is_admin():
            msg = "You must be an administrator to access this feature."
            admin_users = trans.app.config.get( "admin_users", "" ).split( "," )
            user = trans.get_user()
            if not admin_users:
                msg = "You must be logged in as an administrator to access this feature, but no administrators are set in the Galaxy configuration."
            elif not user:
                msg = "You must be logged in as an administrator to access this feature."
            trans.response.status = 403
            if trans.response.get_content_type() == 'application/json':
                return msg
            else:
                return trans.show_error_message( msg )
        return func( self, trans, *args, **kwargs )
    return decorator

NOT_SET = object()

def error( message ):
    raise MessageException( message, type='error' )

def form( *args, **kwargs ):
    return FormBuilder( *args, **kwargs )
    
class WebApplication( base.WebApplication ):
    def __init__( self, galaxy_app, session_cookie='galaxysession' ):
        base.WebApplication.__init__( self )
        self.set_transaction_factory( lambda e: self.transaction_chooser( e, galaxy_app, session_cookie ) )
        # Mako support
        self.mako_template_lookup = mako.lookup.TemplateLookup(
            directories = [ galaxy_app.config.template_path ] ,
            module_directory = galaxy_app.config.template_cache,
            collection_size = 500,
            output_encoding = 'utf-8' )
        # Security helper
        self.security = galaxy_app.security
    def handle_controller_exception( self, e, trans, **kwargs ):
        if isinstance( e, MessageException ):
            return trans.show_message( e.err_msg, e.type )
    def make_body_iterable( self, trans, body ):
        if isinstance( body, FormBuilder ):
            body = trans.show_form( body )
        return base.WebApplication.make_body_iterable( self, trans, body )
    def transaction_chooser( self, environ, galaxy_app, session_cookie ):
        if 'is_api_request' in environ:
            return GalaxyWebAPITransaction( environ, galaxy_app, self, session_cookie )
        else:
            return GalaxyWebUITransaction( environ, galaxy_app, self, session_cookie )

class GalaxyWebTransaction( base.DefaultWebTransaction ):
    """
    Encapsulates web transaction specific state for the Galaxy application
    (specifically the user's "cookie" session and history)
    """
    def __init__( self, environ, app, webapp ):
        self.app = app
        self.webapp = webapp
        self.security = webapp.security
        base.DefaultWebTransaction.__init__( self, environ )
        self.setup_i18n()
        self.sa_session.expunge_all()
        self.debug = asbool( self.app.config.get( 'debug', False ) )
        # Flag indicating whether we are in workflow building mode (means
        # that the current history should not be used for parameter values
        # and such).
        self.workflow_building_mode = False
        # Flag indicating whether this is an API call and the API key user is an administrator
        self.api_inherit_admin = False
    def setup_i18n( self ):
        locales = []
        if 'HTTP_ACCEPT_LANGUAGE' in self.environ:
            # locales looks something like: ['en', 'en-us;q=0.7', 'ja;q=0.3']
            client_locales = self.environ['HTTP_ACCEPT_LANGUAGE'].split( ',' )
            for locale in client_locales:
                try:
                    locales.append( Locale.parse( locale.split( ';' )[0], sep='-' ).language )
                except UnknownLocaleError:
                    pass
        if not locales:
            # Default to English
            locales = 'en'
        t = Translations.load( dirname='locale', locales=locales, domain='ginga' )
        self.template_context.update ( dict( _=t.ugettext, n_=t.ugettext, N_=t.ungettext ) )
    @property
    def sa_session( self ):
        """
        Returns a SQLAlchemy session -- currently just gets the current
        session from the threadlocal session context, but this is provided
        to allow migration toward a more SQLAlchemy 0.4 style of use.
        """
        return self.app.model.context.current
    def log_action( self, user=None, action=None, context=None, params=None):
        """
        Application-level logging of user actions.
        """
        if self.app.config.log_actions:
            action = self.app.model.UserAction(action=action, context=context, params=unicode( to_json_string( params ) ) )
            try:
                if user:
                    action.user = user
                else:
                    action.user = self.user
            except:
                action.user = None
            try:
                action.session_id = self.galaxy_session.id
            except:
                action.session_id = None
            self.sa_session.add( action )
            self.sa_session.flush()
    def log_event( self, message, tool_id=None, **kwargs ):
        """
        Application level logging. Still needs fleshing out (log levels and such)
        Logging events is a config setting - if False, do not log.
        """
        if self.app.config.log_events:
            event = self.app.model.Event()
            event.tool_id = tool_id
            try:
                event.message = message % kwargs
            except:
                event.message = message
            try:
                event.history = self.get_history()
            except:
                event.history = None
            try:
                event.history_id = self.history.id
            except:
                event.history_id = None
            try:
                event.user = self.user
            except:
                event.user = None
            try:
                event.session_id = self.galaxy_session.id   
            except:
                event.session_id = None
            self.sa_session.add( event )
            self.sa_session.flush()
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
        self.response.cookies[name]['max-age'] = 3600 * 24 * age # 90 days
        tstamp = time.localtime ( time.time() + 3600 * 24 * age )
        self.response.cookies[name]['expires'] = time.strftime( '%a, %d-%b-%Y %H:%M:%S GMT', tstamp ) 
        self.response.cookies[name]['version'] = version
    def _ensure_valid_session( self, session_cookie, create=True):
        """
        Ensure that a valid Galaxy session exists and is available as
        trans.session (part of initialization)
        
        Support for universe_session and universe_user cookies has been
        removed as of 31 Oct 2008.
        """
        sa_session = self.sa_session
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
                                                .filter( and_( self.app.model.GalaxySession.table.c.session_key==session_key,
                                                               self.app.model.GalaxySession.table.c.is_valid==True ) ) \
                                                .first()
        # If remote user is in use it can invalidate the session, so we need to to check some things now.
        if self.app.config.use_remote_user:
            assert "HTTP_REMOTE_USER" in self.environ, \
                "use_remote_user is set but no HTTP_REMOTE_USER variable"
            remote_user_email = self.environ[ 'HTTP_REMOTE_USER' ]    
            if galaxy_session:
                # An existing session, make sure correct association exists
                if galaxy_session.user is None:
                    # No user, associate
                    galaxy_session.user = self.get_or_create_remote_user( remote_user_email )
                    galaxy_session_requires_flush = True
                elif galaxy_session.user.email != remote_user_email:
                    # Session exists but is not associated with the correct remote user
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
        # If the old session was invalid, get a new history with our new session
        if invalidate_existing_session:
            self.new_history()
    def _ensure_logged_in_user( self, environ, session_cookie ):
        # The value of session_cookie can be one of 
        # 'galaxysession' or 'galaxycommunitysession'
        # Currently this method does nothing unless session_cookie is 'galaxysession'
        if session_cookie == 'galaxysession':
            # TODO: re-engineer to eliminate the use of allowed_paths
            # as maintenance overhead is far too high.
            allowed_paths = (
                url_for( controller='root', action='index' ),
                url_for( controller='root', action='tool_menu' ),
                url_for( controller='root', action='masthead' ),
                url_for( controller='root', action='history' ),
                url_for( controller='user', action='api_keys' ),
                url_for( controller='user', action='create' ),
                url_for( controller='user', action='index' ),
                url_for( controller='user', action='login' ),
                url_for( controller='user', action='logout' ),
                url_for( controller='user', action='manage_user_info' ),
                url_for( controller='user', action='set_default_permissions' ),
                url_for( controller='user', action='reset_password' ),
                url_for( controller='library', action='browse' ),
                url_for( controller='history', action='list' ),
                url_for( controller='dataset', action='list' )
            )
            display_as = url_for( controller='root', action='display_as' )
            if self.galaxy_session.user is None:
                if self.app.config.ucsc_display_sites and self.request.path == display_as:
                    try:
                        host = socket.gethostbyaddr( self.environ[ 'REMOTE_ADDR' ] )[0]
                    except( socket.error, socket.herror, socket.gaierror, socket.timeout ):
                        host = None
                    if host in UCSC_SERVERS:
                        return
                if self.request.path not in allowed_paths:
                    self.response.send_redirect( url_for( controller='root', action='index' ) )
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
            remote_host = self.request.remote_host,
            remote_addr = self.request.remote_addr,
            referer = self.request.headers.get( 'Referer', None ) )
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
        
        user = self.sa_session.query( self.app.model.User ) \
                              .filter( self.app.model.User.table.c.email==remote_user_email ) \
                              .first()
        if user:
            # GVK: June 29, 2009 - This is to correct the behavior of a previous bug where a private
            # role and default user / history permissions were not set for remote users.  When a
            # remote user authenticates, we'll look for this information, and if missing, create it.
            if not self.app.security_agent.get_private_user_role( user ):
                self.app.security_agent.create_private_user_role( user )
            if not user.default_permissions:
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
            if ( self.sa_session.query( self.app.model.User ).filter_by( username=username ).first() ):
                i = 1
                while ( self.sa_session.query( self.app.model.User ).filter_by( username=(username + '-' + str(i) ) ).first() ):
                    i += 1
                username += '-' + str(i)
            user.username = username
            self.sa_session.add( user )
            self.sa_session.flush()
            self.app.security_agent.create_private_user_role( user )
            # We set default user permissions, before we log in and set the default history permissions
            self.app.security_agent.user_set_default_permissions( user )
            #self.log_event( "Automatically created account '%s'", user.email )
        return user
    def __update_session_cookie( self, name='galaxysession' ):
        """
        Update the session cookie to match the current session.
        """
        self.set_cookie( self.security.encode_guid( self.galaxy_session.session_key ), name=name, path=self.app.config.cookie_path )
    def handle_user_login( self, user, webapp ):
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
        if webapp == 'galaxy':
            cookie_name = 'galaxysession'
            # Associated the current user's last accessed history (if exists) with their new session
            history = None
            try:
                users_last_session = user.galaxy_sessions[0]
                last_accessed = True
            except:
                users_last_session = None
                last_accessed = False
            if prev_galaxy_session.current_history and \
                not prev_galaxy_session.current_history.deleted and \
                prev_galaxy_session.current_history.datasets:
                if prev_galaxy_session.current_history.user is None or prev_galaxy_session.current_history.user == user:
                    # If the previous galaxy session had a history, associate it with the new
                    # session, but only if it didn't belong to a different user.
                    history = prev_galaxy_session.current_history
                    if prev_galaxy_session.user is None:
                        # Increase the user's disk usage by the amount of the previous history's datasets if they didn't already own it.
                        for hda in history.datasets:
                            user.total_disk_usage += hda.quota_amount( user )
            elif self.galaxy_session.current_history:
                history = self.galaxy_session.current_history
            if not history and \
                users_last_session and \
                users_last_session.current_history and \
                not users_last_session.current_history.deleted:
                history = users_last_session.current_history
            elif not history:
                history = self.get_history( create=True )
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
            for other_galaxy_session in self.sa_session.query( self.app.model.GalaxySession ) \
                                            .filter( and_( self.app.model.GalaxySession.table.c.user_id==galaxy_user_id,
                                                                self.app.model.GalaxySession.table.c.is_valid==True,
                                                                self.app.model.GalaxySession.table.c.id!=prev_galaxy_session.id ) ):
                other_galaxy_session.is_valid = False
                self.sa_session.add( other_galaxy_session )
        self.sa_session.flush()
        # This method is not called from the Galaxy reports, so the cookie will always be galaxysession
        self.__update_session_cookie( name='galaxysession' )
    def get_galaxy_session( self ):
        """
        Return the current galaxy session
        """
        return self.galaxy_session
    def get_history( self, create=False ):
        """
        Load the current history, creating a new one only if there is not 
        current history and we're told to create"
        """
        history = self.galaxy_session.current_history
        if not history:
            if util.string_as_bool( create ):
                history = self.new_history()
            else:
                # Perhaps a bot is running a tool without having logged in to get a history
                log.debug( "Error: this request returned None from get_history(): %s" % self.request.browser_url )
                return None
        return history
    def set_history( self, history ):
        if history and not history.deleted:
            self.galaxy_session.current_history = history
        self.sa_session.add( self.galaxy_session )
        self.sa_session.flush()
    history = property( get_history, set_history )
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
        history.genome_build = util.dbnames.default_value
        # Set the user's default history permissions
        self.app.security_agent.history_set_default_permissions( history )
        # Save
        self.sa_session.add_all( ( self.galaxy_session, history ) )
        self.sa_session.flush()
        return history
    def get_current_user_roles( self ):
        user = self.get_user()
        if user:
            roles = user.all_roles()
        else:
            roles = []
        return roles
    def user_is_admin( self ):
        if self.api_inherit_admin:
            return True
        admin_users = self.app.config.get( "admin_users", "" ).split( "," )
        return self.user and admin_users and self.user.email in admin_users
    def user_can_do_run_as( self ):
        run_as_users = self.app.config.get( "api_allow_run_as", "" ).split( "," )
        return self.user and run_as_users and self.user.email in run_as_users
    def get_toolbox(self):
        """Returns the application toolbox"""
        return self.app.toolbox
    @base.lazy_property
    def template_context( self ):
        return dict()
    @property
    def model( self ):
        return self.app.model
    def make_form_data( self, name, **kwargs ):
        rval = self.template_context[name] = FormData()
        rval.values.update( kwargs )
        return rval
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
        return self.fill_template( template, form=form, header=header, use_panels=( form.use_panels or use_panels ), 
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
    def fill_template_mako( self, filename, **kwargs ):
        template = self.webapp.mako_template_lookup.get_template( filename )
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
        ## return template.render( **data )
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

    @property
    def db_builds( self ):
        """
        Returns the builds defined by galaxy and the builds defined by
        the user (chromInfo in history).
        """
        dbnames = list()
        datasets = self.sa_session.query( self.app.model.HistoryDatasetAssociation ) \
                                  .filter_by( deleted=False, history_id=self.history.id, extension="len" )
        
        for dataset in datasets:
            dbnames.append( (dataset.dbkey, dataset.name) )
            
        user = self.get_user()
        if user and 'dbkeys' in user.preferences:
            user_keys = from_json_string( user.preferences['dbkeys'] )
            for key, chrom_dict in user_keys.iteritems():
                dbnames.append((key, "%s (%s) [Custom]" % (chrom_dict['name'], key) ))
                    
        dbnames.extend( util.dbnames )
        return dbnames

    def db_dataset_for( self, dbkey ):
        """
        Returns the db_file dataset associated/needed by `dataset`, or `None`.
        """
        # If no history, return None.
        if self.history is None:
            return None
        if isinstance(self.history, Bunch):
            # The API presents a Bunch for a history.  Until the API is
            # more fully featured for handling this, also return None.
            return None
        datasets = self.sa_session.query( self.app.model.HistoryDatasetAssociation ) \
                                  .filter_by( deleted=False, history_id=self.history.id, extension="len" )
        for ds in datasets:
            if dbkey == ds.dbkey:
                return ds
        return None

    def request_types(self):
        if self.sa_session.query( self.app.model.RequestType ).filter_by( deleted=False ).count() > 0:
            return True
        return False
        
class FormBuilder( object ):
    """
    Simple class describing an HTML form
    """
    def __init__( self, action="", title="", name="form", submit_text="submit", use_panels=False ):
        self.title = title
        self.name = name
        self.action = action
        self.submit_text = submit_text
        self.inputs = []
        self.use_panels = use_panels
    def add_input( self, type, name, label, value=None, error=None, help=None, use_label=True  ):
        self.inputs.append( FormInput( type, label, name, value, error, help, use_label ) )
        return self
    def add_text( self, name, label, value=None, error=None, help=None  ):
        return self.add_input( 'text', label, name, value, error, help )
    def add_password( self, name, label, value=None, error=None, help=None  ):
        return self.add_input( 'password', label, name, value, error, help )
    def add_select( self, name, label, value=None, options=[], error=None, help=None, use_label=True ):
        self.inputs.append( SelectInput( name, label, value=value, options=options, error=error, help=help, use_label=use_label   ) ) 
        return self

class FormInput( object ):
    """
    Simple class describing a form input element
    """
    def __init__( self, type, name, label, value=None, error=None, help=None, use_label=True ):
        self.type = type
        self.name = name
        self.label = label
        self.value = value
        self.error = error
        self.help = help
        self.use_label = use_label

class GalaxyWebAPITransaction( GalaxyWebTransaction ):
    """
        TODO:  Unify this with WebUITransaction, since we allow session auth now.  
              Enable functionality of 'create' parameter in parent _ensure_valid_session
    """
    def __init__( self, environ, app, webapp, session_cookie):
        GalaxyWebTransaction.__init__( self, environ, app, webapp )
        self.__user = None
        self._ensure_valid_session( session_cookie )
    def _ensure_valid_session( self, session_cookie ):
        #Check to see if there is an existing session.  Never create a new one.
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
                                                .filter( and_( self.app.model.GalaxySession.table.c.session_key==session_key,
                                                               self.app.model.GalaxySession.table.c.is_valid==True ) ) \
                                                .first()
        if galaxy_session:
            # If remote user is in use it can invalidate the session, so we need to to check some things now.
            if self.app.config.use_remote_user:
                assert "HTTP_REMOTE_USER" in self.environ, \
                    "use_remote_user is set but no HTTP_REMOTE_USER variable"
                remote_user_email = self.environ[ 'HTTP_REMOTE_USER' ]
                # An existing session, make sure correct association exists
                if galaxy_session.user is None:
                    # No user, associate
                    galaxy_session.user = self.get_or_create_remote_user( remote_user_email )
                    galaxy_session_requires_flush = True
                elif galaxy_session.user.email != remote_user_email:
                    # Session exists but is not associated with the correct remote user
                    log.warning( "User logged in as '%s' externally, but has a cookie as '%s' invalidating session",
                                 remote_user_email, galaxy_session.user.email )
                    galaxy_session = None
            else:
                if galaxy_session.user and galaxy_session.user.external:
                    # Remote user support is not enabled, but there is an existing
                    # session with an external user, invalidate
                    invalidate_existing_session = True
                    log.warning( "User '%s' is an external user with an existing session, invalidating session since external auth is disabled",
                                 galaxy_session.user.email )
                    galaxy_session = None
                elif galaxy_session.user is not None and galaxy_session.user.deleted:
                    invalidate_existing_session = True
                    log.warning( "User '%s' is marked deleted, invalidating session" % galaxy_session.user.email )
                    galaxy_session = None
            # No relevant cookies, or couldn't find, or invalid, so create a new session
            if galaxy_session:
                self.galaxy_session = galaxy_session
                self.user = galaxy_session.user
            # Do we need to flush the session?
            if galaxy_session_requires_flush:
                self.sa_session.add( galaxy_session )
                # FIXME: If prev_session is a proper relation this would not
                #        be needed.
                if prev_galaxy_session:
                    self.sa_session.add( prev_galaxy_session )
                self.sa_session.flush()
            # If the old session was invalid, get a new history with our new session
        if not galaxy_session:
            #Failed to find a session.  Set up fake stuff for API transaction
            self.user = None
            self.galaxy_session = Bunch()
            self.galaxy_session.history = self.galaxy_session.current_history = Bunch()
            self.galaxy_session.history.genome_build = None
            self.galaxy_session.is_api = True

    def get_user( self ):
        """Return the current user (the expose_api decorator ensures that it is set)."""
        return self.__user
    def set_user( self, user ):
        """Compatibility method"""
        self.__user = user
    user = property( get_user, set_user )
    @property
    def db_builds( self ):
        dbnames = []
        if 'dbkeys' in self.user.preferences:
            user_keys = from_json_string( self.user.preferences['dbkeys'] )
            for key, chrom_dict in user_keys.iteritems():
                dbnames.append((key, "%s (%s) [Custom]" % (chrom_dict['name'], key) ))
        dbnames.extend( util.dbnames )
        return dbnames

class GalaxyWebUITransaction( GalaxyWebTransaction ):
    def __init__( self, environ, app, webapp, session_cookie ):
        GalaxyWebTransaction.__init__( self, environ, app, webapp )
        # Always have a valid galaxy session
        self._ensure_valid_session( session_cookie )
        # Prevent deleted users from accessing Galaxy
        if self.app.config.use_remote_user and self.galaxy_session.user.deleted:
            self.response.send_redirect( url_for( '/static/user_disabled.html' ) )
        if self.app.config.require_login:
            self._ensure_logged_in_user( environ, session_cookie )
    def get_user( self ):
        """Return the current user if logged in or None."""
        return self.galaxy_session.user
    def set_user( self, user ):
        """Set the current user."""
        self.galaxy_session.user = user
        self.sa_session.add( self.galaxy_session )
        self.sa_session.flush()
    user = property( get_user, set_user )

class SelectInput( FormInput ):
    """ A select form input. """
    def __init__( self, name, label, value=None, options=[], error=None, help=None, use_label=True ):
        FormInput.__init__( self, "select", name, label, value=value, error=error, help=help, use_label=use_label )
        self.options = options
    
class FormData( object ):
    """
    Class for passing data about a form to a template, very rudimentary, could
    be combined with the tool form handling to build something more general.
    """
    def __init__( self ):
        self.values = Bunch()
        self.errors = Bunch()
        
class Bunch( dict ):
    """
    Bunch based on a dict
    """
    def __getattr__( self, key ):
        if key not in self: raise AttributeError, key
        return self[key]
    def __setattr__( self, key, value ):
        self[key] = value
