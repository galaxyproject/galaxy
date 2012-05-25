from galaxy import web
from galaxy.web.base.controller import BaseController, BaseAPIController

class VisualizationsController( BaseAPIController ):
    """
    RESTful controller for interactions with visualizations.
    """
    
    @web.expose_api
    def index( self, trans, **kwds ):
        """
        GET /api/visualizations: 
        """
        pass
        
    @web.json
    def show( self, trans, id, **kwd ):
        """
        GET /api/visualizations/{viz_id}
        """
        pass
        
    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/visualizations
        """
        pass