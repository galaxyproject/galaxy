from galaxy import web, util
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.framework.helpers import is_true

def get_id( base, format ):
    if format:
        return "%s.%s" % ( base, format )
    else:
        return base

class GenomesController( BaseAPIController ):
    """
    RESTful controller for interactions with genome data.
    """

    @web.expose_api_anonymous
    def index( self, trans, **kwd ):
        """
        GET /api/genomes: returns a list of installed genomes
        """

        return self.app.genomes.get_dbkeys( trans, **kwd )

    @web.json
    def show( self, trans, id, num=None, chrom=None, low=None, high=None, **kwd ):
        """
        GET /api/genomes/{id}

        Returns information about build <id>
        """

        # Process kwds.
        id = get_id( id, kwd.get( 'format', None ) )
        reference = is_true( kwd.get( 'reference', False ) )

        # Return info.
        rval = None
        if reference:
            region = self.app.genomes.reference( trans, dbkey=id, chrom=chrom, low=low, high=high )
            rval = { 'dataset_type': 'refseq', 'data': region.sequence }
        else:
            rval = self.app.genomes.chroms( trans, dbkey=id, num=num, chrom=chrom, low=low )
        return rval
