import logging
from types import SimpleNamespace

import pytest

from galaxy.celery import (
    celery_app,
    DEFAULT_TASK_QUEUE,
    GalaxyCelery,
    PYDANTIC_AWARE_SERIALIZER_NAME,
    setup_periodic_tasks,
    tasks,
    TASKS_MODULES,
)
from galaxy.config import GalaxyAppConfiguration
from galaxy.workflow import curated


def test_default_configuration():
    conf = celery_app.conf
    galaxy_conf = GalaxyAppConfiguration(override_tempdir=False)

    assert conf.task_default_queue == DEFAULT_TASK_QUEUE
    assert conf.include == TASKS_MODULES
    assert conf.task_create_missing_queues is True
    assert conf.timezone == "UTC"
    assert conf.task_serializer == PYDANTIC_AWARE_SERIALIZER_NAME
    assert conf.broker_url == galaxy_conf.amqp_internal_connection
    assert conf.task_routes["galaxy.fetch_data"] == "galaxy.external"
    assert conf.task_routes["galaxy.set_job_metadata"] == "galaxy.external"
    assert conf.beat_schedule["prune-history-audit-table"] == {
        "task": "galaxy.prune_history_audit_table",
        "schedule": galaxy_conf.history_audit_table_prune_interval,
    }
    assert conf.beat_schedule["cleanup-short-term-storage"] == {
        "task": "galaxy.cleanup_short_term_storage",
        "schedule": galaxy_conf.short_term_storage_cleanup_interval,
    }
    # The GTN refresh is gated on inference_services, which the default config
    # doesn't set. The IWC refresh is not: curated_workflows_source defaults to
    # iwc, and the curated workflows tab needs the projection this task writes.
    assert "refresh-gtn-database" not in conf.beat_schedule
    assert conf.beat_schedule["refresh-iwc-manifest"] == {
        "task": "galaxy.refresh_iwc_manifest",
        "schedule": galaxy_conf.iwc_manifest_refresh_interval,
    }


def test_gtn_refresh_schedules_when_inference_configured():
    config = GalaxyAppConfiguration(override_tempdir=False)
    config.inference_services = {"default": {"model": "test"}}
    app = GalaxyCelery("test-gtn-schedule")
    setup_periodic_tasks(config, app)
    assert app.conf.beat_schedule["refresh-gtn-database"] == {
        "task": "galaxy.refresh_gtn_database",
        "schedule": config.gtn_database_refresh_interval,
    }


def test_iwc_refresh_schedules_when_inference_configured():
    config = GalaxyAppConfiguration(override_tempdir=False)
    config.inference_services = {"default": {"model": "test"}}
    config.curated_workflows_source = "off"
    app = GalaxyCelery("test-iwc-schedule")
    setup_periodic_tasks(config, app)
    assert app.conf.beat_schedule["refresh-iwc-manifest"] == {
        "task": "galaxy.refresh_iwc_manifest",
        "schedule": config.iwc_manifest_refresh_interval,
    }


def test_iwc_refresh_schedules_in_iwc_mode():
    config = GalaxyAppConfiguration(override_tempdir=False, curated_workflows_source="iwc")
    config.inference_services = None
    app = GalaxyCelery("test-iwc-curated-schedule")
    setup_periodic_tasks(config, app)
    assert app.conf.beat_schedule["refresh-iwc-manifest"] == {
        "task": "galaxy.refresh_iwc_manifest",
        "schedule": config.iwc_manifest_refresh_interval,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"curated_workflows_source": "off"},
        {"curated_workflows_source": "local", "curated_workflow_owners": "curator"},
        # Owners alone never select local mode, and off with owners still means off.
        {"curated_workflows_source": "off", "curated_workflow_owners": "curator"},
    ],
)
def test_iwc_refresh_not_scheduled_when_nothing_reads_it(overrides):
    config = GalaxyAppConfiguration(override_tempdir=False, **overrides)
    config.inference_services = None
    app = GalaxyCelery("test-iwc-no-schedule")
    setup_periodic_tasks(config, app)
    assert "refresh-iwc-manifest" not in app.conf.beat_schedule


def test_iwc_refresh_not_scheduled_when_interval_is_zero():
    config = GalaxyAppConfiguration(override_tempdir=False, iwc_manifest_refresh_interval=0)
    config.inference_services = None
    app = GalaxyCelery("test-iwc-zero-interval")
    setup_periodic_tasks(config, app)
    assert "refresh-iwc-manifest" not in app.conf.beat_schedule


def test_galaxycelery_trim_module_name():
    gc = GalaxyCelery()
    assert gc.trim_module_name("notgalaxy.celery.tasks") == "notgalaxy.celery.tasks"
    assert gc.trim_module_name("galaxy.notcelery.tasks") == "galaxy.notcelery.tasks"
    assert gc.trim_module_name("galaxy.celery.tasks") == "galaxy"
    assert gc.trim_module_name("galaxy.celery.tasks.nextlevel") == "galaxy.nextlevel"


@pytest.mark.parametrize("source", ["local", "off"])
def test_iwc_refresh_task_writes_no_projection_outside_iwc_mode(tmp_path, monkeypatch, source):
    def unexpected_refresh(path: str) -> int:
        raise AssertionError("refresh_projection must not run outside iwc mode")

    monkeypatch.setattr(curated, "refresh_projection", unexpected_refresh)
    config = SimpleNamespace(
        curated_workflows_path=str(tmp_path / "iwc_workflows.json"),
        curated_workflows_source=source,
        inference_services=None,
    )
    tasks.refresh_iwc_manifest.run.__wrapped__(config)


def test_iwc_refresh_task_reports_a_skip_when_another_process_is_refreshing(tmp_path, monkeypatch, caplog):
    def busy_refresh(path: str) -> int:
        raise curated.RefreshInProgress(path)

    monkeypatch.setattr(curated, "refresh_projection", busy_refresh)
    config = SimpleNamespace(
        curated_workflows_path=str(tmp_path / "iwc_workflows.json"),
        curated_workflows_source="iwc",
        inference_services=None,
    )
    # The undecorated body: the celery wrapper needs a running Galaxy app to inject config.
    task_body = tasks.refresh_iwc_manifest.run.__wrapped__
    with caplog.at_level(logging.INFO, logger=tasks.log.name):
        task_body(config)

    assert "already refreshing" in caplog.text
    assert "could not refresh" not in caplog.text
