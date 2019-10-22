"""
Adds timestamps to hdac table. Adds triggers to dataset, hda, hdac tables
to update history.update_time when contents are changed.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import Column, DateTime, DDL, MetaData, Table

from galaxy.model.migrate.versions.util import add_column, drop_column

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    create_timestamps(metadata, "history_dataset_collection_association")
    drop_update_trigger(migrate_engine)
    install_update_trigger(migrate_engine)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_update_trigger(migrate_engine)
    drop_timestamps(metadata, "history_dataset_collection_association")


def install_update_trigger(migrate_engine):
    """Installs trigger on dataset table to update history table
    when contents have changed. Installs a function and a trigger
    for postgres, other sql variants only require the trigger def
    """

    if migrate_engine.name in ['postgres', 'postgresql']:
        pg_create_trigger = DDL("""
            CREATE FUNCTION update_hda_update_time()
                RETURNS trigger
                LANGUAGE 'plpgsql'
            AS $BODY$
            BEGIN
                UPDATE history_dataset_association hda
                SET update_time = (now() at time zone 'utc')
                WHERE hda.dataset_id = NEW.id;
                RETURN NEW;
            END;
            $BODY$;

            CREATE FUNCTION update_history_update_time()
                RETURNS trigger
                LANGUAGE 'plpgsql'
            AS $BODY$
            BEGIN
                UPDATE history h
                SET update_time = (now() at time zone 'utc')
                WHERE h.id = NEW.history_id;
                RETURN NEW;
            END;
            $BODY$;

            CREATE TRIGGER trigger_dataset_aidur
                AFTER INSERT OR DELETE OR UPDATE
                ON dataset
                FOR EACH ROW
                EXECUTE PROCEDURE update_hda_update_time();

            CREATE TRIGGER trigger_hda_aidur
                AFTER INSERT OR DELETE OR UPDATE
                ON history_dataset_association
                FOR EACH ROW
                EXECUTE PROCEDURE update_history_update_time();

            CREATE TRIGGER trigger_hdca_aidur
                AFTER INSERT OR DELETE OR UPDATE
                ON history_dataset_collection_association
                FOR EACH ROW
                EXECUTE PROCEDURE update_history_update_time();
        """)
        pg_create_trigger.execute(bind=migrate_engine)
    else:
        install_trigger('INSERT', migrate_engine)
        install_trigger('UPDATE', migrate_engine)
        install_trigger('DELETE', migrate_engine)


def drop_update_trigger(migrate_engine):
    """Drops trigger on dataset table."""

    if migrate_engine.name in ['postgres', 'postgresql']:
        drop_trigger_stmt = """
            DROP TRIGGER IF EXISTS trigger_hdca_aidur ON history_dataset_collection_association;
            DROP TRIGGER IF EXISTS trigger_hda_aidur ON history_dataset_association;
            DROP TRIGGER IF EXISTS trigger_dataset_aidur ON dataset;
            DROP FUNCTION IF EXISTS update_hda_update_time();
            DROP FUNCTION IF EXISTS update_history_update_time();
        """
        pg_drop_trigger = DDL(drop_trigger_stmt)
        pg_drop_trigger.execute(bind=migrate_engine)
    else:
        build_drop_trigger('INSERT', migrate_engine)
        build_drop_trigger('UPDATE', migrate_engine)
        build_drop_trigger('DELETE', migrate_engine)


def install_trigger(op, migrate_engine):
    """Installs a single trigger"""

    dataset_trigger = """
        CREATE TRIGGER trigger_dataset_a{op_initial}r
            AFTER {operation}
            ON dataset
            FOR EACH ROW
            BEGIN
                UPDATE history_dataset_association
                SET update_time = current_timestamp
                WHERE dataset_id = {rowset}.id;
            END;
    """

    hda_trigger = """
        CREATE TRIGGER trigger_hda_a{op_initial}r
            AFTER {operation}
            ON history_dataset_association
            FOR EACH ROW
            BEGIN
                UPDATE history
                SET update_time = current_timestamp
                WHERE id = {rowset}.history_id;
            END;
    """

    hdca_trigger = """
        CREATE TRIGGER trigger_hdca_a{op_initial}r
            AFTER {operation}
            ON history_dataset_collection_association
            FOR EACH ROW
            BEGIN
                UPDATE history
                SET update_time = current_timestamp
                WHERE id = {rowset}.history_id;
            END;
    """

    statements = [
        dataset_trigger,
        hda_trigger,
        hdca_trigger
    ]

    rs = 'OLD' if op == 'DELETE' else 'NEW'

    for statement in statements:
        sql = statement.format(operation=op, rowset=rs, op_initial=op.lower()[0])
        create_trigger = DDL(sql)
        create_trigger.execute(bind=migrate_engine)


def build_drop_trigger(op, migrate_engine):
    statements = [
        "DROP TRIGGER IF EXISTS trigger_dataset_a{op_initial}r;",
        "DROP TRIGGER IF EXISTS trigger_hdca_a{op_initial}r;",
        "DROP TRIGGER IF EXISTS trigger_hda_a{op_initial}r;"
    ]

    for statement in statements:
        sql = statement.format(op_initial=op.lower()[0])
        drop_trigger = DDL(sql)
        drop_trigger.execute(bind=migrate_engine)


def create_timestamps(metadata, table_name):
    now = datetime.datetime.utcnow
    create_time_column = Column("create_time", DateTime, default=now)
    update_time_column = Column("update_time", DateTime, default=now, onupdate=now)
    target_table = Table(table_name, metadata, autoload=True)
    add_column(create_time_column, target_table, metadata)
    add_column(update_time_column, target_table, metadata)


def drop_timestamps(metadata, table_name):
    target_table = Table(table_name, metadata, autoload=True)
    drop_column("create_time", target_table)
    drop_column("update_time", target_table)
