from galaxy.celery import (
    celery_app,
    DEFAULT_TASK_QUEUE,
    GalaxyCelery,
    setup_periodic_tasks,
    TASKS_MODULES,
)
from galaxy.config import GalaxyAppConfiguration


def test_default_configuration():
    conf = celery_app.conf
    galaxy_conf = GalaxyAppConfiguration(override_tempdir=False)

    assert conf.task_default_queue == DEFAULT_TASK_QUEUE
    assert conf.include == TASKS_MODULES
    assert conf.task_create_missing_queues is True
    assert conf.timezone == "UTC"
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
    # GTN and IWC refreshes are gated on inference_services being configured;
    # default config doesn't set it, so neither schedule is registered here.
    assert "refresh-gtn-database" not in conf.beat_schedule
    assert "refresh-iwc-manifest" not in conf.beat_schedule


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
    app = GalaxyCelery("test-iwc-schedule")
    setup_periodic_tasks(config, app)
    assert app.conf.beat_schedule["refresh-iwc-manifest"] == {
        "task": "galaxy.refresh_iwc_manifest",
        "schedule": config.iwc_manifest_refresh_interval,
    }


def test_galaxycelery_trim_module_name():
    gc = GalaxyCelery()
    assert gc.trim_module_name("notgalaxy.celery.tasks") == "notgalaxy.celery.tasks"
    assert gc.trim_module_name("galaxy.notcelery.tasks") == "galaxy.notcelery.tasks"
    assert gc.trim_module_name("galaxy.celery.tasks") == "galaxy"
    assert gc.trim_module_name("galaxy.celery.tasks.nextlevel") == "galaxy.nextlevel"
