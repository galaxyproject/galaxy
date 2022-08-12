import pytest

from galaxy.tool_util.deps.requirements import ContainerDescription


@pytest.mark.parametrize(
    "identifier,expected_identifier",
    [
        ("mulled-abc", "mulled-abc"),
        ("docker://mulled-abc", "docker://mulled-abc"),
        ("/Cache/mulled-abc", "/Cache/mulled-abc"),
        ("/Cache/mUlled-abc", "/Cache/mulled-abc"),
        ("", None),
        (None, None),
    ],
)
def test_container_description(identifier, expected_identifier):
    assert ContainerDescription(identifier=identifier).identifier == expected_identifier


def test_to_from_dict():
    container_description_dict = ContainerDescription("mulled-abc").to_dict()
    container_description = ContainerDescription.from_dict(container_description_dict)
    assert container_description_dict == container_description.to_dict()
