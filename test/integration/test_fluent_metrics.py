import json
from datetime import (
    datetime,
    timezone,
)

from galaxy_test.driver import integration_util


class TestFluentMetricsIntegration(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["fluent_log"] = True
        config["fluent_host"] = "localhost"
        config["fluent_port"] = 24224

    def test_create(self):
        metrics = self._get_test_metrics()
        payload = {"metrics": metrics}
        response = self._post("metrics", payload, json=True)
        self._assert_status_code_is(response, 200)

    def _get_test_metrics(self):
        """
        Returns a list containing dictionaries of the form:
            namespace:       label indicating the source of the metric
            time:            isoformat datetime when the metric was recorded
            level:           an integer representing the metric's log level
            args:            a json string containing an array of extra data
        """
        metrics = [
            {
                "namespace": "api-test",
                "time": f"{datetime.now(tz=timezone.utc).isoformat()}Z",
                "level": 1,
                "args": json.dumps({"arg01": "test"}),
            }
        ]
        return metrics
