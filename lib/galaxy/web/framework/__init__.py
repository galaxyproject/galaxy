"""
Galaxy web application framework
"""

import pkg_resources

import os, sys, time, socket, random, string
pkg_resources.require( "Cheetah" )
from Cheetah.Template import Template
import base
import pickle
from galaxy import util

pkg_resources.require( "simplejson" )
import simplejson

import helpers

pkg_resources.require( "PasteDeploy" )
from paste.deploy.converters import asbool

pkg_resources.require( "Mako" )
import mako.template
import mako.lookup
import mako.runtime

pkg_resources.require( "Babel" )
from babel.support import Translations

pkg_resources.require( "SQLAlchemy >= 0.4" )
from sqlalchemy import and_
            
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
    def decorator( self, trans, *args, **kwargs ):
        trans.response.set_content_type( "text/javascript" )
        return simplejson.dumps( func( self, trans, *args, **kwargs ) )
    if not hasattr(func, '_orig'):
        decorator._orig = func
    decorator.exposed = True
    return decorator

def require_login( verb="perform this action" ):
    def argcatcher( func ):
        def decorator( self, trans, *args, **kwargs ):
            if trans.get_user():
                return func( self, trans, *args, **kwargs )
            else:
                return trans.show_error_message(
                    "You must be <a target='galaxy_main' href='%s'>logged in</a> to %s</div>"
                    % ( url_for( controller='user', action='login' ), verb ) )      
        return decorator
    return argcatcher
    
def require_admin( func ):
    def decorator( self, trans, *args, **kwargs ):
        admin_users = trans.app.config.get( "admin_users", "" ).split( "," )
        if not admin_users:
            return trans.show_error_message( "You must be logged in as an administrator to access this feature, but no administrators are set in the Galaxy configuration." )
        user = trans.get_user()
        if not user:
            return trans.show_error_message( "You must be logged in as an administrator to access this feature." )
        if not user.email in admin_users:
            return trans.show_error_message( "You must be an administrator to access this feature." )
        return func( self, trans, *args, **kwargs )
    return decorator

NOT_SET = object()

class MessageException( Exception ):
    """
    Exception to make throwing errors from deep in controllers easier
    """
    def __init__( self, err_msg, type="info" ):
        self.err_msg = err_msg
        self.type = type
        
def error( message ):
    raise MessageException( message, type='error' )

def form( *args, **kwargs ):
    return FormBuilder( *args, **kwargs )
    
class WebApplication( base.WebApplication ):
    def __init__( self, galaxy_app, session_cookie='galaxysession' ):
        base.WebApplication.__init__( self )
        self.set_transaction_factory( lambda e: UniverseWebTransaction( e, galaxy_app, self, session_cookie ) )
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
    
class UniverseWebTransaction( base.DefaultWebTransaction ):
    """
    Encapsulates web transaction specific state for the Universe application
    (specifically the user's "cookie" session and history)
    """
    def __init__( self, environ, app, webapp, session_cookie ):
        self.app = app
        self.webapp = webapp
        self.security = webapp.security
        # FIXME: the following 3 attributes are not currently used
        #        Remove them if they are not going to be...
        self.__user = NOT_SET
        self.__history = NOT_SET
        self.__galaxy_session = NOT_SET
        base.DefaultWebTransaction.__init__( self, environ )
        self.setup_i18n()
        self.sa_session.clear()
        self.debug = asbool( self.app.config.get( 'debug', False ) )
        # Flag indicating whether we are in workflow building mode (means
        # that the current history should not be used for parameter values
        # and such).
        self.workflow_building_mode = False
        # Always have a valid galaxy session
        self.__ensure_valid_session( session_cookie )
        # Prevent deleted users from accessing Galaxy
        if self.app.config.use_remote_user and self.galaxy_session.user.deleted:
            self.response.send_redirect( url_for( '/static/user_disabled.html' ) )
        if self.app.config.require_login:
            self.__ensure_logged_in_user( environ )
    def setup_i18n( self ):
        if 'HTTP_ACCEPT_LANGUAGE' in self.environ:
            # locales looks something like: ['en', 'en-us;q=0.7', 'ja;q=0.3']
            locales = self.environ['HTTP_ACCEPT_LANGUAGE'].split( ',' )
            locales = [ l.split( ';' )[0] for l in locales ]
        else:
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
            event.flush()
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
    #@property
    #def galaxy_session( self ):
    #    if not self.__galaxy_session:
    #        self.__ensure_valid_session()
    #    return self.__galaxy_session  
    def __ensure_valid_session( self, session_cookie ):
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
            session_key = self.security.decode_session_key( secure_id )
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
                    galaxy_session.user = self.__get_or_create_remote_user( remote_user_email )
                    galaxy_session_requires_flush = True
                elif galaxy_session.user.email != remote_user_email:
                    # Session exists but is not associated with the correct remote user
                    invalidate_existing_session = True
                    user_for_new_session = self.__get_or_create_remote_user( remote_user_email )
                    log.warning( "User logged in as '%s' externally, but has a cookie as '%s' invalidating session",
                                 remote_user_email, galaxy_session.user.email )
            else:
                # No session exists, get/create user for new session
                user_for_new_session = self.__get_or_create_remote_user( remote_user_email )
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
            objects_to_flush = [ galaxy_session ]
            # FIXME: If prev_session is a proper relation this would not
            #        be needed.
            if prev_galaxy_session:
                objects_to_flush.append( prev_galaxy_session )            
            sa_session.flush( objects_to_flush )
        # If the old session was invalid, get a new history with our new session
        if invalidate_existing_session:
            self.new_history()
    def __ensure_logged_in_user( self, environ ):
        allowed_paths = (
            url_for( controller='root', action='index' ),
            url_for( controller='root', action='tool_menu' ),
            url_for( controller='root', action='masthead' ),
            url_for( controller='root', action='history' ),
            url_for( controller='user', action='login' ),
            url_for( controller='user', action='create' ),
            url_for( controller='user', action='reset_password' ),
            url_for( controller='library', action='browse' )
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
        session_key = self.security.get_new_session_key()
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
    def __get_or_create_remote_user( self, remote_user_email ):
        """
        Return the user in $HTTP_REMOTE_USER and create if necessary
        """
        # remote_user middleware ensures HTTP_REMOTE_USER exists
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
            random.seed()
            user = self.app.model.User( email=remote_user_email )
            user.set_password_cleartext( ''.join( random.sample( string.letters + string.digits, 12 ) ) )
            user.external = True
            user.flush()
            self.app.security_agent.create_private_user_role( user )
            # We set default user permissions, before we log in and set the default history permissions
            self.app.security_agent.user_set_default_permissions( user )
            #self.log_event( "Automatically created account '%s'", user.email )
        return user
    def __update_session_cookie( self, name='galaxysession' ):
        """
        Update the session cookie to match the current session.
        """
        self.set_cookie( self.security.encode_session_key( self.galaxy_session.session_key ), name=name )
    def handle_user_login( self, user ):
        """
        Login a new user (possibly newly created)
           - create a new session
           - associate new session with user
           - if old session had a history and it was not associated with a user, associate it with the new session, 
             otherwise associate the current session's history with the user
        """
        # Set the previous session
        prev_galaxy_session = self.galaxy_session
        prev_galaxy_session.is_valid = False
        # Define a new current_session
        self.galaxy_session = self.__create_new_session( prev_galaxy_session, user )
        # Associated the current user's last accessed history (if exists) with their new session
        history = None
        try:
            users_last_session = user.galaxy_sessions[0]
            last_accessed = True
        except:
            users_last_session = None
            last_accessed = False
        if prev_galaxy_session.current_history and prev_galaxy_session.current_history.datasets:
            if prev_galaxy_session.current_history.user is None or prev_galaxy_session.current_history.user == user:
                # If the previous galaxy session had a history, associate it with the new
                # session, but only if it didn't belong to a different user.
                history = prev_galaxy_session.current_history
        elif self.galaxy_session.current_history:
            history = self.galaxy_session.current_history
        if not history and users_last_session and users_last_session.current_history:
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
        self.sa_session.flush( [ prev_galaxy_session, self.galaxy_session, history ] )
        # This method is not called from the Galaxy reports, so the cookie will always be galaxysession
        self.__update_session_cookie( name='galaxysession' )
    def handle_user_logout( self ):
        """
        Logout the current user:
           - invalidate the current session
           - create a new session with no user associated
        """
        prev_galaxy_session = self.galaxy_session
        prev_galaxy_session.is_valid = False
        self.galaxy_session = self.__create_new_session( prev_galaxy_session )
        self.sa_session.flush( [ prev_galaxy_session, self.galaxy_session ] )
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
        self.sa_session.flush( [ self.galaxy_session ] )
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
        self.sa_session.flush( [ self.galaxy_session, history ] )
        return history

    def get_user( self ):
        """Return the current user if logged in or None."""
        return self.galaxy_session.user
    def set_user( self, user ):
        """Set the current user."""
        self.galaxy_session.user = user
        self.sa_session.flush( [ self.galaxy_session ] )
    user = property( get_user, set_user )

    def get_user_and_roles( self ):
        user = self.get_user()
        if user:
            roles = user.all_roles()
        else:
            roles = []
        return user, roles

    def user_is_admin( self ):
        admin_users = self.app.config.get( "admin_users", "" ).split( "," )
        if self.user and admin_users and self.user.email in admin_users:
            return True
        return False

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
    def set_message( self, message ):
        """
        Convenience method for setting the 'message' element of the template
        context.
        """
        self.template_context['message'] = message
    def show_message( self, message, type='info', refresh_frames=[], cont=None ):
        """
        Convenience method for displaying a simple page with a single message.
        
        `type`: one of "error", "warning", "info", or "done"; determines the
                type of dialog box and icon displayed with the message
                
        `refresh_frames`: names of frames in the interface that should be 
                          refreshed when the message is displayed
        """
        return self.fill_template( "message.mako", message_type=type, message=message, refresh_frames=refresh_frames, cont=cont )
    def show_error_message( self, message, refresh_frames=[] ):
        """
        Convenience method for displaying an error message. See `show_message`.
        """
        return self.show_message( message, 'error', refresh_frames )
    def show_ok_message( self, message, refresh_frames=[] ):
        """
        Convenience method for displaying an ok message. See `show_message`.
        """
        return self.show_message( message, 'done', refresh_frames )
    def show_warn_message( self, message, refresh_frames=[] ):
        """
        Convenience method for displaying an warn message. See `show_message`.
        """
        return self.show_message( message, 'warning', refresh_frames )
    def show_form( self, form, header=None, template="form.mako" ):
        """
        Convenience method for displaying a simple page with a single HTML
        form.
        """    
        return self.fill_template( template, form=form, header=header )
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
        if datasets.count() > 0:
            dbnames.append( (util.dbnames.default_value, '--------- User Defined Builds ----------') )
        for dataset in datasets:
            dbnames.append( (dataset.dbkey, dataset.name) )
        dbnames.extend( util.dbnames )
        return dbnames
        
    def db_dataset_for( self, dbkey ):
        """
        Returns the db_file dataset associated/needed by `dataset`, or `None`.
        """
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
    def __init__( self, action="", title="", name="form", submit_text="submit" ):
        self.title = title
        self.name = name
        self.action = action
        self.submit_text = submit_text
        self.inputs = []
    def add_input( self, type, name, label, value=None, error=None, help=None, use_label=True  ):
        self.inputs.append( FormInput( type, label, name, value, error, help, use_label ) )
        return self
    def add_text( self, name, label, value=None, error=None, help=None  ):
        return self.add_input( 'text', label, name, value, error, help )
    def add_password( self, name, label, value=None, error=None, help=None  ):
        return self.add_input( 'password', label, name, value, error, help )
        
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
