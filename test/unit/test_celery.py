from galaxy.celery import (
    celery_app,
    DEFAULT_TASK_QUEUE,
    GalaxyCelery,
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


def test_galaxycelery_trim_module_name():
    gc = GalaxyCelery()
    assert gc.trim_module_name("notgalaxy.celery.tasks") == "notgalaxy.celery.tasks"
    assert gc.trim_module_name("galaxy.notcelery.tasks") == "galaxy.notcelery.tasks"
    assert gc.trim_module_name("galaxy.celery.tasks") == "galaxy"
    assert gc.trim_module_name("galaxy.celery.tasks.nextlevel") == "galaxy.nextlevel"
