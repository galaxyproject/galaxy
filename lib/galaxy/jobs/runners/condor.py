import os, sys, logging, threading, time, subprocess, re
from Queue import Queue, Empty

from galaxy import model
from galaxy.jobs.runners import BaseJobRunner

from galaxy.util import asbool

import pkg_resources

if sys.version_info[:2] == ( 2, 4 ):
    pkg_resources.require( "ctypes" )

log = logging.getLogger( __name__ )

__all__ = [ 'CondorJobRunner' ]

drm_template = """#!/bin/sh
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

class CondorJobState( object ):
    def __init__( self ):
        """
        Encapsulates state related to a job that is being run via the DRM and 
        that we need to monitor.
        """
        self.job_wrapper = None
        self.job_id = None
        self.running = False
        self.failed = False
        self.job_file = None
        self.ofile = None
        self.efile = None
        self.user_log = None
        self.user_log_size = 0
        self.runner_url = None

class CondorJobRunner( BaseJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Initialize this job runner and start the monitor thread"""
        # Check if drmaa was importable, fail if not
        self.app = app
        self.sa_session = app.model.context
        # 'watched' and 'queue' are both used to keep track of jobs to watch.
        # 'queue' is used to add new watched jobs, and can be called from
        # any thread (usually by the 'queue_job' method). 'watched' must only
        # be modified by the monitor thread, which will move items from 'queue'
        # to 'watched' and then manage the watched jobs.
        self.watched = []
        self.monitor_queue = Queue()
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

    def get_native_spec( self, url ):
        """Get any native DRM arguments specified by the site configuration"""
        try:
            return url.split('/')[2] or None
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
                if op == 'queue':
                    obj.fail( "Uncaught exception queueing job", exception=True )

    def queue_job( self, job_wrapper ):
        """Create job script and submit it to the DRM"""

        try:
            job_wrapper.prepare()
            command_line = self.build_command_line( job_wrapper, include_metadata=True )
        except:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %s" % job_wrapper.get_id_tag())
            return

        runner_url = job_wrapper.get_job_runner()
        
        # This is silly, why would we queue a job with no command line?
        if not command_line:
            job_wrapper.finish( '', '' )
            return

        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "Job %s deleted by user before it entered the queue" % job_wrapper.get_id_tag() )
            job_wrapper.cleanup()
            return

        # Change to queued state immediately
        job_wrapper.change_state( model.Job.states.QUEUED )

        # define job attributes
        ofile = "%s/%s.o" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
        efile = "%s/%s.e" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
        user_log = "%s/%s.condor.log" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
        executable = "%s/galaxy_%s.sh" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
        submit_desc = [ ]
        submit_desc.append( 'universe = vanilla' )
        submit_desc.append( 'getenv = true' )
        submit_desc.append( 'executable = ' + executable )
        submit_desc.append( 'output = ' + ofile )
        submit_desc.append( 'error = ' + efile )
        submit_desc.append( 'log = ' + user_log )
        submit_desc.append( 'notification = NEVER' )
        submit_desc.append( 'queue' )
        submit_file = "%s/%s.condor.desc" % (self.app.config.cluster_files_directory, job_wrapper.job_id)

        script = drm_template % (job_wrapper.galaxy_lib_dir, os.path.abspath( job_wrapper.working_directory ), command_line)
        try:
            fh = file( executable, "w" )
            fh.write( script )
            fh.close()
            os.chmod( executable, 0750 )
        except:
            job_wrapper.fail( "failure preparing job script", exception=True )
            log.exception("failure running job %s" % job_wrapper.get_id_tag())
            return

        try:
            fh = file( submit_file, 'w' )
            for line in submit_desc:
                fh.write( line + '\n' )
            fh.close()
        except:
            job_wrapper.fail( "failure writing submit file", exception=True )
            log.exception("failure running job %s" % job_wrapper.get_id_tag())
            self.cleanup( ( executable, submit_file ) )
            return

        # job was deleted while we were preparing it
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "Job %s deleted by user before it entered the queue" % job_wrapper.get_id_tag() )
            self.cleanup( ( executable, submit_file ) )
            job_wrapper.cleanup()
            return

        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()
        
        log.debug("(%s) submitting file %s" % ( galaxy_id_tag, executable ) )
        log.debug("(%s) command is: %s" % ( galaxy_id_tag, command_line ) )
        s_out = ''
        job_id = None
        try:
            submit = subprocess.Popen( ( 'condor_submit', submit_file ), stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
            s_out, s_err = submit.communicate()
            if submit.returncode == 0:
                match = re.search( 'submitted to cluster (\\d+).', s_out )
                if match is None:
                    s_out = 'Failed to find job id from condor_submit'
                else:
                    job_id = match.group( 1 )
        except Exception, e:
            # TODO Add extra except for OSError?
            s_out = str(e)

        if job_id is None:
            log.debug( "condor_submit failed for job %s: %s" % (job_wrapper.get_id_tag(), s_out) )
            self.cleanup( ( submit_file, executable ) )
            job_wrapper.fail( "condor_submit failed", exception=True )
            return

        log.info("(%s) queued as %s" % ( galaxy_id_tag, job_id ) )

        self.cleanup( ( submit_file, ) )

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_runner( runner_url, job_id )

        # Store DRM related state information for job
        drm_job_state = CondorJobState()
        drm_job_state.job_wrapper = job_wrapper
        drm_job_state.job_id = job_id
        drm_job_state.ofile = ofile
        drm_job_state.efile = efile
        drm_job_state.job_file = executable
        drm_job_state.user_log = user_log
        drm_job_state.running = False
        drm_job_state.runner_url = runner_url
        
        # Add to our 'queue' of jobs to monitor
        self.monitor_queue.put( drm_job_state )

    def monitor( self ):
        """
        Watches jobs currently in the PBS queue and deals with state changes
        (queued to running) and job completion
        """
        while 1:
            # Take any new watched jobs and put them on the monitor list
            try:
                while 1: 
                    drm_job_state = self.monitor_queue.get_nowait()
                    if drm_job_state is self.STOP_SIGNAL:
                        # TODO: This is where any cleanup would occur
                        #self.ds.exit()
                        #   Do we need any cleanup here?
                        return
                    self.watched.append( drm_job_state )
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
        for drm_job_state in self.watched:
            job_id = drm_job_state.job_id
            log_job_id = job_id.zfill(3)
            galaxy_job_id = drm_job_state.job_wrapper.job_id
            job_running = False;
            job_complete = False;
            job_failed = False;
            try:
                if os.stat( drm_job_state.user_log ).st_size == drm_job_state.user_log_size:
                    new_watched.append( drm_job_state )
                    continue
                with open(drm_job_state.user_log, 'r') as fh:
                    for line in fh:
                        if '001 (' + log_job_id + '.' in line:
                            job_running = True
                        if '004 (' + log_job_id + '.' in line:
                            job_running = False
                        if '007 (' + log_job_id + '.' in line:
                            job_running = False
                        if '005 (' + log_job_id + '.' in line:
                            job_complete = True
                        if '009 (' + log_job_id + '.' in line:
                            job_failed = True
                    drm_job_state.user_log_size = fh.tell()
            except Exception, e:
                # so we don't kill the monitor thread
                log.exception("(%s/%s) Unable to check job status" % ( galaxy_job_id, job_id ) )
                log.warning("(%s/%s) job will now be errored" % ( galaxy_job_id, job_id ) )
                drm_job_state.fail_message = "Cluster could not complete job"
                self.work_queue.put( ( 'fail', drm_job_state ) )
                continue
            if job_running and not drm_job_state.running:
                log.debug("(%s/%s) job is now running" % ( galaxy_job_id, job_id ) )
                drm_job_state.job_wrapper.change_state( model.Job.states.RUNNING )
            if not job_running and drm_job_state.running:
                log.debug("(%s/%s) job has stopped running" % ( galaxy_job_id, job_id ) )
                # Will switching from RUNNING to QUEUED confuse Galaxy?
                #drm_job_state.job_wrapper.change_state( model.Job.states.QUEUED )
            if job_complete:
                log.debug("(%s/%s) job has completed" % ( galaxy_job_id, job_id ) )
                self.work_queue.put( ( 'finish', drm_job_state ) )
                continue
            if job_failed:
                log.debug("(%s/%s) job failed" % ( galaxy_job_id, job_id ) )
                drm_job_state.failed = True
                self.work_queue.put( ( 'finish', drm_job_state ) )
                continue
            drm_job_state.runnning = job_running
            new_watched.append( drm_job_state )
        # Replace the watch list with the updated version
        self.watched = new_watched
        
    def finish_job( self, drm_job_state ):
        """
        Get the output/error for a finished job, pass to `job_wrapper.finish`
        and cleanup all the DRM temporary files.
        """
        ofile = drm_job_state.ofile
        efile = drm_job_state.efile
        job_file = drm_job_state.job_file
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
            drm_job_state.job_wrapper.finish( stdout, stderr )
        except:
            log.exception("Job wrapper finish method failed")

        # clean up the drm files
        self.cleanup( ( ofile, efile, job_file, drm_job_state.user_log ) )

    def fail_job( self, drm_job_state ):
        """
        Seperated out so we can use the worker threads for it.
        """
        self.stop_job( self.sa_session.query( self.app.model.Job ).get( drm_job_state.job_wrapper.job_id ) )
        drm_job_state.job_wrapper.fail( drm_job_state.fail_message )
        self.cleanup( ( drm_job_state.ofile, drm_job_state.efile, drm_job_state.job_file, drm_job_state.user_log ) )

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
        log.info( "condor job runner stopped" )

    def stop_job( self, job ):
        """Attempts to delete a job from the DRM queue"""
        try:
            subprocess.check_call( ( 'condor_rm', job.job_runner_external_id ) )
            log.debug( "(%s/%s) Removed from DRM queue at user's request" % ( job.id, job.job_runner_external_id ) )
        except subprocess.CalledProcessError:
            log.debug( "(%s/%s) User killed running job, but condor_rm failed" % ( job.id, job.job_runner_external_id ) )
        except Exception, e:
            log.debug( "(%s/%s) User killed running job, but error encountered removing from Condor queue: %s" % ( job.id, job.job_runner_external_id, e ) )

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        # TODO Check if we need any changes here
        job_id = job.get_job_runner_external_id()
        if job_id is None:
            self.put( job_wrapper )
            return
        drm_job_state = CondorJobState()
        drm_job_state.ofile = "%s/database/pbs/%s.o" % (os.getcwd(), job.id)
        drm_job_state.efile = "%s/database/pbs/%s.e" % (os.getcwd(), job.id)
        drm_job_state.job_file = "%s/database/pbs/galaxy_%s.sh" % (os.getcwd(), job.id)
        drm_job_state.job_id = str( job_id )
        drm_job_state.runner_url = job_wrapper.get_job_runner()
        job_wrapper.command_line = job.command_line
        drm_job_state.job_wrapper = job_wrapper
        drm_job_state.user_log = "%s/%s.condor.log" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the DRM queue" % ( job.id, job.job_runner_external_id ) )
            drm_job_state.running = True
            self.monitor_queue.put( drm_job_state )
        elif job.state == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in DRM queued state, adding to the DRM queue" % ( job.id, job.job_runner_external_id ) )
            drm_job_state.running = False
            self.monitor_queue.put( drm_job_state )
