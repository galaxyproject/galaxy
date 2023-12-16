"""
API operations for for querying and recording user metrics from some client
(typically a user's browser).
"""
# TODO: facade or adapter to fluentd

import logging
from typing import Any

from fastapi import Body

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.metrics import (
    CreateMetricsPayload,
    MetricsManager,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


router = Router(tags=["metrics"])


@router.post(
    "/api/metrics",
    summary="Records a collection of metrics.",
)
def create(
    trans: ProvidesUserContext = DependsOnTrans,
    payload: CreateMetricsPayload = Body(...),
    manager: MetricsManager = depends(MetricsManager),
) -> Any:
    """Record any metrics sent and return some status object."""
    return manager.create(trans, payload)
