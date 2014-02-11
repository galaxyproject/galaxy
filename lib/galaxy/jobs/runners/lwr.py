import logging

from galaxy import model
from galaxy.jobs.runners import AsynchronousJobState, AsynchronousJobRunner
from galaxy.jobs import ComputeEnvironment
from galaxy.jobs import JobDestination
from galaxy.jobs.command_factory import build_command
from galaxy.util import string_as_bool_or_none
from galaxy.util import in_directory
from galaxy.util.bunch import Bunch

import errno
from time import sleep
import os

from .lwr_client import ClientManager, url_to_destination_params
from .lwr_client import finish_job as lwr_finish_job
from .lwr_client import submit_job as lwr_submit_job
from .lwr_client import ClientJobDescription
from .lwr_client import LwrOutputs
from .lwr_client import GalaxyOutputs
from .lwr_client import PathMapper

log = logging.getLogger( __name__ )

__all__ = [ 'LwrJobRunner' ]

NO_REMOTE_GALAXY_FOR_METADATA_MESSAGE = "LWR misconfiguration - LWR client configured to set metadata remotely, but remote LWR isn't properly configured with a galaxy_home directory."
NO_REMOTE_DATATYPES_CONFIG = "LWR client is configured to use remote datatypes configuration when setting metadata externally, but LWR is not configured with this information. Defaulting to datatypes_conf.xml."


class LwrJobRunner( AsynchronousJobRunner ):
    """
    LWR Job Runner
    """
    runner_name = "LWRRunner"

    def __init__( self, app, nworkers, transport=None, cache=None ):
        """Start the job runner """
        super( LwrJobRunner, self ).__init__( app, nworkers )
        self._init_monitor_thread()
        self._init_worker_threads()
        client_manager_kwargs = {'transport_type': transport, 'cache': string_as_bool_or_none(cache)}
        self.client_manager = ClientManager(**client_manager_kwargs)

    def url_to_destination( self, url ):
        """Convert a legacy URL to a job destination"""
        return JobDestination( runner="lwr", params=url_to_destination_params( url ) )

    def check_watched_item(self, job_state):
        try:
            client = self.get_client_from_state(job_state)
            status = client.get_status()
        except Exception:
            # An orphaned job was put into the queue at app startup, so remote server went down
            # either way we are done I guess.
            self.mark_as_finished(job_state)
            return None
        if status == "complete":
            self.mark_as_finished(job_state)
            return None
        if status == "running" and not job_state.running:
            job_state.running = True
            job_state.job_wrapper.change_state( model.Job.states.RUNNING )
        return job_state

    def queue_job(self, job_wrapper):
        job_destination = job_wrapper.job_destination

        command_line, client, remote_job_config = self.__prepare_job( job_wrapper, job_destination )

        if not command_line:
            return

        try:
            dependency_resolution = LwrJobRunner.__dependency_resolution( client )
            remote_dependency_resolution = dependency_resolution == "remote"
            requirements = job_wrapper.tool.requirements if remote_dependency_resolution else []
            rewrite_paths = not LwrJobRunner.__rewrite_parameters( client )
            client_job_description = ClientJobDescription(
                command_line=command_line,
                output_files=self.get_output_files(job_wrapper),
                input_files=self.get_input_files(job_wrapper),
                working_directory=job_wrapper.working_directory,
                tool=job_wrapper.tool,
                config_files=job_wrapper.extra_filenames,
                requirements=requirements,
                version_file=job_wrapper.get_version_string_path(),
                rewrite_paths=rewrite_paths,
            )
            job_id = lwr_submit_job(client, client_job_description, remote_job_config)
            log.info("lwr job submitted with job_id %s" % job_id)
            job_wrapper.set_job_destination( job_destination, job_id )
            job_wrapper.change_state( model.Job.states.QUEUED )
        except Exception:
            job_wrapper.fail( "failure running job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        lwr_job_state = AsynchronousJobState()
        lwr_job_state.job_wrapper = job_wrapper
        lwr_job_state.job_id = job_id
        lwr_job_state.old_state = True
        lwr_job_state.running = False
        lwr_job_state.job_destination = job_destination
        self.monitor_job(lwr_job_state)

    def __prepare_job(self, job_wrapper, job_destination):
        """ Build command-line and LWR client for this job. """
        command_line = None
        client = None
        remote_job_config = None
        try:
            client = self.get_client_from_wrapper(job_wrapper)
            tool = job_wrapper.tool
            remote_job_config = client.setup(tool.id, tool.version)
            rewrite_parameters = LwrJobRunner.__rewrite_parameters( client )
            prepare_kwds = {}
            if rewrite_parameters:
                compute_environment = LwrComputeEnvironment( client, job_wrapper, remote_job_config )
                prepare_kwds[ 'compute_environment' ] = compute_environment
            job_wrapper.prepare( **prepare_kwds )
            self.__prepare_input_files_locally(job_wrapper)
            remote_metadata = LwrJobRunner.__remote_metadata( client )
            remote_work_dir_copy = LwrJobRunner.__remote_work_dir_copy( client )
            dependency_resolution = LwrJobRunner.__dependency_resolution( client )
            metadata_kwds = self.__build_metadata_configuration(client, job_wrapper, remote_metadata, remote_job_config)
            remote_command_params = dict(
                working_directory=remote_job_config['working_directory'],
                metadata_kwds=metadata_kwds,
                dependency_resolution=dependency_resolution,
            )
            command_line = build_command(
                self,
                job_wrapper=job_wrapper,
                include_metadata=remote_metadata,
                include_work_dir_outputs=remote_work_dir_copy,
                remote_command_params=remote_command_params,
            )
        except Exception:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)

        # If we were able to get a command line, run the job
        if not command_line:
            job_wrapper.finish( '', '' )

        return command_line, client, remote_job_config

    def __prepare_input_files_locally(self, job_wrapper):
        """Run task splitting commands locally."""
        prepare_input_files_cmds = getattr(job_wrapper, 'prepare_input_files_cmds', None)
        if prepare_input_files_cmds is not None:
            for cmd in prepare_input_files_cmds:  # run the commands to stage the input files
                if 0 != os.system(cmd):
                    raise Exception('Error running file staging command: %s' % cmd)
            job_wrapper.prepare_input_files_cmds = None  # prevent them from being used in-line

    def get_output_files(self, job_wrapper):
        output_paths = job_wrapper.get_output_fnames()
        return [ str( o ) for o in output_paths ]   # Force job_path from DatasetPath objects.

    def get_input_files(self, job_wrapper):
        input_paths = job_wrapper.get_input_paths()
        return [ str( i ) for i in input_paths ]  # Force job_path from DatasetPath objects.

    def get_client_from_wrapper(self, job_wrapper):
        job_id = job_wrapper.job_id
        if hasattr(job_wrapper, 'task_id'):
            job_id = "%s_%s" % (job_id, job_wrapper.task_id)
        params = job_wrapper.job_destination.params.copy()
        for key, value in params.iteritems():
            params[key] = model.User.expand_user_properties( job_wrapper.get_job().user, value )
        return self.get_client( params, job_id )

    def get_client_from_state(self, job_state):
        job_destination_params = job_state.job_destination.params
        job_id = job_state.job_id
        return self.get_client( job_destination_params, job_id )

    def get_client( self, job_destination_params, job_id ):
        return self.client_manager.get_client( job_destination_params, job_id )

    def finish_job( self, job_state ):
        stderr = stdout = ''
        job_wrapper = job_state.job_wrapper
        try:
            client = self.get_client_from_state(job_state)

            run_results = client.raw_check_complete()
            stdout = run_results.get('stdout', '')
            stderr = run_results.get('stderr', '')
            exit_code = run_results.get('returncode', None)
            lwr_outputs = LwrOutputs(run_results)
            # Use LWR client code to transfer/copy files back
            # and cleanup job if needed.
            completed_normally = \
                job_wrapper.get_state() not in [ model.Job.states.ERROR, model.Job.states.DELETED ]
            cleanup_job = self.app.config.cleanup_job
            remote_work_dir_copy = LwrJobRunner.__remote_work_dir_copy( client )
            if not remote_work_dir_copy:
                work_dir_outputs = self.get_work_dir_outputs( job_wrapper )
            else:
                # They have already been copied over to look like regular outputs remotely,
                # no need to handle them differently here.
                work_dir_outputs = []
            output_files = self.get_output_files( job_wrapper )
            galaxy_outputs = GalaxyOutputs(
                working_directory=job_wrapper.working_directory,
                work_dir_outputs=work_dir_outputs,
                output_files=output_files,
                version_file=job_wrapper.get_version_string_path(),
            )
            finish_args = dict( client=client,
                                job_completed_normally=completed_normally,
                                cleanup_job=cleanup_job,
                                galaxy_outputs=galaxy_outputs,
                                lwr_outputs=lwr_outputs )
            failed = lwr_finish_job( **finish_args )

            if failed:
                job_wrapper.fail("Failed to find or download one or more job outputs from remote server.", exception=True)
        except Exception:
            message = "Failed to communicate with remote job server."
            job_wrapper.fail( message, exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return
        if not LwrJobRunner.__remote_metadata( client ):
            self._handle_metadata_externally( job_wrapper, resolve_requirements=True )
        # Finish the job
        try:
            job_wrapper.finish( stdout, stderr, exit_code )
        except Exception:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

    def fail_job( self, job_state ):
        """
        Seperated out so we can use the worker threads for it.
        """
        self.stop_job( self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id ) )
        job_state.job_wrapper.fail( job_state.fail_message )

    def check_pid( self, pid ):
        try:
            os.kill( pid, 0 )
            return True
        except OSError, e:
            if e.errno == errno.ESRCH:
                log.debug( "check_pid(): PID %d is dead" % pid )
            else:
                log.warning( "check_pid(): Got errno %s when attempting to check PID %d: %s" % ( errno.errorcode[e.errno], pid, e.strerror ) )
            return False

    def stop_job( self, job ):
        #if our local job has JobExternalOutputMetadata associated, then our primary job has to have already finished
        job_ext_output_metadata = job.get_external_output_metadata()
        if job_ext_output_metadata:
            pid = job_ext_output_metadata[0].job_runner_external_pid  # every JobExternalOutputMetadata has a pid set, we just need to take from one of them
            if pid in [ None, '' ]:
                log.warning( "stop_job(): %s: no PID in database for job, unable to stop" % job.id )
                return
            pid = int( pid )
            if not self.check_pid( pid ):
                log.warning( "stop_job(): %s: PID %d was already dead or can't be signaled" % ( job.id, pid ) )
                return
            for sig in [ 15, 9 ]:
                try:
                    os.killpg( pid, sig )
                except OSError, e:
                    log.warning( "stop_job(): %s: Got errno %s when attempting to signal %d to PID %d: %s" % ( job.id, errno.errorcode[e.errno], sig, pid, e.strerror ) )
                    return  # give up
                sleep( 2 )
                if not self.check_pid( pid ):
                    log.debug( "stop_job(): %s: PID %d successfully killed with signal %d" % ( job.id, pid, sig ) )
                    return
                else:
                    log.warning( "stop_job(): %s: PID %d refuses to die after signaling TERM/KILL" % ( job.id, pid ) )
        else:
            # Remote kill
            lwr_url = job.job_runner_name
            job_id = job.job_runner_external_id
            log.debug("Attempt remote lwr kill of job with url %s and id %s" % (lwr_url, job_id))
            client = self.get_client(job.destination_params, job_id)
            client.kill()

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_state = AsynchronousJobState()
        job_state.job_id = str( job.get_job_runner_external_id() )
        job_state.runner_url = job_wrapper.get_job_runner_url()
        job_state.job_destination = job_wrapper.job_destination
        job_wrapper.command_line = job.get_command_line()
        job_state.job_wrapper = job_wrapper
        state = job.get_state()
        if state in [model.Job.states.RUNNING, model.Job.states.QUEUED]:
            log.debug( "(LWR/%s) is still in running state, adding to the LWR queue" % ( job.get_id()) )
            job_state.old_state = True
            job_state.running = state == model.Job.states.RUNNING
            self.monitor_queue.put( job_state )

    @staticmethod
    def __dependency_resolution( lwr_client ):
        dependency_resolution = lwr_client.destination_params.get( "dependency_resolution", "local" )
        if dependency_resolution not in ["none", "local", "remote"]:
            raise Exception("Unknown dependency_resolution value encountered %s" % dependency_resolution)
        return dependency_resolution

    @staticmethod
    def __remote_metadata( lwr_client ):
        remote_metadata = string_as_bool_or_none( lwr_client.destination_params.get( "remote_metadata", False ) )
        return remote_metadata

    @staticmethod
    def __remote_work_dir_copy( lwr_client ):
        # Right now remote metadata handling assumes from_work_dir outputs
        # have been copied over before it runs. So do that remotely. This is
        # not the default though because adding it to the command line is not
        # cross-platform (no cp on Windows) and its un-needed work outside
        # the context of metadata settting (just as easy to download from
        # either place.)
        return LwrJobRunner.__remote_metadata( lwr_client )

    @staticmethod
    def __use_remote_datatypes_conf( lwr_client ):
        """ When setting remote metadata, use integrated datatypes from this
        Galaxy instance or use the datatypes config configured via the remote
        LWR.

        Both options are broken in different ways for same reason - datatypes
        may not match. One can push the local datatypes config to the remote
        server - but there is no guarentee these datatypes will be defined
        there. Alternatively, one can use the remote datatype config - but
        there is no guarentee that it will contain all the datatypes available
        to this Galaxy.
        """
        use_remote_datatypes = string_as_bool_or_none( lwr_client.destination_params.get( "use_remote_datatypes", False ) )
        return use_remote_datatypes

    @staticmethod
    def __rewrite_parameters( lwr_client ):
        return string_as_bool_or_none( lwr_client.destination_params.get( "rewrite_parameters", False ) ) or False

    def __build_metadata_configuration(self, client, job_wrapper, remote_metadata, remote_job_config):
        metadata_kwds = {}
        if remote_metadata:
            remote_system_properties = remote_job_config.get("system_properties", {})
            remote_galaxy_home = remote_system_properties.get("galaxy_home", None)
            if not remote_galaxy_home:
                raise Exception(NO_REMOTE_GALAXY_FOR_METADATA_MESSAGE)
            metadata_kwds['exec_dir'] = remote_galaxy_home
            outputs_directory = remote_job_config['outputs_directory']
            configs_directory = remote_job_config['configs_directory']
            outputs = [Bunch(false_path=os.path.join(outputs_directory, os.path.basename(path)), real_path=path) for path in self.get_output_files(job_wrapper)]
            metadata_kwds['output_fnames'] = outputs
            metadata_kwds['config_root'] = remote_galaxy_home
            default_config_file = os.path.join(remote_galaxy_home, 'universe_wsgi.ini')
            metadata_kwds['config_file'] = remote_system_properties.get('galaxy_config_file', default_config_file)
            metadata_kwds['dataset_files_path'] = remote_system_properties.get('galaxy_dataset_files_path', None)
            if LwrJobRunner.__use_remote_datatypes_conf( client ):
                remote_datatypes_config = remote_system_properties.get('galaxy_datatypes_config_file', None)
                if not remote_datatypes_config:
                    log.warn(NO_REMOTE_DATATYPES_CONFIG)
                    remote_datatypes_config = os.path.join(remote_galaxy_home, 'datatypes_conf.xml')
                metadata_kwds['datatypes_config'] = remote_datatypes_config
            else:
                integrates_datatypes_config = self.app.datatypes_registry.integrated_datatypes_configs
                # Ensure this file gets pushed out to the remote config dir.
                job_wrapper.extra_filenames.append(integrates_datatypes_config)

                metadata_kwds['datatypes_config'] = os.path.join(configs_directory, os.path.basename(integrates_datatypes_config))
        return metadata_kwds


class LwrComputeEnvironment( ComputeEnvironment ):

    def __init__( self, lwr_client, job_wrapper, remote_job_config ):
        self.lwr_client = lwr_client
        self.job_wrapper = job_wrapper
        self.local_path_config = job_wrapper.default_compute_environment()
        # job_wrapper.prepare is going to expunge the job backing the following
        # computations, so precalculate these paths.
        self._wrapper_input_paths = self.local_path_config.input_paths()
        self._wrapper_output_paths = self.local_path_config.output_paths()
        self.path_mapper = PathMapper(lwr_client, remote_job_config, self.local_path_config.working_directory())
        self._config_directory = remote_job_config[ "configs_directory" ]
        self._working_directory = remote_job_config[ "working_directory" ]
        self._sep = remote_job_config[ "system_properties" ][ "separator" ]
        self._tool_dir = remote_job_config[ "tools_directory" ]

    def output_paths( self ):
        local_output_paths = self._wrapper_output_paths

        results = []
        for local_output_path in local_output_paths:
            wrapper_path = str( local_output_path )
            remote_path = self.path_mapper.remote_output_path_rewrite( wrapper_path )
            results.append( local_output_path.with_path_for_job( remote_path ) )
        return results

    def input_paths( self ):
        local_input_paths = self._wrapper_input_paths

        results = []
        for local_input_path in local_input_paths:
            wrapper_path = str( local_input_path )
            # This will over-copy in some cases. For instance in the case of task
            # splitting, this input will be copied even though only the work dir
            # input will actually be used.
            remote_path = self.path_mapper.remote_input_path_rewrite( wrapper_path )
            results.append( local_input_path.with_path_for_job( remote_path ) )
        return results

    def working_directory( self ):
        return self._working_directory

    def config_directory( self ):
        return self._config_directory

    def new_file_path( self ):
        return self.working_directory()  # Problems with doing this?

    def sep( self ):
        return self._sep
