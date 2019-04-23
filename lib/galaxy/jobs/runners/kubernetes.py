"""
Offload jobs to a Kubernetes cluster.
"""

import logging
import math
import os
import re
from time import sleep

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
    JobState
)
from galaxy.util.bytesize import ByteSize

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
            k8s_config_path=dict(map=str, default=os.environ.get('KUBECONFIG', None)),
            k8s_use_service_account=dict(map=bool, default=False),
            k8s_persistent_volume_claims=dict(map=str),
            k8s_namespace=dict(map=str, default="default"),
            k8s_galaxy_instance_id=dict(map=str),
            k8s_timeout_seconds_job_deletion=dict(map=int, valid=lambda x: int > 0, default=30),
            k8s_job_api_version=dict(map=str, default="batch/v1"),
            k8s_supplemental_group_id=dict(map=str),
            k8s_pull_policy=dict(map=str, default="Default"),
            k8s_fs_group_id=dict(map=int),
            k8s_default_requests_cpu=dict(map=str, default=None),
            k8s_default_requests_memory=dict(map=str, default=None),
            k8s_default_limits_cpu=dict(map=str, default=None),
            k8s_default_limits_memory=dict(map=str, default=None),
            k8s_pod_retrials=dict(map=int, valid=lambda x: int >= 0, default=3))

        if 'runner_param_specs' not in kwargs:
            kwargs['runner_param_specs'] = dict()
        kwargs['runner_param_specs'].update(runner_param_specs)

        """Start the job runner parent object """
        super(KubernetesJobRunner, self).__init__(app, nworkers, **kwargs)

        if "k8s_use_service_account" in self.runner_params and self.runner_params["k8s_use_service_account"]:
            self._pykube_api = HTTPClient(KubeConfig.from_service_account())
        else:
            self._pykube_api = HTTPClient(KubeConfig.from_file(self.runner_params["k8s_config_path"]))

        self._galaxy_instance_id = self.__get_galaxy_instance_id()

        self._supplemental_group = self.__get_supplemental_group()
        self._fs_group = self.__get_fs_group()
        self._default_pull_policy = self.__get_pull_policy()

        self._init_monitor_thread()
        self._init_worker_threads()
        self.setup_volumes()

    def setup_volumes(self):
        volume_claims = dict(volume.split(":") for volume in self.runner_params['k8s_persistent_volume_claims'].split(','))
        mountable_volumes = [{'name': claim_name, 'persistentVolumeClaim': {'claimName': claim_name}} for claim_name in volume_claims]
        self.runner_params['k8s_mountable_volumes'] = mountable_volumes
        volume_mounts = [{'name': claim_name, 'mountPath': mount_path} for claim_name, mount_path in volume_claims.items()]
        self.runner_params['k8s_volume_mounts'] = volume_mounts

    def queue_job(self, job_wrapper):
        """Create job script and submit it to Kubernetes cluster"""
        # prepare the job
        # We currently don't need to include_metadata or include_work_dir_outputs, as working directory is the same
        # where galaxy will expect results.
        log.debug("Starting queue_job for job " + job_wrapper.get_id_tag())
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory,
                                   job_wrapper=job_wrapper,
                                   job_destination=job_wrapper.job_destination)

        if not self.prepare_job(job_wrapper,
                                include_metadata=False,
                                modify_command_for_container=False,
                                stdout_file=ajs.output_file,
                                stderr_file=ajs.error_file):
            return

        script = self.get_job_file(job_wrapper, exit_code_path=ajs.exit_code_file, shell=job_wrapper.shell, galaxy_virtual_env=None)
        try:
            self.write_executable_script(ajs.job_file, script)
        except Exception:
            job_wrapper.fail("failure preparing job script", exception=True)
            log.exception("(%s) failure writing job script" % job_wrapper.get_id_tag())
            return

        # Construction of the Kubernetes Job object follows: http://kubernetes.io/docs/user-guide/persistent-volumes/
        k8s_job_name = self.__produce_unique_k8s_job_name(job_wrapper.get_id_tag())
        k8s_job_obj = {
            "apiVersion": self.runner_params['k8s_job_api_version'],
            "kind": "Job",
            "metadata": {
                    # metadata.name is the name of the pod resource created, and must be unique
                    # http://kubernetes.io/docs/user-guide/configuring-containers/
                    "name": k8s_job_name,
                    "namespace": self.runner_params['k8s_namespace'],
                    "labels": {"app": k8s_job_name}
            },
            "spec": self.__get_k8s_job_spec(ajs)
        }

        # Checks if job exists and is trusted, or if it needs re-creation.
        job = Job(self._pykube_api, k8s_job_obj)
        if job.exists() and not self._galaxy_instance_id:
            # if galaxy instance id is not set, then we don't trust matching jobs and we simply delete and
            # re-create the job
            log.debug("Matching job exists, but Job is not trusted, so it will be deleted and a new one created.")
            job.delete()
            elapsed_seconds = 0
            while job.exists():
                sleep(3)
                elapsed_seconds += 3
                if elapsed_seconds > self.runner_params['k8s_timeout_seconds_job_deletion']:
                    log.debug("Timed out before k8s could delete existing untrusted job " + k8s_job_name +
                              ", not queuing associated Galaxy job.")
                    return
                log.debug("Waiting for job to be deleted " + k8s_job_name)

            Job(self._pykube_api, k8s_job_obj).create()
        elif job.exists() and self._galaxy_instance_id:
            # The job exists and we trust the identifier.
            log.debug("Matching job exists, but Job is trusted, so we simply use the existing one for " + k8s_job_name)
            # We simply leave the k8s job to be handled later on by the check watched-items.
        else:
            # Creates the Kubernetes Job if it doesn't exist.
            job.create()

        # define job attributes in the AsyncronousJobState for follow-up
        ajs.job_id = k8s_job_name
        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_job_destination(job_wrapper.job_destination, k8s_job_name)
        self.monitor_queue.put(ajs)

    def __get_pull_policy(self):
        if "k8s_pull_policy" in self.runner_params:
            if self.runner_params['k8s_pull_policy'] in ["Always", "IfNotPresent", "Never"]:
                return self.runner_params['k8s_pull_policy']
        return None

    def __get_supplemental_group(self):
        if "k8s_supplemental_group_id" in self.runner_params:
            try:
                return int(self.runner_params["k8s_supplemental_group_id"])
            except Exception:
                log.warning("Supplemental group passed for Kubernetes runner needs to be an integer, value "
                         + self.runner_params["k8s_supplemental_group_id"] + " passed is invalid")
                return None
        return None

    def __get_fs_group(self):
        if "k8s_fs_group_id" in self.runner_params:
            try:
                return int(self.runner_params["k8s_fs_group_id"])
            except Exception:
                log.warning("FS group passed for Kubernetes runner needs to be an integer, value "
                         + self.runner_params["k8s_fs_group_id"] + " passed is invalid")
                return None
        return None

    def __get_galaxy_instance_id(self):
        """
        Gets the id of the Galaxy instance. This will be added to Jobs and Pods names, so it needs to be DNS friendly,
        this means: `The Internet standards (Requests for Comments) for protocols mandate that component hostname labels
        may contain only the ASCII letters 'a' through 'z' (in a case-insensitive manner), the digits '0' through '9',
        and the minus sign ('-').`

        It looks for the value set on self.runner_params['k8s_galaxy_instance_id'], which might or not be set. The
        idea behind this is to allow the Galaxy instance to trust (or not) existing k8s Jobs and Pods that match the
        setup of a Job that is being recovered or restarted after a downtime/reboot.
        :return:
        :rtype:
        """
        if "k8s_galaxy_instance_id" in self.runner_params:
            if re.match(r"(?!-)[a-z\d-]{1,20}(?<!-)$", self.runner_params['k8s_galaxy_instance_id']):
                return self.runner_params['k8s_galaxy_instance_id']
            else:
                log.error("Galaxy instance '" + self.runner_params['k8s_galaxy_instance_id'] + "' is either too long "
                          + '(>20 characters) or it includes non DNS acceptable characters, ignoring it.')
        return None

    def __produce_unique_k8s_job_name(self, galaxy_internal_job_id):
        # wrapper.get_id_tag() instead of job_id for compatibility with TaskWrappers.
        instance_id = ""
        if self._galaxy_instance_id and len(self._galaxy_instance_id) > 0:
            instance_id = self._galaxy_instance_id + "-"
        return "galaxy-" + instance_id + galaxy_internal_job_id

    def __get_k8s_job_spec(self, ajs):
        """Creates the k8s Job spec. For a Job spec, the only requirement is to have a .spec.template."""
        k8s_job_spec = {"template": self.__get_k8s_job_spec_template(ajs)}
        return k8s_job_spec

    def __get_k8s_job_spec_template(self, ajs):
        """The k8s spec template is nothing but a Pod spec, except that it is nested and does not have an apiversion
        nor kind. In addition to required fields for a Pod, a pod template in a job must specify appropriate labels
        (see pod selector) and an appropriate restart policy."""
        k8s_spec_template = {
            "metadata": {
                "labels": {"app": self.__produce_unique_k8s_job_name(ajs.job_wrapper.get_id_tag())}
            },
            "spec": {
                "volumes": self.runner_params['k8s_mountable_volumes'],
                "restartPolicy": self.__get_k8s_restart_policy(ajs.job_wrapper),
                "containers": self.__get_k8s_containers(ajs)
            }
        }
        # TODO include other relevant elements that people might want to use from
        # TODO http://kubernetes.io/docs/api-reference/v1/definitions/#_v1_podspec

        if self._supplemental_group and self._supplemental_group > 0:
            k8s_spec_template["spec"]["securityContext"] = dict(supplementalGroups=[self._supplemental_group])
        if self._fs_group and self._fs_group > 0:
            if "securityContext" in k8s_spec_template["spec"]:
                k8s_spec_template["spec"]["securityContext"]["fsGroup"] = self._fs_group
            else:
                k8s_spec_template["spec"]["securityContext"] = dict(fsGroup=self._fs_group)

        return k8s_spec_template

    def __get_k8s_restart_policy(self, job_wrapper):
        """The default Kubernetes restart policy for Jobs"""
        return "Never"

    def __get_k8s_containers(self, ajs):
        """Fills in all required for setting up the docker containers to be used, including setting a pull policy if
           this has been set.
           $GALAXY_VIRTUAL_ENV is set to None to avoid the galaxy virtualenv inside the tool container.
           $GALAXY_LIB is set to None to avoid changing the python path inside the container.
           Setting these variables changes the described behaviour in the job file shell script
           used to execute the tool inside the container.
        """
        k8s_container = {
            "name": self.__get_k8s_container_name(ajs.job_wrapper),
            "image": self._find_container(ajs.job_wrapper).container_id,
            # this form of command overrides the entrypoint and allows multi command
            # command line execution, separated by ;, which is what Galaxy does
            # to assemble the command.
            "command": [ajs.job_wrapper.shell],
            "args": ["-c", ajs.job_file],
            "workingDir": ajs.job_wrapper.working_directory,
            "volumeMounts": self.runner_params['k8s_volume_mounts']
        }

        resources = self.__get_resources(ajs.job_wrapper)
        if resources:
            envs = []
            if 'limits' in resources:
                limits = resources['limits']
                if 'memory' in limits:
                    envs.append({'name': 'GALAXY_MEMORY_MB', 'value': str(ByteSize(limits['memory']).to_unit('M', as_string=False))})
                if 'cpu' in limits:
                    envs.append({'name': 'GALAXY_SLOTS', 'value': str(int(math.ceil(float(limits['cpu']))))})
            k8s_container['resources'] = resources
            k8s_container['env'] = envs

        if self._default_pull_policy:
            k8s_container["imagePullPolicy"] = self._default_pull_policy

        return [k8s_container]

    def __get_resources(self, job_wrapper):
        mem_request = self.__get_memory_request(job_wrapper)
        cpu_request = self.__get_cpu_request(job_wrapper)

        mem_limit = self.__get_memory_limit(job_wrapper)
        cpu_limit = self.__get_cpu_limit(job_wrapper)

        requests = {}
        limits = {}

        if mem_request:
            requests['memory'] = mem_request
        if cpu_request:
            requests['cpu'] = cpu_request

        if mem_limit:
            limits['memory'] = mem_limit
        if cpu_limit:
            limits['cpu'] = cpu_limit

        resources = {}
        if requests:
            resources['requests'] = requests
        if limits:
            resources['limits'] = limits

        return resources

    def __get_memory_request(self, job_wrapper):
        """Obtains memory requests for job, checking if available on the destination, otherwise using the default"""
        job_destinantion = job_wrapper.job_destination

        if 'requests_memory' in job_destinantion.params:
            return self.__transform_memory_value(job_destinantion.params['requests_memory'])
        return None

    def __get_memory_limit(self, job_wrapper):
        """Obtains memory limits for job, checking if available on the destination, otherwise using the default"""
        job_destinantion = job_wrapper.job_destination

        if 'limits_memory' in job_destinantion.params:
            return self.__transform_memory_value(job_destinantion.params['limits_memory'])
        return None

    def __get_cpu_request(self, job_wrapper):
        """Obtains cpu requests for job, checking if available on the destination, otherwise using the default"""
        job_destinantion = job_wrapper.job_destination

        if 'requests_cpu' in job_destinantion.params:
            return job_destinantion.params['requests_cpu']
        return None

    def __get_cpu_limit(self, job_wrapper):
        """Obtains cpu requests for job, checking if available on the destination, otherwise using the default"""
        job_destinantion = job_wrapper.job_destination

        if 'limits_cpu' in job_destinantion.params:
            return job_destinantion.params['limits_cpu']
        return None

    def __transform_memory_value(self, mem_value):
        """
        Transforms valid kubernetes memory value to bytes
        """
        return ByteSize(mem_value).value

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
        # These must follow a specific regex for Kubernetes.
        raw_id = job_wrapper.job_destination.id
        if isinstance(raw_id, str):
            cleaned_id = re.sub("[^-a-z0-9]", "-", raw_id)
            if cleaned_id.startswith("-") or cleaned_id.endswith("-"):
                cleaned_id = "x%sx" % cleaned_id
            return cleaned_id
        return "job-container"

    def check_watched_item(self, job_state):
        """Checks the state of a job already submitted on k8s. Job state is a AsynchronousJobState"""
        jobs = Job.objects(self._pykube_api).filter(selector="app=" + job_state.job_id,
                                                    namespace=self.runner_params['k8s_namespace'])
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
                job_state.running = False
                self.mark_as_finished(job_state)
                return None
            elif failed > 0 and self.__job_failed_due_to_low_memory(job_state):
                return self._handle_job_failure(job, job_state, reason="OOM")
            elif active > 0 and failed <= max_pod_retrials:
                if not job_state.running:
                    job_state.running = True
                    job_state.job_wrapper.change_state(model.Job.states.RUNNING)
                return job_state
            elif failed > max_pod_retrials:
                return self._handle_job_failure(job, job_state)
            elif job_state.job_wrapper.get_job().state == model.Job.states.DELETED:
                # Job has been deleted via stop_job, cleanup and remove from watched_jobs by returning `None`
                if job_state.job_wrapper.cleanup_job in ("always", "onsuccess"):
                    job_state.job_wrapper.cleanup()
                return None
            else:
                # We really shouldn't reach this point, but we might if the job has been killed by the kubernetes admin
                log.info("Kubernetes job '%s' not classified as succ., active or failed. Full Job object: \n%s", job.name, job.obj)

        elif len(jobs.response['items']) == 0:
            # there is no job responding to this job_id, it is either lost or something happened.
            log.error("No Jobs are available under expected selector app=%s", job_state.job_id)
            with open(job_state.error_file, 'w') as error_file:
                error_file.write("No Kubernetes Jobs are available under expected selector app=%s\n" % job_state.job_id)
            self.mark_as_failed(job_state)
            return job_state
        else:
            # there is more than one job associated to the expected unique job id used as selector.
            log.error("More than one Kubernetes Job associated to job id '%s'", job_state.job_id)
            with open(job_state.error_file, 'w') as error_file:
                error_file.write("More than one Kubernetes Job associated to job id '%s'\n" % job_state.job_id)
            self.mark_as_failed(job_state)
            return job_state

    def _handle_job_failure(self, job, job_state, reason=None):
        with open(job_state.error_file, 'a') as error_file:
            if reason == "OOM":
                error_file.write("Job killed after running out of memory. Try with more memory.\n")
                job_state.fail_message = "Tool failed due to insufficient memory. Try with more memory."
                job_state.runner_state = JobState.runner_states.MEMORY_LIMIT_REACHED
            else:
                error_file.write("Exceeded max number of Kubernetes pod retrials allowed for job\n")
                job_state.fail_message = "More pods failed than allowed. See stdout for pods details."
        job_state.running = False
        self.mark_as_failed(job_state)
        job.scale(replicas=0)
        return None

    def __job_failed_due_to_low_memory(self, job_state):
        """
        checks the state of the pod to see if it was killed
        for being out of memory (pod status OOMKilled). If that is the case
        marks the job for resubmission (resubmit logic is part of destinations).
        """

        pods = Pod.objects(self._pykube_api).filter(selector="app=%s" % job_state.job_id)
        pod = Pod(self._pykube_api, pods.response['items'][0])

        if pod.obj['status']['phase'] == "Failed" and \
                pod.obj['status']['containerStatuses'][0]['state']['terminated']['reason'] == "OOMKilled":
            return True

        return False

    def stop_job(self, job_wrapper):
        """Attempts to delete a dispatched job to the k8s cluster"""
        job = job_wrapper.get_job()
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
        job_id = job.get_job_runner_external_id()
        log.debug("k8s trying to recover job: " + job_id)
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
