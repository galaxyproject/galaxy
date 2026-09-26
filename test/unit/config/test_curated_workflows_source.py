import logging

import pytest

from galaxy.config import (
    GalaxyAppConfiguration,
    resolve_curated_workflows_source,
)
from galaxy.exceptions import ConfigurationError


def _config(**kwargs) -> GalaxyAppConfiguration:
    return GalaxyAppConfiguration(override_tempdir=False, **kwargs)


def test_default_is_iwc():
    config = _config()
    assert config.curated_workflows_source == "iwc"
    assert config.curated_workflow_owners == []


@pytest.mark.parametrize(
    "source, owners, expected",
    [
        ("iwc", "", "iwc"),
        ("local", "curator", "local"),
        ("local", "curator, other", "local"),
        ("off", "", "off"),
        # Case and surrounding whitespace are forgiven; the spelling is not.
        (" Local ", "curator", "local"),
        ("OFF", "", "off"),
    ],
)
def test_valid_modes(source, owners, expected):
    assert _config(curated_workflows_source=source, curated_workflow_owners=owners).curated_workflows_source == expected


def test_local_owners_are_listified():
    config = _config(curated_workflows_source="local", curated_workflow_owners="curator, other")
    assert config.curated_workflow_owners == ["curator", "other"]


@pytest.mark.parametrize("source", ["", "on", "true", "iwc,local", "disabled"])
def test_unknown_mode_fails_at_startup(source):
    with pytest.raises(ConfigurationError, match="curated_workflows_source"):
        _config(curated_workflows_source=source)


def test_unquoted_yaml_off_means_off():
    # YAML 1.1 loads `curated_workflows_source: off` as False.
    assert _config(curated_workflows_source=False).curated_workflows_source == "off"


def test_unquoted_yaml_on_fails_at_startup():
    # True (from `on`, `yes` or `true`) names no source, so it can't be guessed at.
    with pytest.raises(ConfigurationError, match="curated_workflows_source"):
        _config(curated_workflows_source=True)


@pytest.mark.parametrize("owners", ["", " , "])
def test_local_without_owners_fails_at_startup(owners):
    with pytest.raises(ConfigurationError, match="curated_workflow_owners is empty"):
        _config(curated_workflows_source="local", curated_workflow_owners=owners)


@pytest.mark.parametrize("source", ["iwc", "off"])
def test_owners_outside_local_mode_are_ignored_with_a_warning(source, caplog):
    with caplog.at_level(logging.WARNING, logger="galaxy.config"):
        config = _config(curated_workflows_source=source, curated_workflow_owners="curator")
    # The mode is the one configured; owners never switch it.
    assert config.curated_workflows_source == source
    assert "curated_workflow_owners is set" in caplog.text


def test_no_warning_without_owners(caplog):
    with caplog.at_level(logging.WARNING, logger="galaxy.config"):
        _config(curated_workflows_source="iwc")
    assert "curated_workflow_owners" not in caplog.text


def test_resolution_is_a_pure_function_of_config():
    assert resolve_curated_workflows_source("iwc", []) == "iwc"
    assert resolve_curated_workflows_source("local", ["curator"]) == "local"
    assert resolve_curated_workflows_source("off", []) == "off"
    with pytest.raises(ConfigurationError):
        resolve_curated_workflows_source(None, [])
