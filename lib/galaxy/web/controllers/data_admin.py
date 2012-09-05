import sys, ftplib, json
from galaxy import model, util
from galaxy.jobs import transfer_manager
from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from library_common import get_comptypes, lucene_search, whoosh_search

# Older py compatibility
try:
    set()
except:
    from sets import Set as set

import logging
log = logging.getLogger( __name__ )

class DataAdmin( BaseUIController ): 
    jobstyles = dict( 
                     done='panel-done-message',
                     waiting='state-color-waiting',
                     running='state-color-running',
                     downloaded='state-color-running',
                     new='state-color-new',
                     ok='panel-done-message',
                     error='panel-error-message',
                     queued='state-color-waiting'
                    )
    
    @web.expose
    @web.require_admin
    def manage_data( self, trans, **kwd ):
        if trans.app.config.get_bool( 'enable_beta_job_managers', False ) == False:
            return trans.fill_template( '/admin/data_admin/generic_error.mako', message='This feature requires that enable_beta_job_managers be set to True in your Galaxy configuration.' )
        if 'all_fasta' not in trans.app.tool_data_tables.data_tables:
            return trans.fill_template( '/admin/data_admin/generic_error.mako', message='The local data manager requires that an all_fasta entry exists in your tool_data_table_conf.xml.' )
        indextable = {}
        dbkeys = []
        labels = { 'bowtie_indexes': 'Bowtie', 'bowtie2_indexes': 'Bowtie 2', 'bwa_indexes': 'BWA', 'srma_indexes': 'Picard', 'sam_fa_indexes': 'SAM', 'perm_base_indexes': 'PerM' }
        tablenames = { 'Bowtie': 'bowtie_indexes', 'Bowtie 2': 'bowtie2_indexes', 'BWA': 'bwa_indexes', 'Picard': 'srma_indexes', 'SAM': 'sam_fa_indexes', 'PerM': 'perm_base_indexes' }
        indexfuncs = dict( bowtie_indexes='bowtie', bowtie2_indexes='bowtie2', bwa_indexes='bwa', srma_indexes='picard', sam_fa_indexes='sam', perm_base_indexes='perm' )
        for genome in trans.app.tool_data_tables.data_tables[ 'all_fasta' ].data:
            dbkey = genome[0]
            dbkeys.append( dbkey )
            indextable[ dbkey ] = dict( indexes=dict(), name=genome[2], path=genome[3] )
        for genome in indextable:
            for label in labels:
                indextable[ genome ][ 'indexes' ][ label ] = 'Generate'
                if label not in trans.app.tool_data_tables.data_tables:
                    indextable[ genome ][ 'indexes' ][ label ] = 'Disabled'
                else:
                    for row in trans.app.tool_data_tables.data_tables[ label ].data:
                        if genome in row or row[0].startswith( genome ):
                            indextable[ genome ][ 'indexes' ][ label ] = 'Generated'
        jobgrid = []
        sa_session = trans.app.model.context.current
        jobs = sa_session.query( model.GenomeIndexToolData ).order_by( model.GenomeIndexToolData.created_time.desc() ).filter_by( user_id=trans.get_user().id ).group_by( model.GenomeIndexToolData.deferred ).limit( 20 ).all()
        prevjobid = 0
        for job in jobs:
            if prevjobid == job.deferred.id:
                continue
            prevjobid = job.deferred.id
            state = job.deferred.state
            params = job.deferred.params
            if job.transfer is not None:
                jobtype = 'download'
            else:
                jobtype = 'index'
            indexers = ', '.join( params['indexes'] )
            jobgrid.append( dict( jobtype=jobtype, indexers=indexers, rowclass=state, deferred=job.deferred.id, state=state, intname=job.deferred.params[ 'intname' ], dbkey=job.deferred.params[ 'dbkey' ] ) )
        styles = dict( Generate=self.jobstyles['new'], Generated=self.jobstyles['ok'], Disabled=self.jobstyles['error'] )
        return trans.fill_template( '/admin/data_admin/local_data.mako', jobgrid=jobgrid, indextable=indextable, labels=labels, dbkeys=dbkeys, styles=styles, indexfuncs=indexfuncs )
    
    @web.expose
    @web.require_admin
    def add_genome( self, trans, **kwd ):
        if trans.app.config.get_bool( 'enable_beta_job_managers', False ) == False:
            return trans.fill_template( '/admin/data_admin/generic_error.mako', message='This feature requires that enable_beta_job_managers be set to True in your Galaxy configuration.' )
        dbkeys = trans.ucsc_builds
        ensemblkeys = trans.ensembl_builds
        ncbikeys = trans.ncbi_builds
        return trans.fill_template( '/admin/data_admin/data_form.mako', dbkeys=dbkeys, ensembls=ensemblkeys, ncbi=ncbikeys )
        
    @web.expose
    @web.require_admin
    def genome_search( self, trans, **kwd ):
        results = list()
        ncbikeys = trans.ncbi_builds
        params = util.Params( kwd )
        search = params.get( 'q', None )
        limit = params.get( 'limit', None )
        if search is not None:
            query = search.lower()
            for row in ncbikeys:
                if query in row[ 'name' ].lower() or query in row[ 'dbkey' ].lower():
                    result = '|'.join( [ ': '.join( [ row[ 'dbkey' ], row[ 'name' ] ] ), row[ 'dbkey' ] ] )
                    results.append( result )
                    if len( results ) >= limit:
                        break
        return trans.fill_template( '/admin/data_admin/ajax_status.mako', json='\n'.join( results ) )

    @web.expose
    @web.require_admin
    def index_build( self, trans, **kwd ):
    	"""Index a previously downloaded genome."""
        params = util.Params( kwd )
        path = os.path.abspath( params.get( 'path', None ) )
        indexes = [ params.get( 'indexes', None ) ]
        dbkey = params.get( 'dbkey', None )
        intname = params.get( 'longname', None )
    	indexjob = trans.app.job_manager.deferred_job_queue.plugins['GenomeIndexPlugin'].create_job( trans, path, indexes, dbkey, intname )
    	return indexjob
    	
    @web.expose
    @web.require_admin
    def download_build( self, trans, **kwd ):
        """Download a genome from a remote source and add it to the library."""
        params = util.Params( kwd )
        paramdict = build_param_dict( params, trans )
        if paramdict[ 'status' ] == 'error':
            return trans.fill_template( '/admin/data_admin/generic_error.mako', message=paramdict[ 'message' ] )
        url = paramdict[ 'url' ]
        liftover = paramdict[ 'liftover' ]
        dbkey = paramdict[ 'dbkey' ]
        indexers = paramdict[ 'indexers' ]
        longname = paramdict[ 'longname' ]
        dbkeys = dict()
        protocol = 'http'
        if url is None:
            return trans.fill_template( '/admin/data_admin/generic_error.mako', message='Unable to generate a valid URL with the specified parameters.' )
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
            trans.app.model.context.current.add( job )
            trans.app.model.context.current.flush()
        return trans.response.send_redirect( web.url_for( controller='data_admin',
                                                          action='monitor_status',
                                                          job=jobid ) )
        
    @web.expose
    @web.require_admin
    def monitor_status( self, trans, **kwd ):
        params = util.Params( kwd )
        jobid = params.get( 'job', '' )
        deferred = trans.app.model.context.current.query( model.DeferredJob ).filter_by( id=jobid ).first()
        if deferred is None: 
            return trans.fill_template( '/admin/data_admin/generic_error.mako', message='Invalid genome downloader job specified.' )
        gname = deferred.params[ 'intname' ]
        indexers = ', '.join( deferred.params[ 'indexes' ] )
        jobs = self._get_jobs( deferred, trans )
        jsonjobs = json.dumps( jobs )
        return trans.fill_template( '/admin/data_admin/download_status.mako', name=gname, indexers=indexers, mainjob=jobid, jobs=jobs, jsonjobs=jsonjobs )
        
    @web.expose
    @web.require_admin
    def get_jobs( self, trans, **kwd ):
        sa_session = trans.app.model.context.current
        jobs = []
        params = util.Params( kwd )
        jobid = params.get( 'jobid', '' )
        job = sa_session.query( model.DeferredJob ).filter_by( id=jobid ).first()
        jobs = self._get_jobs( job, trans )
        return trans.fill_template( '/admin/data_admin/ajax_status.mako', json=json.dumps( jobs ) )
        
    def _get_job( self, jobid, jobtype, trans ):
        sa = trans.app.model.context.current
        if jobtype == 'liftover':
            liftoverjob = sa.query( model.DeferredJob ).filter_by( id=jobid ).first()
            job = sa.query( model.TransferJob ).filter_by( id=liftoverjob.params[ 'transfer_job_id' ] ).first()
            joblabel = 'Download liftOver (%s to %s)' % ( liftoverjob.params[ 'from_genome' ], liftoverjob.params[ 'to_genome' ] )
        elif jobtype == 'transfer':
            job = sa.query( model.TransferJob ).filter_by( id=jobid ).first()
            joblabel = 'Download Genome'
        elif jobtype == 'deferred':
            job = sa.query( model.DeferredJob ).filter_by( id=jobid ).first()
            joblabel = 'Main Controller'
        elif jobtype == 'index':
            job = sa.query( model.Job ).filter_by( id=jobid.job_id ).first()
            joblabel = 'Index Genome (%s)' % jobid.indexer
        return dict( status=job.state, jobid=job.id, style=self.jobstyles[job.state], type=jobtype, label=joblabel )
        
    def _get_jobs( self, deferredjob, trans ):
        jobs = []
        idxjobs = []
        sa_session = trans.app.model.context.current
        job = sa_session.query( model.GenomeIndexToolData ).filter_by( deferred=deferredjob ).first()
        jobs.append( self._get_job( deferredjob.id, 'deferred', trans ) )
        if 'transfer_job_id' in deferredjob.params: #hasattr( job, 'transfer' ) and job.transfer is not None: # This is a transfer job, check for indexers
            jobs.append( self._get_job( deferredjob.params[ 'transfer_job_id' ], 'transfer', trans ) )
        if hasattr( job, 'deferred' ):
            idxjobs = sa_session.query( model.GenomeIndexToolData ).filter_by( deferred=job.deferred, transfer=job.transfer ).all()
        if deferredjob.params.has_key( 'liftover' ) and deferredjob.params[ 'liftover' ] is not None:
            for jobid in deferredjob.params[ 'liftover' ]:
                jobs.append( self._get_job( jobid, 'liftover', trans ) )
        for idxjob in idxjobs:
            jobs.append( self._get_job( idxjob, 'index', trans ) )
        return jobs

def build_param_dict( params, trans ):
    
    source = params.get('source', '')
    longname = params.get('longname', None)
    if not isinstance( params.get( 'indexers', None ), list ):
        indexers = [ params.get( 'indexers', None ) ]
    else:
        indexers = params.get( 'indexers', None )
    if indexers is not None:
        if indexers == [None]:
            indexers = None
    url = None
    liftover = None
    newlift = []
    dbkey = params.get( 'dbkey', None )
    dbkeys = dict()
    protocol = 'http'
    
    if source == 'NCBI':
        build = params.get('ncbi_name', '')
        dbkey = build.split( ': ' )[0]
        longname = build.split( ': ' )[-1]
        url = 'http://togows.dbcls.jp/entry/ncbi-nucleotide/%s.fasta' % dbkey
    elif source == 'URL':
        dbkey = params.get( 'url_dbkey', '' )
        url = params.get( 'url', None )
        longname = params.get( 'longname', None )
    elif source == 'UCSC':
        longname = None
        for build in trans.ucsc_builds:
            if dbkey == build[0]:
                dbkey = build[0]
                longname = build[1]
                break       
        if dbkey == '?':
            return dict( status='error', message='An invalid build was specified.' )
        ftp = ftplib.FTP('hgdownload.cse.ucsc.edu')
        ftp.login('anonymous', trans.get_user().email)
        checker = []
        liftover = []
        newlift = []
        ftp.retrlines('NLST /goldenPath/%s/liftOver/*.chain.gz' % dbkey, liftover.append)
        try:
            for chain in liftover:
                lifts = []
                fname = chain.split( '/' )[-1]
                organisms = fname.replace( '.over.chain.gz', '' ).split( 'To' )
                lifts.append( [ organisms[0], organisms[1][0].lower() + organisms[1][1:] ] )
                lifts.append( [ organisms[1][0].lower() + organisms[1][1:], organisms[0] ] )
                for organism in lifts:
                    remotepath = '/goldenPath/%s/liftOver/%sTo%s.over.chain.gz' % ( organism[0], organism[0], organism[1][0].upper() + organism[1][1:] )
                    localfile = '%sTo%s.over.chain' % ( organism[0], organism[1][0].upper() + organism[1][1:] )
                    localpath = os.path.join( trans.app.config.get( 'genome_data_path', 'tool-data/genome' ), organism[0], 'liftOver', localfile )
                    if not os.path.exists( localpath ) or os.path.getsize( localpath ) == 0:
                        newlift.append( [ remotepath, organism[0], organism[1] ] )
        except:
            newlift = None
            pass
        ftp.retrlines('NLST /goldenPath/%s/bigZips/' % dbkey, checker.append)
        ftp.quit()
        for filename in [ dbkey, 'chromFa' ]:
            for extension in [ '.tar.gz', '.tar.bz2', '.zip', '.fa.gz', '.fa.bz2' ]:
                testfile = '/goldenPath/%s/bigZips/%s%s' % ( dbkey, filename, extension )
                if testfile in checker:
                    url = 'ftp://hgdownload.cse.ucsc.edu%s' % testfile
                    break;
                else:
                    continue
        if url is None:
            message = 'The genome %s was not found on the UCSC server.' % dbkey
            status = 'error'
            return dict( status=status, message=message )
            
    elif source == 'Ensembl':
        dbkey = params.get( 'ensembl_dbkey', None )
        if dbkey == '?':
            return dict( status='error', message='An invalid build was specified.' )
        for build in trans.ensembl_builds:
            if build[ 'dbkey' ] == dbkey:
                dbkey = build[ 'dbkey' ]
                release = build[ 'release' ]
                pathname = '_'.join( build[ 'name' ].split(' ')[0:2] )
                longname = build[ 'name' ].replace('_', ' ')
                break
        url = 'ftp://ftp.ensembl.org/pub/release-%s/fasta/%s/dna/%s.%s.%s.dna.toplevel.fa.gz' % ( release, pathname.lower(), pathname, dbkey, release )
        
    params = dict( status='ok', dbkey=dbkey, datatype='fasta', url=url, user=trans.user.id, liftover=newlift, longname=longname, indexers=indexers )

    return params