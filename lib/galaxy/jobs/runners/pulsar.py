from __future__ import absolute_import  # Need to import pulsar_client absolutely.

import logging

from galaxy import model
from galaxy.jobs.runners import AsynchronousJobState, AsynchronousJobRunner
from galaxy.jobs import ComputeEnvironment
from galaxy.jobs import JobDestination
from galaxy.jobs.command_factory import build_command
from galaxy.tools.deps import dependencies
from galaxy.util import string_as_bool_or_none
from galaxy.util.bunch import Bunch
from galaxy.util import specs

import errno
from time import sleep
import os

from pulsar.client import build_client_manager
from pulsar.client import url_to_destination_params
from pulsar.client import finish_job as pulsar_finish_job
from pulsar.client import submit_job as pulsar_submit_job
from pulsar.client import ClientJobDescription
from pulsar.client import PulsarOutputs
from pulsar.client import ClientOutputs
from pulsar.client import PathMapper

log = logging.getLogger( __name__ )

__all__ = [ 'PulsarLegacyJobRunner', 'PulsarRESTJobRunner', 'PulsarMQJobRunner' ]

NO_REMOTE_GALAXY_FOR_METADATA_MESSAGE = "Pulsar misconfiguration - Pulsar client configured to set metadata remotely, but remote Pulsar isn't properly configured with a galaxy_home directory."
NO_REMOTE_DATATYPES_CONFIG = "Pulsar client is configured to use remote datatypes configuration when setting metadata externally, but Pulsar is not configured with this information. Defaulting to datatypes_conf.xml."
GENERIC_REMOTE_ERROR = "Failed to communicate with remote job server."

# Is there a good way to infer some default for this? Can only use
# url_for from web threads. https://gist.github.com/jmchilton/9098762
DEFAULT_GALAXY_URL = "http://localhost:8080"

PULSAR_PARAM_SPECS = dict(
    transport=dict(
        map=specs.to_str_or_none,
        valid=specs.is_in("urllib", "curl", None),
        default=None
    ),
    cache=dict(
        map=specs.to_bool_or_none,
        default=None,
    ),
    amqp_url=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    galaxy_url=dict(
        map=specs.to_str_or_none,
        default=DEFAULT_GALAXY_URL,
    ),
    manager=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    amqp_consumer_timeout=dict(
        map=lambda val: None if val == "None" else float(val),
        default=None,
    ),
    amqp_connect_ssl_ca_certs=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    amqp_connect_ssl_keyfile=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    amqp_connect_ssl_certfile=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    amqp_connect_ssl_cert_reqs=dict(
        map=specs.to_str_or_none,
        default=None,
    ),
    # http://kombu.readthedocs.org/en/latest/reference/kombu.html#kombu.Producer.publish
    amqp_publish_retry=dict(
        map=specs.to_bool,
        default=False,
    ),
    amqp_publish_priority=dict(
        map=int,
        valid=lambda x: 0 <= x and x <= 9,
        default=0,
    ),
    # http://kombu.readthedocs.org/en/latest/reference/kombu.html#kombu.Exchange.delivery_mode
    amqp_publish_delivery_mode=dict(
        map=str,
        valid=specs.is_in("transient", "persistent"),
        default="persistent",
    ),
    amqp_publish_retry_max_retries=dict(
        map=int,
        default=None,
    ),
    amqp_publish_retry_interval_start=dict(
        map=int,
        default=None,
    ),
    amqp_publish_retry_interval_step=dict(
        map=int,
        default=None,
    ),
    amqp_publish_retry_interval_max=dict(
        map=int,
        default=None,
    ),
)


PARAMETER_SPECIFICATION_REQUIRED = object()
PARAMETER_SPECIFICATION_IGNORED = object()


class PulsarJobRunner( AsynchronousJobRunner ):
    """
    Pulsar Job Runner
    """
    runner_name = "PulsarJobRunner"

    def __init__( self, app, nworkers, **kwds ):
        """Start the job runner """
        super( PulsarJobRunner, self ).__init__( app, nworkers, runner_param_specs=PULSAR_PARAM_SPECS, **kwds )
        self._init_worker_threads()
        galaxy_url = self.runner_params.galaxy_url
        if galaxy_url:
            galaxy_url = galaxy_url.rstrip("/")
        self.galaxy_url = galaxy_url
        self.__init_client_manager()
        self._monitor()

    def _monitor( self ):
        # Extension point allow MQ variant to setup callback instead
        self._init_monitor_thread()

    def __init_client_manager( self ):
        client_manager_kwargs = {}
        for kwd in 'manager', 'cache', 'transport':
            client_manager_kwargs[ kwd ] = self.runner_params[ kwd ]
        for kwd in self.runner_params.keys():
            if kwd.startswith( 'amqp_' ):
                client_manager_kwargs[ kwd ] = self.runner_params[ kwd ]
        self.client_manager = build_client_manager(**client_manager_kwargs)

    def url_to_destination( self, url ):
        """Convert a legacy URL to a job destination"""
        return JobDestination( runner="pulsar", params=url_to_destination_params( url ) )

    def check_watched_item(self, job_state):
        try:
            client = self.get_client_from_state(job_state)
            status = client.get_status()
        except Exception:
            # An orphaned job was put into the queue at app startup, so remote server went down
            # either way we are done I guess.
            self.mark_as_finished(job_state)
            return None
        job_state = self._update_job_state_for_status(job_state, status)
        return job_state

    def _update_job_state_for_status(self, job_state, pulsar_status):
        if pulsar_status == "complete":
            self.mark_as_finished(job_state)
            return None
        if pulsar_status == "failed":
            self.fail_job(job_state)
            return None
        if pulsar_status == "running" and not job_state.running:
            job_state.running = True
            job_state.job_wrapper.change_state( model.Job.states.RUNNING )
        return job_state

    def queue_job(self, job_wrapper):
        job_destination = job_wrapper.job_destination
        self._populate_parameter_defaults( job_destination )

        command_line, client, remote_job_config, compute_environment = self.__prepare_job( job_wrapper, job_destination )

        if not command_line:
            return

        try:
            dependencies_description = PulsarJobRunner.__dependencies_description( client, job_wrapper )
            rewrite_paths = not PulsarJobRunner.__rewrite_parameters( client )
            unstructured_path_rewrites = {}
            if compute_environment:
                unstructured_path_rewrites = compute_environment.unstructured_path_rewrites

            client_job_description = ClientJobDescription(
                command_line=command_line,
                input_files=self.get_input_files(job_wrapper),
                client_outputs=self.__client_outputs(client, job_wrapper),
                working_directory=job_wrapper.working_directory,
                tool=job_wrapper.tool,
                config_files=job_wrapper.extra_filenames,
                dependencies_description=dependencies_description,
                env=client.env,
                rewrite_paths=rewrite_paths,
                arbitrary_files=unstructured_path_rewrites,
            )
            job_id = pulsar_submit_job(client, client_job_description, remote_job_config)
            log.info("Pulsar job submitted with job_id %s" % job_id)
            job_wrapper.set_job_destination( job_destination, job_id )
            job_wrapper.change_state( model.Job.states.QUEUED )
        except Exception:
            job_wrapper.fail( "failure running job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)
            return

        pulsar_job_state = AsynchronousJobState()
        pulsar_job_state.job_wrapper = job_wrapper
        pulsar_job_state.job_id = job_id
        pulsar_job_state.old_state = True
        pulsar_job_state.running = False
        pulsar_job_state.job_destination = job_destination
        self.monitor_job(pulsar_job_state)

    def __prepare_job(self, job_wrapper, job_destination):
        """ Build command-line and Pulsar client for this job. """
        command_line = None
        client = None
        remote_job_config = None
        compute_environment = None
        try:
            client = self.get_client_from_wrapper(job_wrapper)
            tool = job_wrapper.tool
            remote_job_config = client.setup(tool.id, tool.version)
            rewrite_parameters = PulsarJobRunner.__rewrite_parameters( client )
            prepare_kwds = {}
            if rewrite_parameters:
                compute_environment = PulsarComputeEnvironment( client, job_wrapper, remote_job_config )
                prepare_kwds[ 'compute_environment' ] = compute_environment
            job_wrapper.prepare( **prepare_kwds )
            self.__prepare_input_files_locally(job_wrapper)
            remote_metadata = PulsarJobRunner.__remote_metadata( client )
            dependency_resolution = PulsarJobRunner.__dependency_resolution( client )
            metadata_kwds = self.__build_metadata_configuration(client, job_wrapper, remote_metadata, remote_job_config)
            remote_command_params = dict(
                working_directory=remote_job_config['working_directory'],
                metadata_kwds=metadata_kwds,
                dependency_resolution=dependency_resolution,
            )
            remote_working_directory = remote_job_config['working_directory']
            # TODO: Following defs work for Pulsar, always worked for Pulsar but should be
            # calculated at some other level.
            remote_job_directory = os.path.abspath(os.path.join(remote_working_directory, os.path.pardir))
            remote_tool_directory = os.path.abspath(os.path.join(remote_job_directory, "tool_files"))
            container = self._find_container(
                job_wrapper,
                compute_working_directory=remote_working_directory,
                compute_tool_directory=remote_tool_directory,
                compute_job_directory=remote_job_directory,
            )
            command_line = build_command(
                self,
                job_wrapper=job_wrapper,
                container=container,
                include_metadata=remote_metadata,
                include_work_dir_outputs=False,
                remote_command_params=remote_command_params,
            )
        except Exception:
            job_wrapper.fail( "failure preparing job", exception=True )
            log.exception("failure running job %d" % job_wrapper.job_id)

        # If we were able to get a command line, run the job
        if not command_line:
            job_wrapper.finish( '', '' )

        return command_line, client, remote_job_config, compute_environment

    def __prepare_input_files_locally(self, job_wrapper):
        """Run task splitting commands locally."""
        prepare_input_files_cmds = getattr(job_wrapper, 'prepare_input_files_cmds', None)
        if prepare_input_files_cmds is not None:
            for cmd in prepare_input_files_cmds:  # run the commands to stage the input files
                if 0 != os.system(cmd):
                    raise Exception('Error running file staging command: %s' % cmd)
            job_wrapper.prepare_input_files_cmds = None  # prevent them from being used in-line

    def _populate_parameter_defaults( self, job_destination ):
        updated = False
        params = job_destination.params
        for key, value in self.destination_defaults.iteritems():
            if key in params:
                if value is PARAMETER_SPECIFICATION_IGNORED:
                    log.warn( "Pulsar runner in selected configuration ignores parameter %s" % key )
                continue
            #if self.runner_params.get( key, None ):
            #    # Let plugin define defaults for some parameters -
            #    # for instance that way jobs_directory can be
            #    # configured next to AMQP url (where it belongs).
            #    params[ key ] = self.runner_params[ key ]
            #    continue

            if not value:
                continue

            if value is PARAMETER_SPECIFICATION_REQUIRED:
                raise Exception( "Pulsar destination does not define required parameter %s" % key )
            elif value is not PARAMETER_SPECIFICATION_IGNORED:
                params[ key ] = value
                updated = True
        return updated

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
            if value:
                params[key] = model.User.expand_user_properties( job_wrapper.get_job().user, value )

        env = getattr( job_wrapper.job_destination, "env", [] )
        return self.get_client( params, job_id, env )

    def get_client_from_state(self, job_state):
        job_destination_params = job_state.job_destination.params
        job_id = job_state.job_id
        return self.get_client( job_destination_params, job_id )

    def get_client( self, job_destination_params, job_id, env=[] ):
        # Cannot use url_for outside of web thread.
        #files_endpoint = url_for( controller="job_files", job_id=encoded_job_id )

        encoded_job_id = self.app.security.encode_id(job_id)
        job_key = self.app.security.encode_id( job_id, kind="jobs_files" )
        files_endpoint = "%s/api/jobs/%s/files?job_key=%s" % (
            self.galaxy_url,
            encoded_job_id,
            job_key
        )
        get_client_kwds = dict(
            job_id=str( job_id ),
            files_endpoint=files_endpoint,
            env=env
        )
        return self.client_manager.get_client( job_destination_params, **get_client_kwds )

    def finish_job( self, job_state ):
        stderr = stdout = ''
        job_wrapper = job_state.job_wrapper
        try:
            client = self.get_client_from_state(job_state)
            run_results = client.full_status()
            remote_working_directory = run_results.get("working_directory", None)
            stdout = run_results.get('stdout', '')
            stderr = run_results.get('stderr', '')
            exit_code = run_results.get('returncode', None)
            pulsar_outputs = PulsarOutputs.from_status_response(run_results)
            # Use Pulsar client code to transfer/copy files back
            # and cleanup job if needed.
            completed_normally = \
                job_wrapper.get_state() not in [ model.Job.states.ERROR, model.Job.states.DELETED ]
            cleanup_job = self.app.config.cleanup_job
            client_outputs = self.__client_outputs(client, job_wrapper)
            finish_args = dict( client=client,
                                job_completed_normally=completed_normally,
                                cleanup_job=cleanup_job,
                                client_outputs=client_outputs,
                                pulsar_outputs=pulsar_outputs )
            failed = pulsar_finish_job( **finish_args )
            if failed:
                job_wrapper.fail("Failed to find or download one or more job outputs from remote server.", exception=True)
        except Exception:
            message = GENERIC_REMOTE_ERROR
            job_wrapper.fail( message, exception=True )
            log.exception("failure finishing job %d" % job_wrapper.job_id)
            return
        if not PulsarJobRunner.__remote_metadata( client ):
            self._handle_metadata_externally( job_wrapper, resolve_requirements=True )
        # Finish the job
        try:
            job_wrapper.finish(
                stdout,
                stderr,
                exit_code,
                remote_working_directory=remote_working_directory
            )
        except Exception:
            log.exception("Job wrapper finish method failed")
            job_wrapper.fail("Unable to finish job", exception=True)

    def fail_job( self, job_state ):
        """
        Seperated out so we can use the worker threads for it.
        """
        self.stop_job( self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id ) )
        job_state.job_wrapper.fail( getattr( job_state, "fail_message", GENERIC_REMOTE_ERROR ) )

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
        client = self.get_client( job.destination_params, job.job_runner_external_id )
        job_ext_output_metadata = job.get_external_output_metadata()
        if not PulsarJobRunner.__remote_metadata( client ) and job_ext_output_metadata:
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
            pulsar_url = job.job_runner_name
            job_id = job.job_runner_external_id
            log.debug("Attempt remote Pulsar kill of job with url %s and id %s" % (pulsar_url, job_id))
            client = self.get_client(job.destination_params, job_id)
            client.kill()

    def recover( self, job, job_wrapper ):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_state = self._job_state( job, job_wrapper )
        job_wrapper.command_line = job.get_command_line()
        state = job.get_state()
        if state in [model.Job.states.RUNNING, model.Job.states.QUEUED]:
            log.debug( "(Pulsar/%s) is still in running state, adding to the Pulsar queue" % ( job.get_id()) )
            job_state.old_state = True
            job_state.running = state == model.Job.states.RUNNING
            self.monitor_queue.put( job_state )

    def shutdown( self ):
        super( PulsarJobRunner, self ).shutdown()
        self.client_manager.shutdown()

    def _job_state( self, job, job_wrapper ):
        job_state = AsynchronousJobState()
        # TODO: Determine why this is set when using normal message queue updates
        # but not CLI submitted MQ updates...
        raw_job_id = job.get_job_runner_external_id() or job_wrapper.job_id
        job_state.job_id = str( raw_job_id )
        job_state.runner_url = job_wrapper.get_job_runner_url()
        job_state.job_destination = job_wrapper.job_destination
        job_state.job_wrapper = job_wrapper
        return job_state

    def __client_outputs( self, client, job_wrapper ):
        work_dir_outputs = self.get_work_dir_outputs( job_wrapper )
        output_files = self.get_output_files( job_wrapper )
        client_outputs = ClientOutputs(
            working_directory=job_wrapper.working_directory,
            work_dir_outputs=work_dir_outputs,
            output_files=output_files,
            version_file=job_wrapper.get_version_string_path(),
        )
        return client_outputs

    @staticmethod
    def __dependencies_description( pulsar_client, job_wrapper ):
        dependency_resolution = PulsarJobRunner.__dependency_resolution( pulsar_client )
        remote_dependency_resolution = dependency_resolution == "remote"
        if not remote_dependency_resolution:
            return None
        requirements = job_wrapper.tool.requirements or []
        installed_tool_dependencies = job_wrapper.tool.installed_tool_dependencies or []
        return dependencies.DependenciesDescription(
            requirements=requirements,
            installed_tool_dependencies=installed_tool_dependencies,
        )

    @staticmethod
    def __dependency_resolution( pulsar_client ):
        dependency_resolution = pulsar_client.destination_params.get( "dependency_resolution", "local" )
        if dependency_resolution not in ["none", "local", "remote"]:
            raise Exception("Unknown dependency_resolution value encountered %s" % dependency_resolution)
        return dependency_resolution

    @staticmethod
    def __remote_metadata( pulsar_client ):
        remote_metadata = string_as_bool_or_none( pulsar_client.destination_params.get( "remote_metadata", False ) )
        return remote_metadata

    @staticmethod
    def __use_remote_datatypes_conf( pulsar_client ):
        """ When setting remote metadata, use integrated datatypes from this
        Galaxy instance or use the datatypes config configured via the remote
        Pulsar.

        Both options are broken in different ways for same reason - datatypes
        may not match. One can push the local datatypes config to the remote
        server - but there is no guarentee these datatypes will be defined
        there. Alternatively, one can use the remote datatype config - but
        there is no guarentee that it will contain all the datatypes available
        to this Galaxy.
        """
        use_remote_datatypes = string_as_bool_or_none( pulsar_client.destination_params.get( "use_remote_datatypes", False ) )
        return use_remote_datatypes

    @staticmethod
    def __rewrite_parameters( pulsar_client ):
        return string_as_bool_or_none( pulsar_client.destination_params.get( "rewrite_parameters", False ) ) or False

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
            working_directory = remote_job_config['working_directory']
            # For metadata calculation, we need to build a list of of output
            # file objects with real path indicating location on Galaxy server
            # and false path indicating location on compute server. Since the
            # Pulsar disables from_work_dir copying as part of the job command
            # line we need to take the list of output locations on the Pulsar
            # server (produced by self.get_output_files(job_wrapper)) and for
            # each work_dir output substitute the effective path on the Pulsar
            # server relative to the remote working directory as the
            # false_path to send the metadata command generation module.
            work_dir_outputs = self.get_work_dir_outputs(job_wrapper, job_working_directory=working_directory)
            outputs = [Bunch(false_path=os.path.join(outputs_directory, os.path.basename(path)), real_path=path) for path in self.get_output_files(job_wrapper)]
            for output in outputs:
                for pulsar_workdir_path, real_path in work_dir_outputs:
                    if real_path == output.real_path:
                        output.false_path = pulsar_workdir_path
            metadata_kwds['output_fnames'] = outputs
            metadata_kwds['compute_tmp_dir'] = working_directory
            metadata_kwds['config_root'] = remote_galaxy_home
            default_config_file = os.path.join(remote_galaxy_home, 'config/galaxy.ini')
            metadata_kwds['config_file'] = remote_system_properties.get('galaxy_config_file', default_config_file)
            metadata_kwds['dataset_files_path'] = remote_system_properties.get('galaxy_dataset_files_path', None)
            if PulsarJobRunner.__use_remote_datatypes_conf( client ):
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


class PulsarLegacyJobRunner( PulsarJobRunner ):
    destination_defaults = dict(
        rewrite_parameters="false",
        dependency_resolution="local",
    )


class PulsarMQJobRunner( PulsarJobRunner ):
    destination_defaults = dict(
        default_file_action="remote_transfer",
        rewrite_parameters="true",
        dependency_resolution="remote",
        jobs_directory=PARAMETER_SPECIFICATION_REQUIRED,
        url=PARAMETER_SPECIFICATION_IGNORED,
        private_token=PARAMETER_SPECIFICATION_IGNORED
    )

    def _monitor( self ):
        # This is a message queue driven runner, don't monitor
        # just setup required callback.
        self.client_manager.ensure_has_status_update_callback(self.__async_update)

    def __async_update( self, full_status ):
        job_id = None
        try:
            job_id = full_status[ "job_id" ]
            job, job_wrapper = self.app.job_manager.job_handler.job_queue.job_pair_for_id( job_id )
            job_state = self._job_state( job, job_wrapper )
            self._update_job_state_for_status(job_state, full_status[ "status" ] )
        except Exception:
            log.exception( "Failed to update Pulsar job status for job_id %s" % job_id )
            raise
            # Nothing else to do? - Attempt to fail the job?


class PulsarRESTJobRunner( PulsarJobRunner ):
    destination_defaults = dict(
        default_file_action="transfer",
        rewrite_parameters="true",
        dependency_resolution="remote",
        url=PARAMETER_SPECIFICATION_REQUIRED,
    )


class PulsarComputeEnvironment( ComputeEnvironment ):

    def __init__( self, pulsar_client, job_wrapper, remote_job_config ):
        self.pulsar_client = pulsar_client
        self.job_wrapper = job_wrapper
        self.local_path_config = job_wrapper.default_compute_environment()
        self.unstructured_path_rewrites = {}
        # job_wrapper.prepare is going to expunge the job backing the following
        # computations, so precalculate these paths.
        self._wrapper_input_paths = self.local_path_config.input_paths()
        self._wrapper_output_paths = self.local_path_config.output_paths()
        self.path_mapper = PathMapper(pulsar_client, remote_job_config, self.local_path_config.working_directory())
        self._config_directory = remote_job_config[ "configs_directory" ]
        self._working_directory = remote_job_config[ "working_directory" ]
        self._sep = remote_job_config[ "system_properties" ][ "separator" ]
        self._tool_dir = remote_job_config[ "tools_directory" ]
        version_path = self.local_path_config.version_path()
        new_version_path = self.path_mapper.remote_version_path_rewrite(version_path)
        if new_version_path:
            version_path = new_version_path
        self._version_path = version_path

    def output_paths( self ):
        local_output_paths = self._wrapper_output_paths

        results = []
        for local_output_path in local_output_paths:
            wrapper_path = str( local_output_path )
            remote_path = self.path_mapper.remote_output_path_rewrite( wrapper_path )
            results.append( self._dataset_path( local_output_path, remote_path ) )
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
            results.append( self._dataset_path( local_input_path, remote_path ) )
        return results

    def _dataset_path( self, local_dataset_path, remote_path ):
        remote_extra_files_path = None
        if remote_path:
            remote_extra_files_path = "%s_files" % remote_path[ 0:-len( ".dat" ) ]
        return local_dataset_path.with_path_for_job( remote_path, remote_extra_files_path )

    def working_directory( self ):
        return self._working_directory

    def config_directory( self ):
        return self._config_directory

    def new_file_path( self ):
        return self.working_directory()  # Problems with doing this?

    def sep( self ):
        return self._sep

    def version_path( self ):
        return self._version_path

    def rewriter( self, parameter_value ):
        unstructured_path_rewrites = self.unstructured_path_rewrites
        if parameter_value in unstructured_path_rewrites:
            # Path previously mapped, use previous mapping.
            return unstructured_path_rewrites[ parameter_value ]
        if parameter_value in unstructured_path_rewrites.itervalues():
            # Path is a rewritten remote path (this might never occur,
            # consider dropping check...)
            return parameter_value

        rewrite, new_unstructured_path_rewrites = self.path_mapper.check_for_arbitrary_rewrite( parameter_value )
        if rewrite:
            unstructured_path_rewrites.update(new_unstructured_path_rewrites)
            return rewrite
        else:
            # Did need to rewrite, use original path or value.
            return parameter_value

    def unstructured_path_rewriter( self ):
        return self.rewriter
