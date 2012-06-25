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
        genomes = dict()
        if trans.app.config.get_bool( 'enable_beta_job_managers', False ) == False:
            return trans.fill_template( '/admin/data_admin/betajob.mako' )
        for line in trans.app.tool_data_tables.data_tables[ 'all_fasta' ].data:
            indexers = dict( bowtie_indexes='Generate', bowtie2_indexes='Generate', bwa_indexes='Generate', perm_base_indexes='Generate', srma_indexes='Generate', sam_fa_indexes='Generate' )
            dbkey = line[0]
            name = line[2]
            indexers[ 'name' ] = name
            indexers[ 'fapath' ] = line[3]
            genomes[ dbkey ] = indexers
        for table in [ 'bowtie_indexes', 'bowtie2_indexes', 'bwa_indexes', 'srma_indexes' ]:
            for line in trans.app.tool_data_tables.data_tables[ table ].data:
                dbkey = line[0]
                genomes[ dbkey ][ table ] = 'Generated'
        for line in trans.app.tool_data_tables.data_tables[ 'sam_fa_indexes' ].data:
            genomes[ line[1] ][ 'sam_fa_indexes' ] = 'Generated'
        for line in trans.app.tool_data_tables.data_tables[ 'perm_base_indexes' ].data:
            genomes[ line[1].split(':')[0] ][ 'perm_base_indexes' ] = 'Generated'
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
        return trans.fill_template( '/admin/data_admin/local_data.mako', jobgrid=jobgrid, genomes=genomes )
    
    @web.expose
    @web.require_admin
    def add_genome( self, trans, **kwd ):
        if trans.app.config.get_bool( 'enable_beta_job_managers', False ) == False:
            return trans.fill_template( '/admin/data_admin/betajob.mako' )
        dbkeys = trans.ucsc_builds
        ensemblkeys = trans.ensembl_builds
        return trans.fill_template( '/admin/data_admin/data_form.mako', dbkeys=dbkeys, ensembls=ensemblkeys )
        
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
            dbkey = params.get('ncbi_dbkey', '')[0]
            url = 'http://togows.dbcls.jp/entry/ncbi-nucleotide/%s.fasta' % dbkey
        elif source == 'Broad':
            dbkey = params.get('broad_dbkey', '')[0]
            url = 'ftp://ftp.broadinstitute.org/pub/seq/references/%s.fasta' % dbkey
        elif source == 'UCSC':
            longname = None
            for build in trans.ucsc_builds:
                if dbkey == build[0]:
                    dbkey = build[0]
                    longname = build[1]
                    break       
            assert dbkey is not '?', 'That build was not found'
            ftp = ftplib.FTP('hgdownload.cse.ucsc.edu')
            ftp.login('anonymous', trans.get_user().email)
            checker = []
            liftover = []
            newlift = []
            try:
                ftp.retrlines('NLST /goldenPath/%s/liftOver/*.chain.gz' % dbkey, liftover.append)
                for chain in liftover:
                    fname = chain.split( '/' )[-1]
                    target = fname.replace( '.over.chain.gz', '' ).split( 'To' )[1]
                    target = target[0].lower() + target[1:]
                    if not os.path.exists( os.path.join( trans.app.config.get( 'genome_data_path', 'tool-data/genome' ), dbkey, 'liftOver', fname ) ):
                        newlift.append( [ chain, dbkey, target ] )
                    current = dbkey[0].upper() + dbkey[1:]
                    targetfile = '%sTo%s.over.chain.gz' % ( target, current )
                    if not os.path.exists( os.path.join( trans.app.config.get( 'genome_data_path', 'tool-data/genome' ), target, 'liftOver', targetfile ) ):
                        newlift.append( [ '/goldenPath/%s/liftOver/%s' % ( target, targetfile ), target, dbkey ] )
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
                message = u'The genome %s was not found on the UCSC server.' % dbkey
                status = u'error'
                return trans.fill_template( '/admin/data_admin/data_form.mako',
                                            message=message,
                                            status=status,
                                            ensembls=trans.ensembl_builds,
                                            dbkeys=trans.ucsc_builds )
        elif source == 'Ensembl':
            dbkey = params.get( 'ensembl_dbkey', None )
            assert dbkey is not '?', 'That build was not found'
            for build in trans.ensembl_builds:
                if build[ 'dbkey' ] == dbkey:
                    dbkey = build[ 'dbkey' ]
                    release = build[ 'release' ]
                    pathname = '_'.join( build[ 'name' ].split(' ')[0:2] )
                    longname = build[ 'name' ].replace('_', ' ')
                    break
            url = 'ftp://ftp.ensembl.org/pub/release-%s/fasta/%s/dna/%s.%s.%s.dna.toplevel.fa.gz' % ( release, pathname.lower(), pathname, dbkey, release )
            log.debug( build )
            log.debug( url )
        else:
            raise ValueError, 'Somehow an invalid data source was specified.'
        params = dict( protocol='http', name=dbkey, datatype='fasta', url=url, user=trans.user.id )
        jobid = trans.app.job_manager.deferred_job_queue.plugins['GenomeTransferPlugin'].create_job( trans, url, dbkey, longname, indexers )
        chainjob = []
        if newlift is not None:
            for chain in newlift:
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
        gname = params.get( 'intname', '' )
        deferred = trans.app.model.context.current.query( model.DeferredJob ).filter_by( id=jobid ).first()
        gname = deferred.params[ 'intname' ]
        indexers = ', '.join( deferred.params[ 'indexes' ] )
        jobs = self._get_jobs( jobid, trans )
        jsonjobs = json.dumps( jobs )
        return trans.fill_template( '/admin/data_admin/download_status.mako', name=gname, indexers=indexers, mainjob=jobid, jobs=jobs, jsonjobs=jsonjobs )
        
    @web.expose
    @web.require_admin
    def get_jobs( self, trans, **kwd ):
        sa_session = trans.app.model.context.current
        jobs = []
        params = util.Params( kwd )
        jobid = params.get( 'jobid', '' )
        jobs = self._get_jobs( jobid, trans )
        return trans.fill_template( '/admin/data_admin/ajax_status.mako', json=json.dumps( jobs ) )
        
    def _get_job( self, jobid, jobtype, trans ):
        sa = trans.app.model.context.current
        if jobtype == 'liftover':
            job = sa.query( model.TransferJob ).filter_by( id=jobid ).first()
            joblabel = 'Download liftOver'
        elif jobtype == 'transfer':
            job = sa.query( model.TransferJob ).filter_by( id=jobid ).first()
            joblabel = 'Download Genome'
        elif jobtype == 'deferred':
            job = sa.query( model.DeferredJob ).filter_by( id=jobid ).first()
            joblabel = 'Main Controller'
        elif jobtype == 'index':
            job = sa.query( model.Job ).filter_by( id=jobid ).first()
            joblabel = 'Index Genome'
        return dict( status=job.state, jobid=job.id, style=self.jobstyles[job.state], type=jobtype, label=joblabel )
        
    def _get_jobs( self, jobid, trans ):
        jobs = []
        job = trans.app.job_manager.deferred_job_queue.plugins['GenomeTransferPlugin'].get_job_status( jobid )
        sa_session = trans.app.model.context.current
        jobs.append( self._get_job( job.id, 'deferred', trans ) )
        if hasattr( job, 'transfer_job' ): # This is a transfer job, check for indexers
            jobs.append( self._get_job( job.transfer_job.id, 'transfer', trans ) )
            idxjobs = sa_session.query( model.GenomeIndexToolData ).filter_by( deferred_job_id=job.id, transfer_job_id=job.transfer_job.id ).all()
            if job.params.has_key( 'liftover' ) and job.params[ 'liftover' ] is not None:
                for jobid in job.params[ 'liftover' ]:
                    jobs.append( self._get_job( jobid, 'liftover', trans ) )
            for idxjob in idxjobs:
                jobs.append( self._get_job( idxjob.job_id, 'index', trans ) )
        return jobs
