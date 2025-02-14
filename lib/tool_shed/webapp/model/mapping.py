"""
Details of how the data model objects are mapped onto the relational database
are encapsulated here.
"""

import logging
from typing import (
    Any,
    Dict,
    Optional,
    Type,
    TYPE_CHECKING,
)

import tool_shed.webapp.model
import tool_shed.webapp.util.shed_statistics as shed_statistics
from galaxy.model.base import SharedModelMapping
from galaxy.model.orm.engine_factory import build_engine
from tool_shed.webapp.model import mapper_registry
from tool_shed.webapp.security import CommunityRBACAgent

if TYPE_CHECKING:
    from tool_shed.webapp.model import User as ToolShedUser

log = logging.getLogger(__name__)

metadata = mapper_registry.metadata


class ToolShedModelMapping(SharedModelMapping):
    User: Type["ToolShedUser"]
    security_agent: CommunityRBACAgent
    shed_counter: shed_statistics.ShedCounter
    create_tables: bool


def init(
    url: str, engine_options: Optional[Dict[str, Any]] = None, create_tables: bool = False
) -> ToolShedModelMapping:
    """Connect mappings to the database"""
    engine_options = engine_options or {}
    # Create the database engine
    engine = build_engine(url, engine_options)

    result = ToolShedModelMapping([tool_shed.webapp.model], engine=engine)

    if create_tables:
        metadata.create_all(bind=engine)

    result.create_tables = create_tables

    result.security_agent = CommunityRBACAgent(result)
    result.shed_counter = shed_statistics.ShedCounter(result)

    session = result.session()
    with session.begin():
        result.shed_counter.generate_statistics(session)

    return result
