import pytest

from galaxy.config import GalaxyAppConfiguration


def _allowed(**kwargs) -> list[str]:
    return GalaxyAppConfiguration(override_tempdir=False, **kwargs).user_defined_tool_allowed_containers


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({}, ["quay.io/biocontainers/*"]),
        ({"user_defined_tool_allowed_containers": None}, ["quay.io/biocontainers/*"]),
        ({"user_defined_tool_allowed_containers": []}, []),
        # As set through GALAXY_CONFIG_USER_DEFINED_TOOL_ALLOWED_CONTAINERS.
        (
            {"user_defined_tool_allowed_containers": "quay.io/biocontainers/*, docker.io/library/python"},
            ["quay.io/biocontainers/*", "docker.io/library/python"],
        ),
    ],
)
def test_user_defined_tool_allowed_containers(kwargs, expected):
    assert _allowed(**kwargs) == expected
