import inspect
import os

from galaxy import eggs
eggs.require( "Cheetah" )
from Cheetah.Template import Template
eggs.require( "Mako" )
import mako.lookup

from galaxy.exceptions import MessageException
from galaxy.util.backports.importlib import import_module
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web.framework import base
from galaxy.web.framework import transaction
from galaxy.web.framework import formbuilder

import logging
log = logging.getLogger( __name__ )


class WebApplication( base.WebApplication ):

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
        return transaction.GalaxyWebTransaction( environ, galaxy_app, self, session_cookie )

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
                except ControllerUnavailable, exc:
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
                except ControllerUnavailable, exc:
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
