from galaxy import config, tools, web, util
from galaxy.web.base.controller import BaseController, BaseAPIController
from galaxy.util.bunch import Bunch

class GenomesController( BaseAPIController ):
    """
    RESTful controller for interactions with genome data.
    """
    
    @web.expose_api
    def index( self, trans, **kwds ):
        """
        GET /api/genomes: returns a list of installed genomes
        """        
        
        return []

    @web.json
    def show( self, trans, id, num=None, chrom=None, low=None ):
        """
        GET /api/genomes/{id}
        
        Returns information about build <id>
        """
        return self.app.genomes.chroms( trans, dbkey=id, num=num, chrom=chrom, low=low )