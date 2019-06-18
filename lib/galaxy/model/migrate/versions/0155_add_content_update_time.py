"""
Adds trigger to dataset table to update history.update_time when
contents are changed.
"""
from __future__ import print_function

import datetime
import logging

from sqlalchemy import DDL, MetaData

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_update_trigger(migrate_engine)
    install_update_trigger(migrate_engine)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()
    drop_update_trigger(migrate_engine)


def not_pg(self, target, bind, state, **kw):
    return bind.engine.name != 'postgresql'


def install_update_trigger(migrate_engine):
    """Installs trigger on database table to update history table
    when contents have changed. Installs a function and a trigger
    for postgres, other sql variants only require the trigger def
    """

    pg_create_trigger = DDL("""
        CREATE FUNCTION update_history_content_update_time()
            RETURNS trigger
            LANGUAGE 'plpgsql'
        AS $BODY$
        begin
            update history h
            set update_time = current_timestamp
            from history_dataset_association hda
            where h.id = hda.history_id
            and hda.dataset_id = NEW.id;
            return NEW;
        end;
        $BODY$;
        CREATE TRIGGER update_history_update_time
            BEFORE INSERT OR DELETE OR UPDATE
            ON dataset
            FOR EACH ROW
            EXECUTE PROCEDURE update_history_content_update_time();
    """).execute_if(dialect='postgresql')

    pg_create_trigger.execute(bind=migrate_engine)

    # Looks like sqlite doesn't like multiple actions in some
    # variants, so we build 3 triggers
    build_trigger('INSERT').execute(bind=migrate_engine)
    build_trigger('UPDATE').execute(bind=migrate_engine)
    build_trigger('DELETE').execute(bind=migrate_engine)


def drop_update_trigger(migrate_engine):
    """Drops trigger on dataset table."""

    pg_drop_trigger = DDL("""
        DROP TRIGGER IF EXISTS update_history_update_time ON dataset;
        DROP FUNCTION IF EXISTS update_history_content_update_time();
    """).execute_if(dialect='postgresql')

    pg_drop_trigger.execute(bind=migrate_engine)
    build_drop_trigger("INSERT").execute(bind=migrate_engine)
    build_drop_trigger("UPDATE").execute(bind=migrate_engine)
    build_drop_trigger("DELETE").execute(bind=migrate_engine)


def build_trigger(op):
    create_trigger_template = """
        CREATE TRIGGER BEFORE_{operation}_DATASET
            BEFORE {operation} ON dataset
            BEGIN
                update history
                set update_time = current_timestamp
                where id in (
                    select hda.history_id
                    from history_dataset_association as hda
                    where hda.dataset_id = {rowset}.id
                );
            END;
    """
    rs = 'OLD' if op == 'DELETE' else 'NEW'
    sql = create_trigger_template.format(operation=op,rowset=rs)
    return DDL(sql).execute_if(callable_=not_pg)


def build_drop_trigger(op):
    trigger_template = """DROP TRIGGER IF EXISTS BEFORE_{operation}_DATASET;"""
    sql = trigger_template.format(operation=op)
    return DDL(sql).execute_if(callable_=not_pg)

