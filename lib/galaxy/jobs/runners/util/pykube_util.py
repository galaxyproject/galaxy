"""Interface layer for pykube library shared between Galaxy and Pulsar."""
import os
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

    if instance_id and instance_id > 0:
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


__all__ = (
    "DEFAULT_JOB_API_VERSION",
    "ensure_pykube",
    "Job",
    "job_object_dict",
    "Pod",
    "produce_unique_k8s_job_name",
    "pull_policy",
    "pykube_client_from_dict",
)
