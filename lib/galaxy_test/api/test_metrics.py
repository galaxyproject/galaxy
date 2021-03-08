import datetime
from unittest import mock

from ._framework import ApiTestCase


class MetricsApiTestCase(ApiTestCase):

    def setUp(self):
        super().setUp()
        self._test_driver.app.trace_logger = mock.MagicMock()
        self.mock_trace_logger = self._test_driver.app.trace_logger

    def test_create(self):
        metrics = self._get_test_metrics()
        payload = {
            "metrics": metrics
        }

        response = self._post("metrics", payload, json=True)
        self._assert_status_code_is(response, 200)
        assert self.mock_trace_logger.log.called
        assert self.mock_trace_logger.log.call_count == len(metrics)

    def _get_test_metrics(self):
        metrics = [
            {
                "namespace": "api-test",
                "time": datetime.datetime.utcnow().isoformat() + "Z",
                "level": "debug",
                "args": {
                    "arg01": "test"
                },
            }
        ]
        return metrics
