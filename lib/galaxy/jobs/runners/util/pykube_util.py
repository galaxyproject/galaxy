"""Interface layer for pykube library shared between Galaxy and Pulsar."""
import logging
import os
import re
import uuid

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


def produce_unique_k8s_job_name(app_prefix=None, instance_id=None, job_id=None):
    if job_id is None:
        job_id = str(uuid.uuid4())

    job_name = ""
    if app_prefix:
        job_name += "%s-" % app_prefix

    if instance_id and len(instance_id) > 0:
        job_name += "%s-" % instance_id

    return job_name + job_id


def pull_policy(params):
    # If this doesn't validate it returns None, that seems odd?
    if "k8s_pull_policy" in params:
        if params['k8s_pull_policy'] in ["Always", "IfNotPresent", "Never"]:
            return params['k8s_pull_policy']
    return None


def job_object_dict(params, job_name, spec):
    k8s_job_obj = {
        "apiVersion": params.get('k8s_job_api_version', DEFAULT_JOB_API_VERSION),
        "kind": "Job",
        "metadata": {
                # metadata.name is the name of the pod resource created, and must be unique
                # http://kubernetes.io/docs/user-guide/configuring-containers/
                "name": job_name,
                "namespace": params.get('k8s_namespace', DEFAULT_NAMESPACE),
                "labels": {"app": job_name}
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
        if re.match(r"(?!-)[a-z\d-]{1,20}(?<!-)$", params['k8s_galaxy_instance_id']):
            return params['k8s_galaxy_instance_id']
        else:
            log.error("Galaxy instance '" + params['k8s_galaxy_instance_id'] + "' is either too long "
                        + '(>20 characters) or it includes non DNS acceptable characters, ignoring it.')
    return None


__all__ = (
    "DEFAULT_JOB_API_VERSION",
    "ensure_pykube",
    "galaxy_instance_id",
    "Job",
    "job_object_dict",
    "Pod",
    "produce_unique_k8s_job_name",
    "pull_policy",
    "pykube_client_from_dict",
)
