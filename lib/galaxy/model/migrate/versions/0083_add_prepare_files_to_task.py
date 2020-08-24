"""
Migration script to add 'prepare_input_files_cmd' column to the task table and to rename a column.
"""

import logging

from sqlalchemy import Column, MetaData, String, Table, TEXT

from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    task_table = Table("task", metadata, autoload=True)
    c = Column("prepare_input_files_cmd", TEXT, nullable=True)
    add_column(c, task_table, metadata)

    c = Column("working_directory", String(1024), nullable=True)
    add_column(c, task_table, metadata)

    # remove the 'part_file' column - nobody used tasks before this, so no data needs to be migrated
    drop_column('part_file', task_table)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    task_table = Table("task", metadata, autoload=True)
    c = Column("part_file", String(1024), nullable=True)
    add_column(c, task_table, metadata)

    drop_column('working_directory', task_table)
    drop_column('prepare_input_files_cmd', task_table)
