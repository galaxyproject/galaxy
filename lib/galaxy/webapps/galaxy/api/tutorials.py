"""
API operations on tutorials.
"""
import os

from galaxy import util
from galaxy import exceptions
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController

import logging
log = logging.getLogger( __name__ )

try:
    import yaml
except ImportError:
    log.debug('unable to import yaml')

class TutorialsController( BaseAPIController ):

    def __init__( self, app ):
        super( TutorialsController, self ).__init__( app )

    @expose_api_anonymous_and_sessionless
    def load_config( self, trans, tutorial_config_file, **kwd ):
        """
        load_config( self, trans, tutorial_config_file, **kwd )
        * GET /api/tutorials/{tutorial_config_file}:
            Read a yaml file with intro.js configurations and return it as json

        :returns:   introjs tutorial conf
        :rtype:     dictionary
        """
        return  yaml.load( open( os.path.join(trans.app.config.introduction_tutorials_config_dir, tutorial_config_file ) ) )
