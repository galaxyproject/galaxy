import logging
from threading import local
from typing import (
    Optional,
    TYPE_CHECKING,
)

from galaxy import model
from galaxy.config import GalaxyAppConfiguration
from galaxy.model import (
    mapper_registry,
    setup_global_object_store_for_models,
)
from galaxy.model.base import SharedModelMapping
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.security import GalaxyRBACAgent
from galaxy.model.triggers.update_audit_table import install as install_timestamp_triggers

if TYPE_CHECKING:
    from galaxy.objectstore import BaseObjectStore

log = logging.getLogger(__name__)

metadata = mapper_registry.metadata


class GalaxyModelMapping(SharedModelMapping):
    security_agent: GalaxyRBACAgent
    thread_local_log: Optional[local]


def init(
    file_path,
    url,
    engine_options=None,
    create_tables=False,
    map_install_models=False,
    database_query_profiling_proxy=False,
    trace_logger=None,
    use_pbkdf2=True,
    slow_query_log_threshold=0,
    thread_local_log: Optional[local] = None,
    log_query_counts=False,
) -> GalaxyModelMapping:
    # Build engine
    engine = build_engine(
        url,
        engine_options,
        database_query_profiling_proxy,
        trace_logger,
        slow_query_log_threshold,
        thread_local_log=thread_local_log,
        log_query_counts=log_query_counts,
    )

    # Create tables if needed
    if create_tables:
        mapper_registry.metadata.create_all(bind=engine)
        create_additional_database_objects(engine)
        if map_install_models:
            from galaxy.model.tool_shed_install import mapping as install_mapping  # noqa: F401

            install_mapping.create_database_objects(engine)

    # Configure model, build ModelMapping
    return configure_model_mapping(file_path, use_pbkdf2, engine, map_install_models, thread_local_log)


def create_additional_database_objects(engine):
    install_timestamp_triggers(engine)


def configure_model_mapping(
    file_path: str,
    use_pbkdf2,
    engine,
    map_install_models,
    thread_local_log,
) -> GalaxyModelMapping:
    _configure_model(file_path, use_pbkdf2)
    return _build_model_mapping(engine, map_install_models, thread_local_log)


def _configure_model(file_path: str, use_pbkdf2) -> None:
    model.Dataset.file_path = file_path
    model.User.use_pbkdf2 = use_pbkdf2


def _build_model_mapping(engine, map_install_models, thread_local_log) -> GalaxyModelMapping:
    model_modules = [model]
    if map_install_models:
        from galaxy.model import tool_shed_install

        model_modules.append(tool_shed_install)

    model_mapping = GalaxyModelMapping(model_modules, engine)
    model_mapping.security_agent = GalaxyRBACAgent(model_mapping.session)
    model_mapping.thread_local_log = thread_local_log
    return model_mapping


def init_models_from_config(
    config: GalaxyAppConfiguration,
    map_install_models: bool = False,
    object_store: Optional["BaseObjectStore"] = None,
    trace_logger=None,
) -> GalaxyModelMapping:
    model = init(
        config.file_path,
        config.database_connection,
        config.database_engine_options,
        map_install_models=map_install_models,
        database_query_profiling_proxy=config.database_query_profiling_proxy,
        trace_logger=trace_logger,
        use_pbkdf2=config.get_bool("use_pbkdf2", True),
        slow_query_log_threshold=config.slow_query_log_threshold,
        thread_local_log=config.thread_local_log,
        log_query_counts=config.database_log_query_counts,
    )
    if object_store:
        setup_global_object_store_for_models(object_store)
    return model
