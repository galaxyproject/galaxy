"""
This migration script renames the sequencer table to 'external_service' table and
creates a association table, 'request_type_external_service_association' and
populates it. The 'sequencer_id' foreign_key from the 'request_type' table is removed.
The 'sequencer_type_id' column is renamed to 'external_service_type_id' in the renamed
table 'external_service'. Finally, adds a foreign key to the external_service table in the
sample_dataset table and populates it.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import (
    add_column,
    create_table,
    drop_column,
    drop_table,
    nextval
)

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # rename 'sequencer' table to 'external_service'
    Sequencer_table = Table("sequencer", metadata, autoload=True)
    Sequencer_table.rename('external_service')

    # if running PostgreSQL, rename the primary key sequence too
    if migrate_engine.name in ['postgres', 'postgresql']:
        cmd = "ALTER SEQUENCE sequencer_id_seq RENAME TO external_service_id_seq"
        migrate_engine.execute(cmd)

    # Add 'external_services_id' column to 'sample_dataset' table
    SampleDataset_table = Table("sample_dataset", metadata, autoload=True)
    # SQLAlchemy Migrate has a bug when adding a column with both a ForeignKey and a index in SQLite
    if migrate_engine.name != 'sqlite':
        col = Column("external_service_id", Integer, ForeignKey("external_service.id", name='sample_dataset_external_services_id_fk'), index=True)
    else:
        col = Column("external_service_id", Integer, index=True)
    add_column(col, SampleDataset_table, index_name="ix_sample_dataset_external_service_id")

    # populate the column
    cmd = "SELECT sample_dataset.id, request_type.sequencer_id " \
          + " FROM sample_dataset, sample, request, request_type " \
          + " WHERE sample.id=sample_dataset.sample_id and request.id=sample.request_id and request.request_type_id=request_type.id " \
          + " ORDER BY sample_dataset.id"
    try:
        result = migrate_engine.execute(cmd)
        for r in result:
            sample_dataset_id = int(r[0])
            sequencer_id = int(r[1])
            cmd = "UPDATE sample_dataset SET external_service_id='%i' where id=%i" % (sequencer_id, sample_dataset_id)
            migrate_engine.execute(cmd)
    except Exception:
        log.exception("Exception executing SQL command: %s", cmd)

    # rename 'sequencer_type_id' column to 'external_service_type_id' in the table 'external_service'
    # create the column as 'external_service_type_id'
    ExternalServices_table = Table("external_service", metadata, autoload=True)
    col = Column("external_service_type_id", TrimmedString(255))
    add_column(col, ExternalServices_table)

    # populate this new column
    cmd = "UPDATE external_service SET external_service_type_id=sequencer_type_id"
    migrate_engine.execute(cmd)

    # remove the 'sequencer_type_id' column
    drop_column('sequencer_type_id', ExternalServices_table)

    # create 'request_type_external_service_association' table
    RequestTypeExternalServiceAssociation_table = Table("request_type_external_service_association", metadata,
                                                        Column("id", Integer, primary_key=True),
                                                        Column("request_type_id", Integer, ForeignKey("request_type.id"), index=True),
                                                        Column("external_service_id", Integer, ForeignKey("external_service.id"), index=True))
    create_table(RequestTypeExternalServiceAssociation_table)

    # populate 'request_type_external_service_association' table
    cmd = "SELECT id, sequencer_id FROM request_type ORDER BY id ASC"
    result = migrate_engine.execute(cmd)
    results_list = result.fetchall()
    # Proceed only if request_types exists
    for row in results_list:
        request_type_id = row[0]
        sequencer_id = row[1]
        if not sequencer_id:
            sequencer_id = 'null'
        cmd = "INSERT INTO request_type_external_service_association VALUES ( %s, %s, %s )" % (
            nextval(migrate_engine, 'request_type_external_service_association'),
            request_type_id,
            sequencer_id)
        migrate_engine.execute(cmd)

    # drop the 'sequencer_id' column in the 'request_type' table
    drop_column('sequencer_id', 'request_type', metadata)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # SQLite does not always update foreign key constraints when the target
    # table is renamed, so we start with the table rename.
    # rename the 'external_service' table to 'sequencer'
    ExternalServices_table = Table("external_service", metadata, autoload=True)
    ExternalServices_table.rename('sequencer')

    # if running PostgreSQL, rename the primary key sequence too
    if migrate_engine.name in ['postgres', 'postgresql']:
        cmd = "ALTER SEQUENCE external_service_id_seq RENAME TO sequencer_id_seq"
        migrate_engine.execute(cmd)

    # create the 'sequencer_id' column in the 'request_type' table
    col = Column("sequencer_id", Integer, ForeignKey("sequencer.id"), nullable=True)
    add_column(col, 'request_type', metadata)

    # populate 'sequencer_id' column in the 'request_type' table from the
    # 'request_type_external_service_association' table
    cmd = "SELECT request_type_id, external_service_id FROM request_type_external_service_association ORDER BY id ASC"
    result = migrate_engine.execute(cmd)
    results_list = result.fetchall()
    for row in results_list:
        request_type_id = row[0]
        external_service_id = row[1]
        cmd = "UPDATE request_type SET sequencer_id=%i WHERE id=%i" % (external_service_id, request_type_id)
        migrate_engine.execute(cmd)

    # remove the 'request_type_external_service_association' table
    RequestTypeExternalServiceAssociation_table = Table("request_type_external_service_association", metadata, autoload=True)
    drop_table(RequestTypeExternalServiceAssociation_table)

    # rename 'external_service_type_id' column to 'sequencer_type_id' in the table 'sequencer'
    # create the column 'sequencer_type_id'
    Sequencer_table = Table("sequencer", metadata, autoload=True)
    col = Column("sequencer_type_id", TrimmedString(255))  # should also have nullable=False
    add_column(col, Sequencer_table)

    # populate this new column
    cmd = "UPDATE sequencer SET sequencer_type_id=external_service_type_id"
    migrate_engine.execute(cmd)

    # remove the 'external_service_type_id' column
    drop_column('external_service_type_id', Sequencer_table)

    # drop the 'external_service_id' column in the 'sample_dataset' table
    drop_column('external_service_id', 'sample_dataset', metadata)
