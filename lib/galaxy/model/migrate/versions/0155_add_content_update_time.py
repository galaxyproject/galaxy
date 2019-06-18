"""
Adds trigger to dataset table to update history.update_time when 
contents are changed.
"""

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

    pg_create_function = DDL("""
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
    """).execute_if(dialect='postgresql')

    pg_create_trigger = DDL("""
        CREATE TRIGGER update_history_update_time
            BEFORE INSERT OR DELETE OR UPDATE 
            ON dataset
            FOR EACH ROW
            EXECUTE PROCEDURE update_history_content_update_time();
    """).execute_if(dialect='postgresql')

    trigger = DDL("""
        CREATE TRIGGER dataset_history_update_time 
            BEFORE INSERT OR DELETE OR UPDATE 
            ON dataset
            FOR EACH ROW
            BEGIN
                update history h
                set update_time = now()
                from history_dataset_association hda
                where h.id = hda.history_id
                and hda.dataset_id = NEW.id;
            END;
    """).execute_if(callable_=not_pg)

    pg_create_function.execute(bind=migrate_engine)
    pg_create_trigger.execute(bind=migrate_engine)
    trigger.execute(bind=migrate_engine)


def drop_update_trigger(migrate_engine):
    """Drops trigger on dataset table. Also removes associated function
    for postgres sql variants.
    """

    pg_drop_trigger = DDL("""
        DROP TRIGGER IF EXISTS update_history_update_time ON dataset;
        DROP FUNCTION IF EXISTS update_history_content_update_time();
    """).execute_if(dialect='postgresql')

    drop_trigger = DDL("""
        DROP TRIGGER IF EXISTS dataset_history_update_time;
    """).execute_if(callable_=not_pg)

    pg_drop_trigger.execute(bind=migrate_engine)
    drop_trigger.execute(bind=migrate_engine)
