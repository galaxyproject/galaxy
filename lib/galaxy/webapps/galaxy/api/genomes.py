from galaxy import config, tools, web, util
from galaxy.web.base.controller import BaseController, BaseAPIController
from galaxy.util.bunch import Bunch
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
    
    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/genomes: returns a list of installed genomes
        """        
        
        return self.app.genomes.get_dbkeys( trans )

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
            rval = self.app.genomes.reference( trans, dbkey=id, chrom=chrom, low=low, high=high )
        else:
            rval = self.app.genomes.chroms( trans, dbkey=id, num=num, chrom=chrom, low=low )
        return rval
    
    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/genomes
        Download and/or index a genome.
        
        Parameters::
        
            dbkey           DB key of the build to download, ignored unless 'UCSC' is specified as the source
            ncbi_name       NCBI's genome identifier, ignored unless NCBI is specified as the source
            ensembl_dbkey   Ensembl's genome identifier, ignored unless Ensembl is specified as the source
            url_dbkey       DB key to use for this build, ignored unless URL is specified as the source
            source          Data source for this build. Can be: UCSC, Ensembl, NCBI, URL
            indexers        POST array of indexers to run after downloading (indexers[] = first, indexers[] = second, ...)
            func            Allowed values:
                            'download'  Download and index
                            'index'     Index only

        Returns::
        
            If no error:
            dict( status: 'ok', job: <job ID> )
        
            If error:
            dict( status: 'error', error: <error message> )
        
        """
        params = util.Params( payload )
        from galaxy.web.controllers.data_admin import build_param_dict as massage
        paramdict = massage( params, trans )
        func = params.get( 'func', 'download' )
        if func == 'download':
            url = paramdict[ 'url' ]
            liftover = paramdict[ 'liftover' ]
            dbkey = paramdict[ 'dbkey' ]
            indexers = paramdict[ 'indexers' ]
            longname = paramdict[ 'longname' ]
            jobid = trans.app.job_manager.deferred_job_queue.plugins['GenomeTransferPlugin'].create_job( trans, url, dbkey, longname, indexers )
            chainjob = []
            if liftover is not None:
                for chain in liftover:
                    liftover_url = u'ftp://hgdownload.cse.ucsc.edu%s' % chain[0]
                    from_genome = chain[1]
                    to_genome = chain[2]
                    destfile = liftover_url.split('/')[-1].replace('.gz', '')
                    lochain = trans.app.job_manager.deferred_job_queue.plugins['LiftOverTransferPlugin'].create_job( trans, liftover_url, dbkey, from_genome, to_genome, destfile, jobid )
                    chainjob.append( lochain )
                job = trans.app.job_manager.deferred_job_queue.plugins['GenomeTransferPlugin'].get_job_status( jobid )
                job.params['liftover'] = chainjob
                trans.app.model.context.current.flush()
            return dict( status='ok', job=jobid )
        elif func == 'index':
            dbkey = paramdict[ 'dbkey' ]
            indexer = [ params.get( 'indexer', None ) ]
            longname = None
            path = None
            for build in trans.app.tool_data_tables.data_tables[ 'all_fasta' ].data:
                if build[0] == dbkey:
                    longname = build[2]
                    path = build[3]
                    break
            if longname is not None and indexer is not None and path is not None:
                jobid = trans.app.job_manager.deferred_job_queue.plugins['GenomeIndexPlugin'].create_job( trans, path, indexer, dbkey, longname )
                return dict( status='ok', job=jobid )
            else:
                return dict( status='error', error='Build not %s found in tool data table.' % dbkey )
        else:
            return dict( status='error', error='Unkown function selected.' )
