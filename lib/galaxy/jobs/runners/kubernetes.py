"""
Offload jobs to a Kubernetes cluster.
"""

import logging
from os import environ as os_environ

from six import text_type

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)

# pykube imports:
try:
    from pykube.config import KubeConfig
    from pykube.http import HTTPClient
    from pykube.objects import (
        Job,
        Pod
    )
except ImportError as exc:
    KubeConfig = None
    K8S_IMPORT_MESSAGE = ('The Python pykube package is required to use '
                          'this feature, please install it or correct the '
                          'following error:\nImportError %s' % str(exc))

log = logging.getLogger(__name__)

__all__ = ('KubernetesJobRunner', )


class KubernetesJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "KubernetesRunner"

    def __init__(self, app, nworkers, **kwargs):
        # Check if pykube was importable, fail if not
        assert KubeConfig is not None, K8S_IMPORT_MESSAGE
        runner_param_specs = dict(
            k8s_config_path=dict(map=str, default=os_environ.get('KUBECONFIG', None)),
            k8s_use_service_account=dict(map=bool, default=False),
            k8s_persistent_volume_claim_name=dict(map=str),
            k8s_persistent_volume_claim_mount_path=dict(map=str),
            k8s_namespace=dict(map=str, default="default"),
            k8s_pod_retrials=dict(map=int, valid=lambda x: int > 0, default=3))

        if 'runner_param_specs' not in kwargs:
            kwargs['runner_param_specs'] = dict()
        kwargs['runner_param_specs'].update(runner_param_specs)

        """Start the job runner parent object """
        super(KubernetesJobRunner, self).__init__(app, nworkers, **kwargs)

        # self.cli_interface = CliInterface()

        if "k8s_use_service_account" in self.runner_params and self.runner_params["k8s_use_service_account"]:
            self._pykube_api = HTTPClient(KubeConfig.from_service_account())
        else:
            self._pykube_api = HTTPClient(KubeConfig.from_file(self.runner_params["k8s_config_path"]))
        self._galaxy_vol_name = "pvc-galaxy"  # TODO this needs to be read from params!!

        self._init_monitor_thread()
        self._init_worker_threads()

    def queue_job(self, job_wrapper):
        """Create job script and submit it to Kubernetes cluster"""
        # prepare the job
        # We currently don't need to include_metadata or include_work_dir_outputs, as working directory is the same
        # were galaxy will expect results.
        log.debug("Starting queue_job for job " + job_wrapper.get_id_tag())
        if not self.prepare_job(job_wrapper, include_metadata=False, modify_command_for_container=False):
            return

        job_destination = job_wrapper.job_destination

        # Construction of the Kubernetes Job object follows: http://kubernetes.io/docs/user-guide/persistent-volumes/
        k8s_job_name = self.__produce_unique_k8s_job_name(job_wrapper.get_id_tag())
        k8s_job_obj = {
            "apiVersion": "extensions/v1beta1",
            "kind": "Job",
            "metadata":
            # metadata.name is the name of the pod resource created, and must be unique
            # http://kubernetes.io/docs/user-guide/configuring-containers/
                {
                    "name": k8s_job_name,
                    "namespace": "default",  # TODO this should be set
                    "labels": {"app": k8s_job_name},
                }
            ,
            "spec": self.__get_k8s_job_spec(job_wrapper)
        }

        # Checks if job exists
        job = Job(self._pykube_api, k8s_job_obj)
        if job.exists():
            job.delete()
        # Creates the Kubernetes Job
        # TODO if a job with that ID exists, what should we do?
        # TODO do we trust that this is the same job and use that?
        # TODO or create a new job as we cannot make sure
        Job(self._pykube_api, k8s_job_obj).create()

        # define job attributes in the AsyncronousJobState for follow-up
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper,
                                   job_id=k8s_job_name, job_destination=job_destination)
        self.monitor_queue.put(ajs)

        # external_runJob_script can be None, in which case it's not used.
        external_runjob_script = None
        return external_runjob_script

    def __produce_unique_k8s_job_name(self, galaxy_internal_job_id):
        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        return "galaxy-" + galaxy_internal_job_id

    def __get_k8s_job_spec(self, job_wrapper):
        """Creates the k8s Job spec. For a Job spec, the only requirement is to have a .spec.template."""
        k8s_job_spec = {"template": self.__get_k8s_job_spec_template(job_wrapper)}
        return k8s_job_spec

    def __get_k8s_job_spec_template(self, job_wrapper):
        """The k8s spec template is nothing but a Pod spec, except that it is nested and does not have an apiversion
        nor kind. In addition to required fields for a Pod, a pod template in a job must specify appropriate labels
        (see pod selector) and an appropriate restart policy."""
        k8s_spec_template = {
            "metadata": {
                "labels": {"app": self.__produce_unique_k8s_job_name(job_wrapper.get_id_tag())}
            },
            "spec": {
                "volumes": self.__get_k8s_mountable_volumes(job_wrapper),
                "restartPolicy": self.__get_k8s_restart_policy(job_wrapper),
                "containers": self.__get_k8s_containers(job_wrapper)
            }
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
        return [k8s_mountable_volume]

    def __get_k8s_containers(self, job_wrapper):
        """Fills in all required for setting up the docker containers to be used."""
        k8s_container = {
            "name": self.__get_k8s_container_name(job_wrapper),
            "image": self._find_container(job_wrapper).container_id,
            # this form of command overrides the entrypoint and allows multi command
            # command line execution, separated by ;, which is what Galaxy does
            # to assemble the command.
            # TODO possibly shell needs to be set by job_wrapper
            "command": ["/bin/bash", "-c", job_wrapper.runner_command_line],
            "workingDir": job_wrapper.working_directory,
            "volumeMounts": [{
                "mountPath": self.runner_params['k8s_persistent_volume_claim_mount_path'],
                "name": self._galaxy_vol_name
            }]
        }

        # if self.__requires_ports(job_wrapper):
        #    k8s_container['ports'] = self.__get_k8s_containers_ports(job_wrapper)

        return [k8s_container]

    # def __get_k8s_containers_ports(self, job_wrapper):

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
            repo = job_destination.params['repo'] + "/"
        if 'owner' in job_destination.params:
            owner = job_destination.params['owner'] + "/"

        k8s_cont_image = repo + owner + job_destination.params['image']

        if 'tag' in job_destination.params:
            k8s_cont_image += ":" + job_destination.params['tag']

        return k8s_cont_image

    def __get_k8s_container_name(self, job_wrapper):
        # TODO check if this is correct
        return job_wrapper.job_destination.id

    def check_watched_item(self, job_state):
        """Checks the state of a job already submitted on k8s. Job state is a AsynchronousJobState"""
        jobs = Job.objects(self._pykube_api).filter(selector="app=" + job_state.job_id)
        if len(jobs.response['items']) == 1:
            job = Job(self._pykube_api, jobs.response['items'][0])
            job_destination = job_state.job_wrapper.job_destination
            succeeded = 0
            active = 0
            failed = 0

            max_pod_retrials = 1
            if 'k8s_pod_retrials' in self.runner_params:
                max_pod_retrials = int(self.runner_params['k8s_pod_retrials'])
            if 'max_pod_retrials' in job_destination.params:
                max_pod_retrials = int(job_destination.params['max_pod_retrials'])

            if 'succeeded' in job.obj['status']:
                succeeded = job.obj['status']['succeeded']
            if 'active' in job.obj['status']:
                active = job.obj['status']['active']
            if 'failed' in job.obj['status']:
                failed = job.obj['status']['failed']

            # This assumes jobs dependent on a single pod, single container
            if succeeded > 0:
                self.__produce_log_file(job_state)
                error_file = open(job_state.error_file, 'w')
                error_file.write("")
                error_file.close()
                job_state.running = False
                self.mark_as_finished(job_state)
                return None
            elif active > 0 and failed <= max_pod_retrials:
                job_state.running = True
                return job_state
            elif failed > max_pod_retrials:
                self.__produce_log_file(job_state)
                error_file = open(job_state.error_file, 'w')
                error_file.write("Exceeded max number of Kubernetes pod retrials allowed for job\n")
                error_file.close()
                job_state.running = False
                job_state.fail_message = "More pods failed than allowed. See stdout for pods details."
                self.mark_as_failed(job_state)
                job.scale(replicas=0)
                return None

            # We should not get here
            log.debug(
                "Reaching unexpected point for Kubernetes job, where it is not classified as succ., active nor failed.")
            return job_state

        elif len(jobs.response['items']) == 0:
            # there is no job responding to this job_id, it is either lost or something happened.
            log.error("No Jobs are available under expected selector app=" + job_state.job_id)
            error_file = open(job_state.error_file, 'w')
            error_file.write("No Kubernetes Jobs are available under expected selector app=" + job_state.job_id + "\n")
            error_file.close()
            self.mark_as_failed(job_state)
            return job_state
        else:
            # there is more than one job associated to the expected unique job id used as selector.
            log.error("There is more than one Kubernetes Job associated to job id " + job_state.job_id)
            self.__produce_log_file(job_state)
            error_file = open(job_state.error_file, 'w')
            error_file.write("There is more than one Kubernetes Job associated to job id " + job_state.job_id + "\n")
            error_file.close()
            self.mark_as_failed(job_state)
            return job_state

    def fail_job(self, job_state):
        """
        Kubernetes runner overrides fail_job (called by mark_as_failed) to rescue the pod's log files which are left as
        stdout (pods logs are the natural stdout and stderr of the running processes inside the pods) and are
        deleted in the parent implementation as part of the failing the job process.

        :param job_state:
        :return:
        """

        # First we rescue the pods logs
        with open(job_state.output_file, 'r') as outfile:
            stdout_content = outfile.read()

        if getattr(job_state, 'stop_job', True):
            self.stop_job(self.sa_session.query(self.app.model.Job).get(job_state.job_wrapper.job_id))
        self._handle_runner_state('failure', job_state)
        # Not convinced this is the best way to indicate this state, but
        # something necessary
        if not job_state.runner_state_handled:
            job_state.job_wrapper.fail(
                message=getattr(job_state, 'fail_message', 'Job failed'),
                stdout=stdout_content, stderr='See stdout for pod\'s stderr.'
            )
            if job_state.job_wrapper.cleanup_job == "always":
                job_state.cleanup()

    def __produce_log_file(self, job_state):
        pod_r = Pod.objects(self._pykube_api).filter(selector="app=" + job_state.job_id)
        logs = ""
        for pod_obj in pod_r.response['items']:
            try:
                pod = Pod(self._pykube_api, pod_obj)
                logs += "\n\n==== Pod " + pod.name + " log start ====\n\n"
                logs += pod.logs(timestamps=True)
                logs += "\n\n==== Pod " + pod.name + " log end   ===="
            except Exception as detail:
                log.info("Could not write pod\'s " + pod_obj['metadata']['name'] +
                         " log file due to HTTPError " + str(detail))

        logs_file_path = job_state.output_file
        logs_file = open(logs_file_path, mode="w")
        if isinstance(logs, text_type):
            logs = logs.encode('utf8')
        logs_file.write(logs)
        logs_file.close()
        return logs_file_path

    def stop_job(self, job):
        """Attempts to delete a dispatched job to the k8s cluster"""
        try:
            jobs = Job.objects(self._pykube_api).filter(selector="app=" +
                                                                 self.__produce_unique_k8s_job_name(job.get_id_tag()))
            if len(jobs.response['items']) >= 0:
                job_to_delete = Job(self._pykube_api, jobs.response['items'][0])
                job_to_delete.scale(replicas=0)
            # TODO assert whether job parallelism == 0
            # assert not job_to_delete.exists(), "Could not delete job,"+job.job_runner_external_id+" it still exists"
            log.debug("(%s/%s) Terminated at user's request" % (job.id, job.job_runner_external_id))
        except Exception as e:
            log.debug("(%s/%s) User killed running job, but error encountered during termination: %s" % (
                job.id, job.job_runner_external_id, e))

    def recover(self, job, job_wrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        # TODO this needs to be implemented to override unimplemented base method
        job_id = job.get_job_runner_external_id()
        if job_id is None:
            self.put(job_wrapper)
            return
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper)
        ajs.job_id = str(job_id)
        ajs.command_line = job.command_line
        ajs.job_wrapper = job_wrapper
        ajs.job_destination = job_wrapper.job_destination
        if job.state == model.Job.states.RUNNING:
            log.debug("(%s/%s) is still in running state, adding to the runner monitor queue" % (
                job.id, job.job_runner_external_id))
            ajs.old_state = model.Job.states.RUNNING
            ajs.running = True
            self.monitor_queue.put(ajs)
        elif job.state == model.Job.states.QUEUED:
            log.debug("(%s/%s) is still in queued state, adding to the runner monitor queue" % (
                job.id, job.job_runner_external_id))
            ajs.old_state = model.Job.states.QUEUED
            ajs.running = False
            self.monitor_queue.put(ajs)
