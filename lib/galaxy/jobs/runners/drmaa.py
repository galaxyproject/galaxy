"""
Job control via the DRMAA API.
"""
from __future__ import absolute_import

import json
import logging
import os
import string
import subprocess
import time

from galaxy import model
from galaxy.jobs import JobDestination
from galaxy.jobs.handler import DEFAULT_JOB_PUT_FAILURE_MESSAGE
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)
from galaxy.util import asbool

drmaa = None

log = logging.getLogger( __name__ )

__all__ = ( 'DRMAAJobRunner', )

RETRY_EXCEPTIONS_LOWER = frozenset(['invalidjobexception', 'internalexception'])


class DRMAAJobRunner( AsynchronousJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "DRMAARunner"
    restrict_job_name_length = 15

    def __init__( self, app, nworkers, **kwargs ):
        """Start the job runner"""
        global drmaa

        runner_param_specs = {
            'drmaa_library_path': dict( map=str, default=os.environ.get( 'DRMAA_LIBRARY_PATH', None ) ) }
        for retry_exception in RETRY_EXCEPTIONS_LOWER:
            runner_param_specs[retry_exception + '_state'] = dict( map=str, valid=lambda x: x in ( model.Job.states.OK, model.Job.states.ERROR ), default=model.Job.states.OK )
            runner_param_specs[retry_exception + '_retries'] = dict( map=int, valid=lambda x: int >= 0, default=0 )

        if 'runner_param_specs' not in kwargs:
            kwargs[ 'runner_param_specs' ] = dict()
        kwargs[ 'runner_param_specs' ].update( runner_param_specs )

        super( DRMAAJobRunner, self ).__init__( app, nworkers, **kwargs )

        # This allows multiple drmaa runners (although only one per handler) in the same job config file
        if 'drmaa_library_path' in kwargs:
            log.info( 'Overriding DRMAA_LIBRARY_PATH due to runner plugin parameter: %s', self.runner_params.drmaa_library_path )
            os.environ['DRMAA_LIBRARY_PATH'] = self.runner_params.drmaa_library_path

        # Import is delayed until runner initialization to allow for the
        # drmaa_library_path plugin param to override $DRMAA_LIBRARY_PATH
        try:
            drmaa = __import__( "drmaa" )
        except (ImportError, RuntimeError) as exc:
            raise exc.__class__('The Python drmaa package is required to use this '
                                'feature, please install it or correct the '
                                'following error:\n%s: %s' %
                                (exc.__class__.__name__, str(exc)))
        from pulsar.managers.util.drmaa import DrmaaSessionFactory

        # Subclasses may need access to state constants
        self.drmaa_job_states = drmaa.JobState

        # Descriptive state strings pulled from the drmaa lib itself
        self.drmaa_job_state_strings = {
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

        # Ensure a DRMAA session exists and is initialized
        self.ds = DrmaaSessionFactory().get()

        self.userid = None

        self._init_monitor_thread()
        self._init_worker_threads()

    def url_to_destination(self, url):
        """Convert a legacy URL to a job destination"""
        if not url:
            return
        native_spec = url.split('/')[2]
        if native_spec:
            params = dict( nativeSpecification=native_spec )
            log.debug( "Converted URL '%s' to destination runner=drmaa, params=%s" % ( url, params ) )
            return JobDestination( runner='drmaa', params=params )
        else:
            log.debug( "Converted URL '%s' to destination runner=drmaa" % url )
            return JobDestination( runner='drmaa' )

    def get_native_spec( self, url ):
        """Get any native DRM arguments specified by the site configuration"""
        try:
            return url.split('/')[2] or None
        except:
            return None

    def queue_job( self, job_wrapper ):
        """Create job script and submit it to the DRM"""
        # prepare the job

        # external_runJob_script can be None, in which case it's not used.
        external_runjob_script = job_wrapper.get_destination_configuration("drmaa_external_runjob_script", None)

        include_metadata = asbool( job_wrapper.job_destination.params.get( "embed_metadata_in_job", True) )
        if not self.prepare_job( job_wrapper, include_metadata=include_metadata):
            return

        # get configured job destination
        job_destination = job_wrapper.job_destination

        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()

        job_name = self._job_name(job_wrapper)
        ajs = AsynchronousJobState( files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper, job_name=job_name )

        # set up the drmaa job template
        jt = dict(
            remoteCommand=ajs.job_file,
            jobName=ajs.job_name,
            workingDirectory=job_wrapper.working_directory,
            outputPath=":%s" % ajs.output_file,
            errorPath=":%s" % ajs.error_file
        )

        # Avoid a jt.exitCodePath for now - it's only used when finishing.
        native_spec = job_destination.params.get('nativeSpecification', None)
        if native_spec is not None:
            jt['nativeSpecification'] = native_spec

        # fill in the DRM's job run template
        script = self.get_job_file(job_wrapper, exit_code_path=ajs.exit_code_file)
        try:
            self.write_executable_script( ajs.job_file, script )
        except:
            job_wrapper.fail( "failure preparing job script", exception=True )
            log.exception( "(%s) failure writing job script" % galaxy_id_tag )
            return

        # job was deleted while we were preparing it
        if job_wrapper.get_state() == model.Job.states.DELETED:
            log.debug( "(%s) Job deleted by user before it entered the queue" % galaxy_id_tag )
            if job_wrapper.cleanup_job in ( "always", "onsuccess" ):
                job_wrapper.cleanup()
            return

        log.debug( "(%s) submitting file %s", galaxy_id_tag, ajs.job_file )
        if native_spec:
            log.debug( "(%s) native specification is: %s", galaxy_id_tag, native_spec )

        # runJob will raise if there's a submit problem
        if external_runjob_script is None:
            # TODO: create a queue for retrying submission indefinitely
            # TODO: configurable max tries and sleep
            trynum = 0
            external_job_id = None
            fail_msg = None
            while external_job_id is None and trynum < 5:
                try:
                    external_job_id = self.ds.run_job(**jt)
                    break
                except ( drmaa.InternalException, drmaa.DeniedByDrmException ) as e:
                    trynum += 1
                    log.warning( '(%s) drmaa.Session.runJob() failed, will retry: %s', galaxy_id_tag, e )
                    fail_msg = "Unable to run this job due to a cluster error, please retry it later"
                    time.sleep( 5 )
                except:
                    log.exception( '(%s) drmaa.Session.runJob() failed unconditionally', galaxy_id_tag )
                    trynum = 5
            else:
                log.error( "(%s) All attempts to submit job failed" % galaxy_id_tag )
                if not fail_msg:
                    fail_msg = DEFAULT_JOB_PUT_FAILURE_MESSAGE
                job_wrapper.fail( fail_msg )
                return
        else:
            job_wrapper.change_ownership_for_run()
            # if user credentials are not available, use galaxy credentials (if permitted)
            allow_guests = asbool(job_wrapper.job_destination.params.get( "allow_guests", False) )
            pwent = job_wrapper.user_system_pwent
            if pwent is None:
                if not allow_guests:
                    fail_msg = "User %s is not mapped to any real user, and not permitted to start jobs." % job_wrapper.user
                    job_wrapper.fail( fail_msg )
                    return
                pwent = job_wrapper.galaxy_system_pwent
            log.debug( '(%s) submitting with credentials: %s [uid: %s]' % ( galaxy_id_tag, pwent[0], pwent[2] ) )
            filename = self.store_jobtemplate(job_wrapper, jt)
            self.userid = pwent[2]
            external_job_id = self.external_runjob(external_runjob_script, filename, pwent[2]).strip()
        log.info( "(%s) queued as %s" % ( galaxy_id_tag, external_job_id ) )

        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_job_destination( job_destination, external_job_id )

        # Store DRM related state information for job
        ajs.job_id = external_job_id
        ajs.old_state = 'new'
        ajs.job_destination = job_destination

        # Add to our 'queue' of jobs to monitor
        self.monitor_queue.put( ajs )

    def _complete_terminal_job( self, ajs, drmaa_state, **kwargs ):
        """
        Handle a job upon its termination in the DRM. This method is meant to
        be overridden by subclasses to improve post-mortem and reporting of
        failures.
        Returns True if job was not actually terminal, None otherwise.
        """
        if drmaa_state == drmaa.JobState.FAILED:
            if ajs.job_wrapper.get_state() != model.Job.states.DELETED:
                ajs.stop_job = False
                ajs.fail_message = "The cluster DRM system terminated this job"
                self.work_queue.put( ( self.fail_job, ajs ) )
        elif drmaa_state == drmaa.JobState.DONE:
            # External metadata processing for external runjobs
            external_metadata = not asbool( ajs.job_wrapper.job_destination.params.get( "embed_metadata_in_job", True) )
            if external_metadata:
                self._handle_metadata_externally( ajs.job_wrapper, resolve_requirements=True )
            if ajs.job_wrapper.get_state() != model.Job.states.DELETED:
                self.work_queue.put( ( self.finish_job, ajs ) )

    def check_watched_items( self ):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []
        for ajs in self.watched:
            external_job_id = ajs.job_id
            galaxy_id_tag = ajs.job_wrapper.get_id_tag()
            old_state = ajs.old_state
            try:
                assert external_job_id not in ( None, 'None' ), '(%s/%s) Invalid job id' % ( galaxy_id_tag, external_job_id )
                state = self.ds.job_status( external_job_id )
                # Reset exception retries
                for retry_exception in RETRY_EXCEPTIONS_LOWER:
                    setattr( ajs, retry_exception + '_retries', 0)
            except ( drmaa.InternalException, drmaa.InvalidJobException ) as e:
                ecn = type(e).__name__
                retry_param = ecn.lower() + '_retries'
                state_param = ecn.lower() + '_state'
                retries = getattr( ajs, retry_param, 0 )
                log.warning("(%s/%s) unable to check job status because of %s exception for %d consecutive tries: %s", galaxy_id_tag, external_job_id, ecn, retries + 1, e)
                if self.runner_params[ retry_param ] > 0:
                    if retries < self.runner_params[ retry_param ]:
                        # will retry check on next iteration
                        setattr( ajs, retry_param, retries + 1 )
                        new_watched.append( ajs )
                        continue
                if self.runner_params[ state_param ] == model.Job.states.OK:
                    log.warning( "(%s/%s) job will now be finished OK", galaxy_id_tag, external_job_id )
                    self.work_queue.put( ( self.finish_job, ajs ) )
                elif self.runner_params[ state_param ] == model.Job.states.ERROR:
                    log.warning( "(%s/%s) job will now be errored", galaxy_id_tag, external_job_id )
                    self.work_queue.put( ( self.fail_job, ajs ) )
                else:
                    raise Exception( "%s is set to an invalid value (%s), this should not be possible. See galaxy.jobs.drmaa.__init__()", state_param, self.runner_params[ state_param ] )
                continue
            except drmaa.DrmCommunicationException as e:
                log.warning( "(%s/%s) unable to communicate with DRM: %s", galaxy_id_tag, external_job_id, e )
                new_watched.append( ajs )
                continue
            except Exception as e:
                # so we don't kill the monitor thread
                log.exception( "(%s/%s) unable to check job status: %s" % ( galaxy_id_tag, external_job_id, e ) )
                log.warning( "(%s/%s) job will now be errored" % ( galaxy_id_tag, external_job_id ) )
                ajs.fail_message = "Cluster could not complete job"
                self.work_queue.put( ( self.fail_job, ajs ) )
                continue
            if state != old_state:
                log.debug( "(%s/%s) state change: %s" % ( galaxy_id_tag, external_job_id, self.drmaa_job_state_strings[state] ) )
            if state == drmaa.JobState.RUNNING and not ajs.running:
                ajs.running = True
                ajs.job_wrapper.change_state( model.Job.states.RUNNING )
            if state in ( drmaa.JobState.FAILED, drmaa.JobState.DONE ):
                if self._complete_terminal_job( ajs, drmaa_state=state ) is not None:
                    # job was not actually terminal
                    state = ajs.old_state
                else:
                    continue
            if ajs.check_limits():
                self.work_queue.put( ( self.fail_job, ajs ) )
                continue
            ajs.old_state = state
            new_watched.append( ajs )
        # Replace the watch list with the updated version
        self.watched = new_watched

    def stop_job( self, job ):
        """Attempts to delete a job from the DRM queue"""
        try:
            ext_id = job.get_job_runner_external_id()
            assert ext_id not in ( None, 'None' ), 'External job id is None'
            kill_script = job.get_destination_configuration(self.app.config, "drmaa_external_killjob_script", None)
            if kill_script is None:
                self.ds.kill( ext_id )
            else:
                # FIXME: hardcoded path
                subprocess.Popen( [ '/usr/bin/sudo', '-E', kill_script, str( ext_id ), str( self.userid ) ], shell=False )
            log.debug( "(%s/%s) Removed from DRM queue at user's request" % ( job.get_id(), ext_id ) )
        except drmaa.InvalidJobException:
            log.debug( "(%s/%s) User killed running job, but it was already dead" % ( job.get_id(), ext_id ) )
        except Exception as e:
            log.debug( "(%s/%s) User killed running job, but error encountered removing from DRM queue: %s" % ( job.get_id(), ext_id, e ) )

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_id = job.get_job_runner_external_id()
        if job_id is None:
            self.put( job_wrapper )
            return
        ajs = AsynchronousJobState( files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper )
        ajs.job_id = str( job_id )
        ajs.command_line = job.get_command_line()
        ajs.job_wrapper = job_wrapper
        ajs.job_destination = job_wrapper.job_destination
        if job.state == model.Job.states.RUNNING:
            log.debug( "(%s/%s) is still in running state, adding to the DRM queue" % ( job.get_id(), job.get_job_runner_external_id() ) )
            ajs.old_state = drmaa.JobState.RUNNING
            ajs.running = True
            self.monitor_queue.put( ajs )
        elif job.get_state() == model.Job.states.QUEUED:
            log.debug( "(%s/%s) is still in DRM queued state, adding to the DRM queue" % ( job.get_id(), job.get_job_runner_external_id() ) )
            ajs.old_state = drmaa.JobState.QUEUED_ACTIVE
            ajs.running = False
            self.monitor_queue.put( ajs )

    def store_jobtemplate(self, job_wrapper, jt):
        """ Stores the content of a DRMAA JobTemplate object in a file as a JSON string.
        Path is hard-coded, but it's no worse than other path in this module.
        Uses Galaxy's JobID, so file is expected to be unique."""
        filename = "%s/%s.jt_json" % (self.app.config.cluster_files_directory, job_wrapper.get_id_tag())
        with open(filename, 'w+') as fp:
            json.dump(jt, fp)
        log.debug( '(%s) Job script for external submission is: %s' % ( job_wrapper.job_id, filename ) )
        return filename

    def external_runjob(self, external_runjob_script, jobtemplate_filename, username):
        """ runs an external script the will QSUB a new job.
        The external script will be run with sudo, and will setuid() to the specified user.
        Effectively, will QSUB as a different user (then the one used by Galaxy).
        """
        script_parts = external_runjob_script.split()
        script = script_parts[0]
        command = [ '/usr/bin/sudo', '-E', script]
        for script_argument in script_parts[1:]:
            command.append(script_argument)

        command.extend( [ str(username), jobtemplate_filename ] )
        log.info("Running command %s" % command)
        p = subprocess.Popen(command,
                             shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdoutdata, stderrdata) = p.communicate()
        exitcode = p.returncode
        # os.unlink(jobtemplate_filename)
        if exitcode != 0:
            # There was an error in the child process
            raise RuntimeError("External_runjob failed (exit code %s)\nChild process reported error:\n%s" % (str(exitcode), stderrdata))
        if not stdoutdata.strip():
            raise RuntimeError("External_runjob did return the job id: %s" % (stdoutdata))

        # The expected output is a single line containing a single numeric value:
        # the DRMAA job-ID. If not the case, will throw an error.
        jobId = stdoutdata
        return jobId

    def _job_name(self, job_wrapper):
        external_runjob_script = job_wrapper.get_destination_configuration("drmaa_external_runjob_script", None)
        galaxy_id_tag = job_wrapper.get_id_tag()

        # define job attributes
        job_name = 'g%s' % galaxy_id_tag
        if job_wrapper.tool.old_id:
            job_name += '_%s' % job_wrapper.tool.old_id
        if external_runjob_script is None:
            job_name += '_%s' % job_wrapper.user
        job_name = ''.join( x if x in ( string.letters + string.digits + '_' ) else '_' for x in job_name )
        if self.restrict_job_name_length:
            job_name = job_name[:self.restrict_job_name_length]
        return job_name
