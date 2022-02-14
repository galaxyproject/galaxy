from galaxy.model import tool_shed_install as install_model
from galaxy.model.base import ModelMapping
from galaxy.model.orm.engine_factory import build_engine
from galaxy.model.tool_shed_install import mapper_registry

metadata = mapper_registry.metadata


def init(url, engine_options=None, create_tables=False):
    """Connect mappings to the database"""
    # Load the appropriate db module
    engine_options = engine_options or {}
    engine = build_engine(url, engine_options)
    result = ModelMapping([install_model], engine=engine)
    # Create tables if needed
    if create_tables:
        metadata.create_all(bind=engine)
        # metadata.engine.commit()
    result.create_tables = create_tables
    # load local galaxy security policy
    return result
