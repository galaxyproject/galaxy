import os, sys, time
import pkg_resources; pkg_resources.require( "Cheetah" )
from Cheetah.Template import Template
import framework
import pickle
from galaxy import util

import pkg_resources
pkg_resources.require( "WebHelpers" )
pkg_resources.require( "PasteDeploy" )

import webhelpers
from paste.deploy.converters import asbool

def expose( func ):
    """
    Decorator: mark a function as 'exposed' and thus web accessible
    """
    func.exposed = True
    return func
    
NOT_SET = object()
    
class UniverseWebTransaction( framework.DefaultWebTransaction ):
    """
    Encapsulates web transaction specific state for the Universe application
    (specifically the user's "cookie" session and history)
    """
    def __init__( self, environ, app ):
        self.app = app
        self.__user = NOT_SET
        self.__history = NOT_SET
        self.__galaxy_session = NOT_SET
        framework.DefaultWebTransaction.__init__( self, environ )
        self.app.model.context.current.clear()
        self.debug = asbool( self.app.config.get( 'debug', False ) )
        
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
        if self.galaxy_session_is_valid():
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
        
    def get_history( self ):
        """
        Load the current history
        """
        if self.__history is NOT_SET:
            history = None
            id = self.get_cookie( name='universe' )
            if id:
                history = self.app.model.History.get( id )
            if history is None:
                history = self.new_history()
            self.__history = history                
        return self.__history
    
    def new_history( self ):
        history = self.app.model.History()
        if history.user_id is None and self.user is not None:
            history.user_id = self.user.id
        if self.galaxy_session_is_valid():
            history.add_galaxy_session(self.get_galaxy_session())
        history.flush()
        self.set_cookie( name='universe', value=history.id )
        self.__history = history
        return history
    
    def set_history( self, history ):
        if history is None:
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
    
    def get_galaxy_session( self ):
        """
        Return the current user's galaxy_session.
        """
        if self.__galaxy_session is NOT_SET:
            id = self.get_cookie( name='universe_session' )
            if not id:
                self.__galaxy_session = None
            else:
                self.__galaxy_session = self.app.model.GalaxySession.get( int( id ) )
        return self.__galaxy_session
    
    def new_galaxy_session( self ):
        galaxy_session = self.app.model.GalaxySession()
        if self.user is not None:
            galaxy_session.user_id = self.user.id
        galaxy_session.remote_host = self.request.remote_host
        galaxy_session.remote_addr = self.request.remote_addr
        if self.history is not None:
            galaxy_session.add_history(self.history)
        galaxy_session.flush()
        self.set_cookie( name='universe_session', value=galaxy_session.id )
        self.__galaxy_session = galaxy_session
        return self.__galaxy_session
    
    def set_galaxy_session( self, galaxy_session ):
        """
        Set the current galaxy_session by setting the universe_session cookie.
        """
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
        a_galaxy_session = self.get_galaxy_session()
        if a_galaxy_session is not None and a_galaxy_session.id is not None:
            valid = True
        return valid
                
    def end_galaxy_session( self ):
        """
        End the current galaxy_session by expiring the universe_session cookie.
        """
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
    @framework.lazy_property
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
    def fill_template(self, file_name, **kwargs):
        """
        Fill in a template, putting any keyword arguments on the context.
        """
        template = Template( file=os.path.join(self.app.config.template_path, file_name), 
                             searchList=[kwargs, self.template_context, dict(caller=self, t=self, h=webhelpers, util=util, request=self.request, response=self.response, app=self.app)] )
        return str(template)
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
