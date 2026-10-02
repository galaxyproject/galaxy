"""Network access to the IWC (Intergalactic Workflows Commission) workflow manifest.

Kept outside ``galaxy.agents`` on purpose: importing any submodule there runs
``galaxy.agents.__init__``, which pulls in pydantic-ai and every agent. The
curated workflows catalog only needs these download helpers and is imported by
the workflow manager, so it must not drag that in.
"""

import logging
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from email.utils import parsedate_to_datetime
from typing import Any

from galaxy.util import requests

log = logging.getLogger(__name__)

IWC_MANIFEST_URL = "https://iwc.galaxyproject.org/workflow_manifest.json"
FRESHNESS_TIMEOUT_SECONDS = 10.0
_ONE_SECOND = timedelta(seconds=1)


def manifest_modified_since(local_mtime: float, timeout: float = FRESHNESS_TIMEOUT_SECONDS) -> bool:
    """Whether the published manifest is newer than ``local_mtime``.

    A HEAD costs nothing next to the ~16 MB body, and the manifest changes every
    few days, so callers that keep a derived copy on disk can skip almost every
    download. Returns True when the answer is unknown -- re-downloading is
    wasteful, but serving indefinitely stale data because one HEAD failed is worse.
    """
    try:
        response = requests.head(IWC_MANIFEST_URL, timeout=timeout)
        response.raise_for_status()
        header = response.headers.get("Last-Modified")
    except Exception as e:
        log.debug(f"IWC manifest freshness HEAD failed: {e}")
        return True
    if not header:
        return True
    try:
        remote = parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return True
    local = datetime.fromtimestamp(local_mtime, tz=timezone.utc)
    # Last-Modified has second resolution; the slack keeps a refresh we just
    # completed from immediately looking stale again.
    return remote > local + _ONE_SECOND


def download_manifest(timeout: float) -> list[dict[str, Any]]:
    """Fetch and validate the IWC manifest over the network, bypassing any cache.

    Intentionally cache-free: the parsed manifest is ~16 MB, so callers that
    only need a derived projection of it (see ``galaxy.workflow.curated``) can
    drop it as soon as they are done instead of pinning it in every process
    that happens to touch this module. ``galaxy.agents.iwc`` layers its TTL
    cache on top of this.
    """
    response = requests.get(IWC_MANIFEST_URL, timeout=timeout)
    response.raise_for_status()
    manifest = response.json()
    if not isinstance(manifest, list):
        raise ValueError(f"IWC manifest at {IWC_MANIFEST_URL} did not return a JSON array")
    return manifest
