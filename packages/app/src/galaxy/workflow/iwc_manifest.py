"""Network access to the IWC (Intergalactic Workflows Commission) workflow manifest.

Kept outside ``galaxy.agents`` on purpose: importing any submodule there runs
``galaxy.agents.__init__``, which pulls in pydantic-ai and every agent. The
curated workflows catalog only needs these download helpers and is imported by
the workflow manager, so it must not drag that in.
"""

import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from galaxy.util import requests

log = logging.getLogger(__name__)

IWC_MANIFEST_URL = "https://iwc.galaxyproject.org/workflow_manifest.json"
FRESHNESS_TIMEOUT_SECONDS = 10.0


def manifest_last_modified(timeout: float = FRESHNESS_TIMEOUT_SECONDS) -> datetime | None:
    """The published manifest's ``Last-Modified``, or None when it can't be had.

    A HEAD costs nothing next to the ~16 MB body, and the manifest changes every
    few days, so callers that keep a derived copy on disk can skip almost every
    download. Callers should treat None as "changed" -- re-downloading is
    wasteful, but serving indefinitely stale data because one HEAD failed is worse.
    """
    try:
        response = requests.head(IWC_MANIFEST_URL, timeout=timeout)
        response.raise_for_status()
    except Exception as e:
        log.debug(f"IWC manifest freshness HEAD failed: {e}")
        return None
    return _parse_last_modified(response.headers.get("Last-Modified"))


def _parse_last_modified(header: str | None) -> datetime | None:
    if not header:
        return None
    try:
        return parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return None


def download_manifest(timeout: float) -> list[dict[str, Any]]:
    """Fetch and validate the IWC manifest over the network, bypassing any cache.

    Intentionally cache-free: the parsed manifest is ~16 MB, so callers that
    only need a derived projection of it (see ``galaxy.workflow.curated``) can
    drop it as soon as they are done instead of pinning it in every process
    that happens to touch this module. ``galaxy.workflow.iwc`` layers its TTL
    cache on top of this.
    """
    return fetch_manifest(timeout)[0]


def fetch_manifest(timeout: float) -> tuple[list[dict[str, Any]], datetime | None]:
    """Like ``download_manifest``, plus the ``Last-Modified`` of the body actually served.

    That date, not one from an earlier HEAD, is what a cached copy has to be
    stamped with: the HEAD and the GET are separate requests to a CDN, and can be
    answered from different cached versions of the manifest.
    """
    response = requests.get(IWC_MANIFEST_URL, timeout=timeout)
    response.raise_for_status()
    manifest = response.json()
    if not isinstance(manifest, list):
        raise ValueError(f"IWC manifest at {IWC_MANIFEST_URL} did not return a JSON array")
    return manifest, _parse_last_modified(response.headers.get("Last-Modified"))
