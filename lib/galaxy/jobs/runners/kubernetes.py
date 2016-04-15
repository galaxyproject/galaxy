"""
Job control via a command line interface (e.g. qsub/qstat), possibly over a remote connection (e.g. ssh).
"""

import logging

from galaxy import model
from galaxy.jobs import JobDestination
from galaxy.jobs.runners import AsynchronousJobState, AsynchronousJobRunner
from .util.cli import CliInterface, split_params

# pykube imports:
try:
    import operator

    from pykube.config import KubeConfig
    from pykube.http import HTTPClient
    from pykube.objects import Job
    from pykube.objects import Pod
except ImportError as exc:
    operator = None
    K8S_IMPORT_MESSAGE = ('The Python pykube package is required to use '
                          'this feature, please install it or correct the '
                          'following error:\nImportError %s' % str(exc))



log = logging.getLogger( __name__ )

__all__ = [ 'KubernetesJobRunner' ]


class KubernetesJobRunner( AsynchronousJobRunner ):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "KubernetesRunner"

    def __init__( self, app, nworkers ):
        # Check if pykube was importable, fail if not
        assert operator is not None, K8S_IMPORT_MESSAGE
        """Start the job runner parent object """
        super(KubernetesJobRunner, self).__init__(app, nworkers)

        # self.cli_interface = CliInterface()

        # here we need to fetch the default kubeconfig path from the plugin defined in job_conf...
        self._pykube_api = HTTPClient(KubeConfig.from_file(self.runner_params["k8s_config_path"]))
        self._galaxy_vol_name = "pvc_galaxy"

        # TODO do we need these?
        # self._init_monitor_thread()
        # self._init_worker_threads()

    def get_cli_plugins(self, shell_params, job_params ):
        return self.cli_interface.get_plugins( shell_params, job_params )

    def url_to_destination( self, url ):
        # TODO apparently needs to be implemented for pykube-k8s
        params = {}
        shell_params, job_params = url.split('/')[2:4]
        # split 'foo=bar&baz=quux' into { 'foo' : 'bar', 'baz' : 'quux' }
        shell_params = dict( [ ( 'shell_' + k, v ) for k, v in [ kv.split( '=', 1 ) for kv in shell_params.split( '&' ) ] ] )
        job_params = dict( [ ( 'job_' + k, v ) for k, v in [ kv.split( '=', 1 ) for kv in job_params.split( '&' ) ] ] )
        params.update( shell_params )
        params.update( job_params )
        log.debug( "Converted URL '%s' to destination runner=cli, params=%s" % ( url, params ) )
        # Create a dynamic JobDestination
        return JobDestination( runner='cli', params=params )

    def parse_destination_params( self, params ):
        # TODO apparently no need to re-implement, can be deleted.
        return split_params( params )

    def queue_job( self, job_wrapper ):
        """Create job script and submit it to Kubernetes cluster"""
        # prepare the job
        # TODO understand whether we need to include_metadata and include_work_dir_outputs
        if not self.prepare_job(job_wrapper, include_metadata=True ):
            return

        # Get shell and job execution interface
        job_destination = job_wrapper.job_destination

        # Determine the job's Kubernetes destination (context, namespace) and options from the job destination definition

        # Construction of the Kubernetes Job object follows: http://kubernetes.io/docs/user-guide/persistent-volumes/
        k8s_job_name = self.__produce_unique_k8s_job_name(job_wrapper)
        k8s_job_obj = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata":
                 # metadata.name is the name of the pod resource created, and must be unique
                 # http://kubernetes.io/docs/user-guide/configuring-containers/
                 {"name": k8s_job_name}
            ,
            "spec": self.__get_k8s_job_spec(job_wrapper)
        }


        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        galaxy_id_tag = job_wrapper.get_id_tag()

        k8s_job = Job(self._pykube_api, k8s_job_obj).create()


        # define job attributes in the AsyncronousJobState for follow-up
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper,
                                   job_id=k8s_job_name, job_destination=job_destination)
        self.monitor_queue.put(ajs)

        # external_runJob_script can be None, in which case it's not used.
        external_runjob_script = None

    def __produce_unique_k8s_job_name(self, job_wrapper):
        return "galaxy-" + job_wrapper.get_id_tag()

    def __get_k8s_job_spec(self, job_wrapper):
        """Creates the k8s Job spec. For a Job spec, the only requirement is to have a .spec.template."""
        k8s_job_spec = {"template": self.__get_k8s_job_spec_template(job_wrapper)}
        return k8s_job_spec

    def __get_k8s_job_spec_template(self, job_wrapper):
        """The spec template is nothing but a Pod spec, except that it is nested and does not have an apiversion
        nor kind. In addition to required fields for a Pod, a pod template in a job must specify appropriate labels
        (see pod selector) and an appropriate restart policy."""
        k8s_spec_template = {
            "volumes": self.__get_k8s_mountable_volumes(self, job_wrapper),
            "containers": self.__get_k8s_containers(self, job_wrapper),
            "restartPolicy": self.__get_k8s_restart_policy(self, job_wrapper)
                            }
        # TODO include other relevant elements that people might want to use from
        # TODO http://kubernetes.io/docs/api-reference/v1/definitions/#_v1_podspec

        return k8s_spec_template

    def __get_k8s_restart_policy(self, job_wrapper):
        """The default Kubernetes restart policy for Jobs"""
        return "Never"

    def __get_k8s_mountable_volumes(self, job_wrapper):
        """Provides the required volumes that the containers in the pod should be able to mount. This should be using
        the new persistent volumes and persistent volumes claim objects. This requires that both a PersistentVolume and
        a PersistentVolumeClaim are created before starting galaxy (starting a k8s job).
        """
        # TODO on this initial version we only support a single volume to be mounted.
        k8s_mountable_volume = {
            "name": self._galaxy_vol_name,
            "persistentVolumeClaim": {
                "claimName": self.runner_params['k8s_persistent_volume_claim_name']
            }
        }
        return k8s_mountable_volume

    def __get_k8s_containers(self, job_wrapper):
        """Fills in all required for setting up the docker containers to be used."""
        k8s_container = {
            "name": self.__get_k8s_container_name(job_wrapper),
            "image": self.__assemble_k8s_container_image_name(job_wrapper),
            # this form of command overrides the entrypoint and allows multi command
            # command line execution, separated by ;, which is what Galaxy does
            # to assemble the command.
            # TODO possibly shell needs to be set by job_wrapper
            "command": "[\"/bin/bash\",\"-c\",\""+job_wrapper.runner_command_line+"\"]",
            "volumeMounts": {
                "mountPath": self.runner_params['k8s_persistent_volume_claim_mount_path'],
                "name": self._galaxy_vol_name
            }
        }

        #if self.__requires_ports(job_wrapper):
        #    k8s_container['ports'] = self.__get_k8s_containers_ports(job_wrapper)

        return k8s_container

    #def __get_k8s_containers_ports(self, job_wrapper):

    #    for k,v self.runner_params:
    #        if k.startswith("container_port_"):

    def __assemble_k8s_container_image_name(self, job_wrapper):
        """Assembles the container image name as repo/owner/image:tag, where repo, owner and tag are optional"""
        job_destination = job_wrapper.job_destination

        # Determine the job's Kubernetes destination (context, namespace) and options from the job destination
        # definition
        repo = ""
        owner = ""
        if 'repo' in job_destination.params:
            repo = job_destination.params['repo']+"/"
        if 'owner' in job_destination.params:
            owner = job_destination.params['owner']+"/"

        k8s_cont_image = repo + owner + job_destination.params['image']

        if 'tag' in job_destination.params:
            k8s_cont_image += ":" + job_destination.params['tag']

        return k8s_cont_image

    def __get_k8s_container_name(self, job_wrapper):
        # TODO check if this is correct
        return job_wrapper.job_destination.id


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
                    log.debug("(%s/%s) state change: %s" % ( id_tag, external_job_id, state ) )
                    ajs.job_wrapper.change_state( state )
                if state == model.Job.states.RUNNING and not ajs.running:
                    ajs.running = True
                    ajs.job_wrapper.change_state( model.Job.states.RUNNING )
            ajs.old_state = state
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
        """Attempts to delete a dispatched job to the k8s cluster"""
        try:
            jobs = Job.objects(self._pykube_api).filter(selector="app="+job.job_runner_external_id)
            if jobs.response['items'].len() >= 0:
                job_to_delete = Job(self._pykube_api, jobs.response['items'][0])
                if job_to_delete.exists():
                    job_to_delete.delete()
            assert not job_to_delete.exists(), "Could not delete job,"+job.job_runner_external_id+" it still exists"
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
