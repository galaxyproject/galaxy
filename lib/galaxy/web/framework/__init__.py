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
        
    def get_cookie( self, name='universe' ):
        """
        Convienience method for getting the universe cookie
        """
        try:
            # If we've changed the cookie during the request return the new 
            # value
            if name in self.response.cookies:
                return self.response.cookies[name].value
            else:
                return self.request.cookies[name].value
        except Exception:
            return None
        
    def set_cookie( self, value, name='universe', path='/', age=90, version='1' ):
        """
        Convienience method for setting the universe cookie
        """
        self.response.cookies[name] = value
        self.response.cookies[name]['path']     = path
        self.response.cookies[name]['max-age']  = 3600 * 24 * age
        tstamp = time.localtime ( time.time() + 3600 * 24 * age  )
        self.response.cookies[name]['expires'] = time.strftime('%a, %d-%b-%Y %H:%M:%S GMT', tstamp) 
        self.response.cookies[name]['version'] = version
        
    def get_history( self, create=False ):
        """
        Load the current history
        """
        if self.__history is NOT_SET:
            history = None
            id = self.get_cookie( name='universe' )
            if id:
                history = self.app.model.History.get( id )
            if history is None or history.deleted:
                history = self.new_history()
            self.__history = history
        if create is True and ( history is None or history.deleted ):
            history = self.new_history()             
        return self.__history
    
    def new_history( self ):
        history = self.app.model.History()
        """
        We are associating the last used genome_build with histories, so we will always
        initialize a new history with the first dbkey in util.dbnames which is currently
        ?    unspecified (?)
        """
        history.genome_build = util.dbnames[0][0]
        if history.user_id is None and self.user is not None:
            history.user_id = self.user.id
        if self.galaxy_session_is_valid():
            history.add_galaxy_session(self.get_galaxy_session())
        history.flush()
        self.set_cookie( name='universe', value=history.id )
        self.__history = history
        return history
    
    def set_history( self, history ):
        if history is None or history.deleted:
            self.set_cookie( name='universe', value='' )
        else:
            self.set_cookie( name='universe', value=history.id )
        self.__history = history
    history = property( get_history, set_history )
    
    def get_user( self ):
        """
        Return the current user if logged in (based on cookie) or `None`.
        """
        if self.__user is NOT_SET:
            id = self.get_cookie( name='universe_user' )
            if not id:
                self.__user = None
            else:
                self.__user = self.app.model.User.get( int( id ) )
        return self.__user
    
    def set_user( self, user ):
        """
        Set the current user to `user` (by setting a cookie).
        """
        if user is None:
            self.set_cookie( name='universe_user', value='' )
        else:
            self.set_cookie( name='universe_user', value=user.id )  
        self.__user = user
    user = property( get_user, set_user )
    
    def get_galaxy_session( self, create=False ):
        # Return the current user's galaxy_session.
        if self.__galaxy_session is NOT_SET:
            id = self.get_cookie( name='universe_session' )
            if not id:
                self.__galaxy_session = None
            else:
                self.__galaxy_session = self.app.model.GalaxySession.get( int( id ) )
        if create is True and self.__galaxy_session is None:
            galaxy_session = self.new_galaxy_session()   
        return self.__galaxy_session
    
    def new_galaxy_session( self ):
        # Create a new galaxy_session, retrieving the user's most recently updated history
        galaxy_session = self.app.model.GalaxySession()
        if self.user is not None:
            galaxy_session.user_id = self.user.id
            h = self.app.model.History
            ht = h.table
            where = ( ht.c.user_id==self.user.id ) & ( ht.c.deleted=='f' )
            history = h.query().filter( where ).order_by( desc( ht.c.update_time ) ).first()
            if history is not None:
                self.history = history
        galaxy_session.remote_host = self.request.remote_host
        galaxy_session.remote_addr = self.request.remote_addr
        try:
            galaxy_session.referer = self.request.headers['Referer']
        except:
            galaxy_session.referer = None
        if self.history is not None:
            galaxy_session.add_history(self.history)
        galaxy_session.flush()
        self.set_cookie( name='universe_session', value=galaxy_session.id )
        self.__galaxy_session = galaxy_session
        return self.__galaxy_session

    def set_galaxy_session( self, galaxy_session ):
        # Set the current galaxy_session by setting the universe_session cookie.
        if galaxy_session is None:
            #TODO we may want to raise an exception here instead of creating a new galaxy_session
            galaxy_session = self.new_galaxy_session()
        else:
            if galaxy_session.user_id is None and self.user is not None:
                galaxy_session.user_id = self.user.id
                galaxy_session.flush()
            self.set_cookie( name='universe_session', value=galaxy_session.id )
            self.__galaxy_session = galaxy_session
            
    def galaxy_session_is_valid( self ):
        # TODO do we want better validation here?
        valid = False
        galaxy_session = self.get_galaxy_session()
        if galaxy_session is not None and galaxy_session.id is not None:
            valid = True
        return valid

    def ensure_valid_galaxy_session( self ):
        if not self.galaxy_session_is_valid():
            self.new_galaxy_session()

    def end_galaxy_session( self ):
        # End the current galaxy_session by expiring the universe_session cookie.
        if self.galaxy_session_is_valid():
            self.set_cookie( name='universe_session', value=self.galaxy_session.id, age=0 )
            self.__galaxy_session = None
    galaxy_session = property( get_galaxy_session, set_galaxy_session )
    
    def make_associations( self ):
        if self.galaxy_session_is_valid():
           if self.galaxy_session.user_id is None and self.user is not None:
                self.galaxy_session.user_id = self.user.id
                self.galaxy_session.flush()
                self.__galaxy_session = self.galaxy_session
        if self.history is not None and self.user is not None:
            self.history.user_id = self.user.id
            self.history.flush()
            self.__history = self.history
                
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
        return self.fill_template( "message.tmpl", type=type, message=message, refresh_frames=refresh_frames )
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
        return self.show_message( message, 'warn', refresh_frames )
    def show_form( self, form ):
        """
        Convenience method for displaying a simple page with a single HTML
        form.
        """    
        return self.fill_template( "form.tmpl", form=form )
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
    def __init__( self, action, title, name="form", submit_text="submit" ):
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
