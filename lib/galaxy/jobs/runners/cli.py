"""
Job control via a command line interface (e.g. qsub/qstat), possibly over a remote connection (e.g. ssh).
"""

import logging

from galaxy import model
from galaxy.jobs import JobDestination
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)
from galaxy.util import asbool

from .util.cli import CliInterface, split_params

log = logging.getLogger( __name__ )

__all__ = ( 'ShellJobRunner', )

DEFAULT_EMBED_METADATA_IN_JOB = True


class ShellJobRunner( AsynchronousJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "ShellRunner"

    def __init__( self, app, nworkers ):
        """Start the job runner """
        super( ShellJobRunner, self ).__init__( app, nworkers )

        self.cli_interface = CliInterface()
        self._init_monitor_thread()
        self._init_worker_threads()

    def get_cli_plugins( self, shell_params, job_params ):
        return self.cli_interface.get_plugins( shell_params, job_params )

    def url_to_destination( self, url ):
        params = {}
        shell_params, job_params = url.split( '/' )[ 2:4 ]
        # split 'foo=bar&baz=quux' into { 'foo' : 'bar', 'baz' : 'quux' }
        shell_params = dict( [ ( 'shell_' + k, v ) for k, v in [ kv.split( '=', 1 ) for kv in shell_params.split( '&' ) ] ] )
        job_params = dict( [ ( 'job_' + k, v ) for k, v in [ kv.split( '=', 1 ) for kv in job_params.split( '&' ) ] ] )
        params.update( shell_params )
        params.update( job_params )
        log.debug( "Converted URL '%s' to destination runner=cli, params=%s" % ( url, params ) )
        # Create a dynamic JobDestination
        return JobDestination( runner='cli', params=params )

    def parse_destination_params( self, params ):
        return split_params( params )

    def queue_job( self, job_wrapper ):
        """Create job script and submit it to the DRM"""
        # prepare the job
        include_metadata = asbool( job_wrapper.job_destination.params.get( "embed_metadata_in_job", DEFAULT_EMBED_METADATA_IN_JOB ) )
        if not self.prepare_job( job_wrapper, include_metadata=include_metadata ):
            return

        # Get shell and job execution interface
        job_destination = job_wrapper.job_destination
        shell_params, job_params = self.parse_destination_params(job_destination.params)
        shell, job_interface = self.get_cli_plugins(shell_params, job_params)

        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()

        # define job attributes
        ajs = AsynchronousJobState( files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper )

        job_file_kwargs = job_interface.job_script_kwargs(ajs.output_file, ajs.error_file, ajs.job_name)
        script = self.get_job_file(
            job_wrapper,
            exit_code_path=ajs.exit_code_file,
            **job_file_kwargs
        )

        try:
            self.write_executable_script( ajs.job_file, script )
        except:
            log.exception("(%s) failure writing job script" % galaxy_id_tag )
            job_wrapper.fail("failure preparing job script", exception=True)
            return

        # job was deleted while we were preparing it
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.info("(%s) Job deleted by user before it entered the queue" % galaxy_id_tag )
            if job_wrapper.cleanup_job in ("always", "onsuccess"):
                job_wrapper.cleanup()
            return

        log.debug( "(%s) submitting file: %s" % ( galaxy_id_tag, ajs.job_file ) )

        cmd_out = shell.execute(job_interface.submit(ajs.job_file))
        if cmd_out.returncode != 0:
            log.error('(%s) submission failed (stdout): %s' % (galaxy_id_tag, cmd_out.stdout))
            log.error('(%s) submission failed (stderr): %s' % (galaxy_id_tag, cmd_out.stderr))
            job_wrapper.fail("failure submitting job")
            return
        # Some job runners return something like 'Submitted batch job XXXX'
        # Strip and split to get job ID.
        external_job_id = cmd_out.stdout.strip().split()[-1]
        if not external_job_id:
            log.error('(%s) submission did not return a job identifier, failing job' % galaxy_id_tag)
            job_wrapper.fail("failure submitting job")
            return

        log.info("(%s) queued with identifier: %s" % ( galaxy_id_tag, external_job_id ) )

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_job_destination( job_destination, external_job_id )

        # Store state information for job
        ajs.job_id = external_job_id
        ajs.old_state = 'new'
        ajs.job_destination = job_destination

        # Add to our 'queue' of jobs to monitor
        self.monitor_queue.put( ajs )

    def check_watched_items( self ):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []

        job_states = self.__get_job_states()

        for ajs in self.watched:
            external_job_id = ajs.job_id
            id_tag = ajs.job_wrapper.get_id_tag()
            old_state = ajs.old_state
            state = job_states.get(external_job_id, None)
            if state is None:
                if ajs.job_wrapper.get_state() == model.Job.states.DELETED:
                    continue

                external_metadata = not asbool( ajs.job_wrapper.job_destination.params.get( "embed_metadata_in_job", DEFAULT_EMBED_METADATA_IN_JOB ) )
                if external_metadata:
                    self._handle_metadata_externally( ajs.job_wrapper, resolve_requirements=True )

                log.debug("(%s/%s) job not found in batch state check" % ( id_tag, external_job_id ) )
                shell_params, job_params = self.parse_destination_params(ajs.job_destination.params)
                shell, job_interface = self.get_cli_plugins(shell_params, job_params)
                cmd_out = shell.execute(job_interface.get_single_status(external_job_id))
                state = job_interface.parse_single_status(cmd_out.stdout, external_job_id)
                if state == model.Job.states.OK:
                    log.debug('(%s/%s) job execution finished, running job wrapper finish method' % ( id_tag, external_job_id ) )
                    self.work_queue.put( ( self.finish_job, ajs ) )
                    continue
                else:
                    log.warning('(%s/%s) job not found in batch state check, but found in individual state check' % ( id_tag, external_job_id ) )
                    if state != old_state:
                        ajs.job_wrapper.change_state( state )
            else:
                if state != old_state:
                    log.debug("(%s/%s) state change: from %s to %s" % ( id_tag, external_job_id, old_state, state ) )
                    ajs.job_wrapper.change_state( state )
                if state == model.Job.states.RUNNING and not ajs.running:
                    ajs.running = True
                    ajs.job_wrapper.change_state( model.Job.states.RUNNING )
            ajs.old_state = state
            if state == model.Job.states.OK:
                self.work_queue.put( ( self.finish_job, ajs ) )
            else:
                new_watched.append( ajs )
        # Replace the watch list with the updated version
        self.watched = new_watched

    def __get_job_states(self):
        job_destinations = {}
        job_states = {}
        # unique the list of destinations
        for ajs in self.watched:
            if ajs.job_destination.id not in job_destinations:
                job_destinations[ajs.job_destination.id] = dict( job_destination=ajs.job_destination, job_ids=[ ajs.job_id ] )
            else:
                job_destinations[ajs.job_destination.id]['job_ids'].append( ajs.job_id )
        # check each destination for the listed job ids
        for job_destination_id, v in job_destinations.items():
            job_destination = v['job_destination']
            job_ids = v['job_ids']
            shell_params, job_params = self.parse_destination_params(job_destination.params)
            shell, job_interface = self.get_cli_plugins(shell_params, job_params)
            cmd_out = shell.execute(job_interface.get_status(job_ids))
            assert cmd_out.returncode == 0, cmd_out.stderr
            job_states.update(job_interface.parse_status(cmd_out.stdout, job_ids))
        return job_states

    def stop_job( self, job ):
        """Attempts to delete a dispatched job"""
        try:
            shell_params, job_params = self.parse_destination_params(job.destination_params)
            shell, job_interface = self.get_cli_plugins(shell_params, job_params)
            cmd_out = shell.execute(job_interface.delete( job.job_runner_external_id ))
            assert cmd_out.returncode == 0, cmd_out.stderr
            log.debug( "(%s/%s) Terminated at user's request" % ( job.id, job.job_runner_external_id ) )
        except Exception as e:
            log.debug( "(%s/%s) User killed running job, but error encountered during termination: %s" % ( job.id, job.job_runner_external_id, e ) )

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_id = job.get_job_runner_external_id()
        if job_id is None:
            self.put( job_wrapper )
            return
        ajs = AsynchronousJobState( files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper )
        ajs.job_id = str( job_id )
        ajs.command_line = job.command_line
        ajs.job_wrapper = job_wrapper
        ajs.job_destination = job_wrapper.job_destination
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the runner monitor queue" % ( job.id, job.job_runner_external_id ) )
            ajs.old_state = model.Job.states.RUNNING
            ajs.running = True
            self.monitor_queue.put( ajs )
        elif job.state == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in queued state, adding to the runner monitor queue" % ( job.id, job.job_runner_external_id ) )
            ajs.old_state = model.Job.states.QUEUED
            ajs.running = False
            self.monitor_queue.put( ajs )
