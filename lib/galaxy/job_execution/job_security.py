"""Shared helpers for the per-job authentication used by ``/api/jobs/{id}/files``,
``/api/jobs/{id}/ports`` and ``/api/jobs/{id}/oidc-tokens``.

These endpoints are called by job runners (Pulsar over MQ, the
compute-resource relay, etc.), not by interactive users. They share a
single bearer-token style credential — historically the ``job_key``
query-string parameter — that is derived from Galaxy's ``id_secret``.

This module exists to keep two pieces of policy consistent across the three
endpoints:

* Where the token is read from (``Authorization: Bearer …`` header preferred,
  query/payload fallback for backward compatibility with older Pulsar
  versions that embed the secret in the URL).
* Which "kind" the token is encoded under — see :func:`job_files_kind_for_job`
  and :func:`job_token_kind_for_job` — so that a credential issued for a
  user-controlled compute resource cannot be replayed against a job
  scheduled on a different one (or against a Galaxy-operated Pulsar).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Optional

from galaxy.model import Job

#: ``kind`` used by ``encode_id`` when minting and verifying the file-staging
#: credential for jobs not bound to a user-registered compute resource.
#: Stable wire contract with deployed Pulsar instances — do not rename.
JOB_FILES_KIND = "jobs_files"

#: Default ``kind`` for the OIDC-token credential, overridable per-destination
#: via ``destination_params['job_secret_base']``.
DEFAULT_JOB_TOKEN_KIND = "jobs_token"

#: Per-tenant ``kind`` suffix template for jobs dispatched to a
#: user-registered compute resource. Binding the resource id into the
#: encryption ``kind`` ensures a credential lifted from one user's Pulsar
#: node is rejected if replayed for a job that belongs to a different
#: compute resource — even within the same Galaxy ``id_secret``.
_COMPUTE_RESOURCE_KIND_TEMPLATE = "{base}:compute_resource:{resource_id}"


def _compute_resource_id_from_params(params: Mapping[str, object]) -> Optional[int]:
    raw = params.get("compute_resource_id")
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError:
            return None
    return None


def job_files_kind_for_params(destination_params: Optional[Mapping[str, object]]) -> str:
    """Pick the file-staging credential ``kind`` for a job whose destination
    params are ``destination_params``. Jobs bound to a user-registered
    compute resource get a tenant-scoped variant; everything else gets the
    legacy :data:`JOB_FILES_KIND`.
    """
    params = destination_params or {}
    resource_id = _compute_resource_id_from_params(params)
    if resource_id is None:
        return JOB_FILES_KIND
    return _COMPUTE_RESOURCE_KIND_TEMPLATE.format(base=JOB_FILES_KIND, resource_id=resource_id)


def job_token_kind_for_params(destination_params: Optional[Mapping[str, object]]) -> str:
    """Pick the OIDC-token credential ``kind`` for a job whose destination
    params are ``destination_params``. Honours the existing per-destination
    override (``job_secret_base``, default ``"jobs_token"``) and appends the
    compute-resource tenant suffix when the job is bound to one.
    """
    params = destination_params or {}
    base = str(params.get("job_secret_base") or DEFAULT_JOB_TOKEN_KIND)
    resource_id = _compute_resource_id_from_params(params)
    if resource_id is None:
        return base
    return _COMPUTE_RESOURCE_KIND_TEMPLATE.format(base=base, resource_id=resource_id)


def job_files_kind_for_job(job: Job) -> str:
    """Verifier-side wrapper of :func:`job_files_kind_for_params` for a
    persisted :class:`~galaxy.model.Job`."""
    return job_files_kind_for_params(job.destination_params)


def job_token_kind_for_job(job: Job) -> str:
    """Verifier-side wrapper of :func:`job_token_kind_for_params` for a
    persisted :class:`~galaxy.model.Job`."""
    return job_token_kind_for_params(job.destination_params)


def resolve_job_key(headers: Mapping[str, str], fallback: Optional[str]) -> Optional[str]:
    """Extract the job_key bearer token from request headers, with fallback.

    Looks for an ``Authorization: Bearer <token>`` header (case-insensitive on
    the scheme). If not present, returns ``fallback`` — typically the
    ``job_key`` value pulled from the query string or POST body, kept for
    compatibility with Pulsar versions that embed the secret in the URL.
    """
    if headers is not None:
        auth_header = headers.get("Authorization") or headers.get("authorization")
        if auth_header:
            scheme, _, token = auth_header.partition(" ")
            if scheme.lower() == "bearer" and token.strip():
                return token.strip()
    return fallback
