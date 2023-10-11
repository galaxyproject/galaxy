import logging
from datetime import datetime
from typing import (
    Any,
    Generator,
    List,
    Optional,
    Tuple,
)

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


SOME_EXAMPLE_DATE = "2021-01-23T18:25:43.511Z"


class Metric(BaseModel):
    namespace: str = Field(
        ...,  # Required
        title="Namespace",
        description="Label indicating the source of the metric.",
    )
    time: str = Field(
        ...,  # Required
        title="Timestamp",
        description="The timestamp in ISO format.",
        example=SOME_EXAMPLE_DATE,
    )
    level: int = Field(
        ...,  # Required
        title="Level",
        description="An integer representing the metric's log level.",
    )
    args: str = Field(
        ...,  # Required
        title="Arguments",
        description="A JSON string containing an array of extra data.",
    )


class CreateMetricsPayload(BaseModel):
    metrics: List[Metric] = Field(
        default=[],
        title="List of metrics to be recorded.",
        example=[Metric(namespace="test-source", time=SOME_EXAMPLE_DATE, level=0, args='{"test":"value"}')],
    )


TimeSeriesTuple = Tuple[str, datetime, Any]
TimeSeriesTupleGenerator = Generator[TimeSeriesTuple, None, None]


class MetricsManager:
    """Interface/service object shared by controllers for interacting with metrics."""

    def __init__(self, app: MinimalManagerApp) -> None:
        self._app = app
        #: set to true to send additional debugging info to the log
        self.debugging = True

    def create(self, trans, payload: CreateMetricsPayload):
        """
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
        user_id = trans.user.id if trans.user else None
        session_id = trans.galaxy_session.id if trans.galaxy_session else None
        parsed_gen = self._parse_metrics(payload.metrics, user_id, session_id)
        self._send_metrics(trans, parsed_gen)
        response = self._get_server_pong(trans)
        return response

    def _parse_metrics(
        self, metrics: Optional[List[Metric]] = None, user_id=None, session_id=None
    ) -> TimeSeriesTupleGenerator:
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
            label = metric.namespace
            time = self._deserialize_isoformat_date(metric.time)
            kwargs = {"level": metric.level, "args": metric.args, "user": user_id, "session": session_id}
            yield (label, time, kwargs)

    def _send_metrics(self, trans, metrics: TimeSeriesTupleGenerator) -> None:
        """
        Send metrics to the app's `trace_logger` if set and
        send to `log.debug` if this controller if `self.debugging`.

        Precondition: metrics are parsed and in proper format.
        """
        if trans.app.trace_logger:
            for label, time, kwargs in metrics:
                trans.app.trace_logger.log(label, event_time=int(time.timestamp()), **kwargs)
        elif self.debugging:
            for label, time, kwargs in metrics:
                log.debug(f"{label} {time} {kwargs}")

    def _get_server_pong(self, trans) -> Any:
        """
        Return some status message or object.

        For future use.
        """
        return {}

    def _deserialize_isoformat_date(self, datestring: str) -> datetime:
        """
        Convert ISO formatted date string into python datetime.
        """
        return datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S.%fZ")
