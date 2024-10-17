"""Interface layer for pykube library shared between Galaxy and Pulsar."""

import logging
import os
import re
from pathlib import PurePath

try:
    from pykube.config import KubeConfig
    from pykube.exceptions import (
        HTTPError,
        ObjectDoesNotExist,
    )
    from pykube.http import HTTPClient
    from pykube.objects import (
        Ingress,
        Job,
        Pod,
        Service,
    )
except ImportError as exc:
    KubeConfig = None
    Ingress = None
    Job = None
    Pod = None
    Service = None
    HTTPError = None
    K8S_IMPORT_MESSAGE = (
        "The Python pykube package is required to use "
        "this feature, please install it or correct the "
        f"following error:\nImportError {exc}"
    )

log = logging.getLogger(__name__)

DEFAULT_JOB_API_VERSION = "batch/v1"
DEFAULT_SERVICE_API_VERSION = "v1"
DEFAULT_INGRESS_API_VERSION = "networking.k8s.io/v1"
DEFAULT_NAMESPACE = "default"
INSTANCE_ID_INVALID_MESSAGE = (
    "Galaxy instance [%s] is either too long "
    "(>20 characters) or it includes non DNS "
    "acceptable characters, ignoring it."
)


def ensure_pykube():
    if KubeConfig is None:
        raise Exception(K8S_IMPORT_MESSAGE)


def pykube_client_from_dict(params):
    if "k8s_use_service_account" in params and params["k8s_use_service_account"]:
        pykube_client = HTTPClient(KubeConfig.from_service_account())
    else:
        config_path = params.get("k8s_config_path")
        if config_path is None:
            config_path = os.environ.get("KUBECONFIG", None)
        if config_path is None:
            config_path = "~/.kube/config"
        pykube_client = HTTPClient(KubeConfig.from_file(config_path))
    return pykube_client


def produce_k8s_job_prefix(app_prefix=None, instance_id=None):
    job_name_elems = [app_prefix or "", instance_id or ""]
    return "-".join(elem for elem in job_name_elems if elem)


def pull_policy(params):
    # If this doesn't validate it returns None, that seems odd?
    if "k8s_pull_policy" in params:
        if params["k8s_pull_policy"] in ["Always", "IfNotPresent", "Never"]:
            return params["k8s_pull_policy"]
    return None


def find_service_object_by_name(pykube_api, service_name, namespace=None):
    if not service_name:
        raise ValueError("service name must not be empty")
    return Service.objects(pykube_api).filter(field_selector={"metadata.name": service_name}, namespace=namespace)


def find_ingress_object_by_name(pykube_api, ingress_name, namespace=None):
    if not ingress_name:
        raise ValueError("ingress name must not be empty")
    return Ingress.objects(pykube_api).filter(field_selector={"metadata.name": ingress_name}, namespace=namespace)


def find_job_object_by_name(pykube_api, job_name, namespace=None):
    if not job_name:
        raise ValueError("job name must not be empty")
    return Job.objects(pykube_api).filter(field_selector={"metadata.name": job_name}, namespace=namespace)


def find_pod_object_by_name(pykube_api, job_name, namespace=None):
    return Pod.objects(pykube_api).filter(selector=f"job-name={job_name}", namespace=namespace)


def is_pod_running(pykube_api, pod, namespace=None):
    if pod.obj["status"].get("phase") == "Running":
        return True

    return False


def is_pod_unschedulable(pykube_api, pod, namespace=None):
    is_unschedulable = any(c.get("reason") == "Unschedulable" for c in pod.obj["status"].get("conditions", []))
    if pod.obj["status"].get("phase") == "Pending" and is_unschedulable:
        return True

    return False


def delete_job(job, cleanup="always"):
    job_failed = job.obj["status"]["failed"] > 0 if "failed" in job.obj["status"] else False
    # Scale down the job just in case even if cleanup is never
    try:
        job.scale(replicas=0)
    except ObjectDoesNotExist as e:
        # Okay, job does no longer exist
        log.info(e)
        
    api_delete = cleanup == "always"
    if not api_delete and cleanup == "onsuccess" and not job_failed:
        api_delete = True
    if api_delete:
        delete_options = {"apiVersion": "v1", "kind": "DeleteOptions", "propagationPolicy": "Background"}
        r = job.api.delete(json=delete_options, **job.api_kwargs())
        job.api.raise_for_status(r)


def delete_ingress(ingress, cleanup="always", job_failed=False):
    api_delete = cleanup == "always"
    if not api_delete and cleanup == "onsuccess" and not job_failed:
        api_delete = True
    if api_delete:
        delete_options = {"apiVersion": "v1", "kind": "DeleteOptions", "propagationPolicy": "Background"}
        r = ingress.api.delete(json=delete_options, **ingress.api_kwargs())
        ingress.api.raise_for_status(r)


def delete_service(service, cleanup="always", job_failed=False):
    api_delete = cleanup == "always"
    if not api_delete and cleanup == "onsuccess" and not job_failed:
        api_delete = True
    if api_delete:
        delete_options = {"apiVersion": "v1", "kind": "DeleteOptions", "propagationPolicy": "Background"}
        r = service.api.delete(json=delete_options, **service.api_kwargs())
        service.api.raise_for_status(r)


def job_object_dict(params, job_prefix, spec):
    k8s_job_obj = {
        "apiVersion": params.get("k8s_job_api_version", DEFAULT_JOB_API_VERSION),
        "kind": "Job",
        "metadata": {
            "generateName": f"{job_prefix}-",
            "namespace": params.get("k8s_namespace", DEFAULT_NAMESPACE),
        },
        "spec": spec,
    }
    return k8s_job_obj


def service_object_dict(params, service_name, spec):
    k8s_service_obj = {
        "apiVersion": params.get("k8s_service_api_version", DEFAULT_SERVICE_API_VERSION),
        "kind": "Service",
        "metadata": {
            "name": service_name,
            "namespace": params.get("k8s_namespace", DEFAULT_NAMESPACE),
        },
    }
    k8s_service_obj["metadata"].update(spec.pop("metadata", {}))
    k8s_service_obj.update(spec)
    return k8s_service_obj


def ingress_object_dict(params, ingress_name, spec):
    k8s_ingress_obj = {
        "apiVersion": params.get("k8s_ingress_api_version", DEFAULT_INGRESS_API_VERSION),
        "kind": "Ingress",
        "metadata": {
            "name": ingress_name,
            "namespace": params.get("k8s_namespace", DEFAULT_NAMESPACE),
            # TODO: Add default annotations
        },
    }
    k8s_ingress_obj["metadata"].update(spec.pop("metadata", {}))
    k8s_ingress_obj.update(spec)
    return k8s_ingress_obj


def parse_pvc_param_line(pvc_param):
    """
    :type pvc_param: str
    :param pvc_param: the pvc mount param in the format ``pvc-name/subpath/desired:/mountpath/desired[:r]``

    :rtype: dict
    :return: a dict
      like::

        {"name": "pvc-name",
         "subPath": "subpath/desired",
         "mountPath": "/mountpath/desired",
         "readOnly": False}
    """
    claim, _, rest = pvc_param.partition(":")
    mount_path, _, mode = rest.partition(":")
    read_only = mode == "r"
    claim_name, _, subpath = claim.partition("/")
    return {
        "name": claim_name.strip(),
        "subPath": subpath.strip(),
        "mountPath": mount_path.strip(),
        "readOnly": read_only,
    }


def generate_relative_mounts(pvc_param, files):
    """
    Maps a list of files as mounts, relative to the base volume mount.
    For example, given the pvc mount:
    {
        'name': 'my_pvc',
        'mountPath': '/galaxy/database/jobs',
        'subPath': 'data',
        'readOnly': False
    }

    and files: ['/galaxy/database/jobs/01/input.txt', '/galaxy/database/jobs/01/working']

    returns each file as a relative mount as follows:
    [
        {
          'name': 'my_pvc',
          'mountPath': '/galaxy/database/jobs/01/input.txt',
          'subPath': 'data/01/input.txt',
          'readOnly': False
        },
        {
          'name': 'my_pvc',
          'mountPath': '/galaxy/database/jobs/01/working',
          'subPath': 'data/01/working',
          'readOnly': False
        }
    ]

    :param pvc_param: the pvc claim dict
    :param files: a list of file or folder names
    :return: A list of volume mounts
    """
    if not pvc_param:
        return
    param_claim = parse_pvc_param_line(pvc_param)
    claim_name = param_claim["name"]
    base_subpath = PurePath(param_claim.get("subPath", ""))
    base_mount = PurePath(param_claim["mountPath"])
    read_only = param_claim["readOnly"]
    volume_mounts = []
    for f in files:
        file_path = PurePath(str(f))
        if base_mount not in file_path.parents:
            # force relative directory, needed for the job working directory in particular
            file_path = base_mount.joinpath(file_path.relative_to("/") if file_path.is_absolute() else file_path)
        relpath = file_path.relative_to(base_mount)
        subpath = base_subpath.joinpath(relpath)
        volume_mounts.append(
            {"name": claim_name, "mountPath": str(file_path), "subPath": str(subpath), "readOnly": read_only}
        )
    return volume_mounts


def deduplicate_entries(obj_list):
    # remove duplicate entries in a list of dictionaries
    # based on: https://stackoverflow.com/a/9428041
    return [i for n, i in enumerate(obj_list) if i not in obj_list[n + 1 :]]


def get_volume_mounts_for_job(job_wrapper, data_claim=None, working_claim=None):
    volume_mounts = []
    if data_claim:
        volume_mounts.extend(generate_relative_mounts(data_claim, job_wrapper.job_io.get_input_fnames()))
        # for individual output files, mount the parent folder of each output as there could be wildcard outputs
        output_folders = deduplicate_entries(
            [str(PurePath(str(f)).parent) for f in job_wrapper.job_io.get_output_fnames()]
        )
        volume_mounts.extend(generate_relative_mounts(data_claim, output_folders))

    if working_claim:
        volume_mounts.extend(generate_relative_mounts(working_claim, [job_wrapper.working_directory]))

    return deduplicate_entries(volume_mounts)


def galaxy_instance_id(params):
    """Parse and validate the id of the Galaxy instance from supplied dict.

    This will be added to Jobs and Pods names, so it needs to be DNS friendly,
    this means: `The Internet standards (Requests for Comments) for protocols mandate that component hostname labels
    may contain only the ASCII letters 'a' through 'z' (in a case-insensitive manner), the digits '0' through '9',
    and the minus sign ('-').`

    It looks for the value set on params['k8s_galaxy_instance_id'], which might or not be set. The
    idea behind this is to allow the Galaxy instance to trust (or not) existing k8s Jobs and Pods that match the
    setup of a Job that is being recovered or restarted after a downtime/reboot.
    """
    if "k8s_galaxy_instance_id" in params:
        raw_value = params["k8s_galaxy_instance_id"]
        if re.match(r"(?!-)[a-z\d-]{1,20}(?<!-)$", raw_value):
            return raw_value
        else:
            log.error(INSTANCE_ID_INVALID_MESSAGE % raw_value)
    return None


__all__ = (
    "DEFAULT_JOB_API_VERSION",
    "DEFAULT_SERVICE_API_VERSION",
    "DEFAULT_INGRESS_API_VERSION",
    "ensure_pykube",
    "find_service_object_by_name",
    "find_ingress_object_by_name",
    "find_job_object_by_name",
    "find_pod_object_by_name",
    "galaxy_instance_id",
    "HTTPError",
    "is_pod_running",
    "is_pod_unschedulable",
    "Job",
    "Service",
    "Ingress",
    "job_object_dict",
    "service_object_dict",
    "ingress_object_dict",
    "Pod",
    "produce_k8s_job_prefix",
    "pull_policy",
    "pykube_client_from_dict",
    "delete_job",
    "delete_service",
    "delete_ingress",
    "get_volume_mounts_for_job",
    "parse_pvc_param_line",
)

def reload_job(job):
    try:
        job.reload()
    except HTTPError as e:
        if e.code == 404:
            pass
        else: 
            raise e