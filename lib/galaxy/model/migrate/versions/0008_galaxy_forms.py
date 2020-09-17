"""
This migration script adds the following new tables for supporting Galaxy forms:
1) form_definition_current
2) form_definition
3) form_values
4) request_type
5) request
6) sample
7) sample_state
8) sample_event
"""

import datetime
import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    TEXT
)

from galaxy.model.custom_types import (
    JSONType,
    TrimmedString
)
from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()

FormDefinition_table = Table('form_definition', metadata,
                             Column("id", Integer, primary_key=True),
                             Column("create_time", DateTime, default=now),
                             Column("update_time", DateTime, default=now, onupdate=now),
                             Column("name", TrimmedString(255), nullable=False),
                             Column("desc", TEXT),
                             Column("form_definition_current_id", Integer, ForeignKey("form_definition_current.id", use_alter=True), index=True, nullable=False),
                             Column("fields", JSONType()))

FormDefinitionCurrent_table = Table('form_definition_current', metadata,
                                    Column("id", Integer, primary_key=True),
                                    Column("create_time", DateTime, default=now),
                                    Column("update_time", DateTime, default=now, onupdate=now),
                                    Column("latest_form_id", Integer, ForeignKey("form_definition.id"), index=True),
                                    Column("deleted", Boolean, index=True, default=False))

FormValues_table = Table('form_values', metadata,
                         Column("id", Integer, primary_key=True),
                         Column("create_time", DateTime, default=now),
                         Column("update_time", DateTime, default=now, onupdate=now),
                         Column("form_definition_id", Integer, ForeignKey("form_definition.id"), index=True),
                         Column("content", JSONType()))

RequestType_table = Table('request_type', metadata,
                          Column("id", Integer, primary_key=True),
                          Column("create_time", DateTime, default=now),
                          Column("update_time", DateTime, default=now, onupdate=now),
                          Column("name", TrimmedString(255), nullable=False),
                          Column("desc", TEXT),
                          Column("request_form_id", Integer, ForeignKey("form_definition.id"), index=True),
                          Column("sample_form_id", Integer, ForeignKey("form_definition.id"), index=True))

Request_table = Table('request', metadata,
                      Column("id", Integer, primary_key=True),
                      Column("create_time", DateTime, default=now),
                      Column("update_time", DateTime, default=now, onupdate=now),
                      Column("name", TrimmedString(255), nullable=False),
                      Column("desc", TEXT),
                      Column("form_values_id", Integer, ForeignKey("form_values.id"), index=True),
                      Column("request_type_id", Integer, ForeignKey("request_type.id"), index=True),
                      Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                      Column("library_id", Integer, ForeignKey("library.id"), index=True),
                      Column("deleted", Boolean, index=True, default=False))

Sample_table = Table('sample', metadata,
                     Column("id", Integer, primary_key=True),
                     Column("create_time", DateTime, default=now),
                     Column("update_time", DateTime, default=now, onupdate=now),
                     Column("name", TrimmedString(255), nullable=False),
                     Column("desc", TEXT),
                     Column("form_values_id", Integer, ForeignKey("form_values.id"), index=True),
                     Column("request_id", Integer, ForeignKey("request.id"), index=True),
                     Column("deleted", Boolean, index=True, default=False))

SampleState_table = Table('sample_state', metadata,
                          Column("id", Integer, primary_key=True),
                          Column("create_time", DateTime, default=now),
                          Column("update_time", DateTime, default=now, onupdate=now),
                          Column("name", TrimmedString(255), nullable=False),
                          Column("desc", TEXT),
                          Column("request_type_id", Integer, ForeignKey("request_type.id"), index=True))

SampleEvent_table = Table('sample_event', metadata,
                          Column("id", Integer, primary_key=True),
                          Column("create_time", DateTime, default=now),
                          Column("update_time", DateTime, default=now, onupdate=now),
                          Column("sample_id", Integer, ForeignKey("sample.id"), index=True),
                          Column("sample_state_id", Integer, ForeignKey("sample_state.id"), index=True),
                          Column("comment", TEXT))

TABLES = [
    FormDefinition_table,
    FormDefinitionCurrent_table,
    FormValues_table,
    RequestType_table,
    Request_table,
    Sample_table,
    SampleState_table,
    SampleEvent_table
]


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in TABLES:
        create_table(table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    for table in reversed(TABLES):
        drop_table(table)
