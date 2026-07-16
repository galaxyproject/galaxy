from unittest.mock import Mock

from galaxy_test.driver import driver_util
from galaxy_test.driver.driver_util import attempt_ports


def test_attempt_ports():
    port = int(attempt_ports())
    assert port >= 8000 and port <= 10000


def _gx_app(new_file_path: str) -> Mock:
    return Mock(
        config=Mock(
            galaxy_url_prefix="/",
            enable_mcp_server=False,
            tus_upload_store=None,
            tus_upload_store_job_files=None,
            new_file_path=new_file_path,
            maximum_upload_file_size=1073741824,
        )
    )


def test_caching_fast_app_factory_rebuilds_when_tus_state_changes(monkeypatch):
    driver_util._test_fast_app_slot.cache_clear()
    init_calls = []

    def fake_init(_gx_wsgi_webapp, gx_app):
        init_calls.append(gx_app.config.new_file_path)
        return Mock(router=Mock(lifespan_context=object()))

    def fake_rebind(*args, **kwargs):
        raise AssertionError("Rebind should not be used when TUS state changes and app must be rebuilt")

    monkeypatch.setattr(driver_util, "init_galaxy_fast_app", fake_init)
    monkeypatch.setattr(driver_util, "_rebind_fast_app_for_launch", fake_rebind)

    first = driver_util.caching_fast_app_factory(object(), _gx_app("/tmp/first"))
    second = driver_util.caching_fast_app_factory(object(), _gx_app("/tmp/second"))

    assert first is not second
    assert init_calls == ["/tmp/first", "/tmp/second"]


def test_caching_fast_app_factory_reuses_and_rebinds_when_tus_state_same(monkeypatch):
    driver_util._test_fast_app_slot.cache_clear()
    init_calls = []
    rebind_calls = []

    def fake_init(_gx_wsgi_webapp, gx_app):
        init_calls.append(gx_app.config.new_file_path)
        return Mock(router=Mock(lifespan_context="lifespan"))

    def fake_rebind(*args, **kwargs):
        rebind_calls.append((args, kwargs))

    monkeypatch.setattr(driver_util, "init_galaxy_fast_app", fake_init)
    monkeypatch.setattr(driver_util, "_rebind_fast_app_for_launch", fake_rebind)

    first = driver_util.caching_fast_app_factory(object(), _gx_app("/tmp/shared"))
    second = driver_util.caching_fast_app_factory(object(), _gx_app("/tmp/shared"))

    assert first is second
    assert init_calls == ["/tmp/shared"]
    assert len(rebind_calls) == 1
