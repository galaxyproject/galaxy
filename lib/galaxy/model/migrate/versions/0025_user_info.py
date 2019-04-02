"""
This script adds a foreign key to the form_values table in the galaxy_user table
"""
from __future__ import print_function

import logging
import sys

from migrate import ForeignKeyConstraint
from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.exc import NoSuchTableError

from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)

metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    try:
        User_table = Table("galaxy_user", metadata, autoload=True)
    except NoSuchTableError:
        User_table = None
        log.debug("Failed loading table galaxy_user")
    if User_table is not None:
        col = Column("form_values_id", Integer, index=True)
        add_column(col, User_table, index_name='ix_user_form_values_id')
        try:
            FormValues_table = Table("form_values", metadata, autoload=True)
        except NoSuchTableError:
            FormValues_table = None
            log.debug("Failed loading table form_values")
        if migrate_engine.name != 'sqlite':
            # Add 1 foreign key constraint to the galaxy_user table
            if User_table is not None and FormValues_table is not None:
                try:
                    cons = ForeignKeyConstraint([User_table.c.form_values_id],
                                                [FormValues_table.c.id],
                                                name='user_form_values_id_fk')
                    # Create the constraint
                    cons.create()
                except Exception:
                    log.exception("Adding foreign key constraint 'user_form_values_id_fk' to table 'galaxy_user' failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('form_values_id', 'galaxy_user', metadata)
