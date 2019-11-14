"""
Database trigger installation and removal
"""

from sqlalchemy import DDL


def install_timestamp_triggers(engine):
    """Install update_time propagation triggers for history data tables"""
    sql = get_install_trigger_sql(engine.name)
    drop_timestamp_triggers(engine)
    execute_statements(engine, sql)


def drop_timestamp_triggers(engine):
    """Remove update_time propagation triggers for historydata tables"""
    sql = get_drop_trigger_sql(engine.name)
    execute_statements(engine, sql)


def execute_statements(engine, statements):
    for statement in statements:
        cmd = DDL(statement)
        cmd.execute(bind=engine)


def get_install_trigger_sql(variant):
    """Build statements to install timestamp triggers"""

    sql = []

    if variant in ['postgres', 'postgresql']:
        """Postgres has a separate function definition and a trigger
        assignment. The first two statements the functions, and
        the later assign those functions to triggers on tables"""

        # function: history trigger function
        sql.append(build_pg_timestamp_func('update_history_update_time', 'history', new_key='history_id'))

        # function: hda trigger function
        sql.append(build_pg_timestamp_func('update_hda_update_time', 'history_dataset_association', local_key='dataset_id'))

        # trigger: changes to datasets -> update hda
        sql.append(build_pg_trigger('trigger_dataset_bidur', 'dataset', 'update_hda_update_time'))

        # trigger: changes to hda -> update history
        sql.append(build_pg_trigger('trigger_hda_bidur', 'history_dataset_association', 'update_history_update_time'))

        # trigger: change hdca -> update history
        sql.append(build_pg_trigger('trigger_hdca_bidur', 'history_dataset_collection_association', 'update_history_update_time'))

    else:
        """Other database variants are more granular. Requiring separate
        statements for INSERT/UPDATE/DELETE, and the body of the trigger
        is not necessarily reusable with a function"""

        for operation in ['INSERT', 'UPDATE', 'DELETE']:

            # change dataset -> update hda
            sql.append(build_timestamp_trigger(
                operation, 'dataset', 'history_dataset_association',
                target_key='dataset_id'))

            # change hda -> update history
            sql.append(build_timestamp_trigger(
                operation, 'history_dataset_association', 'history',
                source_key='history_id'))

            # change hdca -> update history
            sql.append(build_timestamp_trigger(
                operation, 'history_dataset_collection_association', 'history',
                source_key='history_id'))

    return sql


def build_pg_timestamp_func(fn_name, table_name, local_key='id', new_key='id'):
    """creates a postgres timestamp trigger function"""

    tmpl = """
        CREATE OR REPLACE FUNCTION {fn_name}()
            RETURNS trigger
            LANGUAGE 'plpgsql'
        AS $BODY$
            BEGIN
                UPDATE {table_name}
                SET update_time = (now() at time zone 'utc')
                WHERE {local_key} = NEW.{new_key}
                AND update_time < (now() at time zone 'utc');
                RETURN NEW;
            END;
        $BODY$;
    """

    return tmpl.format(**locals())


def build_pg_trigger(trigger_name, table_name, fn_name, when='BEFORE'):
    """creates a postgres trigger"""

    tmpl = """
        CREATE TRIGGER {trigger_name}
            {when} INSERT OR DELETE OR UPDATE
            ON {table_name}
            FOR EACH ROW
            EXECUTE PROCEDURE {fn_name}();
    """

    return tmpl.format(**locals())


def build_timestamp_trigger(operation, source_table, target_table, source_key='id', target_key='id', when='BEFORE'):
    """creates a non-postgres update_time trigger"""

    op_initial = operation.lower()[0]
    when_initial = when.lower()[0]
    rowset = 'OLD' if operation == 'DELETE' else 'NEW'

    tmpl = """
        CREATE TRIGGER trigger_{source_table}_{when_initial}{op_initial}r
            {when} {operation}
            ON {source_table}
            FOR EACH ROW
            BEGIN
                UPDATE {target_table}
                SET update_time = current_timestamp
                WHERE {target_key} = {rowset}.{source_key};
            END;
    """

    return tmpl.format(**locals())


def get_drop_trigger_sql(variant):
    """For use in migrations, creates drop statements when uninstalling triggers"""

    sql = []

    if variant in ['postgres', 'postgresql']:
        sql.append("DROP FUNCTION IF EXISTS update_hda_update_time() CASCADE;")
        sql.append("DROP FUNCTION IF EXISTS update_history_update_time() CASCADE;")
    else:
        for operation in ['INSERT', 'UPDATE', 'DELETE']:
            sql.append(build_drop_trigger(operation, "dataset"))
            sql.append(build_drop_trigger(operation, "history_dataset_association"))
            sql.append(build_drop_trigger(operation, "history_dataset_collection_association"))

    return sql


def build_drop_trigger(operation, source_table, when='BEFORE'):
    """drops a non-postgres trigger by name"""
    op_initial = operation.lower()[0]
    when_initial = when.lower()[0]
    tmpl = "DROP TRIGGER IF EXISTS trigger_{source_table}_{when_initial}{op_initial}r"
    return tmpl.format(**locals())
