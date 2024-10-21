"""
Offload jobs to a Kubernetes cluster.
"""

import json  # for debugging of API objects
import logging
import math
import os
import re
import time
from datetime import datetime

import yaml

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
    JobState,
)
from galaxy.jobs.runners.util.pykube_util import (
    deduplicate_entries,
    DEFAULT_INGRESS_API_VERSION,
    DEFAULT_JOB_API_VERSION,
    delete_ingress,
    delete_job,
    delete_service,
    ensure_pykube,
    find_ingress_object_by_name,
    find_job_object_by_name,
    find_pod_object_by_name,
    find_service_object_by_name,
    galaxy_instance_id,
    get_volume_mounts_for_job,
    HTTPError,
    Ingress,
    ingress_object_dict,
    is_pod_running,
    is_pod_unschedulable,
    Job,
    job_object_dict,
    parse_pvc_param_line,
    Pod,
    produce_k8s_job_prefix,
    pull_policy,
    pykube_client_from_dict,
    Service,
    service_object_dict,
)
from galaxy.util import unicodify
from galaxy.util.bytesize import ByteSize

log = logging.getLogger(__name__)

__all__ = ("KubernetesJobRunner",)


class KubernetesJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """

    runner_name = "KubernetesRunner"

    LABEL_START = re.compile("^[A-Za-z0-9]")
    LABEL_END = re.compile("[A-Za-z0-9]$")
    LABEL_REGEX = re.compile("[^-A-Za-z0-9_.]")

    def __init__(self, app, nworkers, **kwargs):
        # Check if pykube was importable, fail if not
        ensure_pykube()
        runner_param_specs = dict(
            k8s_config_path=dict(map=str, default=None),
            k8s_use_service_account=dict(map=bool, default=False),
            k8s_persistent_volume_claims=dict(map=str),
            k8s_working_volume_claim=dict(map=str),
            k8s_data_volume_claim=dict(map=str),
            k8s_namespace=dict(map=str, default="default"),
            k8s_pod_priority_class=dict(map=str, default=None),
            k8s_affinity=dict(map=str, default=None),
            k8s_node_selector=dict(map=str, default=None),
            k8s_extra_job_envs=dict(map=str, default=None),
            k8s_tolerations=dict(map=str, default=None),
            k8s_galaxy_instance_id=dict(map=str),
            k8s_timeout_seconds_job_deletion=dict(map=int, valid=lambda x: int > 0, default=30),
            k8s_job_api_version=dict(map=str, default=DEFAULT_JOB_API_VERSION),
            k8s_job_ttl_secs_after_finished=dict(map=int, valid=lambda x: x is None or int(x) >= 0, default=None),
            k8s_job_metadata=dict(map=str, default=None),
            k8s_supplemental_group_id=dict(
                map=str, valid=lambda s: s == "$gid" or isinstance(s, int) or not s or s.isdigit(), default=None
            ),
            k8s_pull_policy=dict(map=str, default="Default"),
            k8s_run_as_user_id=dict(
                map=str, valid=lambda s: s == "$uid" or isinstance(s, int) or not s or s.isdigit(), default=None
            ),
            k8s_run_as_group_id=dict(
                map=str, valid=lambda s: s == "$gid" or isinstance(s, int) or not s or s.isdigit(), default=None
            ),
            k8s_fs_group_id=dict(
                map=str, valid=lambda s: s == "$gid" or isinstance(s, int) or not s or s.isdigit(), default=None
            ),
            k8s_cleanup_job=dict(map=str, valid=lambda s: s in {"onsuccess", "always", "never"}, default="always"),
            k8s_pod_retries=dict(
                map=int, valid=lambda x: int(x) >= 0, default=1
            ),  # note that if the backOffLimit is lower, this paramer will have no effect.
            k8s_job_spec_back_off_limit=dict(
                map=int, valid=lambda x: int(x) >= 0, default=0
            ),  # this means that it will stop retrying after 1 failure.
            k8s_walltime_limit=dict(map=int, valid=lambda x: int(x) >= 0, default=172800),
            k8s_unschedulable_walltime_limit=dict(map=int, valid=lambda x: not x or int(x) >= 0, default=None),
            k8s_interactivetools_use_ssl=dict(map=bool, default=False),
            k8s_interactivetools_ingress_annotations=dict(map=str),
            k8s_interactivetools_ingress_class=dict(map=str, default=None),
            k8s_interactivetools_tls_secret=dict(map=str, default=None),
            k8s_ingress_api_version=dict(map=str, default=DEFAULT_INGRESS_API_VERSION),
        )

        if "runner_param_specs" not in kwargs:
            kwargs["runner_param_specs"] = {}
        kwargs["runner_param_specs"].update(runner_param_specs)

        # Start the job runner parent object
        super().__init__(app, nworkers, **kwargs)

        self._pykube_api = pykube_client_from_dict(self.runner_params)
        self._galaxy_instance_id = self.__get_galaxy_instance_id()

        self._run_as_user_id = self.__get_run_as_user_id()
        self._run_as_group_id = self.__get_run_as_group_id()
        self._supplemental_group = self.__get_supplemental_group()
        self._fs_group = self.__get_fs_group()
        self._default_pull_policy = self.__get_pull_policy()

        self.setup_base_volumes()

    def setup_base_volumes(self):
        def generate_volumes(pvc_list):
            return [{"name": pvc["name"], "persistentVolumeClaim": {"claimName": pvc["name"]}} for pvc in pvc_list]

        def get_volume_mounts_for(claim):
            if self.runner_params.get(claim):
                volume_mounts = [parse_pvc_param_line(pvc) for pvc in self.runner_params[claim].split(",")]
                # generate default list of volumes for all jobs
                volumes = generate_volumes(volume_mounts)
                return volumes, volume_mounts
            return [], []

        self.runner_params["k8s_volumes"], self.runner_params["k8s_volume_mounts"] = get_volume_mounts_for(
            "k8s_persistent_volume_claims"
        )
        # ignore volume mounts for the following two, as they are generated per job
        self.runner_params["k8s_volumes"].extend(get_volume_mounts_for("k8s_data_volume_claim")[0])
        self.runner_params["k8s_volumes"].extend(get_volume_mounts_for("k8s_working_volume_claim")[0])

    def queue_job(self, job_wrapper):
        """Create job script and submit it to Kubernetes cluster"""
        # prepare the job
        # We currently don't need to include_metadata or include_work_dir_outputs, as working directory is the same
        # where galaxy will expect results.
        log.debug(f"Starting queue_job for job {job_wrapper.get_id_tag()}")

        ajs = AsynchronousJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper,
            job_destination=job_wrapper.job_destination,
        )
        # Kubernetes doesn't really produce meaningful "job stdout", but file needs to be present
        with open(ajs.output_file, "w"):
            pass
        with open(ajs.error_file, "w"):
            pass

        if not self.prepare_job(
            job_wrapper,
            include_metadata=False,
            modify_command_for_container=False,
            stream_stdout_stderr=True,
        ):
            return

        script = self.get_job_file(
            job_wrapper, exit_code_path=ajs.exit_code_file, shell=job_wrapper.shell, galaxy_virtual_env=None
        )
        try:
            self.write_executable_script(ajs.job_file, script, job_io=job_wrapper.job_io)
        except Exception:
            job_wrapper.fail("failure preparing job script", exception=True)
            log.exception(f"({job_wrapper.get_id_tag()}) failure writing job script")
            return

        # Construction of Kubernetes objects follow: https://kubernetes.io/docs/concepts/workloads/controllers/job/
        if self.__has_guest_ports(job_wrapper):
            try:
                self.__configure_port_routing(ajs)
            except HTTPError:
                log.exception("Kubernetes failed to expose tool ports as services, HTTP exception encountered")
                ajs.runner_state = JobState.runner_states.UNKNOWN_ERROR
                ajs.fail_message = "Kubernetes failed to export tool ports as services."
                self.mark_as_failed(ajs)
                return

        k8s_job_prefix = self.__produce_k8s_job_prefix()
        k8s_job_obj = job_object_dict(self.runner_params, k8s_job_prefix, self.__get_k8s_job_spec(ajs))

        job = Job(self._pykube_api, k8s_job_obj)
        try:
            job.create()
        except HTTPError:
            log.exception("Kubernetes failed to create job, HTTP exception encountered")
            ajs.runner_state = JobState.runner_states.UNKNOWN_ERROR
            ajs.fail_message = "Kubernetes failed to create job."
            self.mark_as_failed(ajs)
            return
        if not job.name:
            log.exception(f"Kubernetes failed to create job, empty name encountered: [{job.obj}]")
            ajs.runner_state = JobState.runner_states.UNKNOWN_ERROR
            ajs.fail_message = "Kubernetes failed to create job."
            self.mark_as_failed(ajs)
            return
        job_id = job.name

        # define job attributes in the AsyncronousJobState for follow-up
        ajs.job_id = job_id
        # store runner information for tracking if Galaxy restarts
        job_wrapper.set_external_id(job_id)
        self.monitor_queue.put(ajs)

    def __has_guest_ports(self, job_wrapper):
        # Check if job has guest ports or interactive tool entry points that would signal that
        log.debug(
            f"Checking if job {job_wrapper.get_id_tag()} is an interactive tool. guest ports: {job_wrapper.guest_ports}. interactive entry points: {job_wrapper.get_job().interactivetool_entry_points}"
        )
        return bool(job_wrapper.guest_ports) or bool(job_wrapper.get_job().interactivetool_entry_points)

    def __configure_port_routing(self, ajs):
        # Configure interactive tool entry points first
        guest_ports = ajs.job_wrapper.guest_ports
        ports_dict = {}
        for guest_port in guest_ports:
            ports_dict[str(guest_port)] = dict(host="manual", port=guest_port, protocol="https")
        self.app.interactivetool_manager.configure_entry_points(ajs.job_wrapper.get_job(), ports_dict)

        # Configure additional k8s service and ingress for tools with guest ports
        k8s_job_prefix = self.__produce_k8s_job_prefix()
        k8s_job_name = self.__get_k8s_job_name(k8s_job_prefix, ajs.job_wrapper)
        log.debug(f"Configuring entry points and deploying service/ingress for job with ID {ajs.job_id}")
        k8s_service_obj = service_object_dict(self.runner_params, k8s_job_name, self.__get_k8s_service_spec(ajs))

        k8s_ingress_obj = ingress_object_dict(self.runner_params, k8s_job_name, self.__get_k8s_ingress_spec(ajs))
        log.debug(f"Kubernetes service object: {json.dumps(k8s_service_obj, indent=4)}")
        log.debug(f"Kubernetes ingress object: {json.dumps(k8s_ingress_obj, indent=4)}")
        # We avoid creating service and ingress if they already exist (e.g. when Galaxy is restarted or resubmitting a job)
        service = Service(self._pykube_api, k8s_service_obj)
        service.create()
        ingress = Ingress(self._pykube_api, k8s_ingress_obj)
        ingress.version = self.runner_params["k8s_ingress_api_version"]
        ingress.create()

    def __get_overridable_params(self, job_wrapper, param_key):
        dest_params = self.__get_destination_params(job_wrapper)
        return dest_params.get(param_key, self.runner_params[param_key])

    def __get_pull_policy(self):
        return pull_policy(self.runner_params)

    def __get_run_as_user_id(self):
        if self.runner_params.get("k8s_run_as_user_id") or self.runner_params.get("k8s_run_as_user_id") == 0:
            run_as_user = self.runner_params["k8s_run_as_user_id"]
            if run_as_user == "$uid":
                return os.getuid()
            else:
                try:
                    return int(self.runner_params["k8s_run_as_user_id"])
                except Exception:
                    log.warning(
                        'User ID passed for Kubernetes runner needs to be an integer or "$uid", value %s passed is invalid',
                        self.runner_params["k8s_run_as_user_id"],
                    )
                    return None
        return None

    def __get_run_as_group_id(self):
        if self.runner_params.get("k8s_run_as_group_id") or self.runner_params.get("k8s_run_as_group_id") == 0:
            run_as_group = self.runner_params["k8s_run_as_group_id"]
            if run_as_group == "$gid":
                return self.app.config.gid
            else:
                try:
                    return int(self.runner_params["k8s_run_as_group_id"])
                except Exception:
                    log.warning(
                        'Group ID passed for Kubernetes runner needs to be an integer or "$gid", value %s passed is invalid',
                        self.runner_params["k8s_run_as_group_id"],
                    )
        return None

    def __get_supplemental_group(self):
        if (
            self.runner_params.get("k8s_supplemental_group_id")
            or self.runner_params.get("k8s_supplemental_group_id") == 0
        ):
            try:
                return int(self.runner_params["k8s_supplemental_group_id"])
            except Exception:
                log.warning(
                    'Supplemental group passed for Kubernetes runner needs to be an integer or "$gid", value %s passed is invalid',
                    self.runner_params["k8s_supplemental_group_id"],
                )
                return None
        return None

    def __get_fs_group(self):
        if self.runner_params.get("k8s_fs_group_id") or self.runner_params.get("k8s_fs_group_id") == 0:
            try:
                return int(self.runner_params["k8s_fs_group_id"])
            except Exception:
                log.warning(
                    'FS group passed for Kubernetes runner needs to be an integer or "$gid", value %s passed is invalid',
                    self.runner_params["k8s_fs_group_id"],
                )
                return None
        return None

    def __get_galaxy_instance_id(self):
        """Parse the ID of the Galaxy instance from runner params."""
        return galaxy_instance_id(self.runner_params)

    def __produce_k8s_job_prefix(self):
        instance_id = self._galaxy_instance_id or ""
        return produce_k8s_job_prefix(app_prefix="gxy", instance_id=instance_id)

    def __get_k8s_job_spec(self, ajs):
        """Creates the k8s Job spec. For a Job spec, the only requirement is to have a .spec.template.
        If the job hangs around unlimited it will be ended after k8s wall time limit, which sets activeDeadlineSeconds
        """
        k8s_job_spec = {
            "template": self.__get_k8s_job_spec_template(ajs),
            "activeDeadlineSeconds": int(self.runner_params["k8s_walltime_limit"]),
        }
        job_ttl = self.runner_params["k8s_job_ttl_secs_after_finished"]
        if self.runner_params["k8s_cleanup_job"] != "never" and job_ttl is not None:
            k8s_job_spec["ttlSecondsAfterFinished"] = job_ttl
        k8s_job_spec["backoffLimit"] = self.runner_params["k8s_job_spec_back_off_limit"]
        return k8s_job_spec

    def __force_label_conformity(self, value):
        """
        Make sure that a label conforms to k8s requirements.
        A valid label must be an empty string or consist of alphanumeric characters, '-', '_' or '.',
        and must start and end with an alphanumeric character (e.g. 'MyValue',  or 'my_value',  or '12345',
        regex used for validation is '(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?')
        """
        label_val = self.LABEL_REGEX.sub("_", value)
        if not self.LABEL_START.search(label_val):
            label_val = f"x{label_val}"
        if not self.LABEL_END.search(label_val):
            label_val += "x"
        return label_val

    def __get_k8s_job_spec_template(self, ajs):
        """The k8s spec template is nothing but a Pod spec, except that it is nested and does not have an apiversion
        nor kind. In addition to required fields for a Pod, a pod template in a job must specify appropriate labels
        (see pod selector) and an appropriate restart policy."""
        k8s_spec_template = {
            "metadata": {
                "labels": {
                    "app.kubernetes.io/name": self.__force_label_conformity(ajs.job_wrapper.tool.old_id),
                    "app.kubernetes.io/instance": self.__produce_k8s_job_prefix(),
                    "app.kubernetes.io/version": self.__force_label_conformity(str(ajs.job_wrapper.tool.version)),
                    "app.kubernetes.io/component": "tool",
                    "app.kubernetes.io/part-of": "galaxy",
                    "app.kubernetes.io/managed-by": "galaxy",
                    "app.galaxyproject.org/job_id": self.__force_label_conformity(ajs.job_wrapper.get_id_tag()),
                    "app.galaxyproject.org/handler": self.__force_label_conformity(self.app.config.server_name),
                    "app.galaxyproject.org/destination": self.__force_label_conformity(
                        str(ajs.job_wrapper.job_destination.id)
                    ),
                },
                "annotations": {"app.galaxyproject.org/tool_id": ajs.job_wrapper.tool.id},
            },
            "spec": {
                "volumes": deduplicate_entries(self.runner_params["k8s_volumes"]),
                "restartPolicy": self.__get_k8s_restart_policy(ajs.job_wrapper),
                "containers": self.__get_k8s_containers(ajs),
                "priorityClassName": self.runner_params["k8s_pod_priority_class"],
                "tolerations": yaml.safe_load(self.runner_params["k8s_tolerations"] or "[]"),
                "affinity": yaml.safe_load(self.__get_overridable_params(ajs.job_wrapper, "k8s_affinity") or "{}"),
                "nodeSelector": yaml.safe_load(
                    self.__get_overridable_params(ajs.job_wrapper, "k8s_node_selector") or "{}"
                ),
            },
        }
        # TODO include other relevant elements that people might want to use from
        # TODO http://kubernetes.io/docs/api-reference/v1/definitions/#_v1_podspec
        k8s_spec_template["spec"]["securityContext"] = self.__get_k8s_security_context()
        extra_metadata = self.runner_params["k8s_job_metadata"] or "{}"
        if isinstance(extra_metadata, str):
            extra_metadata = yaml.safe_load(extra_metadata)
        k8s_spec_template["metadata"]["labels"].update(extra_metadata.get("labels", {}))
        k8s_spec_template["metadata"]["annotations"].update(extra_metadata.get("annotations", {}))
        return k8s_spec_template

    def __get_k8s_service_spec(self, ajs):
        """The k8s spec template is nothing but a Service spec, except that it is nested and does not have an apiversion
        nor kind."""
        guest_ports = ajs.job_wrapper.guest_ports
        k8s_spec_template = {
            "metadata": {
                "labels": {
                    "app.galaxyproject.org/handler": self.__force_label_conformity(self.app.config.server_name),
                    "app.galaxyproject.org/destination": self.__force_label_conformity(
                        str(ajs.job_wrapper.job_destination.id)
                    ),
                },
                "annotations": {"app.galaxyproject.org/tool_id": ajs.job_wrapper.tool.id},
            },
            "spec": {
                "ports": [
                    {
                        "name": f"job-{self.__force_label_conformity(ajs.job_wrapper.get_id_tag())}-{p}",
                        "port": int(p),
                        "protocol": "TCP",
                        "targetPort": int(p),
                    }
                    for p in guest_ports
                ],
                "selector": {
                    "app.kubernetes.io/name": self.__force_label_conformity(ajs.job_wrapper.tool.old_id),
                    "app.kubernetes.io/component": "tool",
                    "app.galaxyproject.org/job_id": self.__force_label_conformity(ajs.job_wrapper.get_id_tag()),
                },
                "type": "ClusterIP",
            },
        }
        return k8s_spec_template

    def __get_k8s_ingress_rules_spec(self, ajs, entry_points):
        """This represents the template for the "rules" portion of the Ingress spec."""
        if "v1beta1" in self.runner_params["k8s_ingress_api_version"]:
            rules_spec = [
                {
                    "host": ep["domain"],
                    "http": {
                        "paths": [
                            {
                                "backend": {
                                    "serviceName": self.__get_k8s_job_name(
                                        self.__produce_k8s_job_prefix(), ajs.job_wrapper
                                    ),
                                    "servicePort": int(ep["tool_port"]),
                                },
                                "path": ep.get("entry_path", "/"),
                                "pathType": "Prefix",
                            }
                        ]
                    },
                }
                for ep in entry_points
            ]
        else:
            rules_spec = [
                {
                    "host": ep["domain"],
                    "http": {
                        "paths": [
                            {
                                "backend": {
                                    "service": {
                                        "name": self.__get_k8s_job_name(
                                            self.__produce_k8s_job_prefix(), ajs.job_wrapper
                                        ),
                                        "port": {"number": int(ep["tool_port"])},
                                    }
                                },
                                "path": ep.get("entry_path", "/"),
                                "pathType": "ImplementationSpecific",
                            }
                        ]
                    },
                }
                for ep in entry_points
            ]
        return rules_spec

    def __get_k8s_ingress_spec(self, ajs):
        """The k8s spec template is nothing but a Ingress spec, except that it is nested and does not have an apiversion
        nor kind."""
        guest_ports = ajs.job_wrapper.guest_ports
        if len(guest_ports) > 0:
            entry_points = []
            configured_eps = [ep for ep in ajs.job_wrapper.get_job().interactivetool_entry_points if ep.configured]
            for entry_point in configured_eps:
                # sending in self.app as `trans` since it's only used for `.security` so seems to work
                entry_point_path = self.app.interactivetool_manager.get_entry_point_path(self.app, entry_point)
                if "?" in entry_point_path:
                    # Removing all the parameters from the ingress path, but they will still be in the database
                    # so the link that the user clicks on will still have them
                    log.warning(
                        "IT urls including parameters (eg: /myit?mykey=myvalue) are only experimentally supported on K8S"
                    )
                    entry_point_path = entry_point_path.split("?")[0]
                entry_point_domain = f"{self.app.config.interactivetools_proxy_host}"
                if entry_point.requires_domain:
                    entry_point_subdomain = self.app.interactivetool_manager.get_entry_point_subdomain(
                        self.app, entry_point
                    )
                    entry_point_domain = f"{entry_point_subdomain}.{entry_point_domain}"
                    entry_point_path = "/"
                entry_points.append(
                    {"tool_port": entry_point.tool_port, "domain": entry_point_domain, "entry_path": entry_point_path}
                )
        k8s_spec_template = {
            "metadata": {
                "labels": {
                    "app.galaxyproject.org/handler": self.__force_label_conformity(self.app.config.server_name),
                    "app.galaxyproject.org/destination": self.__force_label_conformity(
                        str(ajs.job_wrapper.job_destination.id)
                    ),
                },
                "annotations": {"app.galaxyproject.org/tool_id": ajs.job_wrapper.tool.id},
            },
            "spec": {"rules": self.__get_k8s_ingress_rules_spec(ajs, entry_points)},
        }
        default_ingress_class = self.runner_params.get("k8s_interactivetools_ingress_class")
        if default_ingress_class:
            k8s_spec_template["spec"]["ingressClassName"] = default_ingress_class
        if self.runner_params.get("k8s_interactivetools_use_ssl"):
            domains = list({e["domain"] for e in entry_points})
            override_secret = self.runner_params.get("k8s_interactivetools_tls_secret")
            if override_secret:
                k8s_spec_template["spec"]["tls"] = [
                    {"hosts": [domain], "secretName": override_secret} for domain in domains
                ]
            else:
                k8s_spec_template["spec"]["tls"] = [
                    {"hosts": [domain], "secretName": re.sub("[^a-z0-9-]", "-", domain)} for domain in domains
                ]
        if self.runner_params.get("k8s_interactivetools_ingress_annotations"):
            new_ann = yaml.safe_load(self.runner_params.get("k8s_interactivetools_ingress_annotations"))
            k8s_spec_template["metadata"]["annotations"].update(new_ann)
        return k8s_spec_template

    def __get_k8s_security_context(self):
        security_context = {}
        if self._run_as_user_id or self._run_as_user_id == 0:
            security_context["runAsUser"] = self._run_as_user_id
        if self._run_as_group_id or self._run_as_group_id == 0:
            security_context["runAsGroup"] = self._run_as_group_id
        if self._supplemental_group and self._supplemental_group > 0:
            security_context["supplementalGroups"] = [self._supplemental_group]
        if self._fs_group and self._fs_group > 0:
            security_context["fsGroup"] = self._fs_group
        return security_context

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
        container = self._find_container(ajs.job_wrapper)

        mounts = get_volume_mounts_for_job(
            ajs.job_wrapper,
            self.runner_params.get("k8s_data_volume_claim"),
            self.runner_params.get("k8s_working_volume_claim"),
        )
        mounts.extend(self.runner_params["k8s_volume_mounts"])

        k8s_container = {
            "name": self.__get_k8s_container_name(ajs.job_wrapper),
            "image": container.container_id,
            # this form of command overrides the entrypoint and allows multi command
            # command line execution, separated by ;, which is what Galaxy does
            # to assemble the command.
            "command": [ajs.job_wrapper.shell],
            # Make sure that the exit code is propagated to k8s, so k8s knows why the tool failed (e.g. OOM)
            "args": ["-c", f"{ajs.job_file}; exit $(cat {ajs.exit_code_file})"],
            "workingDir": ajs.job_wrapper.working_directory,
            "volumeMounts": deduplicate_entries(mounts),
        }

        if resources := self.__get_resources(ajs.job_wrapper):
            envs = []
            cpu_val = None
            if "requests" in resources:
                requests = resources["requests"]
                if "cpu" in requests:
                    cpu_val = int(math.ceil(float(requests["cpu"])))
                    envs.append({"name": "GALAXY_SLOTS", "value": str(cpu_val)})
                if "memory" in requests:
                    mem_val = ByteSize(requests["memory"]).to_unit("M", as_string=False)
                    envs.append({"name": "GALAXY_MEMORY_MB", "value": str(mem_val)})
                    if cpu_val:
                        envs.append({"name": "GALAXY_MEMORY_MB_PER_SLOT", "value": str(math.floor(mem_val / cpu_val))})
            elif "limits" in resources:
                limits = resources["limits"]
                if "cpu" in limits:
                    cpu_val = int(math.floor(float(limits["cpu"])))
                    cpu_val = cpu_val or 1
                    envs.append({"name": "GALAXY_SLOTS", "value": str(cpu_val)})
                if "memory" in limits:
                    mem_val = ByteSize(limits["memory"]).to_unit("M", as_string=False)
                    envs.append({"name": "GALAXY_MEMORY_MB", "value": str(mem_val)})
                    if cpu_val:
                        envs.append({"name": "GALAXY_MEMORY_MB_PER_SLOT", "value": str(math.floor(mem_val / cpu_val))})
            extra_envs = yaml.safe_load(self.__get_overridable_params(ajs.job_wrapper, "k8s_extra_job_envs") or "{}")
            for key in extra_envs:
                envs.append({"name": key, "value": extra_envs[key]})
            if self.__has_guest_ports(ajs.job_wrapper):
                configured_eps = [ep for ep in ajs.job_wrapper.get_job().interactivetool_entry_points if ep.configured]
                for entry_point in configured_eps:
                    # sending in self.app as `trans` since it's only used for `.security` so seems to work
                    entry_point_path = self.app.interactivetool_manager.get_entry_point_path(self.app, entry_point)
                    if "?" in entry_point_path:
                        # Removing all the parameters from the ingress path, but they will still be in the database
                        # so the link that the user clicks on will still have them
                        log.warning(
                            "IT urls including parameters (eg: /myit?mykey=myvalue) are only experimentally supported on K8S"
                        )
                        entry_point_path = entry_point_path.split("?")[0]
                    entry_point_domain = f"{self.app.config.interactivetools_proxy_host}"
                    if entry_point.requires_domain:
                        entry_point_subdomain = self.app.interactivetool_manager.get_entry_point_subdomain(
                            self.app, entry_point
                        )
                        entry_point_domain = f"{entry_point_subdomain}.{entry_point_domain}"
                    envs.append({"name": "INTERACTIVETOOL_PORT", "value": str(entry_point.tool_port)})
                    envs.append({"name": "INTERACTIVETOOL_DOMAIN", "value": str(entry_point_domain)})
                    envs.append({"name": "INTERACTIVETOOL_PATH", "value": str(entry_point_path)})
            k8s_container["resources"] = resources
            k8s_container["env"] = envs

        if self._default_pull_policy:
            k8s_container["imagePullPolicy"] = self._default_pull_policy

        return [k8s_container]

    def __get_resources(self, job_wrapper):
        requests = {}
        limits = {}

        if mem_request := self.__get_memory_request(job_wrapper):
            requests["memory"] = mem_request
        if cpu_request := self.__get_cpu_request(job_wrapper):
            requests["cpu"] = cpu_request

        if mem_limit := self.__get_memory_limit(job_wrapper):
            limits["memory"] = mem_limit
        if cpu_limit := self.__get_cpu_limit(job_wrapper):
            limits["cpu"] = cpu_limit

        resources = {}
        if requests:
            resources["requests"] = requests
        if limits:
            resources["limits"] = limits

        return resources

    def __get_memory_request(self, job_wrapper):
        """Obtains memory requests for job, checking if available on the destination, otherwise using the default"""
        job_destination = job_wrapper.job_destination

        if "requests_memory" in job_destination.params:
            return self.__transform_memory_value(job_destination.params["requests_memory"])
        return None

    def __get_memory_limit(self, job_wrapper):
        """Obtains memory limits for job, checking if available on the destination, otherwise using the default"""
        job_destination = job_wrapper.job_destination

        if "limits_memory" in job_destination.params:
            return self.__transform_memory_value(job_destination.params["limits_memory"])
        return None

    def __get_cpu_request(self, job_wrapper):
        """Obtains cpu requests for job, checking if available on the destination, otherwise using the default"""
        job_destination = job_wrapper.job_destination

        if "requests_cpu" in job_destination.params:
            return job_destination.params["requests_cpu"]
        return None

    def __get_cpu_limit(self, job_wrapper):
        """Obtains cpu requests for job, checking if available on the destination, otherwise using the default"""
        job_destination = job_wrapper.job_destination

        if "limits_cpu" in job_destination.params:
            return job_destination.params["limits_cpu"]
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
        if "repo" in job_destination.params:
            repo = f"{job_destination.params['repo']}/"
        if "owner" in job_destination.params:
            owner = f"{job_destination.params['owner']}/"

        k8s_cont_image = repo + owner + job_destination.params["image"]

        if "tag" in job_destination.params:
            k8s_cont_image += f":{job_destination.params['tag']}"

        return k8s_cont_image

    def __get_k8s_container_name(self, job_wrapper):
        # These must follow a specific regex for Kubernetes.
        raw_id = job_wrapper.job_destination.id
        if isinstance(raw_id, str):
            cleaned_id = re.sub("[^-a-z0-9]", "-", raw_id)
            if cleaned_id.startswith("-") or cleaned_id.endswith("-"):
                cleaned_id = f"x{cleaned_id}x"
            return cleaned_id
        return "job-container"

    def __get_k8s_job_name(self, prefix, job_wrapper):
        return f"{prefix}-{self.__force_label_conformity(job_wrapper.get_id_tag())}"

    def __get_destination_params(self, job_wrapper):
        """Obtains allowable runner param overrides from the destination"""
        job_destination = job_wrapper.job_destination
        OVERRIDABLE_PARAMS = ["k8s_node_selector", "k8s_affinity", "k8s_extra_job_envs"]
        new_params = {}
        for each_param in OVERRIDABLE_PARAMS:
            if each_param in job_destination.params:
                new_params[each_param] = job_destination.params[each_param]
        return new_params

    def check_watched_item(self, job_state):
        """Checks the state of a job already submitted on k8s. Job state is an AsynchronousJobState"""
        jobs = find_job_object_by_name(self._pykube_api, job_state.job_id, self.runner_params["k8s_namespace"])

        if len(jobs.response["items"]) == 1:
            job = Job(self._pykube_api, jobs.response["items"][0])
            job_destination = job_state.job_wrapper.job_destination
            succeeded = 0
            active = 0
            failed = 0

            if "max_pod_retries" in job_destination.params:
                max_pod_retries = int(job_destination.params["max_pod_retries"])
            elif "k8s_pod_retries" in self.runner_params:
                max_pod_retries = int(self.runner_params["k8s_pod_retries"])
            else:
                max_pod_retries = 1

            # make sure that we don't have any conditions by which the runner
            # would wait forever for a pod that never gets sent.
            max_pod_retries = min(max_pod_retries, self.runner_params["k8s_job_spec_back_off_limit"])

            # Check if job.obj['status'] is empty,
            # return job_state unchanged if this is the case
            # as probably this means that the k8s API server hasn't
            # had time to fill in the object status since the
            # job was created only too recently.
            # It is possible that k8s didn't account for the status of the pods
            # and they are in the uncountedTerminatedPods status. In this
            # case we also need to wait a moment
            if len(job.obj["status"]) == 0 or job.obj["status"].get("uncountedTerminatedPods"):
                return job_state
            if "succeeded" in job.obj["status"]:
                succeeded = job.obj["status"]["succeeded"]
            if "active" in job.obj["status"]:
                active = job.obj["status"]["active"]
            if "failed" in job.obj["status"]:
                failed = job.obj["status"]["failed"]

            job_persisted_state = job_state.job_wrapper.get_state()

            # This assumes jobs dependent on a single pod, single container
            if succeeded > 0 or job_state == model.Job.states.STOPPED:
                job_state.running = False
                self.mark_as_finished(job_state)
                log.debug(f"Job id: {job_state.job_id} with k8s id: {job.name} succeeded")
                return None
            elif active > 0 and failed < max_pod_retries + 1:
                if not job_state.running:
                    if self.__job_pending_due_to_unschedulable_pod(job_state):
                        log.debug(f"Job id: {job_state.job_id} with k8s id: {job.name}  pending...")
                        if self.runner_params.get("k8s_unschedulable_walltime_limit"):
                            creation_time_str = job.obj["metadata"].get("creationTimestamp")
                            creation_time = datetime.strptime(creation_time_str, "%Y-%m-%dT%H:%M:%SZ")
                            elapsed_seconds = (datetime.utcnow() - creation_time).total_seconds()
                            if elapsed_seconds > self.runner_params["k8s_unschedulable_walltime_limit"]:
                                return self._handle_unschedulable_job(job, job_state)
                            else:
                                pass
                        else:
                            pass
                    elif self.__check_job_pod_running(job_state):
                        log.debug("Job set to running...")
                        job_state.running = True
                        job_state.job_wrapper.change_state(model.Job.states.RUNNING)
                    else:
                        log.debug(
                            f"Job id: {job_state.job_id} with k8s id: {job.name} scheduled and is waiting to start..."
                        )
                return job_state
            elif job_persisted_state == model.Job.states.DELETED:
                # Job has been deleted via stop_job and job has not been deleted,
                # remove from watched_jobs by returning `None`
                log.debug(f"Job id: {job_state.job_id} has been already deleted...")
                if job_state.job_wrapper.cleanup_job in ("always", "onsuccess"):
                    job_state.job_wrapper.cleanup()
                return None
            else:
                log.debug(
                    f"Job id: {job_state.job_id} failed and it is not a deletion case. Current state: {job_state.job_wrapper.get_state()}"
                )
                if self._handle_job_failure(job, job_state):
                    # changes for resubmission (removed self.mark_as_failed from handle_job_failure)
                    self.work_queue.put((self.mark_as_failed, job_state))
                else:
                    # Job failure was not due to a k8s issue or something that k8s can handle, so it's a tool error.
                    job_state.running = False
                    self.mark_as_finished(job_state)
                    return None

                return None

        elif len(jobs.response["items"]) == 0:
            if job_state.job_wrapper.get_job().state == model.Job.states.DELETED:
                if job_state.job_wrapper.cleanup_job in ("always", "onsuccess"):
                    job_state.job_wrapper.cleanup()
                return None
            if job_state.job_wrapper.get_job().state == model.Job.states.STOPPED and self.__has_guest_ports(
                job_state.job_wrapper
            ):
                # Interactive job has been stopped via stop_job (most likely by the user),
                # cleanup and remove from watched_jobs by returning `None`. STOPPED jobs are cleaned up elsewhere.
                # Marking as finished makes sure that the interactive job output is available in the UI.
                self.mark_as_finished(job_state)
                return None
            # there is no job responding to this job_id, it is either lost or something happened.
            log.error(
                f"No Jobs are available under expected selector app={job_state.job_id} and they are not deleted or stopped either."
            )
            self.mark_as_failed(job_state)
            # job is no longer viable - remove from watched jobs
            return None
        else:
            # there is more than one job associated to the expected unique job id used as selector.
            log.error("More than one Kubernetes Job associated to job id '%s'", job_state.job_id)
            self.mark_as_failed(job_state)
            # job is no longer viable - remove from watched jobs
            return None

    def _handle_unschedulable_job(self, job, job_state):
        # Handle unschedulable job that exceeded deadline
        job_state.fail_message = "Job was unschedulable longer than specified deadline"
        job_state.runner_state = JobState.runner_states.WALLTIME_REACHED
        job_state.running = False
        self.mark_as_failed(job_state)
        try:
            if self.__has_guest_ports(job_state.job_wrapper):
                self.__cleanup_k8s_guest_ports(job_state.job_wrapper, job)
            self.__cleanup_k8s_job(job)
        except Exception:
            log.exception("Could not clean up k8s batch job. Ignoring...")
        return None

    def _handle_job_failure(self, job, job_state):
        # Figure out why job has failed
        mark_failed = True
        with open(job_state.error_file, "a") as error_file:
            log.debug("Trying with error file in _handle_job_failure")
            if self.__job_failed_due_to_low_memory(job_state):
                log.debug(f"OOM detected for job: {job_state.job_id}")
                error_file.write("Job killed after running out of memory. Try with more memory.\n")
                job_state.fail_message = "Tool failed due to insufficient memory. Try with more memory."
                job_state.runner_state = JobState.runner_states.MEMORY_LIMIT_REACHED
            elif self.__job_failed_due_to_walltime_limit(job):
                log.debug(f"Walltime limit reached for job: {job_state.job_id}")
                error_file.write("DeadlineExceeded")
                job_state.fail_message = "Job was active longer than specified deadline"
                job_state.runner_state = JobState.runner_states.WALLTIME_REACHED
            elif self.__job_failed_due_to_unknown_exit_code(job_state):
                msg = f"Job: {job_state.job_id} failed due to an unknown exit code from the tool."
                log.debug(msg)
                job_state.fail_message = msg
                job_state.runner_state = JobState.runner_states.TOOL_DETECT_ERROR
                mark_failed = False
            else:
                msg = f"An unknown error occurred in this job and the maximum number of retries have been exceeded for job: {job_state.job_id}."
                log.debug(msg)
                error_file.write(msg)
                job_state.fail_message = (
                    "An unknown error occurered with this job. See standard output within the info section for details."
                )
        # changes for resubmission
        # job_state.running = False
        # self.mark_as_failed(job_state)
        try:
            if self.__has_guest_ports(job_state.job_wrapper):
                self.__cleanup_k8s_guest_ports(job_state.job_wrapper, job)
            self.__cleanup_k8s_job(job)
        except Exception:
            log.exception("Could not clean up k8s batch job. Ignoring...")
        return mark_failed

    def __cleanup_k8s_job(self, job):
        k8s_cleanup_job = self.runner_params["k8s_cleanup_job"]
        delete_job(job, k8s_cleanup_job)

    def __cleanup_k8s_ingress(self, ingress, job_failed=False):
        k8s_cleanup_job = self.runner_params["k8s_cleanup_job"]
        delete_ingress(ingress, k8s_cleanup_job, job_failed)

    def __cleanup_k8s_service(self, service, job_failed=False):
        k8s_cleanup_job = self.runner_params["k8s_cleanup_job"]
        delete_service(service, k8s_cleanup_job, job_failed)

    def __job_failed_due_to_walltime_limit(self, job):
        conditions = job.obj["status"].get("conditions") or []
        return any(True for c in conditions if c["type"] == "Failed" and c["reason"] == "DeadlineExceeded")

    def _get_pod_for_job(self, job_state):
        pods = Pod.objects(self._pykube_api).filter(
            selector=f"app={job_state.job_id}", namespace=self.runner_params["k8s_namespace"]
        )
        if not pods.response["items"]:
            return None

        pod = Pod(self._pykube_api, pods.response["items"][0])
        return pod

    def __job_failed_due_to_low_memory(self, job_state):
        """
        checks the state of the pod to see if it was killed
        for being out of memory (pod status OOMKilled). If that is the case
        marks the job for resubmission (resubmit logic is part of destinations).
        """
        pods = find_pod_object_by_name(self._pykube_api, job_state.job_id, self.runner_params["k8s_namespace"])
        if not pods.response["items"]:
            return False

        # pod = self._get_pod_for_job(job_state) # this was always None
        pod = pods.response["items"][0]
        if (
            pod
            and "terminated" in pod["status"]["containerStatuses"][0]["state"]
            and pod["status"]["containerStatuses"][0]["state"]["terminated"]["reason"] == "OOMKilled"
        ):
            return True

        return False

    def __check_job_pod_running(self, job_state):
        """
        checks the state of the pod to see if it is running.
        """
        pods = find_pod_object_by_name(self._pykube_api, job_state.job_id, self.runner_params["k8s_namespace"])
        if not pods.response["items"]:
            return False

        pod = Pod(self._pykube_api, pods.response["items"][0])
        return is_pod_running(self._pykube_api, pod, self.runner_params["k8s_namespace"])

    def __job_pending_due_to_unschedulable_pod(self, job_state):
        """
        checks the state of the pod to see if it is unschedulable.
        """
        pods = find_pod_object_by_name(self._pykube_api, job_state.job_id, self.runner_params["k8s_namespace"])
        if not pods.response["items"]:
            return False

        pod = Pod(self._pykube_api, pods.response["items"][0])
        return is_pod_unschedulable(self._pykube_api, pod, self.runner_params["k8s_namespace"])

    def __job_failed_due_to_unknown_exit_code(self, job_state):
        """
        checks whether the pod exited prematurely due to an unknown exit code (i.e. not an exit code like OOM that
        we can handle). This would mean that the tool failed, but the job should be considered to have succeeded.
        """
        pods = find_pod_object_by_name(self._pykube_api, job_state.job_id, self.runner_params["k8s_namespace"])
        if not pods.response["items"]:
            return False

        pod = pods.response["items"][0]
        if (
            pod
            and "terminated" in pod["status"]["containerStatuses"][0]["state"]
            and pod["status"]["containerStatuses"][0]["state"]["terminated"].get("exitCode")
        ):
            return True

        return False

    def __cleanup_k8s_guest_ports(self, job_wrapper, k8s_job):
        k8s_job_prefix = self.__produce_k8s_job_prefix()
        k8s_job_name = f"{k8s_job_prefix}-{self.__force_label_conformity(job_wrapper.get_id_tag())}"
        log.debug(f"Deleting service/ingress for job with ID {job_wrapper.get_id_tag()}")
        ingress_to_delete = find_ingress_object_by_name(
            self._pykube_api, k8s_job_name, self.runner_params["k8s_namespace"]
        )
        if ingress_to_delete and len(ingress_to_delete.response["items"]) > 0:
            k8s_ingress = Ingress(self._pykube_api, ingress_to_delete.response["items"][0])
            self.__cleanup_k8s_ingress(k8s_ingress)
        else:
            log.debug(f"No ingress found for job with k8s_job_name {k8s_job_name}")
        service_to_delete = find_service_object_by_name(
            self._pykube_api, k8s_job_name, self.runner_params["k8s_namespace"]
        )
        if service_to_delete and len(service_to_delete.response["items"]) > 0:
            k8s_service = Service(self._pykube_api, service_to_delete.response["items"][0])
            self.__cleanup_k8s_service(k8s_service)
        else:
            log.debug(f"No service found for job with k8s_job_name {k8s_job_name}")
        # remove the interactive environment entrypoints
        if eps := job_wrapper.get_job().interactivetool_entry_points:
            log.debug(f"Removing entry points for job with ID {job_wrapper.get_id_tag()}")
            self.app.interactivetool_manager.remove_entry_points(eps)

    def stop_job(self, job_wrapper):
        """Attempts to delete a dispatched job to the k8s cluster"""
        job = job_wrapper.get_job()
        try:
            log.debug(f"Attempting to stop job {job.id} ({job.job_runner_external_id})")
            job_to_delete = find_job_object_by_name(
                self._pykube_api, job.get_job_runner_external_id(), self.runner_params["k8s_namespace"]
            )
            if job_to_delete and len(job_to_delete.response["items"]) > 0:
                k8s_job = Job(self._pykube_api, job_to_delete.response["items"][0])
                log.debug(f"Found job with id {job.get_job_runner_external_id()} to delete")
                # For interactive jobs, at this point because the job stopping has been partly handled by the
                # interactive tool manager, the job wrapper no longer shows any guest ports. We need another way
                # to check if the job is an interactive job.
                if self.__has_guest_ports(job_wrapper):
                    log.debug(f"Job {job.id} ({job.job_runner_external_id}) has guest ports, cleaning them up")
                    self.__cleanup_k8s_guest_ports(job_wrapper, k8s_job)
                self.__cleanup_k8s_job(k8s_job)
            else:
                log.debug(f"Could not find job with id {job.get_job_runner_external_id()} to delete")
            # TODO assert whether job parallelism == 0
            # assert not job_to_delete.exists(), "Could not delete job,"+job.job_runner_external_id+" it still exists"
            log.debug(f"({job.id}/{job.job_runner_external_id}) Terminated at user's request")

        except Exception as e:
            log.exception(
                "(%s/%s) User killed running job, but error encountered during termination: %s",
                job.id,
                job.get_job_runner_external_id(),
                e,
            )

    def recover(self, job, job_wrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_id = job.get_job_runner_external_id()
        log.debug(f"k8s trying to recover job: {job_id}")
        if job_id is None:
            self.put(job_wrapper)
            return
        ajs = AsynchronousJobState(
            files_dir=job_wrapper.working_directory,
            job_wrapper=job_wrapper,
            job_id=job_id,
            job_destination=job_wrapper.job_destination,
        )
        ajs.command_line = job.command_line
        if job.state in (model.Job.states.RUNNING, model.Job.states.STOPPED):
            log.debug(
                "(%s/%s) is still in %s state, adding to the runner monitor queue",
                job.id,
                job.job_runner_external_id,
                job.state,
            )
            ajs.old_state = model.Job.states.RUNNING
            ajs.running = True
            self.monitor_queue.put(ajs)
        elif job.state == model.Job.states.QUEUED:
            log.debug(
                "(%s/%s) is still in queued state, adding to the runner monitor queue",
                job.id,
                job.job_runner_external_id,
            )
            ajs.old_state = model.Job.states.QUEUED
            ajs.running = False
            self.monitor_queue.put(ajs)

    # added to make sure that stdout and stderr is captured for Kubernetes
    def fail_job(self, job_state: "JobState", exception=False, message="Job failed", full_status=None):
        log.debug("PP Getting into fail_job in k8s runner")
        job = job_state.job_wrapper.get_job()

        # Get STDOUT and STDERR from the job and tool to be stored in the database #
        # This is needed because when calling finish_job on a failed job, the check_output method
        # overrides the job error state and tries to figure it out from the job output files
        # breaking OOM resubmissions.
        # To ensure that files below are readable, ownership must be reclaimed first
        job_state.job_wrapper.reclaim_ownership()

        # wait for the files to appear
        which_try = 0
        while which_try < self.app.config.retry_job_output_collection + 1:
            try:
                with open(job_state.output_file, "rb") as stdout_file, open(job_state.error_file, "rb") as stderr_file:
                    job_stdout = self._job_io_for_db(stdout_file)
                    job_stderr = self._job_io_for_db(stderr_file)
                break
            except Exception as e:
                if which_try == self.app.config.retry_job_output_collection:
                    job_stdout = ""
                    job_stderr = job_state.runner_states.JOB_OUTPUT_NOT_RETURNED_FROM_CLUSTER
                    log.error(f"{job.id}/{job.job_runner_external_id} {job_stderr}: {unicodify(e)}")
                else:
                    time.sleep(1)
                which_try += 1

        # get stderr and stdout to database
        outputs_directory = os.path.join(job_state.job_wrapper.working_directory, "outputs")
        if not os.path.exists(outputs_directory):
            outputs_directory = job_state.job_wrapper.working_directory

        tool_stdout_path = os.path.join(outputs_directory, "tool_stdout")
        tool_stderr_path = os.path.join(outputs_directory, "tool_stderr")

        # TODO: These might not exist for running jobs at the upgrade to 19.XX, remove that
        # assumption in 20.XX.
        tool_stderr = "Galaxy issue: stderr could not be retrieved from the job working directory."
        tool_stdout = "Galaxy issue: stdout could not be retrieved from the job working directory."
        if os.path.exists(tool_stdout_path):
            with open(tool_stdout_path, "rb") as stdout_file:
                tool_stdout = self._job_io_for_db(stdout_file)
        else:
            # Legacy job, were getting a merged output - assume it is mostly tool output.
            tool_stdout = job_stdout
            job_stdout = None

        if os.path.exists(tool_stderr_path):
            with open(tool_stderr_path, "rb") as stdout_file:
                tool_stderr = self._job_io_for_db(stdout_file)
        else:
            # Legacy job, were getting a merged output - assume it is mostly tool output.
            tool_stderr = job_stderr
            job_stderr = None

        # full status empty leaves the UI without stderr/stdout
        full_status = {"stderr": tool_stderr, "stdout": tool_stdout}
        log.debug(f"({job.id}/{job.job_runner_external_id}) tool_stdout: {tool_stdout}")
        log.debug(f"({job.id}/{job.job_runner_external_id}) tool_stderr: {tool_stderr}")
        log.debug(f"({job.id}/{job.job_runner_external_id}) job_stdout: {job_stdout}")
        log.debug(f"({job.id}/{job.job_runner_external_id}) job_stderr: {job_stderr}")

        # run super method
        super().fail_job(job_state, exception, message, full_status)

    def finish_job(self, job_state):
        self._handle_metadata_externally(job_state.job_wrapper, resolve_requirements=True)
        super().finish_job(job_state)
        jobs = find_job_object_by_name(self._pykube_api, job_state.job_id, self.runner_params["k8s_namespace"])
        if len(jobs.response["items"]) > 1:
            log.warning(
                "More than one job matches selector: %s. Possible configuration error in job id '%s'",
                jobs.response["items"],
                job_state.job_id,
            )
        elif len(jobs.response["items"]) == 0:
            log.warning("No k8s job found which matches job id '%s'. Ignoring...", job_state.job_id)
        else:
            job = Job(self._pykube_api, jobs.response["items"][0])
            if self.__has_guest_ports(job_state.job_wrapper):
                self.__cleanup_k8s_guest_ports(job_state.job_wrapper, job)
            self.__cleanup_k8s_job(job)
