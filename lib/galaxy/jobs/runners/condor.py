"""
Job control via the Condor DRM.
"""

import os
import re
import sys
import time
import logging
import subprocess

from galaxy import model
from galaxy.jobs.runners import AsynchronousJobState, AsynchronousJobRunner

from galaxy.util import asbool

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

class CondorJobState( AsynchronousJobState ):
    def __init__( self, **kwargs ):
        """
        Encapsulates state related to a job that is being run via the DRM and 
        that we need to monitor.
        """
        super( CondorJobState, self ).__init__( **kwargs )
        self.failed = False
        self.user_log = None
        self.user_log_size = 0

class CondorJobRunner( AsynchronousJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "CondorRunner"
    def __init__( self, app, nworkers ):
        """Initialize this job runner and start the monitor thread"""
        super( CondorJobRunner, self ).__init__( app, nworkers )
        self._init_monitor_thread()
        self._init_worker_threads()

    # superclass url_to_destination is fine - condor runner does not take params

    def queue_job( self, job_wrapper ):
        """Create job script and submit it to the DRM"""
        # Superclass method has some basic sanity checks
        super( CondorJobRunner, self ).queue_job( job_wrapper )
        if not job_wrapper.is_ready:
            return

        # command line has been added to the wrapper by the superclass queue_job()
        command_line = job_wrapper.runner_command_line

        # get configured job destination
        job_destination = job_wrapper.job_destination

        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()

        # define job attributes
        cjs = CondorJobState( files_dir=self.app.config.cluster_files_directory, job_wrapper=job_wrapper )
        cjs.user_log = os.path.join( self.app.config.cluster_files_directory, 'galaxy_%s.condor.log' % galaxy_id_tag )
        cjs.register_cleanup_file_attribute( 'user_log' )
        submit_file = os.path.join( self.app.config.cluster_files_directory, 'galaxy_%s.condor.desc' % galaxy_id_tag )
        executable = cjs.job_file
        submit_desc = [ ]
        submit_desc.append( 'universe = vanilla' )
        submit_desc.append( 'getenv = true' )
        submit_desc.append( 'executable = ' + executable )
        submit_desc.append( 'output = ' + cjs.output_file )
        submit_desc.append( 'error = ' + cjs.error_file )
        submit_desc.append( 'log = ' + cjs.user_log )
        submit_desc.append( 'notification = NEVER' )
        submit_desc.append( 'queue' )

        script = drm_template % (job_wrapper.galaxy_lib_dir, os.path.abspath( job_wrapper.working_directory ), command_line)
        try:
            fh = file( executable, "w" )
            fh.write( script )
            fh.close()
            os.chmod( executable, 0750 )
        except:
            job_wrapper.fail( "failure preparing job script", exception=True )
            log.exception( "(%s) failure preparing job script" % galaxy_id_tag )
            return

        try:
            fh = file( submit_file, 'w' )
            for line in submit_desc:
                fh.write( line + '\n' )
            fh.close()
        except:
            if self.app.config.cleanup_job == "always":
                cjs.cleanup()
                # job_wrapper.fail() calls job_wrapper.cleanup()
            job_wrapper.fail( "failure preparing submit file", exception=True )
            log.exception( "(%s) failure preparing submit file" % galaxy_id_tag )
            return

        # job was deleted while we were preparing it
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "Job %s deleted by user before it entered the queue" % galaxy_id_tag )
            if self.app.config.cleanup_job in ( "always", "onsuccess" ):
                os.unlink( submit_file )
                cjs.cleanup()
                job_wrapper.cleanup()
            return

        log.debug( "(%s) submitting file %s" % ( galaxy_id_tag, executable ) )
        log.debug( "(%s) command is: %s" % ( galaxy_id_tag, command_line ) )

        s_out = ''
        external_job_id = None
        try:
            submit = subprocess.Popen( ( 'condor_submit', submit_file ), stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
            s_out, s_err = submit.communicate()
            if submit.returncode == 0:
                match = re.search( 'submitted to cluster (\\d+).', s_out )
                if match is None:
                    s_out = 'Failed to find job id from condor_submit'
                else:
                    external_job_id = match.group( 1 )
        except Exception, e:
            # TODO Add extra except for OSError?
            s_out = str(e)

        os.unlink( submit_file )

        if external_job_id is None:
            log.debug( "condor_submit failed for job %s: %s" % (job_wrapper.get_id_tag(), s_out) )
            if self.app.config.cleanup_job == "always":
                cjs.cleanup()
            job_wrapper.fail( "condor_submit failed", exception=True )
            return

        log.info( "(%s) queued as %s" % ( galaxy_id_tag, external_job_id ) )

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_job_destination( job_destination, external_job_id )

        # Store DRM related state information for job
        cjs.job_id = external_job_id
        cjs.job_destination = job_destination

        # Add to our 'queue' of jobs to monitor
        self.monitor_queue.put( cjs )

    def check_watched_items( self ):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []
        for cjs in self.watched:
            job_id = cjs.job_id
            log_job_id = job_id.zfill(3)
            galaxy_id_tag = cjs.job_wrapper.get_id_tag()
            job_running = False
            job_complete = False
            job_failed = False
            try:
                if os.stat( cjs.user_log ).st_size == cjs.user_log_size:
                    new_watched.append( cjs )
                    continue
                with open(cjs.user_log, 'r') as fh:
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
                    cjs.user_log_size = fh.tell()
            except Exception, e:
                # so we don't kill the monitor thread
                log.exception( "(%s/%s) Unable to check job status" % ( galaxy_id_tag, job_id ) )
                log.warning( "(%s/%s) job will now be errored" % ( galaxy_id_tag, job_id ) )
                cjs.fail_message = "Cluster could not complete job"
                self.work_queue.put( ( self.fail_job, cjs ) )
                continue
            if job_running and not cjs.running:
                log.debug( "(%s/%s) job is now running" % ( galaxy_id_tag, job_id ) )
                cjs.job_wrapper.change_state( model.Job.states.RUNNING )
            if not job_running and cjs.running:
                log.debug( "(%s/%s) job has stopped running" % ( galaxy_id_tag, job_id ) )
                # Will switching from RUNNING to QUEUED confuse Galaxy?
                #cjs.job_wrapper.change_state( model.Job.states.QUEUED )
            if job_complete:
                log.debug( "(%s/%s) job has completed" % ( galaxy_id_tag, job_id ) )
                self.work_queue.put( ( self.finish_job, cjs ) )
                continue
            if job_failed:
                log.debug( "(%s/%s) job failed" % ( galaxy_id_tag, job_id ) )
                cjs.failed = True
                self.work_queue.put( ( self.finish_job, cjs ) )
                continue
            cjs.runnning = job_running
            new_watched.append( cjs )
        # Replace the watch list with the updated version
        self.watched = new_watched
        
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
        cjs = CondorJobState()
        cjs.job_id = str( job_id )
        cjs.command_line = job.get_command_line()
        cjs.job_wrapper = job_wrapper
        cjs.job_destination = job_wrapper.job_destination
        cjs.user_log = os.path.join( self.app.config.cluster_files_directory, '%s.condor.log' % galaxy_id_tag )
        cjs.register_cleanup_file_attribute( 'user_log' )
        self.__old_state_paths( cjs )
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the DRM queue" % ( job.id, job.job_runner_external_id ) )
            cjs.running = True
            self.monitor_queue.put( cjs )
        elif job.state == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in DRM queued state, adding to the DRM queue" % ( job.id, job.job_runner_external_id ) )
            cjs.running = False
            self.monitor_queue.put( cjs )

    def __old_state_paths( self, cjs, job ):
        """For recovery of jobs started prior to standardizing the naming of
        files in the AsychronousJobState object
        """
        if cjs.job_wrapper is not None:
            user_log = "%s/%s.condor.log" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
            if not os.path.exists( cjs.job_file ) and os.path.exists( job_file ):
                cjs.output_file = "%s/%s.o" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
                cjs.error_file = "%s/%s.e" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
                cjs.job_file = "%s/galaxy_%s.sh" % (self.app.config.cluster_files_directory, job_wrapper.job_id)
                cjs.user_log = user_log
