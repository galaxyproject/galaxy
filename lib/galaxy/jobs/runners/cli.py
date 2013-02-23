"""
Job control via a command line interface (e.g. qsub/qstat), possibly over a remote connection (e.g. ssh).
"""

import os
import time
import glob
import logging
import threading
import subprocess

from Queue import Queue, Empty

from galaxy import model
from galaxy.jobs.runners import BaseJobRunner

log = logging.getLogger( __name__ )

__all__ = [ 'ShellJobRunner' ]

class RunnerJobState( object ):
    def __init__( self ):
        """
        Encapsulates state related to a job that is being run and that we need to monitor.
        """
        self.job_wrapper = None
        self.external_job_id = None
        self.old_state = None
        self.running = False
        self.job_file = None
        self.ofile = None
        self.efile = None
        self.runner_url = None

class ShellJobRunner( BaseJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    STOP_SIGNAL = object()
    def __init__( self, app ):
        """Initialize this job runner and start the monitor thread"""
        # Check if drmaa was importable, fail if not
        self.app = app
        self.sa_session = app.model.context
        self.remote_home_directory = None
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

        self.cli_shells = None
        self.cli_job_interfaces = None
        self.__load_cli_plugins()

        for i in range( nworkers ):
            worker = threading.Thread( target=self.run_next )
            worker.start()
            self.work_threads.append( worker )
        log.debug( "%d workers ready" % nworkers )

    def __load_cli_plugins(self):
        def __load(module_path, d):
            for file in glob.glob(os.path.join(os.path.join(os.getcwd(), 'lib', *module_path.split('.')), '*.py')):
                if os.path.basename(file).startswith('_'):
                    continue
                module_name = '%s.%s' % (module_path, os.path.basename(file).rsplit('.py', 1)[0])
                module = __import__(module_name)
                for comp in module_name.split( "." )[1:]:
                    module = getattr(module, comp)
                for name in module.__all__:
                    log.debug('Loaded cli plugin %s' % name)
                    d[name] = getattr(module, name)

        self.cli_shells = {}
        self.cli_job_interfaces = {}
        __load('galaxy.jobs.runners.cli_shell', self.cli_shells)
        __load('galaxy.jobs.runners.cli_job', self.cli_job_interfaces)

    def get_cli_plugins(self, runner_url):
        shell_params, job_params = runner_url.split('/')[2:4]
        # split 'foo=bar&baz=quux' into { 'foo' : 'bar', 'baz' : 'quux' }
        shell_params = dict ( [ ( k, v ) for k, v in [ kv.split('=', 1) for kv in shell_params.split('&') ] ] )
        job_params = dict ( [ ( k, v ) for k, v in [ kv.split('=', 1) for kv in job_params.split('&') ] ] )
        # load shell plugin
        shell = self.cli_shells[shell_params['plugin']](**shell_params)
        job_interface = self.cli_job_interfaces[job_params['plugin']](**job_params)
        return shell, job_interface

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

        # Get shell and job execution interface
        runner_url = job_wrapper.get_job_runner_url()
        shell, job_interface = self.get_cli_plugins(runner_url)

        # Change to queued state immediately
        job_wrapper.change_state( model.Job.states.QUEUED )

        # define job attributes
        ofile = "%s.gjout" % os.path.join(job_wrapper.working_directory, job_wrapper.get_id_tag())
        efile = "%s.gjerr" % os.path.join(job_wrapper.working_directory, job_wrapper.get_id_tag())
        ecfile = "%s.gjec" % os.path.join(job_wrapper.working_directory, job_wrapper.get_id_tag())
        job_name = "g%s_%s_%s" % ( job_wrapper.job_id, job_wrapper.tool.id, job_wrapper.user )

        # fill in the DRM's job run template
        script = job_interface.get_job_template(ofile, efile, job_name, job_wrapper, command_line, ecfile)
        script_file = "%s/galaxy_%s.sh" % (self.app.config.cluster_files_directory, job_wrapper.get_id_tag())

        try:
            fh = file(script_file, "w")
            fh.write(script)
            fh.close()
        except:
            job_wrapper.fail("failure preparing job script", exception=True)
            log.exception("failure running job %s" % job_wrapper.get_id_tag())
            return

        # job was deleted while we were preparing it
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.info("Job %s deleted by user before it entered the queue" % job_wrapper.get_id_tag())
            if self.app.config.cleanup_job in ("always", "onsuccess"):
                job_wrapper.cleanup()
            return

        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()

        log.debug("(%s) submitting file: %s" % (galaxy_id_tag, script_file ))
        log.debug("(%s) command is: %s" % (galaxy_id_tag, command_line ) )

        cmd_out = shell.execute(job_interface.submit(script_file))
        if cmd_out.returncode != 0:
            log.error('(%s) submission failed (stdout): %s' % (galaxy_id_tag, cmd_out.stdout))
            log.error('(%s) submission failed (stderr): %s' % (galaxy_id_tag, cmd_out.stderr))
            job_wrapper.fail("failure submitting job")
            return
        external_job_id = cmd_out.stdout.strip()
        if not external_job_id:
            log.error('(%s) submission did not return a job identifier, failing job' % galaxy_id_tag)
            job_wrapper.fail("failure submitting job")
            return

        log.info("(%s) queued with identifier: %s" % ( galaxy_id_tag, external_job_id ) )

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_runner( runner_url, external_job_id )

        # Store state information for job
        runner_job_state = RunnerJobState()
        runner_job_state.job_wrapper = job_wrapper
        runner_job_state.external_job_id = external_job_id
        runner_job_state.ofile = ofile
        runner_job_state.efile = efile
        runner_job_state.ecfile = ecfile
        runner_job_state.job_file = script_file
        runner_job_state.old_state = 'new'
        runner_job_state.running = False
        runner_job_state.runner_url = runner_url
        
        # Add to our 'queue' of jobs to monitor
        self.monitor_queue.put( runner_job_state )

    def monitor( self ):
        """
        Watches jobs currently in the PBS queue and deals with state changes
        (queued to running) and job completion
        """
        while 1:
            # Take any new watched jobs and put them on the monitor list
            try:
                while 1: 
                    runner_job_state = self.monitor_queue.get_nowait()
                    if runner_job_state is self.STOP_SIGNAL:
                        # TODO: This is where any cleanup would occur
                        return
                    self.watched.append( runner_job_state )
            except Empty:
                pass
            # Iterate over the list of watched jobs and check state
            try:
                self.check_watched_items()
            except:
                log.exception('Uncaught exception checking job state:')
            # Sleep a bit before the next state check
            time.sleep( 15 )
            
    def check_watched_items( self ):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []

        job_states = self.__get_job_states()

        for runner_job_state in self.watched:
            external_job_id = runner_job_state.external_job_id
            galaxy_job_id = runner_job_state.job_wrapper.job_id
            old_state = runner_job_state.old_state
            state = job_states.get(external_job_id, None)
            if state is None:
                log.debug("(%s/%s) job not found in batch state check" % ( galaxy_job_id, external_job_id ) )
                shell, job_interface = self.get_cli_plugins(runner_job_state.runner_url)
                cmd_out = shell.execute(job_interface.get_single_status(external_job_id))
                state = job_interface.parse_single_status(cmd_out.stdout, external_job_id)
                if state == model.Job.states.OK:
                    log.debug('(%s/%s) job execution finished, running job wrapper finish method' % ( galaxy_job_id, external_job_id ) )
                    self.work_queue.put( ( 'finish', runner_job_state ) )
                    continue
                else:
                    log.warning('(%s/%s) job not found in batch state check, but found in individual state check' % ( galaxy_job_id, external_job_id ) )
                    if state != old_state:
                        runner_job_state.job_wrapper.change_state( state )
            else:
                if state != old_state:
                    log.debug("(%s/%s) state change: %s" % ( galaxy_job_id, external_job_id, state ) )
                    runner_job_state.job_wrapper.change_state( state )
                if state == model.Job.states.RUNNING and not runner_job_state.running:
                    runner_job_state.running = True
                    runner_job_state.job_wrapper.change_state( model.Job.states.RUNNING )
            runner_job_state.old_state = state
            new_watched.append( runner_job_state )
        # Replace the watch list with the updated version
        self.watched = new_watched

    def __get_job_states(self):
        runner_urls = {}
        job_states = {}
        for runner_job_state in self.watched:
            # remove any job plugin options from the runner URL since they should not affect doing a batch state check
            runner_url = runner_job_state.runner_url.split('/')
            job_params = runner_url[3]
            job_params = dict ( [ ( k, v ) for k, v in [ kv.split('=', 1) for kv in job_params.split('&') ] ] )
            runner_url[3] = 'plugin=%s' % job_params['plugin']
            runner_url = '/'.join(runner_url)
            # create the list of job ids to check for each runner url
            if runner_job_state.runner_url not in runner_urls:
                runner_urls[runner_job_state.runner_url] = [runner_job_state.external_job_id]
            else:
                runner_urls[runner_job_state.runner_url].append(runner_job_state.external_job_id)
        # check each runner url for the listed job ids
        for runner_url, job_ids in runner_urls.items():
            shell, job_interface = self.get_cli_plugins(runner_url)
            cmd_out = shell.execute(job_interface.get_status(job_ids))
            assert cmd_out.returncode == 0, cmd_out.stderr
            job_states.update(job_interface.parse_status(cmd_out.stdout, job_ids))
        return job_states
        
    def finish_job( self, runner_job_state ):
        """
        Get the output/error for a finished job, pass to `job_wrapper.finish`
        and cleanup all the DRM temporary files.
        """
        ofile = runner_job_state.ofile
        efile = runner_job_state.efile
        ecfile = runner_job_state.ecfile
        job_file = runner_job_state.job_file
        # collect the output
        # wait for the files to appear
        which_try = 0
        while which_try < (self.app.config.retry_job_output_collection + 1):
            try:
                ofh = file(ofile, "r")
                efh = file(efile, "r")
                ecfh = file(ecfile, "r")
                stdout = ofh.read( 32768 )
                stderr = efh.read( 32768 )
                exit_code = ecfh.read(32)
                which_try = (self.app.config.retry_job_output_collection + 1)
            except:
                if which_try == self.app.config.retry_job_output_collection:
                    stdout = ''
                    stderr = 'Job output not returned from cluster'
                    exit_code = 0
                    log.debug( stderr )
                else:
                    time.sleep(1)
                which_try += 1

        try:
            runner_job_state.job_wrapper.finish( stdout, stderr, exit_code )
        except:
            log.exception("Job wrapper finish method failed")

    def fail_job( self, job_state ):
        """
        Seperated out so we can use the worker threads for it.
        """
        self.stop_job( self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id ) )
        job_state.job_wrapper.fail( job_state.fail_message )

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
        """Attempts to delete a dispatched job"""
        try:
            shell, job_interface = self.get_cli_plugins( job.job_runner )
            cmd_out = shell.execute(job_interface.delete( job.job_runner_external_id ))
            assert cmd_out.returncode == 0, cmd_out.stderr
            log.debug( "(%s/%s) Terminated at user's request" % ( job.id, job.job_runner_external_id ) )
        except Exception, e:
            log.debug( "(%s/%s) User killed running job, but error encountered during termination: %s" % ( job.id, job.job_runner_external_id, e ) )

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_id = job.get_job_runner_external_id()
        if job_id is None:
            self.put( job_wrapper )
            return
        runner_job_state = RunnerJobState()
        runner_job_state.ofile = "%s.gjout" % os.path.join(job_wrapper.working_directory, job_wrapper.get_id_tag())
        runner_job_state.efile = "%s.gjerr" % os.path.join(job_wrapper.working_directory, job_wrapper.get_id_tag())
        runner_job_state.ecfile = "%s.gjec" % os.path.join(job_wrapper.working_directory, job_wrapper.get_id_tag())
        runner_job_state.job_file = "%s/galaxy_%s.sh" % (self.app.config.cluster_files_directory, job_wrapper.get_id_tag())
        runner_job_state.external_job_id = str( job_id )
        job_wrapper.command_line = job.command_line
        runner_job_state.job_wrapper = job_wrapper
        runner_job_state.runner_url = job.job_runner_name
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the runner monitor queue" % ( job.id, job.job_runner_external_id ) )
            runner_job_state.old_state = model.Job.states.RUNNING
            runner_job_state.running = True
            self.monitor_queue.put( runner_job_state )
        elif job.state == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in queued state, adding to the runner monitor queue" % ( job.id, job.job_runner_external_id ) )
            runner_job_state.old_state = model.Job.states.QUEUED
            runner_job_state.running = False
            self.monitor_queue.put( runner_job_state )
