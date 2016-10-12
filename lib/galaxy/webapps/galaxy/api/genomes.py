from galaxy import web
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

    @web.expose_api_raw_anonymous
    def indexes(self, trans, id, **kwd):
        """
        GET /api/genomes/{id}/indexes?type={table name}

        Returns all available indexes for a genome id for type={table name}
        For instance, /api/genomes/hg19/indexes?type=fasta_indexes
        """
        index_extensions = {'fasta_indexes': '.fai'}
        id = get_id( id, kwd.get( 'format', None ) )
        index_type = kwd.get('type', None)

        tbl_entries = self.app.tool_data_tables.data_tables[index_type].data
        index_file_name = [x[-1] for x in tbl_entries if id in x].pop()

        if_open = open(index_file_name + index_extensions[index_type], mode='r')
        return if_open.read()

    @web.expose_api_raw_anonymous
    def sequences(self, trans, id, num=None, chrom=None, low=None, high=None, **kwd ):
        """
        GET /api/genomes/{id}/sequences

        This is a wrapper for accepting sequence requests that
        want a raw return, not json
        """
        id = get_id( id, kwd.get( 'format', None ) )
        reference = is_true( kwd.get( 'reference', False ) )
        assert reference
        region = self.app.genomes.reference( trans, dbkey=id, chrom=chrom, low=low, high=high )
        return region.sequence
