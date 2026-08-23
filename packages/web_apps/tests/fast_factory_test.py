from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from galaxy.util import in_packages
from galaxy.webapps.galaxy import fast_factory


def test_factory_uses_shared_web_app_builder(monkeypatch):
    config = Mock(global_conf={"from": "file"}, load_app_kwds={"config_file": "galaxy.yml"}, wsgi_preflight=True)
    monkeypatch.setattr(
        fast_factory,
        "WebappConfigResolver",
        Mock(return_value=Mock(resolve_config=Mock(return_value=config))),
    )
    web_app = Mock()
    builder = Mock(return_value=web_app)
    monkeypatch.setattr(fast_factory, "build_galaxy_web_app", builder)

    assert fast_factory.factory() is web_app.asgi_app
    builder.assert_called_once_with(
        global_conf=config.global_conf,
        load_app_kwds=config.load_app_kwds,
        wsgi_preflight=config.wsgi_preflight,
    )


def test_build_galaxy_web_app_assembles_and_returns_all_layers(monkeypatch):
    galaxy_app = Mock()
    wsgi_app = Mock()
    asgi_app = Mock()
    observed = {}

    def create_galaxy_app(**kwds):
        observed["app_kwds"] = kwds
        return galaxy_app

    def create_app_pair(global_conf, **kwds):
        observed["global_conf"] = global_conf
        observed["pair_kwds"] = kwds
        return wsgi_app, galaxy_app

    def create_fast_app(actual_wsgi_app, actual_galaxy_app):
        assert actual_wsgi_app is wsgi_app
        assert actual_galaxy_app is galaxy_app
        return asgi_app

    monkeypatch.setattr(fast_factory, "GalaxyUniverseApplication", create_galaxy_app)
    monkeypatch.setattr(fast_factory, "app_pair", create_app_pair)

    web_app = fast_factory.build_galaxy_web_app(
        {"database_connection": "sqlite:///:memory:"},
        global_conf={"static_enabled": False},
        register_shutdown_at_exit=False,
        init_fast_app=create_fast_app,
    )

    assert web_app.galaxy_app is galaxy_app
    assert web_app.wsgi_app is wsgi_app
    assert web_app.asgi_app is asgi_app
    assert observed["app_kwds"]["database_connection"] == "sqlite:///:memory:"
    assert observed["app_kwds"]["register_shutdown_at_exit"] is False
    assert observed["global_conf"] == {"static_enabled": False}
    assert observed["pair_kwds"]["app"] is galaxy_app
    assert observed["pair_kwds"]["register_shutdown_at_exit"] is False


def test_build_galaxy_web_app_does_not_mutate_input(monkeypatch):
    config = {"database_connection": "sqlite:///:memory:"}
    galaxy_app = Mock()
    monkeypatch.setattr(fast_factory, "GalaxyUniverseApplication", Mock(return_value=galaxy_app))
    monkeypatch.setattr(fast_factory, "app_pair", Mock(return_value=(Mock(), galaxy_app)))

    fast_factory.build_galaxy_web_app(config, init_fast_app=Mock())

    assert config == {"database_connection": "sqlite:///:memory:"}


def test_build_galaxy_web_app_propagates_construction_errors(monkeypatch):
    class ExpectedError(Exception):
        pass

    def fail_to_create_app(**kwds):
        raise ExpectedError()

    monkeypatch.setattr(fast_factory, "GalaxyUniverseApplication", fail_to_create_app)

    with pytest.raises(ExpectedError):
        fast_factory.build_galaxy_web_app()


def test_build_galaxy_web_app_shuts_down_partially_built_app(monkeypatch):
    class ExpectedError(Exception):
        pass

    galaxy_app = Mock()
    monkeypatch.setattr(fast_factory, "GalaxyUniverseApplication", Mock(return_value=galaxy_app))
    monkeypatch.setattr(fast_factory, "app_pair", Mock(side_effect=ExpectedError))

    with pytest.raises(ExpectedError):
        fast_factory.build_galaxy_web_app()

    galaxy_app.shutdown.assert_called_once_with()


@pytest.mark.skipif(not in_packages(), reason="requires package-installed Galaxy")
def test_build_galaxy_web_app_starts_without_a_checkout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    paths = {name: tmp_path / name for name in ("config", "data", "files", "jobs", "new")}
    for path in paths.values():
        path.mkdir()

    web_app = fast_factory.build_galaxy_web_app(
        {
            "config_dir": str(paths["config"]),
            "managed_config_dir": str(paths["config"]),
            "data_dir": str(paths["data"]),
            "database_connection": f"sqlite:///{paths['data'] / 'galaxy.sqlite'}?isolation_level=IMMEDIATE",
            "database_auto_migrate": True,
            "file_path": str(paths["files"]),
            "job_working_directory": str(paths["jobs"]),
            "new_file_path": str(paths["new"]),
            "bootstrap_admin_api_key": "package-test-key",
            "id_secret": "package-test-secret",
            "use_heartbeat": False,
        },
        register_shutdown_at_exit=False,
    )

    try:
        tool_path = Path(web_app.galaxy_app.config.tool_path)
        assert tool_path.name == "bundled"
        assert "site-packages" in tool_path.parts
        with TestClient(web_app.asgi_app) as client:
            response = client.get("/api/version")
        assert response.status_code == 200
        assert response.json()["version_major"]
    finally:
        web_app.galaxy_app.shutdown()
