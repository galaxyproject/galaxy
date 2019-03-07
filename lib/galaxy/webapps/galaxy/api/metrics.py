"""
API operations for for querying and recording user metrics from some client
(typically a user's browser).
"""
# TODO: facade or adapter to fluentd

import datetime
import logging

from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class MetricsController(BaseAPIController):

    def __init__(self, app):
        super(MetricsController, self).__init__(app)
        #: set to true to send additional debugging info to the log
        self.debugging = True

    def _deserialize_isoformat_date(self, datestring):
        """
        Convert ISO formatted date string into python datetime.
        """
        return datetime.datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S.%fZ")

    @expose_api_anonymous
    def create(self, trans, payload, **kwd):
        """
        create( trans, payload )
        * POST /api/metrics:
            record any metrics sent and return some status object

        .. note:: Anonymous users can post metrics

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * metrics:          a list containing dictionaries of the form:
                ** namespace:       label indicating the source of the metric
                ** time:            isoformat datetime when the metric was recorded
                ** level:           an integer representing the metric's log level
                ** args:            a json string containing an array of extra data

        :rtype:     dict
        :returns:   status object
        """
        user_id = trans.user.id if trans.user else None
        session_id = trans.galaxy_session.id if trans.galaxy_session else None
        parsed_gen = self._parse_metrics(payload.get('metrics', None), user_id, session_id)
        self._send_metrics(trans, parsed_gen)
        response = self._get_server_pong(trans)
        return response

    # TODO: move the following to DAO/Manager object
    def _parse_metrics(self, metrics, user_id=None, session_id=None):
        """
        Return a generator yielding the each given metric as a tuple:
            * label:    the namespace of the metric
            * time:     datetime of the metric's creation
            * kwargs:   a dictionary containing:
                ** level:   the log level of the metric
                ** user:    the user associated with the metric
                            (will be None if anonymous user)
                ** session: the session of the current user
        """
        metrics = metrics or []
        for metric in metrics:
            label = metric['namespace']
            time = self._deserialize_isoformat_date(metric['time'])
            kwargs = {
                'level'   : metric['level'],
                'args'    : metric['args'],
                'user'    : user_id,
                'session' : session_id
            }
            yield (label, time, kwargs)

    def _send_metrics(self, trans, metrics):
        """
        Send metrics to the app's `trace_logger` if set and
        send to `log.debug` if this controller if `self.debugging`.

        Precondition: metrics are parsed and in proper format.
        """
        if trans.app.trace_logger:
            for label, time, kwargs in metrics:
                trans.app.trace_logger.log(label, event_time=int(time), **kwargs)
        elif self.debugging:
            for label, time, kwargs in metrics:
                log.debug('%s %s %s', label, time, kwargs)

    def _get_server_pong(self, trans):
        """
        Return some status message or object.

        For future use.
        """
        return {}
