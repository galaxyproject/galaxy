"""The API rate limit options are validated when the FastAPI app is built."""

import pytest

from galaxy.exceptions import ConfigurationError
from galaxy.util.bunch import Bunch
from galaxy.webapps.galaxy.fast_app import validate_rate_limit_options


@pytest.mark.parametrize("value", ["10/minute", "100 per hour", "1 per 5 seconds", "", None])
def test_valid_send_notification_rate_limit(value):
    validate_rate_limit_options(Bunch(send_notification_rate_limit=value))


@pytest.mark.parametrize("value", ["10/min", "ten/minute", "10"])
def test_invalid_send_notification_rate_limit(value):
    with pytest.raises(ConfigurationError, match="send_notification_rate_limit"):
        validate_rate_limit_options(Bunch(send_notification_rate_limit=value))
