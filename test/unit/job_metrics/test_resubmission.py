from unittest.mock import Mock

from galaxy.job_metrics.instrumenters.resubmission import (
    RESUBMISSION_COUNT_KEY,
    ResubmissionPlugin,
)
from galaxy.job_metrics.safety import Safety


def test_resubmission_count_comes_from_persisted_state_history():
    app = Mock()
    app.model.context.scalar.return_value = 2
    plugin = ResubmissionPlugin(app=app)

    properties = plugin.job_properties(42, "/cleared-and-recreated-working-directory")

    assert properties == {RESUBMISSION_COUNT_KEY: 2}
    app.model.context.scalar.assert_called_once()


def test_resubmission_plugin_without_application_does_not_collect():
    assert ResubmissionPlugin().job_properties(42, "/job-directory") == {}


def test_resubmission_metric_formatting_and_safety():
    plugin = ResubmissionPlugin()

    assert plugin.formatter.format(RESUBMISSION_COUNT_KEY, 1) == ("Resubmission Count", "1")
    assert plugin.safety(RESUBMISSION_COUNT_KEY) == Safety.SAFE
