"""Interface layer for pykube library shared between Galaxy and Pulsar."""
import logging
import os
import re

try:
    from pykube.config import KubeConfig
    from pykube.http import HTTPClient
    from pykube.objects import (
        Job,
        Pod,
        Service,
        Ingress,
    )
    from pykube.exceptions import HTTPError
except ImportError as exc:
    KubeConfig = None
    Ingress = None
    Job = None
    Pod = None
    Service = None
    HTTPError = None
    K8S_IMPORT_MESSAGE = ('The Python pykube package is required to use '
                          'this feature, please install it or correct the '
                          'following error:\nImportError %s' % str(exc))

log = logging.getLogger(__name__)

DEFAULT_JOB_API_VERSION = "batch/v1"
DEFAULT_SERVICE_API_VERSION = "v1"
DEFAULT_INGRESS_API_VERSION = "extensions/v1beta1"
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


def is_pod_unschedulable(pykube_api, pod, namespace=None):
    is_unschedulable = any(c.get("reason") == "Unschedulable" for c in pod.obj['status'].get('conditions', []))
    if pod.obj['status'].get('phase') == "Pending" and is_unschedulable:
        return True

    return False


def delete_job(job, cleanup="always"):
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


def delete_ingress(ingress, cleanup="always", job_failed=False):
    api_delete = cleanup == "always"
    if not api_delete and cleanup == "onsuccess" and not job_failed:
        api_delete = True
    if api_delete:
        delete_options = {
            "apiVersion": "v1",
            "kind": "DeleteOptions",
            "propagationPolicy": "Background"
        }
        r = ingress.api.delete(json=delete_options, **ingress.api_kwargs())
        ingress.api.raise_for_status(r)


def delete_service(service, cleanup="always", job_failed=False):
    api_delete = cleanup == "always"
    if not api_delete and cleanup == "onsuccess" and not job_failed:
        api_delete = True
    if api_delete:
        delete_options = {
            "apiVersion": "v1",
            "kind": "DeleteOptions",
            "propagationPolicy": "Background"
        }
        r = service.api.delete(json=delete_options, **service.api_kwargs())
        service.api.raise_for_status(r)


def job_object_dict(params, job_prefix, spec):
    k8s_job_obj = {
        "apiVersion": params.get('k8s_job_api_version', DEFAULT_JOB_API_VERSION),
        "kind": "Job",
        "metadata": {
                "generateName": f"{job_prefix}-",
                "namespace": params.get('k8s_namespace', DEFAULT_NAMESPACE),
        },
        "spec": spec,
    }
    return k8s_job_obj


def service_object_dict(params, service_name, spec):
    k8s_service_obj = {
        "apiVersion": params.get('k8s_service_api_version', DEFAULT_SERVICE_API_VERSION),
        "kind": "Service",
        "metadata": {
                "name": service_name,
                "namespace": params.get('k8s_namespace', DEFAULT_NAMESPACE),
        },
    }
    k8s_service_obj["metadata"].update(spec.pop("metadata", {}))
    k8s_service_obj.update(spec)
    return k8s_service_obj


def ingress_object_dict(params, ingress_name, spec):
    k8s_ingress_obj = {
        "apiVersion": params.get('k8s_ingress_api_version', DEFAULT_INGRESS_API_VERSION),
        "kind": "Ingress",
        "metadata": {
                "name": ingress_name,
                "namespace": params.get('k8s_namespace', DEFAULT_NAMESPACE),
            # TODO: Add default annotations
        },
    }
    k8s_ingress_obj["metadata"].update(spec.pop("metadata", {}))
    k8s_ingress_obj.update(spec)
    return k8s_ingress_obj


# takes "pvc-name/subpath/desired:/mountpath/desired[:r]"
# and returns {"claim": "pvc-name",
#              "subpath": "subpath/desired",
#              "mountpath": "/mountpath/desired",
#              "readonly": false}
def parse_pvc_param_line(paramstring):
    retdict = {}
    claim = paramstring.split(":")[0]
    if "/" in claim:
        subpath = "/".join(claim.split("/")[1:])
        retdict["subpath"] = subpath
        claim = claim.split("/")[0]
    retdict["claim"] = claim
    mountpath = ":".join(paramstring.split(":")[1:])
    readonly = False
    if ":" in mountpath:
        read = mountpath.split(":")[1]
        if read == "r":
            readonly = True
        mountpath = mountpath.split(":")[0]
    retdict["mountpath"] = mountpath
    retdict["readonly"] = readonly
    return retdict


def get_volume_mounts_for_job(job_wrapper, data_claim=None, working_claim=None):
    DATA_BASE_PATH = "objects/"
    volume_mounts = []
    if data_claim:
        param_claim = parse_pvc_param_line(data_claim)
        claim_name = param_claim['claim']
        base_subpath = param_claim.get('subpath', "")
        base_mount = param_claim["mountpath"]

        inputs = job_wrapper.get_input_fnames()
        for i in list(inputs):
            file_path = str(i)
            subpath = file_path.lstrip(base_mount).lstrip('/').rstrip('/')
            if base_subpath:
                subpath = "{}/{}".format(base_subpath, subpath)
            if file_path not in [each['mountPath'] for each in volume_mounts]:
                volume_mounts.append({'name': claim_name, 'mountPath': file_path, 'subPath': subpath})
        outputs = job_wrapper.get_output_fnames()
        for o in list(outputs):
            file_path = str(o).rstrip('/').split('/')
            file_path = "/".join(file_path[:-1])
            subpath = str(file_path).lstrip(base_mount).lstrip('/')
            # Avoid mounting the same output directory twice for two output files using same dir
            if (DATA_BASE_PATH in subpath and subpath not in
                    [v.get('subPath') for v in [v for v in volume_mounts if v.get('name') == claim_name]]):
                volume_mounts.append({'name': claim_name, 'mountPath': file_path, 'subPath': subpath})

    if working_claim:
        param_claim = parse_pvc_param_line(working_claim)
        claim_name = param_claim['claim']
        wd_base_subpath = param_claim.get('subpath', "")
        base_mount = param_claim["mountpath"]
        wd_subpath = str(job_wrapper.working_directory).lstrip(base_mount).lstrip('/').rstrip('/')
        if wd_base_subpath:
            wd_subpath = "{}/{}".format(wd_base_subpath, wd_subpath)
        volume_mounts.append({'name': claim_name,
                              'mountPath': str(job_wrapper.working_directory),
                              'subPath': wd_subpath})
        outputs = job_wrapper.get_output_fnames()
        for o in list(outputs):
            file_path = str(o).rstrip('/').split('/')
            file_path = "/".join(file_path[:-1])
            subpath = str(file_path).lstrip(base_mount).lstrip('/')
            # Avoid mounting the same output directory twice for two output files using same dir
            if (wd_subpath not in subpath and DATA_BASE_PATH not in subpath and subpath not in
                    [v.get('subPath') for v in [v for v in volume_mounts if v.get('name') == claim_name]]):
                volume_mounts.append({'name': claim_name, 'mountPath': file_path, 'subPath': subpath})
    return volume_mounts


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
    "DEFAULT_SERVICE_API_VERSION",
    "DEFAULT_INGRESS_API_VERSION",
    "ensure_pykube",
    "find_service_object_by_name",
    "find_ingress_object_by_name",
    "find_job_object_by_name",
    "find_pod_object_by_name",
    "galaxy_instance_id",
    "HTTPError",
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
    "parse_pvc_param_line"
)
