"""
Demo sequencer web application framework
"""

import json
import os
import pkg_resources
import random
import socket
import string
import sys
import time

pkg_resources.require( "Cheetah" )
from Cheetah.Template import Template

from galaxy.web.framework import helpers

from galaxy import util
from galaxy.util.json import dumps
from galaxy.util.json import loads
from galaxy.web.framework import url_for
from galaxy.web.framework.decorators import expose
from galaxy.web.framework.decorators import json
from galaxy.web.framework.decorators import json_pretty
from galaxy.web.framework.decorators import require_login
from galaxy.web.framework.decorators import expose_api
from galaxy.web.framework.decorators import error
from galaxy.web.framework.formbuilder import form
from galaxy.web.framework.formbuilder import FormBuilder
from galaxy.web.framework.formbuilder import FormInput
from galaxy.web.framework.formbuilder import FormData
import galaxy.web.framework.base

from galaxy.util.bunch import Bunch
from galaxy.exceptions import MessageException
from galaxy.util import asbool

pkg_resources.require( "Mako" )
import mako.template
import mako.lookup
import mako.runtime

pkg_resources.require( "pexpect" )
pkg_resources.require( "amqp" )

import logging
log = logging.getLogger( __name__ )

class WebApplication( galaxy.web.framework.base.WebApplication ):
    def __init__( self, demo_app, session_cookie='demosequencersession' ):
        galaxy.web.framework.base.WebApplication.__init__( self )
        self.set_transaction_factory( lambda e: self.transaction_chooser( e, demo_app, session_cookie ) )
        # Mako support
        self.mako_template_lookup = mako.lookup.TemplateLookup(
            directories = [ demo_app.config.template_path ] ,
            module_directory = demo_app.config.template_cache,
            collection_size = 500,
            output_encoding = 'utf-8' )
        # Security helper
        self.security = demo_app.security
    def handle_controller_exception( self, e, trans, **kwargs ):
        if isinstance( e, MessageException ):
            return trans.show_message( e.err_msg, e.type )
    def make_body_iterable( self, trans, body ):
        if isinstance( body, FormBuilder ):
            body = trans.show_form( body )
        return galaxy.web.framework.base.WebApplication.make_body_iterable( self, trans, body )
    def transaction_chooser( self, environ, demo_app, session_cookie ):
        if 'is_api_request' in environ:
            return DemoWebAPITransaction( environ, demo_app, self )
        else:
            return DemoWebUITransaction( environ, demo_app, self, session_cookie )

class DemoWebTransaction( galaxy.web.framework.base.DefaultWebTransaction ):
    """
    Encapsulates web transaction specific state for the Demo application
    (specifically the user's "cookie")
    """
    def __init__( self, environ, app, webapp ):
        self.app = app
        self.webapp = webapp
        self.security = webapp.security
        galaxy.web.framework.base.DefaultWebTransaction.__init__( self, environ )
        self.debug = asbool( self.app.config.get( 'debug', False ) )
    def get_cookie( self, name='demosequencersession' ):
        """Convenience method for getting a session cookie"""
        try:
            # If we've changed the cookie during the request return the new value
            if name in self.response.cookies:
                return self.response.cookies[name].value
            else:
                return self.request.cookies[name].value
        except:
            return None
    def set_cookie( self, value, name='demosequencersession', path='/', age=90, version='1' ):
        """Convenience method for setting a session cookie"""
        # The demosequencersession cookie value must be a high entropy 128 bit random number encrypted
        # using a server secret key.  Any other value is invalid and could pose security issues.
        self.response.cookies[name] = value
        self.response.cookies[name]['path'] = path
        self.response.cookies[name]['max-age'] = 3600 * 24 * age # 90 days
        tstamp = time.localtime ( time.time() + 3600 * 24 * age )
        self.response.cookies[name]['expires'] = time.strftime( '%a, %d-%b-%Y %H:%M:%S GMT', tstamp )
        self.response.cookies[name]['version'] = version
    def __update_session_cookie( self, name='galaxysession' ):
        """
        Update the session cookie to match the current session.
        """
        self.set_cookie( self.security.encode_guid( self.galaxy_session.session_key ), name=name, path=self.app.config.cookie_path )
    def get_galaxy_session( self ):
        """
        Return the current galaxy session
        """
        return self.galaxy_session
    @galaxy.web.framework.base.lazy_property
    def template_context( self ):
        return dict()
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

class DemoWebAPITransaction( DemoWebTransaction ):
    def __init__( self, environ, app, webapp ):
        DemoWebTransaction.__init__( self, environ, app, webapp )

class DemoWebUITransaction( DemoWebTransaction ):
    def __init__( self, environ, app, webapp, session_cookie ):
        DemoWebTransaction.__init__( self, environ, app, webapp )
