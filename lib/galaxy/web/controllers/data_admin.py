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
            return trans.fill_template( '/admin/data_admin/betajob.mako' )
        dbkeys = trans.db_builds
        return trans.fill_template( '/admin/data_admin/data_form.mako', dbkeys=dbkeys )
        
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
            dbkey = params.get('dbkey', '')[0]
            url = 'http://togows.dbcls.jp/entry/ncbi-nucleotide/%s.fasta' % dbkey
        elif source == 'Broad':
            dbkey = params.get('dbkey', '')[0]
            url = 'ftp://ftp.broadinstitute.org/pub/seq/references/%s.fasta' % dbkey
        elif source == 'UCSC':
            longname = None
            for build in trans.db_builds:
                if dbkey[1] == build[0]:
                    dbkey = build[0]
                    longname = build[1]
                    break       
            assert dbkey is not '?', 'That build was not found'
            ftp = ftplib.FTP('hgdownload.cse.ucsc.edu')
            ftp.login('anonymous', 'user@example.com')
            checker = []
            liftover = []
            newlift = []
            try:
                ftp.retrlines('NLST /goldenPath/%s/liftOver/*.chain.gz' % dbkey, liftover.append)
                for chain in liftover:
                    fname = chain.split( '/' )[-1]
                    target = fname.replace( '.over.chain.gz', '' ).split( 'To' )[1]
                    target = target[0].lower() + target[1:]
                    newlift.append( [ chain, dbkey, target ] )
                    current = dbkey[0].upper() + dbkey[1:]
                    targetfile = '%sTo%s.over.chain.gz' % ( target, current )
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
                                            status=status )
        elif source == 'Ensembl':
            section = params.get('ensembl_section', '')
            release1 = params.get('release_number', '')
            organism = params.get('organism', '')
            name = params.get('name', '')
            longname = organism
            dbkey = name
            release2 = params.get('release2', '')
            release2 = ".%s" % release2 if release2 else ""
            if section == 'standard':
                url = 'ftp://ftp.ensembl.org/pub/release-%s/fasta/%s/dna/%s.%s%s.dna.toplevel.fa.gz' % \
                    (release1, organism.lower(), organism, name, release2)
            else:
                url = 'ftp://ftp.ensemblgenomes.org/pub/%s/release-%s/fasta/%s/dna/%s.%s%s.dna.toplevel.fa.gz' % \
                    (section, release1, organism.lower(), organism, name, release2)
        elif source == 'local':
            url = 'http://127.0.0.1/%s.tar.gz' % dbkey
        else:
            raise ValueError
        params = dict( protocol='http', name=dbkey, datatype='fasta', url=url, user=trans.user.id )
        jobid = trans.app.job_manager.deferred_job_queue.plugins['GenomeTransferPlugin'].create_job( trans, url, dbkey, longname, indexers )
        chainjob = []
        if newlift is not None:
            for chain in newlift:
                liftover_url = u'ftp://hgdownload.cse.ucsc.edu%s'  % chain[0]
                from_genome = chain[1]
                to_genome = chain[2]
                destfile = liftover_url.split('/')[-1].replace('.gz', '')
                chainjob.append( trans.app.job_manager.deferred_job_queue.plugins['LiftOverTransferPlugin'].create_job( trans, liftover_url, dbkey, from_genome, to_genome, destfile, jobid ) )
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
        jobs = self._get_jobs( jobid, trans )
        jsonjobs = json.dumps( jobs )
        return trans.fill_template( '/admin/data_admin/download_status.mako', mainjob=jobid, jobs=jobs, jsonjobs=jsonjobs )
        
    @web.expose
    @web.require_admin
    def get_jobs( self, trans, **kwd ):
        sa_session = trans.app.model.context.current
        jobs = []
        params = util.Params( kwd )
        jobid = params.get( 'jobid', '' )
        jobs = self._get_jobs( jobid, trans )
        return trans.fill_template( '/admin/data_admin/ajax_status.mako', json=json.dumps( jobs ) )
        
    @web.expose
    @web.require_admin
    def job_status( self, trans, **kwd ):
        params = util.Params( kwd )
        jobid = params.get( 'jobid', None )
        jobtype = params.get( 'jobtype', None )
        fillvals = None
        fillvals = self._get_job( jobid, jobtype, trans )
        return trans.fill_template( '/admin/data_admin/ajax_status.mako', json=json.dumps( fillvals ) )
        
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
        jobs.append( self._get_job( job.transfer_job.id, 'transfer', trans ) )
        idxjobs = sa_session.query( model.GenomeIndexToolData ).filter_by( deferred_job_id=job.id, transfer_job_id=job.transfer_job.id ).all()
        if job.params.has_key( 'liftover' ):
            for jobid in job.params[ 'liftover' ]:
                jobs.append( self._get_job( jobid, 'liftover', trans ) )
        for idxjob in idxjobs:
            #print idxjob
            jobs.append( self._get_job( idxjob.job_id, 'index', trans ) )
        return jobs
