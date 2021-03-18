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
from galaxy.web import expose_api_anonymous
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


router = Router(tags=['metrics'])


@router.cbv
class FastAPIMetrics:
    manager: MetricsManager = depends(MetricsManager)

    @router.post(
        '/api/metrics',
        summary="Records a collection of metrics.",
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateMetricsPayload = Body(...),
    ) -> Any:
        """Record any metrics sent and return some status object."""
        return self.manager.create(trans, payload)


class MetricsController(BaseGalaxyAPIController):

    manager: MetricsManager = depends(MetricsManager)

    @expose_api_anonymous
    def create(self, trans, payload, **kwd):
        """
        POST /api/metrics

        Record any metrics sent and return some status object.

        .. note:: Anonymous users can post metrics

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * metrics:          a list containing dictionaries of the form

                namespace:       label indicating the source of the metric
                time:            isoformat datetime when the metric was recorded
                level:           an integer representing the metric's log level
                args:            a json string containing an array of extra data

        :rtype:     dict
        :returns:   status object
        """
        return self.manager.create(trans, CreateMetricsPayload(**payload))
