import os

import pytest

from galaxy import config
from galaxy.config import DEFAULT_EMAIL_FROM_LOCAL_PART
from galaxy.exceptions import ConfigurationError
from galaxy.util.properties import running_from_source


@pytest.fixture()
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


@pytest.mark.parametrize("bracket", ["[", "]"])
def test_error_if_database_connection_contains_brackets(bracket):
    uri = f"dbscheme://user:pass{bracket}word@host/db"

    with pytest.raises(ConfigurationError):
        config.GalaxyAppConfiguration(override_tempdir=False, database_connection=uri)

    with pytest.raises(ConfigurationError):
        config.GalaxyAppConfiguration(override_tempdir=False, install_database_connection=uri)

    with pytest.raises(ConfigurationError):
        config.GalaxyAppConfiguration(override_tempdir=False, amqp_internal_connection=uri)


def test_error_if_interactivetoolsproxy_map_matches_other_database_connections():
    """
    The setting `interactivetoolsproxy_map` allows storing the session map in a
    database supported by SQLAlchemy. This database must be different from the Galaxy database
    and the tool shed database.

    Motivation for this constraint:
    https://github.com/galaxyproject/galaxy/pull/18481#issuecomment-2218493956
    """
    database_connection = "dbscheme://user:password@host/db"
    install_database_connection = "dbscheme://user:password@host/install_db"
    settings = dict(
        override_tempdir=False,
        database_connection=database_connection,
        install_database_connection=install_database_connection,
    )

    with pytest.raises(ConfigurationError):
        # interactivetoolsproxy_map matches database_connection
        config.GalaxyAppConfiguration(
            **settings,
            interactivetoolsproxy_map=database_connection,
        )

    with pytest.raises(ConfigurationError):
        # interactivetoolsproxy_map matches install_database_connection
        config.GalaxyAppConfiguration(
            **settings,
            interactivetoolsproxy_map=install_database_connection,
        )

    # interactivetoolsproxy_map differs from database_connection, install_database_connection
    config.GalaxyAppConfiguration(
        **settings,
        interactivetoolsproxy_map="dbscheme://user:password@host/gxitproxy",
    )


class TestIsFetchWithCeleryEnabled:
    def test_disabled_if_celery_disabled(self, appconfig):
        appconfig.enable_celery_tasks = False
        assert not appconfig.is_fetch_with_celery_enabled()

    def test_enabled_if_no_celeryconf(self, appconfig):
        appconfig.enable_celery_tasks = True
        appconfig.celery_conf = None
        assert appconfig.is_fetch_with_celery_enabled()

    def test_enabled_if_no_task_routes_key(self, appconfig):
        appconfig.enable_celery_tasks = True
        appconfig.celery_conf = {"some-other-key": 1}
        assert appconfig.is_fetch_with_celery_enabled()

    def test_enabled_if_task_routes_empty(self, appconfig):
        appconfig.enable_celery_tasks = True
        appconfig.celery_conf["task_routes"] = None
        assert appconfig.is_fetch_with_celery_enabled()

    def test_enabled_if_no_route_key(self, appconfig):
        appconfig.enable_celery_tasks = True
        appconfig.celery_conf["task_routes"] = {"some-other-route": 1}
        assert appconfig.is_fetch_with_celery_enabled()

    def test_enabled_if_no_route(self, appconfig):
        appconfig.enable_celery_tasks = True
        appconfig.celery_conf["task_routes"]["galaxy.fetch_data"] = None
        assert appconfig.is_fetch_with_celery_enabled()

    def test_enabled_if_has_route(self, appconfig):
        appconfig.enable_celery_tasks = True
        appconfig.celery_conf["task_routes"]["galaxy.fetch_data"] = "my_route"
        assert appconfig.is_fetch_with_celery_enabled()

    def test_disabled_if_disabled_flag(self, appconfig):
        appconfig.enable_celery_tasks = True
        appconfig.celery_conf["task_routes"]["galaxy.fetch_data"] = config.DISABLED_FLAG
        assert not appconfig.is_fetch_with_celery_enabled()
