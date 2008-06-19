"""
Galaxy web application framework
"""

import pkg_resources

import os, sys, time
pkg_resources.require( "Cheetah" )
from Cheetah.Template import Template
import base
import pickle
from galaxy import util

pkg_resources.require( "WebHelpers" )
pkg_resources.require( "PasteDeploy" )

import webhelpers
from paste.deploy.converters import asbool

pkg_resources.require( "Mako" )
import mako.template
import mako.lookup

pkg_resources.require( "simplejson" )
import simplejson

pkg_resources.require( "sqlalchemy>=0.3" )
from sqlalchemy import desc
            
import logging
log = logging.getLogger( __name__ )

url_for = base.routes.url_for

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
    
NOT_SET = object()

class MessageException( Exception ):
    """
    Exception to make throwing errors from deep in controllers easier
    """
    def __init__( self, message, type="info" ):
        self.message = message
        self.type = type
        
def error( message ):
    raise MessageException( message, type='error' )
    
class WebApplication( base.WebApplication ):
    def __init__( self, galaxy_app ):
        base.WebApplication.__init__( self )
        self.set_transaction_factory( lambda e: UniverseWebTransaction( e, galaxy_app, self ) )
        # Mako support
        self.mako_template_lookup = mako.lookup.TemplateLookup(
            directories = [ galaxy_app.config.template_path ] ,
            module_directory = galaxy_app.config.template_cache,
            collection_size = 500 )
        # Security helper
        from galaxy.web import security
        self.security = security.SecurityHelper( id_secret = galaxy_app.config.id_secret )
    def handle_controller_exception( self, e, trans, **kwargs ):
        if isinstance( e, MessageException ):
            return trans.show_message( e.message, e.type )
    
class UniverseWebTransaction( base.DefaultWebTransaction ):
    """
    Encapsulates web transaction specific state for the Universe application
    (specifically the user's "cookie" session and history)
    """
    def __init__( self, environ, app, webapp ):
        self.app = app
        self.webapp = webapp
        self.security = webapp.security
        self.__user = NOT_SET
        self.__history = NOT_SET
        self.__galaxy_session = NOT_SET
        base.DefaultWebTransaction.__init__( self, environ )
        self.app.model.context.current.clear()
        self.debug = asbool( self.app.config.get( 'debug', False ) )
        # Flag indicating whether we are in workflow building mode (means
        # that the current history should not be used for parameter values
        # and such).
        self.workflow_building_mode = False
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
        Application level logging. Still needs fleshing out (log levels and
        such)
        """
        event = self.app.model.Event()
        event.tool_id = tool_id
        try:
            event.message = message % kwargs
        except:
            event.message = message
        event.history = self.history
        try:
            event.history_id = self.history.id
        except:
            event.history_id = None
        event.user = self.user
        self.ensure_valid_galaxy_session()
        event.session_id = self.galaxy_session.id   
        event.flush()
    def get_cookie( self, name='galaxysession' ):
        """Convienience method for getting the galaxysession cookie"""
        try:
            # If we've changed the cookie during the request return the new value
            if name in self.response.cookies:
                return self.response.cookies[name].value
            else:
                return self.request.cookies[name].value
        except:
            return None
    def set_cookie( self, value, name='galaxysession', path='/', age=90, version='1' ):
        """Convienience method for setting the galaxysession cookie"""
        # The galaxysession cookie value must be a high entropy 128 bit random number encrypted 
        # using a server secret key.  Any other value is invalid and could pose security issues.
        self.response.cookies[name] = value
        self.response.cookies[name]['path'] = path
        self.response.cookies[name]['max-age'] = 3600 * 24 * age # 90 days
        tstamp = time.localtime ( time.time() + 3600 * 24 * age )
        self.response.cookies[name]['expires'] = time.strftime( '%a, %d-%b-%Y %H:%M:%S GMT', tstamp ) 
        self.response.cookies[name]['version'] = version
    def get_history( self, create=False ):
        """Load the current history"""
        if self.__history is NOT_SET:
            self.__history = None
            # See if we have a galaxysession cookie
            secure_id = self.get_cookie( name='galaxysession' )
            if secure_id:
                session_key = self.security.decode_session_key( secure_id )
                try:
                    galaxy_session = self.app.model.GalaxySession.selectone_by( session_key=session_key )
                    if galaxy_session and galaxy_session.is_valid and galaxy_session.current_history_id:
                        history = self.app.model.History.get( galaxy_session.current_history_id )
                        if history and not history.deleted:
                            self.__history = history
                except Exception, e:
                    # This should only occur in development if the cookie is not synced with the db
                    pass
            else:
                # See if we have a deprecated universe cookie
                # TODO: this should be eliminated some time after October 1, 2008
                # We'll keep it until then because the old universe cookies are valid for 90 days
                history_id = self.get_cookie( name='universe' )
                if history_id:
                    history = self.app.model.History.get( int( history_id ) )
                    if history and not history.deleted:
                        self.__history = history
                    # Expire the universe cookie since it is deprecated
                    self.set_cookie( name='universe', value=id, age=0 )
            if self.__history is None:
                return self.new_history()
        if create is True and self.__history is None:
            return self.new_history()
        return self.__history          
    def new_history( self ):
        history = self.app.model.History()
        # Make sure we have an id
        history.flush()
        # Immediately associate the new history with self
        self.__history = history
        # Make sure we have a valid session to associate with the new history
        if self.galaxy_session_is_valid():
            galaxy_session = self.get_galaxy_session()
        else:
            galaxy_session = self.new_galaxy_session()
        # We are associating the last used genome_build with histories, so we will always
        # initialize a new history with the first dbkey in util.dbnames which is currently
        # ?    unspecified (?)
        history.genome_build = util.dbnames.default_value
        if self.user:
            history.user_id = self.user.id
            galaxy_session.user_id = self.user.id
        try:
            # See if we have already associated the history with the session
            association = self.app.model.GalaxySessionToHistoryAssociation.select_by( session_id=galaxy_session.id, history_id=history.id )[0]
        except:
            association = None
        history.add_galaxy_session( galaxy_session, association=association )
        history.flush()
        galaxy_session.current_history_id = history.id
        galaxy_session.flush()
        self.__history = history
        return self.__history
    def set_history( self, history ):
        if history and not history.deleted and self.galaxy_session_is_valid():
            galaxy_session = self.get_galaxy_session()
            galaxy_session.current_history_id = history.id
            galaxy_session.flush()
        self.__history = history
    history = property( get_history, set_history )
    def get_user( self ):
        """Return the current user if logged in or None."""
        if self.__user is NOT_SET:
            self.__user = None
            # See if we have a galaxysession cookie
            secure_id = self.get_cookie( name='galaxysession' )
            if secure_id:
                session_key = self.security.decode_session_key( secure_id )
                try:
                    galaxy_session = self.app.model.GalaxySession.selectone_by( session_key=session_key )
                    if galaxy_session and galaxy_session.is_valid and galaxy_session.user_id:
                        user = self.app.model.User.get( galaxy_session.user_id )
                        if user:
                            self.__user = user
                except:
                    # This should only occur in development if the cookie is not synced with the db
                    pass
            else:
                # See if we have a deprecated universe_user cookie
                # TODO: this should be eliminated some time after October 1, 2008
                # We'll keep it until then because the old universe cookies are valid for 90 days
                user_id = self.get_cookie( name='universe_user' )
                if user_id:
                    user = self.app.model.User.get( int( user_id ) )
                    if user:
                        self.__user = user
                    # Expire the universe_user cookie since it is deprecated
                    self.set_cookie( name='universe_user', value='', age=0 )
        return self.__user
    def set_user( self, user ):
        """Set the current user if logged in."""
        if user is not None and self.galaxy_session_is_valid():
            galaxy_session = self.get_galaxy_session()
            if galaxy_session.user_id != user.id:
                galaxy_session.user_id = user.id
                galaxy_session.flush()
        self.__user = user
    user = property( get_user, set_user )
    def get_galaxy_session( self, create=False ):
        """Return the current user's GalaxySession"""
        if self.__galaxy_session is NOT_SET:
            self.__galaxy_session = None
            # See if we have a galaxysession cookie
            secure_id = self.get_cookie( name='galaxysession' )
            if secure_id:
                # Decode the cookie value to get the session_key
                session_key = self.security.decode_session_key( secure_id )
                try:
                    # Retrive the galaxy_session id via the unique session_key
                    galaxy_session = self.app.model.GalaxySession.selectone_by( session_key=session_key )
                    if galaxy_session and galaxy_session.is_valid:
                        self.__galaxy_session = galaxy_session
                except:
                    # This should only occur in development if the cookie is not synced with the db
                    pass
            else:
                # See if we have a deprecated universe_session cookie
                # TODO: this should be eliminated some time after October 1, 2008
                # We'll keep it until then because the old universe cookies are valid for 90 days
                session_id = self.get_cookie( name='universe_session' )
                if session_id:
                    galaxy_session = self.app.model.GalaxySession.get( int( session_id ) )
                    # NOTE: We can't test for is_valid here since the old session records did not include this flag
                    if galaxy_session:
                        # Set the new galaxysession cookie value, old session records did not have a session_key or is_valid flag
                        session_key = self.security.get_new_session_key()
                        galaxy_session.session_key = session_key
                        galaxy_session.is_valid = True
                        galaxy_session.flush()
                        secure_id = self.security.encode_session_key( session_key )
                        self.set_cookie( name='galaxysession', value=secure_id )
                        # Expire the universe_user cookie since it is deprecated
                        self.set_cookie( name='universe_session', value='', age=0 )
                        self.__galaxy_session = galaxy_session
        if create is True and self.__galaxy_session is None:
            return self.new_galaxy_session()
        return self.__galaxy_session
    def new_galaxy_session( self, prev_session_id=None ):
        """Create a new secure galaxy_session"""
        session_key = self.security.get_new_session_key()
        galaxy_session = self.app.model.GalaxySession( session_key=session_key, is_valid=True, prev_session_id=prev_session_id )
        # Make sure we have an id
        galaxy_session.flush()
        # Immediately associate the new session with self
        self.__galaxy_session = galaxy_session
        if prev_session_id is not None:
            # User logged out, so we need to create a new history for this session
            self.history = self.new_history()
            galaxy_session.current_history_id = self.history.id
        elif self.user is not None:
            galaxy_session.user_id = self.user.id
            # Set this session's current_history_id to the user's last updated history
            h = self.app.model.History
            ht = h.table
            where = ( ht.c.user_id==self.user.id ) & ( ht.c.deleted=='f' )
            history = h.query().filter( where ).order_by( desc( ht.c.update_time ) ).first()
            if history:
                self.history = history
                galaxy_session.current_history_id = self.history.id
        elif self.history:
            galaxy_session.current_history_id = self.history.id
        galaxy_session.remote_host = self.request.remote_host
        galaxy_session.remote_addr = self.request.remote_addr
        try:
            galaxy_session.referer = self.request.headers['Referer']
        except:
            galaxy_session.referer = None
        if self.history is not None:
            # See if we have already associated the session with the history
            try:
                association = self.app.model.GalaxySessionToHistoryAssociation.select_by( session_id=galaxy_session.id, history_id=self.history.id )[0]
            except:
                association = None
            galaxy_session.add_history( self.history, association=association )
        galaxy_session.flush()
        # Set the cookie value to the encrypted session_key
        self.set_cookie( name='galaxysession', value=self.security.encode_session_key( session_key ) )
        self.__galaxy_session = galaxy_session
        return self.__galaxy_session
    def set_galaxy_session( self, galaxy_session ):
        """Set the current galaxy_session"""
        self.__galaxy_session = galaxy_session
    galaxy_session = property( get_galaxy_session, set_galaxy_session )
    def galaxy_session_is_valid( self ):
        try:
            return self.galaxy_session.is_valid
        except:
            return False
    def ensure_valid_galaxy_session( self ):
        """Make sure we have a valid galaxy session, create a new one if necessary."""
        if not self.galaxy_session_is_valid():
            galaxy_session = self.new_galaxy_session()
    def logout_galaxy_session( self ):
        """
        Logout the current user by setting user to None and galaxy_session.is_valid to False 
        in the db.  A new galaxy_session is automatically created with prev_session_id is set 
        to save a reference to the current one as a way of chaining them together
        """
        if self.galaxy_session_is_valid():
            galaxy_session = self.get_galaxy_session()
            old_session_id = galaxy_session.id
            galaxy_session.is_valid = False
            galaxy_session.flush()
            self.set_user( None )
            return self.new_galaxy_session( prev_session_id=old_session_id )
        else:
            error( "Attempted to logout an invalid galaxy_session" )
    def make_associations( self ):
        history = self.get_history()
        user = self.get_user()
        if self.galaxy_session_is_valid():
            galaxy_session = self.get_galaxy_session()
            if galaxy_session.user_id is None and user is not None:
                galaxy_session.user_id = user.id
            if history is not None:
                galaxy_session.current_history_id = history.id
            galaxy_session.flush()
            self.__galaxy_session = galaxy_session
        if history is not None and user is not None:
            history.user_id = user.id
            history.flush()
            self.__history = history
                
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
    def show_message( self, message, type='info', refresh_frames=[] ):
        """
        Convenience method for displaying a simple page with a single message.
        
        `type`: one of "error", "warning", "info", or "done"; determines the
                type of dialog box and icon displayed with the message
                
        `refresh_frames`: names of frames in the interface that should be 
                          refreshed when the message is displayed
        """
        return self.fill_template( "message.mako", message_type=type, message=message, refresh_frames=refresh_frames )
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
    def show_form( self, form ):
        """
        Convenience method for displaying a simple page with a single HTML
        form.
        """    
        return self.fill_template( "form.mako", form=form )
    def fill_template(self, filename, **kwargs):
        """
        Fill in a template, putting any keyword arguments on the context.
        """
        if filename.endswith( ".mako" ):
            return self.fill_template_mako( filename, **kwargs )
        else:
            template = Template( file=os.path.join(self.app.config.template_path, filename), 
                                searchList=[kwargs, self.template_context, dict(caller=self, t=self, h=webhelpers, util=util, request=self.request, response=self.response, app=self.app)] )
            return str( template )
    def fill_template_mako( self, filename, **kwargs ):
        template = self.webapp.mako_template_lookup.get_template( filename )
        data = dict( caller=self, t=self, trans=self, h=webhelpers, util=util, request=self.request, response=self.response, app=self.app )
        data.update( self.template_context )
        data.update( kwargs )
        return template.render( **data )
    def fill_template_string(self, template_string, context=None, **kwargs):
        """
        Fill in a template, putting any keyword arguments on the context.
        """
        template = Template( source=template_string, searchList=[context or kwargs, dict(caller=self)] )
        return str(template)
        
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
    def add_input( self, type, name, label, value=None, error=None, help=None  ):
        self.inputs.append( FormInput( type, label, name, value, error, help ) )
        return self
    def add_text( self, name, label, value=None, error=None, help=None  ):
        return self.add_input( 'text', label, name, value, error, help )
    def add_password( self, name, label, value=None, error=None, help=None  ):
        return self.add_input( 'password', label, name, value, error, help )
        
class FormInput( object ):
    """
    Simple class describing a form input element
    """
    def __init__( self, type, name, label, value=None, error=None, help=None ):
        self.type = type
        self.name = name
        self.label = label
        self.value = value
        self.error = error
        self.help = help
    
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
