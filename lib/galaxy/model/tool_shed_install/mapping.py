from galaxy.model import tool_shed_install as install_model
from galaxy.model.base import ModelMapping
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.tool_shed_install import mapper_registry

metadata = mapper_registry.metadata


def init(url, engine_options=None, create_tables=False):
    engine = build_engine(url, engine_options)
    if create_tables:
        create_database_objects(engine)
    return configure_model_mapping(engine)


def create_database_objects(engine):
    mapper_registry.metadata.create_all(bind=engine)


def configure_model_mapping(engine):
    # TODO: do we need to load local galaxy security policy?
    return ModelMapping([install_model], engine)
