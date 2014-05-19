"""
Job control via the Condor DRM.
"""

import os
import logging

from galaxy import model
from galaxy.jobs.runners import AsynchronousJobState, AsynchronousJobRunner
from galaxy.jobs.runners.util.condor import submission_params, build_submit_description
from galaxy.jobs.runners.util.condor import condor_submit, condor_stop
from galaxy.jobs.runners.util.condor import summarize_condor_log

log = logging.getLogger( __name__ )

__all__ = [ 'CondorJobRunner' ]


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

    def queue_job( self, job_wrapper ):
        """Create job script and submit it to the DRM"""

        # prepare the job
        if not self.prepare_job( job_wrapper, include_metadata=True ):
            return

        # command line has been added to the wrapper by prepare_job()
        command_line = job_wrapper.runner_command_line

        # get configured job destination
        job_destination = job_wrapper.job_destination

        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()

        # get destination params
        query_params = submission_params(prefix="", **job_destination.params)
        galaxy_slots = query_params.get('request_cpus', None)
        if galaxy_slots:
            galaxy_slots_statement = 'GALAXY_SLOTS="%s"; export GALAXY_SLOTS_CONFIGURED="1"' % galaxy_slots
        else:
            galaxy_slots_statement = 'GALAXY_SLOTS="1"'

        # define job attributes
        cjs = CondorJobState(
            files_dir=self.app.config.cluster_files_directory,
            job_wrapper=job_wrapper
        )

        cluster_directory = self.app.config.cluster_files_directory
        cjs.user_log = os.path.join( cluster_directory, 'galaxy_%s.condor.log' % galaxy_id_tag )
        cjs.register_cleanup_file_attribute( 'user_log' )
        submit_file = os.path.join( cluster_directory, 'galaxy_%s.condor.desc' % galaxy_id_tag )
        executable = cjs.job_file

        build_submit_params = dict(
            executable=executable,
            output=cjs.output_file,
            error=cjs.error_file,
            user_log=cjs.user_log,
            query_params=query_params,
        )

        submit_file_contents = build_submit_description(**build_submit_params)
        script = self.get_job_file(
            job_wrapper,
            exit_code_path=cjs.exit_code_file,
            slots_statement=galaxy_slots_statement,
        )
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
            open(submit_file, "w").write(submit_file_contents)
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

        external_job_id, message = condor_submit(submit_file)
        if external_job_id is None:
            log.debug( "condor_submit failed for job %s: %s" % (job_wrapper.get_id_tag(), message) )
            if self.app.config.cleanup_job == "always":
                os.unlink( submit_file )
                cjs.cleanup()
            job_wrapper.fail( "condor_submit failed", exception=True )
            return

        os.unlink( submit_file )

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
            galaxy_id_tag = cjs.job_wrapper.get_id_tag()
            try:
                if os.stat( cjs.user_log ).st_size == cjs.user_log_size:
                    new_watched.append( cjs )
                    continue
                s1, s4, s7, s5, s9, log_size = summarize_condor_log(cjs.user_log, job_id)
                job_running = s1 and not (s4 or s7)
                job_complete = s5
                job_failed = s9
                cjs.user_log_size = log_size
            except Exception:
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
                if cjs.job_wrapper.get_state() != model.Job.states.DELETED:
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
        external_id = job.job_runner_external_id
        failure_message = condor_stop(external_id)
        if failure_message:
            log.debug("(%s/%s). Failed to stop condor %s" % (external_id, failure_message))

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        # TODO Check if we need any changes here
        job_id = job.get_job_runner_external_id()
        galaxy_id_tag = job_wrapper.get_id_tag()
        if job_id is None:
            self.put( job_wrapper )
            return
        cjs = CondorJobState( job_wrapper=job_wrapper, files_dir=self.app.config.cluster_files_directory )
        cjs.job_id = str( job_id )
        cjs.command_line = job.get_command_line()
        cjs.job_wrapper = job_wrapper
        cjs.job_destination = job_wrapper.job_destination
        cjs.user_log = os.path.join( self.app.config.cluster_files_directory, 'galaxy_%s.condor.log' % galaxy_id_tag )
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

    def __old_state_paths( self, cjs ):
        """For recovery of jobs started prior to standardizing the naming of
        files in the AsychronousJobState object
        """
        if cjs.job_wrapper is not None:
            user_log = "%s/%s.condor.log" % (self.app.config.cluster_files_directory, cjs.job_wrapper.job_id)
            if not os.path.exists( cjs.user_log ) and os.path.exists( user_log ):
                cjs.output_file = "%s/%s.o" % (self.app.config.cluster_files_directory, cjs.job_wrapper.job_id)
                cjs.error_file = "%s/%s.e" % (self.app.config.cluster_files_directory, cjs.job_wrapper.job_id)
                cjs.job_file = "%s/galaxy_%s.sh" % (self.app.config.cluster_files_directory, cjs.job_wrapper.job_id)
                cjs.user_log = user_log
