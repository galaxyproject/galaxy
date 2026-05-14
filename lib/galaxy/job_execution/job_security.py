"""Shared helpers for the per-job authentication used by ``/api/jobs/{id}/files``,
``/api/jobs/{id}/ports`` and ``/api/jobs/{id}/oidc-tokens``.

These endpoints are called by job runners (Pulsar over MQ, BYOC relay, etc.),
not by interactive users. They share a single bearer-token style credential —
historically the ``job_key`` query-string parameter — that is derived from
Galaxy's ``id_secret``.

This module exists to keep one piece of policy consistent across the three
endpoints: where the token is read from. ``Authorization: Bearer …`` is
preferred; the query/payload form remains a fallback for backward
compatibility with older Pulsar versions that embed the secret in the URL.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Optional


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
