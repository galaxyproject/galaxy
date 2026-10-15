import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigurationError


def _config(**kwargs) -> GalaxyAppConfiguration:
    return GalaxyAppConfiguration(override_tempdir=False, **kwargs)


@pytest.mark.parametrize(
    "origins", [None, "", "https://example.org", " https://a.example.org, https://b.example.org:8080 "]
)
def test_accepts_origins(origins):
    assert _config(widgets_allowed_origins=origins).widgets_allowed_origins == origins


@pytest.mark.parametrize(
    "origins",
    [
        "https://example.org; script-src 'none'",
        "https://example.org;",
        "https://example.org\nX-Injected: 1",
        "https://example.org\x00",
        "https://example.org\x7f",
        "https://a.example.org https://b.example.org",
        "https://a.example.org, https://b.example.org\tx",
    ],
)
def test_rejects_malformed_origins(origins):
    with pytest.raises(ConfigurationError, match="widgets_allowed_origins"):
        _config(widgets_allowed_origins=origins)
