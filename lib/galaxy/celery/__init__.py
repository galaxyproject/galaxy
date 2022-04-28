import asyncio
import os
from functools import (
    lru_cache,
    wraps,
)
from threading import local
from typing import (
    Any,
    Callable,
    Dict,
)

from asgiref.sync import (
    async_to_sync,
    sync_to_async,
)
from celery import (
    Celery,
    shared_task,
)
from celery.contrib.abortable import AbortableTask
from kombu import serialization

from galaxy import model
from galaxy.config import Configuration
from galaxy.main_config import find_config
from galaxy.util import ExecutionTimer
from galaxy.util.custom_logging import get_logger
from galaxy.util.properties import load_app_properties
from ._serialization import (
    schema_dumps,
    schema_loads,
)

log = get_logger(__name__)

MAIN_TASK_MODULE = "galaxy.celery.tasks"
TASKS_MODULES = [MAIN_TASK_MODULE]
PYDANTIC_AWARE_SERIALIZER_NAME = "pydantic-aware-json"

APP_LOCAL = local()

serialization.register(
    PYDANTIC_AWARE_SERIALIZER_NAME, encoder=schema_dumps, decoder=schema_loads, content_type="application/json"
)


def set_thread_app(app):
    APP_LOCAL.app = app


def get_galaxy_app():
    try:
        return APP_LOCAL.app
    except AttributeError:
        import galaxy.app

        if galaxy.app.app:
            return galaxy.app.app
    return build_app()


@lru_cache(maxsize=1)
def build_app():
    kwargs = get_app_properties()
    if kwargs:
        kwargs["check_migrate_databases"] = False
        kwargs["use_display_applications"] = False
        kwargs["use_converters"] = False
        import galaxy.app

        galaxy_app = galaxy.app.GalaxyManagerApplication(configure_logging=False, **kwargs)
        return galaxy_app


@lru_cache(maxsize=1)
def get_app_properties():
    config_file = os.environ.get("GALAXY_CONFIG_FILE")
    galaxy_root_dir = os.environ.get("GALAXY_ROOT_DIR")
    if not config_file and galaxy_root_dir:
        config_file = find_config(config_file, galaxy_root_dir)
    if config_file:
        properties = load_app_properties(
            config_file=os.path.abspath(config_file),
            config_section="galaxy",
        )
        if galaxy_root_dir:
            properties["root_dir"] = galaxy_root_dir
        return properties


@lru_cache(maxsize=1)
def get_config():
    kwargs = get_app_properties()
    if kwargs:
        kwargs["override_tempdir"] = False
        return Configuration(**kwargs)


def get_broker():
    config = get_config()
    if config:
        return config.celery_broker or config.amqp_internal_connection


def get_backend():
    config = get_config()
    if config:
        return config.celery_backend


def get_history_audit_table_prune_interval():
    config = get_config()
    if config:
        return config.history_audit_table_prune_interval
    else:
        return 3600


def get_cleanup_short_term_storage_interval():
    config = get_config()
    if config:
        return config.short_term_storage_cleanup_interval
    else:
        return 3600


broker = get_broker()
backend = get_backend()
celery_app_kwd: Dict[str, Any] = {
    "broker": broker,
    "include": TASKS_MODULES,
}
if backend:
    celery_app_kwd["backend"] = backend

celery_app = Celery("galaxy", **celery_app_kwd)
celery_app.set_default()

# setup cron like tasks...
beat_schedule: Dict[str, Dict[str, Any]] = {}

prune_interval = get_history_audit_table_prune_interval()
if prune_interval > 0:
    beat_schedule["prune-history-audit-table"] = {
        "task": f"{MAIN_TASK_MODULE}.prune_history_audit_table",
        "schedule": prune_interval,
    }

cleanup_interval = get_cleanup_short_term_storage_interval()
if cleanup_interval > 0:
    beat_schedule["cleanup-short-term-storage"] = {
        "task": f"{MAIN_TASK_MODULE}.cleanup_short_term_storage",
        "schedule": cleanup_interval,
    }

if beat_schedule:
    celery_app.conf.beat_schedule = beat_schedule
celery_app.conf.timezone = "UTC"


async def cancellable_task(f: Callable, *args, **kwargs):
    coro = sync_to_async(f)
    done, pending = await asyncio.wait(
        [coro(*args, **kwargs), is_aborted(kwargs["job_id"])], return_when=asyncio.FIRST_COMPLETED
    )
    for pending_future in pending:
        pending_future.cancel()
    for done_future in done:
        return done_future.result()


async def is_aborted(job_id):
    # This is not ideal
    # 1. we're calling a method that does I/O (sqlalchemy query)
    # 2. we're polling every second
    # Maybe we should listen for broadcast messages ?
    # Alternatively we could construct an AsyncSession and decrease the polling frequency over time
    # Other notes: AbortableTask could be be revoked, but that only works with the database backend
    # ... which shouldn't be used.
    app = get_galaxy_app()

    # sessionmaker should obviously be created elsewhere, and persist in the worker's main loop
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        create_async_engine,
    )
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.future import select

    db_url = app.config.database_connection
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        if "?client_encoding=utf8" in db_url:
            db_url = db_url.replace("?client_encoding=utf8", "")

    try:
        engine = create_async_engine(
            db_url,
        )
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with async_session() as session:

            async def get_state():
                result = await session.execute(select(model.Job.state).where(model.Job.id == job_id))
                return next(result)

            state = await get_state()
            while state[0] not in {model.Job.states.DELETED, model.Job.states.DELETING}:
                await asyncio.sleep(1)
                state = await get_state()
    finally:
        await engine.dispose()
    log.debug(f"Job {job_id} aborted")


def galaxy_task(*args, action=None, **celery_task_kwd):
    if "serializer" not in celery_task_kwd:
        celery_task_kwd["serializer"] = PYDANTIC_AWARE_SERIALIZER_NAME

    def decorate(func: Callable):
        @shared_task(**celery_task_kwd)
        @wraps(func)
        def wrapper(*args, **kwds):
            app = get_galaxy_app()
            assert app
            desc = func.__name__
            if action is not None:
                desc += f" to {action}"

            try:
                timer = app.execution_timer_factory.get_timer("internals.tasks.{func.__name__}", desc)
            except AttributeError:
                timer = ExecutionTimer()

            try:
                partial_task_function = app.magic_partial(func)
                if args and isinstance(args[0], AbortableTask):
                    rval = async_to_sync(cancellable_task)(partial_task_function, *args, **kwds)
                else:
                    rval = partial_task_function(*args, **kwds)
                message = f"Successfully executed Celery task {desc} {timer}"
                log.info(message)
                return rval
            except Exception:
                log.warning(f"Celery task execution failed for {desc} {timer}")
                raise

        return wrapper

    if len(args) == 1 and callable(args[0]):
        return decorate(args[0])
    else:
        return decorate


if __name__ == "__main__":
    celery_app.start()
