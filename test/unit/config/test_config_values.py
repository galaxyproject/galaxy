import os

import pytest

from galaxy import config
from galaxy.config import DEFAULT_EMAIL_FROM_LOCAL_PART
from galaxy.util.properties import running_from_source


@pytest.fixture(scope="module")
def appconfig():
    return config.GalaxyAppConfiguration(override_tempdir=False)


def test_root(appconfig):
    assert appconfig.root == os.path.abspath(".")


def test_common_base_config(appconfig):
    assert appconfig.shed_tools_dir == os.path.join(appconfig.data_dir, "shed_tools")
    if running_from_source:
        expected_path = os.path.join(appconfig.root, "lib", "galaxy", "config", "sample")
    else:
        expected_path = os.path.join(appconfig.root, "galaxy", "config", "sample")
    assert appconfig.sample_config_dir == expected_path


def test_base_config_if_running_from_source(monkeypatch):
    # Simulated condition: running from source, config_file is None.
    monkeypatch.setattr(config, "running_from_source", True)
    appconfig = config.GalaxyAppConfiguration(override_tempdir=False)
    assert not appconfig.config_file
    assert appconfig.config_dir == os.path.join(appconfig.root, "config")
    assert appconfig.data_dir == os.path.join(appconfig.root, "database")
    assert appconfig.managed_config_dir == appconfig.config_dir


def test_base_config_if_running_not_from_source(monkeypatch):
    # Simulated condition: running not from source, config_file is None.
    monkeypatch.setattr(config, "running_from_source", False)
    appconfig = config.GalaxyAppConfiguration(override_tempdir=False)
    assert not appconfig.config_file
    assert appconfig.config_dir == os.getcwd()
    assert appconfig.data_dir == os.path.join(appconfig.config_dir, "data")
    assert appconfig.managed_config_dir == os.path.join(appconfig.data_dir, "config")


def test_assign_email_from(monkeypatch):
    appconfig = config.GalaxyAppConfiguration(
        override_tempdir=False, galaxy_infrastructure_url="http://myhost:8080/galaxy/"
    )
    assert appconfig.email_from == f"{DEFAULT_EMAIL_FROM_LOCAL_PART}@myhost"
