import os, logging, threading, time
from Queue import Queue, Empty

from galaxy import model
from galaxy.jobs.runners import BaseJobRunner

from paste.deploy.converters import asbool

import pkg_resources

egg_message = """

The 'sge' runner depends on 'DRMAA_python' which is not installed.  Galaxy's
"scramble" system should make this installation simple, please follow the
instructions found at:

  http://wiki.g2.bx.psu.edu/Admin/Config/Performance/Cluster

Additional errors may follow:
%s
"""


try:
    pkg_resources.require( "DRMAA_python" )
    import DRMAA
except Exception, e:
    raise Exception( egg_message % str( e ) )


log = logging.getLogger( __name__ )

__all__ = [ 'SGEJobRunner' ]

DRMAA_state = {
    DRMAA.Session.UNDETERMINED: 'process status cannot be determined',
    DRMAA.Session.QUEUED_ACTIVE: 'job is queued and waiting to be scheduled',
    DRMAA.Session.SYSTEM_ON_HOLD: 'job is queued and in system hold',
    DRMAA.Session.USER_ON_HOLD: 'job is queued and in user hold',
    DRMAA.Session.USER_SYSTEM_ON_HOLD: 'job is queued and in user and system hold',
    DRMAA.Session.RUNNING: 'job is running',
    DRMAA.Session.SYSTEM_SUSPENDED: 'job is system suspended',
    DRMAA.Session.USER_SUSPENDED: 'job is user suspended',
    DRMAA.Session.DONE: 'job finished normally',
    DRMAA.Session.FAILED: 'job finished, but failed',
}

sge_template = """#!/bin/sh
#$ -S /bin/sh
GALAXY_LIB="%s"
if [ "$GALAXY_LIB" != "None" ]; then
    if [ -n "$PYTHONPATH" ]; then
        PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
    else
        PYTHONPATH="$GALAXY_LIB"
    fi
    export PYTHONPATH
fi
cd %s
%s
"""

class SGEJobState( object ):
    def __init__( self ):
        """
        Encapsulates state related to a job that is being run via SGE and 
        that we need to monitor.
        """
        self.job_wrapper = None
        self.job_id = None
        self.old_state = None
        self.running = False
        self.job_file = None
        self.ofile = None
        self.efile = None
        self.runner_url = None

class SGEJobRunner( BaseJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Initialize this job runner and start the monitor thread"""
        self.app = app
        self.sa_session = app.model.context
        # 'watched' and 'queue' are both used to keep track of jobs to watch.
        # 'queue' is used to add new watched jobs, and can be called from
        # any thread (usually by the 'queue_job' method). 'watched' must only
        # be modified by the monitor thread, which will move items from 'queue'
        # to 'watched' and then manage the watched jobs.
        self.watched = []
        self.monitor_queue = Queue()
        self.default_cell = self.determine_sge_cell( self.app.config.default_cluster_job_runner )
        self.ds = DRMAA.Session()
        self.ds.init( self.default_cell )
        self.monitor_thread = threading.Thread( target=self.monitor )
        self.monitor_thread.start()
        self.work_queue = Queue()
        self.work_threads = []
        nworkers = app.config.cluster_job_queue_workers
        for i in range( nworkers ):
            worker = threading.Thread( target=self.run_next )
            worker.start()
            self.work_threads.append( worker )
        log.debug( "%d workers ready" % nworkers )

    def determine_sge_cell( self, url ):
        """Determine what SGE cell we are using"""
        url_split = url.split("/")
        if url_split[0] == 'sge:':
            return url_split[2]
        # this could happen if sge is started, but is not the default runner
        else:
            return ''

    def determine_sge_queue( self, url ):
        """Determine what SGE queue we are submitting to"""
        try:
            return url.split('/')[3] or None
        except:
            return None

    def determine_sge_project( self, url ):
        """Determine what SGE project we are submitting to"""
        try:
            return url.split('/')[4] or None
        except:
            return None

    def determine_sge_tool_parameters( self, url ):
        """Determine what are the tool's specific paramters"""
        try:
            return url.split('/')[5] or None
        except:
            return None

    def run_next( self ):
        """
        Run the next item in the queue (a job waiting to run or finish )
        """
        while 1:
            ( op, obj ) = self.work_queue.get()
            if op is self.STOP_SIGNAL:
                return
            try:
                if op == 'queue':
                    self.queue_job( obj )
                elif op == 'finish':
                    self.finish_job( obj )
                elif op == 'fail':
                    self.fail_job( obj )
            except:
                log.exception( "Uncaught exception %sing job" % op )

    def queue_job( self, job_wrapper ):
        """Create SGE script for a job and submit it to the SGE queue"""

        try:
            job_wrapper.prepare()
            command_line = self.build_command_line( job_wrapper, include_metadata = True )
        except:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        runner_url = job_wrapper.get_job_runner()
        
        # This is silly, why would we queue a job with no command line?
        if not command_line:
            job_wrapper.finish( '', '' )
            return
        
        # Check for deletion before we change state
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "Job %s deleted by user before it entered the SGE queue" % job_wrapper.job_id )
            job_wrapper.cleanup()
            return

        # Change to queued state immediately
        job_wrapper.change_state( model.Job.states.QUEUED )
        
        if self.determine_sge_cell( runner_url ) != self.default_cell:
            # TODO: support multiple cells
            log.warning( "(%s) Using multiple SGE cells is not supported.  This job will be submitted to the default cell." % job_wrapper.job_id )
        sge_queue_name = self.determine_sge_queue( runner_url )
        sge_project_name = self.determine_sge_project( runner_url )
        sge_extra_params = self.determine_sge_tool_parameters ( runner_url )

        # define job attributes
        ofile = "%s/%s.o" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
        efile = "%s/%s.e" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
        jt = self.ds.createJobTemplate()
        jt.remoteCommand = "%s/database/pbs/galaxy_%s.sh" % (os.getcwd(), job_wrapper.job_id)
        jt.outputPath = ":%s" % ofile
        jt.errorPath = ":%s" % efile
        nativeSpec = []
        if sge_queue_name is not None:
            nativeSpec.append( "-q '%s'" % sge_queue_name )
        if sge_project_name is not None:
            nativeSpec.append( "-P '%s'" % sge_project_name)
        if sge_extra_params is not None:
            nativeSpec.append( sge_extra_params ) 
        if len(nativeSpec)>0:
            jt.nativeSpecification = ' '.join(nativeSpec)

        script = sge_template % (job_wrapper.galaxy_lib_dir, os.path.abspath( job_wrapper.working_directory ), command_line)

        fh = file( jt.remoteCommand, "w" )
        fh.write( script )
        fh.close()
        os.chmod( jt.remoteCommand, 0750 )

        # job was deleted while we were preparing it
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "Job %s deleted by user before it entered the SGE queue" % job_wrapper.job_id )
            self.cleanup( ( ofile, efile, jt.remoteCommand ) )
            job_wrapper.cleanup()
            return

        galaxy_job_id = job_wrapper.job_id
        log.debug("(%s) submitting file %s" % ( galaxy_job_id, jt.remoteCommand ) )
        log.debug("(%s) command is: %s" % ( galaxy_job_id, command_line ) )
        # runJob will raise if there's a submit problem
        job_id = self.ds.runJob(jt)
        if sge_queue_name is None:
            log.debug("(%s) queued in default queue as %s" % (galaxy_job_id, job_id) )
        else:
            log.debug("(%s) queued in %s queue as %s" % (galaxy_job_id, sge_queue_name, job_id) )

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_runner( runner_url, job_id )

        # Store SGE related state information for job
        sge_job_state = SGEJobState()
        sge_job_state.job_wrapper = job_wrapper
        sge_job_state.job_id = job_id
        sge_job_state.ofile = ofile
        sge_job_state.efile = efile
        sge_job_state.job_file = jt.remoteCommand
        sge_job_state.old_state = 'new'
        sge_job_state.running = False
        sge_job_state.runner_url = runner_url
        
        # delete the job template
        self.ds.deleteJobTemplate( jt )

        # Add to our 'queue' of jobs to monitor
        self.monitor_queue.put( sge_job_state )

    def monitor( self ):
        """
        Watches jobs currently in the PBS queue and deals with state changes
        (queued to running) and job completion
        """
        while 1:
            # Take any new watched jobs and put them on the monitor list
            try:
                while 1: 
                    sge_job_state = self.monitor_queue.get_nowait()
                    if sge_job_state is self.STOP_SIGNAL:
                        # TODO: This is where any cleanup would occur
                        self.ds.exit()
                        return
                    self.watched.append( sge_job_state )
            except Empty:
                pass
            # Iterate over the list of watched jobs and check state
            self.check_watched_items()
            # Sleep a bit before the next state check
            time.sleep( 1 )
            
    def check_watched_items( self ):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []
        for sge_job_state in self.watched:
            job_id = sge_job_state.job_id
            galaxy_job_id = sge_job_state.job_wrapper.job_id
            old_state = sge_job_state.old_state
            try:
                state = self.ds.getJobProgramStatus( job_id )
            except DRMAA.InvalidJobError:
                # we should only get here if an orphaned job was put into the queue at app startup
                log.debug("(%s/%s) job left SGE queue" % ( galaxy_job_id, job_id ) )
                self.work_queue.put( ( 'finish', sge_job_state ) )
                continue
            except Exception, e:
                # so we don't kill the monitor thread
                log.exception("(%s/%s) Unable to check job status" % ( galaxy_job_id, job_id ) )
                log.warning("(%s/%s) job will now be errored" % ( galaxy_job_id, job_id ) )
                sge_job_state.fail_message = "Cluster could not complete job"
                self.work_queue.put( ( 'fail', sge_job_state ) )
                continue
            if state != old_state:
                log.debug("(%s/%s) state change: %s" % ( galaxy_job_id, job_id, DRMAA_state[state] ) )
            if state == DRMAA.Session.RUNNING and not sge_job_state.running:
                sge_job_state.running = True
                sge_job_state.job_wrapper.change_state( model.Job.states.RUNNING )
            if state in ( DRMAA.Session.DONE, DRMAA.Session.FAILED ):
                self.work_queue.put( ( 'finish', sge_job_state ) )
                continue
            sge_job_state.old_state = state
            new_watched.append( sge_job_state )
        # Replace the watch list with the updated version
        self.watched = new_watched
        
    def finish_job( self, sge_job_state ):
        """
        Get the output/error for a finished job, pass to `job_wrapper.finish`
        and cleanup all the SGE temporary files.
        """
        ofile = sge_job_state.ofile
        efile = sge_job_state.efile
        job_file = sge_job_state.job_file
        # collect the output
        try:
            ofh = file(ofile, "r")
            efh = file(efile, "r")
            stdout = ofh.read( 32768 )
            stderr = efh.read( 32768 )
        except:
            stdout = ''
            stderr = 'Job output not returned from cluster'
            log.debug(stderr)

        try:
            sge_job_state.job_wrapper.finish( stdout, stderr )
        except:
            log.exception("Job wrapper finish method failed")

        # clean up the sge files
        self.cleanup( ( ofile, efile, job_file ) )

    def fail_job( self, sge_job_state ):
        """
        Seperated out so we can use the worker threads for it.
        """
        self.stop_job( self.sa_session.query( self.app.model.Job ).get( sge_job_state.job_wrapper.job_id ) )
        sge_job_state.job_wrapper.fail( sge_job_state.fail_message )
        self.cleanup( ( sge_job_state.ofile, sge_job_state.efile, sge_job_state.job_file ) )

    def cleanup( self, files ):
        if not asbool( self.app.config.get( 'debug', False ) ):
            for file in files:
                if os.access( file, os.R_OK ):
                    os.unlink( file )

    def put( self, job_wrapper ):
        """Add a job to the queue (by job identifier)"""
        # Change to queued state before handing to worker thread so the runner won't pick it up again
        job_wrapper.change_state( model.Job.states.QUEUED )
        self.work_queue.put( ( 'queue', job_wrapper ) )

    def shutdown( self ):
        """Attempts to gracefully shut down the monitor thread"""
        log.info( "sending stop signal to worker threads" )
        self.monitor_queue.put( self.STOP_SIGNAL )
        for i in range( len( self.work_threads ) ):
            self.work_queue.put( ( self.STOP_SIGNAL, None ) )
        log.info( "sge job runner stopped" )

    def stop_job( self, job ):
        """Attempts to delete a job from the SGE queue"""
        try:
            self.ds.control( job.job_runner_external_id, DRMAA.Session.TERMINATE )
            log.debug( "(%s/%s) Removed from SGE queue at user's request" % ( job.id, job.job_runner_external_id ) )
        except DRMAA.InvalidJobError:
            log.debug( "(%s/%s) User killed running job, but it was already dead" % ( job.id, job.job_runner_external_id ) )

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        sge_job_state = SGEJobState()
        sge_job_state.ofile = "%s/database/pbs/%s.o" % (os.getcwd(), job.id)
        sge_job_state.efile = "%s/database/pbs/%s.e" % (os.getcwd(), job.id)
        sge_job_state.job_file = "%s/database/pbs/galaxy_%s.sh" % (os.getcwd(), job.id)
        sge_job_state.job_id = str( job.job_runner_external_id )
        sge_job_state.runner_url = job_wrapper.get_job_runner()
        job_wrapper.command_line = job.command_line
        sge_job_state.job_wrapper = job_wrapper
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the SGE queue" % ( job.id, job.job_runner_external_id ) )
            sge_job_state.old_state = DRMAA.Session.RUNNING
            sge_job_state.running = True
            self.monitor_queue.put( sge_job_state )
        elif job.state == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in SGE queued state, adding to the SGE queue" % ( job.id, job.job_runner_external_id ) )
            sge_job_state.old_state = DRMAA.Session.QUEUED_ACTIVE
            sge_job_state.running = False
            self.monitor_queue.put( sge_job_state )
