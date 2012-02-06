import os, sys, logging, threading, time, string
import pprint, pwd
from pwd import getpwnam
import subprocess
import inspect
import simplejson as json

from Queue import Queue, Empty

from galaxy import model
from galaxy.jobs.runners import BaseJobRunner

from paste.deploy.converters import asbool

import pkg_resources


if sys.version_info[:2] == ( 2, 4 ):
    pkg_resources.require( "ctypes" )
pkg_resources.require( "drmaa" )
# We foolishly named this file the same as the name exported by the drmaa
# library... 'import drmaa' import itself.
drmaa = __import__( "drmaa" )

log = logging.getLogger( __name__ )

__all__ = [ 'DRMAAJobRunner' ]

drmaa_state = {
    drmaa.JobState.UNDETERMINED: 'process status cannot be determined',
    drmaa.JobState.QUEUED_ACTIVE: 'job is queued and active',
    drmaa.JobState.SYSTEM_ON_HOLD: 'job is queued and in system hold',
    drmaa.JobState.USER_ON_HOLD: 'job is queued and in user hold',
    drmaa.JobState.USER_SYSTEM_ON_HOLD: 'job is queued and in user and system hold',
    drmaa.JobState.RUNNING: 'job is running',
    drmaa.JobState.SYSTEM_SUSPENDED: 'job is system suspended',
    drmaa.JobState.USER_SUSPENDED: 'job is user suspended',
    drmaa.JobState.DONE: 'job finished normally',
    drmaa.JobState.FAILED: 'job finished, but failed',
}

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
%s
cd %s
%s
"""
def __lineno__():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

def __filename__():
    """Returns the current filename in our program."""
    return inspect.currentframe().f_back.f_code.co_filename

DRMAA_jobTemplate_attributes = [ 'args', 'remoteCommand', 'outputPath', 'errorPath', 'nativeSpecification',
                    'name','email','project' ]

class DRMAAJobState( object ):
    def __init__( self ):
        """
        Encapsulates state related to a job that is being run via the DRM and 
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

class DRMAAJobRunner( BaseJobRunner ):
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
        self.ds = drmaa.Session()
        self.ds.initialize()
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
        # external_runJob_script can be None, in which case it's not used.
        self.external_runJob_script = app.config.drmaa_external_runjob_script
        self.external_killJob_script = app.config.drmaa_external_killjob_script
        self.userid = None

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
        
        # Check for deletion before we change state
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "Job %s deleted by user before it entered the queue" % job_wrapper.get_id_tag() )
            if self.app.config.cleanup_job in ( "always", "onsuccess" ):
                job_wrapper.cleanup()
            return

        # Change to queued state immediately
        job_wrapper.change_state( model.Job.states.QUEUED )

        # define job attributes
        ofile = "%s.drmout" % os.path.join(job_wrapper.working_directory, job_wrapper.get_id_tag())
        efile = "%s.drmerr" % os.path.join(job_wrapper.working_directory, job_wrapper.get_id_tag())
        job_name = "g%s_%s_%s" % ( job_wrapper.job_id, job_wrapper.tool.id, job_wrapper.user )
        job_name = ''.join( map( lambda x: x if x in ( string.letters + string.digits + '_' ) else '_', job_name ) )

        jt = self.ds.createJobTemplate()
        jt.remoteCommand = "%s/galaxy_%s.sh" % (self.app.config.cluster_files_directory, job_wrapper.get_id_tag())
        jt.jobName = job_name
        jt.outputPath = ":%s" % ofile
        jt.errorPath = ":%s" % efile
        native_spec = self.get_native_spec( runner_url )
        if native_spec is not None:
            jt.nativeSpecification = native_spec

        # fill in the DRM's job run template
        script = drm_template % ( job_wrapper.galaxy_lib_dir,
                                  job_wrapper.get_env_setup_clause(),
                                  os.path.abspath( job_wrapper.working_directory ),
                                  command_line )

        try:
            fh = file( jt.remoteCommand, "w" )
            fh.write( script )
            fh.close()
            os.chmod( jt.remoteCommand, 0755 )
        except:
            job_wrapper.fail( "failure preparing job script", exception=True )
            log.exception( "failure running job %s" % job_wrapper.get_id_tag() )
            return     

        # job was deleted while we were preparing it
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "Job %s deleted by user before it entered the queue" % job_wrapper.get_id_tag() )
            if self.app.config.cleanup_job in ( "always", "onsuccess" ):
                job_wrapper.cleanup()
            return

        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()
        
        log.debug("(%s) submitting file %s" % ( galaxy_id_tag, jt.remoteCommand ) )
        log.debug("(%s) command is: %s" % ( galaxy_id_tag, command_line ) )
        # runJob will raise if there's a submit problem
        if self.external_runJob_script is None:
            job_id = self.ds.runJob(jt)
        else:
            job_wrapper.change_ownership_for_run()
            log.debug( '(%s) submitting with credentials: %s [uid: %s]' % ( galaxy_id_tag, job_wrapper.user_system_pwent[0], job_wrapper.user_system_pwent[2] ) )
            filename = self.store_jobtemplate(job_wrapper, jt)
            self.userid =  job_wrapper.user_system_pwent[2]
            job_id = self.external_runjob(filename, job_wrapper.user_system_pwent[2]).strip()
        log.info("(%s) queued as %s" % ( galaxy_id_tag, job_id ) )

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_runner( runner_url, job_id )

        # Store DRM related state information for job
        drm_job_state = DRMAAJobState()
        drm_job_state.job_wrapper = job_wrapper
        drm_job_state.job_id = job_id
        drm_job_state.ofile = ofile
        drm_job_state.efile = efile
        drm_job_state.job_file = jt.remoteCommand
        drm_job_state.old_state = 'new'
        drm_job_state.running = False
        drm_job_state.runner_url = runner_url
        
        # delete the job template
        self.ds.deleteJobTemplate( jt )

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
                        self.ds.exit()
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
            galaxy_job_id = drm_job_state.job_wrapper.job_id
            old_state = drm_job_state.old_state
            try:
                state = self.ds.jobStatus( job_id )
            # InternalException was reported to be necessary on some DRMs, but
            # this could cause failures to be detected as completion!  Please
            # report if you experience problems with this.
            except ( drmaa.InvalidJobException, drmaa.InternalException ), e:
                # we should only get here if an orphaned job was put into the queue at app startup
                log.debug("(%s/%s) job left DRM queue with following message: %s" % ( galaxy_job_id, job_id, e ) )
                self.work_queue.put( ( 'finish', drm_job_state ) )
                continue
            except drmaa.DrmCommunicationException, e:
                log.warning("(%s/%s) unable to communicate with DRM: %s" % ( galaxy_job_id, job_id, e ))
                new_watched.append( drm_job_state )
                continue
            except Exception, e:
                # so we don't kill the monitor thread
                log.exception("(%s/%s) Unable to check job status" % ( galaxy_job_id, job_id ) )
                log.warning("(%s/%s) job will now be errored" % ( galaxy_job_id, job_id ) )
                drm_job_state.fail_message = "Cluster could not complete job"
                self.work_queue.put( ( 'fail', drm_job_state ) )
                continue
            if state != old_state:
                log.debug("(%s/%s) state change: %s" % ( galaxy_job_id, job_id, drmaa_state[state] ) )
            if state == drmaa.JobState.RUNNING and not drm_job_state.running:
                drm_job_state.running = True
                drm_job_state.job_wrapper.change_state( model.Job.states.RUNNING )
            if state in ( drmaa.JobState.DONE, drmaa.JobState.FAILED ):
                self.work_queue.put( ( 'finish', drm_job_state ) )
                continue
            drm_job_state.old_state = state
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
        # wait for the files to appear
        which_try = 0
        while which_try < (self.app.config.retry_job_output_collection + 1):
            try:
                ofh = file(ofile, "r")
                efh = file(efile, "r")
                stdout = ofh.read( 32768 )
                stderr = efh.read( 32768 )
                which_try = (self.app.config.retry_job_output_collection + 1)
            except:
                if which_try == self.app.config.retry_job_output_collection:
                    stdout = ''
                    stderr = 'Job output not returned from cluster'
                    log.debug( stderr )
                else:
                    time.sleep(1)
                which_try += 1

        try:
            drm_job_state.job_wrapper.finish( stdout, stderr )
        except:
            log.exception("Job wrapper finish method failed")

    def fail_job( self, drm_job_state ):
        """
        Seperated out so we can use the worker threads for it.
        """
        self.stop_job( self.sa_session.query( self.app.model.Job ).get( drm_job_state.job_wrapper.job_id ) )
        drm_job_state.job_wrapper.fail( drm_job_state.fail_message )

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
        log.info( "drmaa job runner stopped" )

    def stop_job( self, job ):
        """Attempts to delete a job from the DRM queue"""
        try:
            if self.external_killJob_script is None:
                self.ds.control( job.job_runner_external_id, drmaa.JobControlAction.TERMINATE )
            else:
                # FIXME: hardcoded path
                subprocess.Popen( [ '/usr/bin/sudo', '-E', self.external_killJob_script, str( job.job_runner_external_id ), str( self.userid ) ], shell=False )
            log.debug( "(%s/%s) Removed from DRM queue at user's request" % ( job.id, job.job_runner_external_id ) )
        except drmaa.InvalidJobException:
            log.debug( "(%s/%s) User killed running job, but it was already dead" % ( job.id, job.job_runner_external_id ) )
        except Exception, e:
            log.debug( "(%s/%s) User killed running job, but error encountered removing from DRM queue: %s" % ( job.id, job.job_runner_external_id, e ) )

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        drm_job_state = DRMAAJobState()
        drm_job_state.ofile = "%s.drmout" % os.path.join(os.getcwd(), job_wrapper.working_directory, job_wrapper.get_id_tag())
        drm_job_state.efile = "%s.drmerr" % os.path.join(os.getcwd(), job_wrapper.working_directory, job_wrapper.get_id_tag())
        drm_job_state.job_file = "%s/galaxy_%s.sh" % (self.app.config.cluster_files_directory, job.id)
        drm_job_state.job_id = str( job.job_runner_external_id )
        drm_job_state.runner_url = job_wrapper.get_job_runner()
        job_wrapper.command_line = job.command_line
        drm_job_state.job_wrapper = job_wrapper
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the DRM queue" % ( job.id, job.job_runner_external_id ) )
            drm_job_state.old_state = drmaa.JobState.RUNNING
            drm_job_state.running = True
            self.monitor_queue.put( drm_job_state )
        elif job.state == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in DRM queued state, adding to the DRM queue" % ( job.id, job.job_runner_external_id ) )
            drm_job_state.old_state = drmaa.JobState.QUEUED_ACTIVE
            drm_job_state.running = False
            self.monitor_queue.put( drm_job_state )

    def store_jobtemplate(self, job_wrapper, jt):
        """ Stores the content of a DRMAA JobTemplate object in a file as a JSON string.
        Path is hard-coded, but it's no worse than other path in this module.
        Uses Galaxy's JobID, so file is expected to be unique."""
        filename = "%s/%s.jt_json" % (self.app.config.cluster_files_directory, job_wrapper.get_id_tag())
        data = {}
        for attr in DRMAA_jobTemplate_attributes:
            try:
                data[attr] = getattr(jt, attr)
            except:
                pass
        s = json.dumps(data)
        f = open(filename,'w')
        f.write(s)
        f.close()
        log.debug( '(%s) Job script for external submission is: %s' % ( job_wrapper.job_id, filename ) )
        return filename

    def external_runjob(self, jobtemplate_filename, username):
        """ runs an external script the will QSUB a new job.
        The external script will be run with sudo, and will setuid() to the specified user.
        Effectively, will QSUB as a different user (then the one used by Galaxy).
        """
        p = subprocess.Popen([ '/usr/bin/sudo', '-E', self.external_runJob_script, str(username), jobtemplate_filename ],
                shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdoutdata, stderrdata) = p.communicate()
        exitcode = p.returncode
        #os.unlink(jobtemplate_filename)
        if exitcode != 0:
            # There was an error in the child process
            raise RuntimeError("External_runjob failed (exit code %s)\nCalled from %s:%d\nChild process reported error:\n%s" % (str(exitcode), __filename__(), __lineno__(), stderrdata))
        if not stdoutdata.strip():
            raise RuntimeError("External_runjob did return the job id: %s" % (stdoutdata))
        
        # The expected output is a single line containing a single numeric value:
        # the DRMAA job-ID. If not the case, will throw an error.
        jobId = stdoutdata
        return jobId


