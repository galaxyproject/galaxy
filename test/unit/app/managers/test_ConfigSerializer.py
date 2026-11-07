from types import SimpleNamespace

import pytest

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.managers.configuration import ConfigSerializer


@pytest.mark.parametrize(
    "default_duration, maximum_duration, expected",
    [
        (86400, 0, 86400),
        (604800, 86400, 86400),
        (None, 3600, 3600),
    ],
)
def test_short_term_storage_effective_duration(default_duration, maximum_duration, expected):
    config = SimpleNamespace(
        short_term_storage_default_duration=default_duration,
        short_term_storage_maximum_duration=maximum_duration,
    )
    serializer = ConfigSerializer(MockApp())
    key = "short_term_storage_effective_duration"
    assert serializer.serializers[key](config, key) == expected
