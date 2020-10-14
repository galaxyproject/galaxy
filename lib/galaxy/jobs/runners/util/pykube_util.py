"""Interface layer for pykube library shared between Galaxy and Pulsar."""
import logging
import os
import re

try:
    from pykube.config import KubeConfig
    from pykube.http import HTTPClient
    from pykube.objects import (
        Job,
        Pod
    )
except ImportError as exc:
    KubeConfig = None
    Job = None
    Pod = None
    K8S_IMPORT_MESSAGE = ('The Python pykube package is required to use '
                          'this feature, please install it or correct the '
                          'following error:\nImportError %s' % str(exc))

log = logging.getLogger(__name__)

DEFAULT_JOB_API_VERSION = "batch/v1"
DEFAULT_NAMESPACE = "default"
INSTANCE_ID_INVALID_MESSAGE = ("Galaxy instance [%s] is either too long "
                               "(>20 characters) or it includes non DNS "
                               "acceptable characters, ignoring it.")


def ensure_pykube():
    if KubeConfig is None:
        raise Exception(K8S_IMPORT_MESSAGE)


def pykube_client_from_dict(params):
    if "k8s_use_service_account" in params and params["k8s_use_service_account"]:
        pykube_client = HTTPClient(KubeConfig.from_service_account())
    else:
        config_path = params.get("k8s_config_path")
        if config_path is None:
            config_path = os.environ.get('KUBECONFIG', None)
        if config_path is None:
            config_path = '~/.kube/config'
        pykube_client = HTTPClient(KubeConfig.from_file(config_path))
    return pykube_client


def produce_k8s_job_prefix(app_prefix=None, instance_id=None):
    job_name_elems = [app_prefix or "", instance_id or ""]
    return '-'.join(elem for elem in job_name_elems if elem)


def pull_policy(params):
    # If this doesn't validate it returns None, that seems odd?
    if "k8s_pull_policy" in params:
        if params['k8s_pull_policy'] in ["Always", "IfNotPresent", "Never"]:
            return params['k8s_pull_policy']
    return None


def find_job_object_by_name(pykube_api, job_name, namespace=None):
    if not job_name:
        raise ValueError("job name must not be empty")
    return Job.objects(pykube_api).filter(field_selector={"metadata.name": job_name}, namespace=namespace)


def find_pod_object_by_name(pykube_api, job_name, namespace=None):
    return Pod.objects(pykube_api).filter(selector="job-name=" + job_name, namespace=namespace)


def stop_job(job, cleanup="always"):
    job_failed = (job.obj['status']['failed'] > 0
                  if 'failed' in job.obj['status'] else False)
    # Scale down the job just in case even if cleanup is never
    job.scale(replicas=0)
    api_delete = cleanup == "always"
    if not api_delete and cleanup == "onsuccess" and not job_failed:
        api_delete = True
    if api_delete:
        delete_options = {
            "apiVersion": "v1",
            "kind": "DeleteOptions",
            "propagationPolicy": "Background"
        }
        r = job.api.delete(json=delete_options, **job.api_kwargs())
        job.api.raise_for_status(r)


def job_object_dict(params, job_prefix, spec):
    k8s_job_obj = {
        "apiVersion": params.get('k8s_job_api_version', DEFAULT_JOB_API_VERSION),
        "kind": "Job",
        "metadata": {
                "generateName": job_prefix + "-",
                "namespace": params.get('k8s_namespace', DEFAULT_NAMESPACE),
        },
        "spec": spec,
    }
    return k8s_job_obj


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
        raw_value = params['k8s_galaxy_instance_id']
        if re.match(r"(?!-)[a-z\d-]{1,20}(?<!-)$", raw_value):
            return raw_value
        else:
            log.error(INSTANCE_ID_INVALID_MESSAGE % raw_value)
    return None


__all__ = (
    "DEFAULT_JOB_API_VERSION",
    "ensure_pykube",
    "find_job_object_by_name",
    "find_pod_object_by_name",
    "galaxy_instance_id",
    "Job",
    "job_object_dict",
    "Pod",
    "produce_k8s_job_prefix",
    "pull_policy",
    "pykube_client_from_dict",
    "stop_job",
)
