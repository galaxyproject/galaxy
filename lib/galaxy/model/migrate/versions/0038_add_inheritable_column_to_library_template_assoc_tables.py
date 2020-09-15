"""
Migration script to add an inheritable column to the following tables:
library_info_association, library_folder_info_association.
Also, in case of sqlite check if the previous migration script deleted the
request table and if so, restore the table.
"""

import datetime
import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, MetaData, Table, TEXT

from galaxy.model.custom_types import TrimmedString
from galaxy.model.migrate.versions.util import engine_false

now = datetime.datetime.utcnow
log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine

    # In case of sqlite, check if the previous migration script deleted the
    # request table and if so, restore the table.
    if migrate_engine.name == 'sqlite':
        if not migrate_engine.has_table('request'):
            # load the tables referenced in foreign keys
            metadata.reflect(only=['form_values', 'request_type', 'galaxy_user'])
            # create a temporary table
            Request_table = Table('request', metadata,
                                  Column("id", Integer, primary_key=True),
                                  Column("create_time", DateTime, default=now),
                                  Column("update_time", DateTime, default=now, onupdate=now),
                                  Column("name", TrimmedString(255), nullable=False),
                                  Column("desc", TEXT),
                                  Column("form_values_id", Integer, ForeignKey("form_values.id"), index=True),
                                  Column("request_type_id", Integer, ForeignKey("request_type.id"), index=True),
                                  Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True),
                                  Column("deleted", Boolean, index=True, default=False))
            try:
                Request_table.create()
            except Exception:
                log.exception("Creating request table failed.")

    metadata.reflect()
    try:
        LibraryInfoAssociation_table = Table("library_info_association", metadata, autoload=True)
        c = Column("inheritable", Boolean, index=True, default=False)
        c.create(LibraryInfoAssociation_table, index_name='ix_library_info_association_inheritable')
        assert c is LibraryInfoAssociation_table.c.inheritable
    except Exception:
        log.exception("Adding column 'inheritable' to 'library_info_association' table failed.")
    cmd = "UPDATE library_info_association SET inheritable = %s" % engine_false(migrate_engine)
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Setting value of column inheritable to false in library_info_association failed.")
    try:
        LibraryFolderInfoAssociation_table = Table("library_folder_info_association", metadata, autoload=True)
        c = Column("inheritable", Boolean, index=True, default=False)
        c.create(LibraryFolderInfoAssociation_table, index_name='ix_library_folder_info_association_inheritable')
        assert c is LibraryFolderInfoAssociation_table.c.inheritable
    except Exception:
        log.exception("Adding column 'inheritable' to 'library_folder_info_association' table failed.")
    cmd = "UPDATE library_folder_info_association SET inheritable = %s" % engine_false(migrate_engine)
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Setting value of column inheritable to false in library_folder_info_association failed.")


def downgrade(migrate_engine):
    pass
