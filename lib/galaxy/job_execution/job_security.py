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

import string
from collections.abc import Mapping
from typing import Optional

from galaxy.model import Job

#: Alphabet for the compact resource-id encoding baked into compute-resource
#: ``kind`` strings (see :func:`_base62`). Order is fixed forever — issuer and
#: verifier must agree, and it's a bijective radix encoding, not a hash, so
#: there are no collisions (distinct resource ids never share a ``kind``).
_BASE62_ALPHABET = string.digits + string.ascii_uppercase + string.ascii_lowercase

#: Authorization scheme expected on the bearer header. Lowercased for
#: case-insensitive matching.
_BEARER_SCHEME = "bearer"

#: ``kind`` used by ``encode_id`` when minting and verifying the file-staging
#: credential for jobs not bound to a user-registered compute resource.
#: Stable wire contract with deployed Pulsar instances — do not rename.
JOB_FILES_KIND = "jobs_files"

#: Default ``kind`` for the OIDC-token credential, overridable per-destination
#: via ``destination_params['job_secret_base']``.
DEFAULT_JOB_TOKEN_KIND = "jobs_token"

#: Compact per-tenant ``kind`` prefixes for jobs dispatched to a
#: user-registered compute resource. Binding the resource id into the
#: encryption ``kind`` ensures a credential lifted from one user's Pulsar
#: node is rejected if replayed for a job that belongs to a different
#: compute resource — even within the same Galaxy ``id_secret``.
#:
#: These are deliberately terse (``jf``/``jt`` = job files/token, ``cr`` =
#: compute resource) because ``galaxy.security.idencoding`` requires
#: ``len(kind) < 15`` — the ``kind`` is appended to ``id_secret`` before the
#: last 56 bytes are taken as the Blowfish key, so a long ``kind`` crowds the
#: random secret bytes out of the key. A descriptive
#: ``jobs_files:compute_resource:<id>`` form (30+ chars) would blow past that
#: limit. The ``kind`` is internal to Galaxy (issuer and verifier both derive
#: it here); Pulsar never sees it, so the terse form costs nothing externally.
_COMPUTE_RESOURCE_FILES_PREFIX = "jf:cr:"
_COMPUTE_RESOURCE_TOKEN_PREFIX = "jt:cr:"

#: idencoding caps ``kind`` at 14 chars; with the 6-char prefixes above that
#: leaves 8 characters for the resource id. The id is base62-encoded, so that's
#: ``62**8 ≈ 2.18e14`` headroom — unreachable by any autoincrement PK. The guard
#: below is pure defence-in-depth (it can't realistically fire) and turns the
#: theoretical ceiling into a clear error instead of idencoding's opaque
#: ``AssertionError``.
_MAX_COMPUTE_RESOURCE_KIND_LEN = 14


def _base62(n: int) -> str:
    """Encode a non-negative int in base62 (``0-9A-Za-z``). Bijective and
    deterministic — used to pack the resource id into a short ``kind``."""
    if n < 0:
        raise ValueError(f"cannot base62-encode negative value {n}")
    if n == 0:
        return _BASE62_ALPHABET[0]
    digits: list[str] = []
    while n:
        n, rem = divmod(n, 62)
        digits.append(_BASE62_ALPHABET[rem])
    return "".join(reversed(digits))


def _compute_resource_kind(prefix: str, resource_id: int) -> str:
    kind = f"{prefix}{_base62(resource_id)}"
    if len(kind) > _MAX_COMPUTE_RESOURCE_KIND_LEN:
        raise ValueError(
            f"compute_resource_id {resource_id} is too large to encode a job-credential "
            f"'kind' within idencoding's {_MAX_COMPUTE_RESOURCE_KIND_LEN + 1}-char limit "
            f"(would be {kind!r})."
        )
    return kind


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
    return _compute_resource_kind(_COMPUTE_RESOURCE_FILES_PREFIX, resource_id)


def job_token_kind_for_params(destination_params: Optional[Mapping[str, object]]) -> str:
    """Pick the OIDC-token credential ``kind`` for a job whose destination
    params are ``destination_params``. Honours the existing per-destination
    override (``job_secret_base``, default ``"jobs_token"``) for non-tenant
    jobs; compute-resource jobs use the tenant-scoped ``jt:cr:<id>`` kind
    instead (the resource id already namespaces the credential, and a custom
    base could exceed idencoding's length limit).
    """
    params = destination_params or {}
    resource_id = _compute_resource_id_from_params(params)
    if resource_id is None:
        return str(params.get("job_secret_base") or DEFAULT_JOB_TOKEN_KIND)
    return _compute_resource_kind(_COMPUTE_RESOURCE_TOKEN_PREFIX, resource_id)


def job_files_kind_for_job(job: Job) -> str:
    """Verifier-side wrapper of :func:`job_files_kind_for_params` for a
    persisted :class:`~galaxy.model.Job`."""
    return job_files_kind_for_params(job.destination_params)


def job_token_kind_for_job(job: Job) -> str:
    """Verifier-side wrapper of :func:`job_token_kind_for_params` for a
    persisted :class:`~galaxy.model.Job`."""
    return job_token_kind_for_params(job.destination_params)


def resolve_job_key(authorization_header: Optional[str], fallback: Optional[str]) -> Optional[str]:
    """Pick the job_key from an ``Authorization`` header value or fall back.

    ``authorization_header`` is the raw value of the request's
    ``Authorization`` header (or ``None`` if absent). When it carries a
    ``Bearer <token>`` value, the token wins. Otherwise ``fallback`` is
    returned — typically the ``job_key`` pulled from the query string or
    POST body, kept for compatibility with Pulsar versions that embed the
    secret in the URL.

    Both web frameworks Galaxy uses (webob, FastAPI) already do
    case-insensitive lookup of the header *name*, so the caller passes the
    single header string. The ``Bearer`` *scheme* match here is
    case-insensitive.
    """
    if authorization_header:
        scheme, _, token = authorization_header.partition(" ")
        if scheme.lower() == _BEARER_SCHEME and token.strip():
            return token.strip()
    return fallback
