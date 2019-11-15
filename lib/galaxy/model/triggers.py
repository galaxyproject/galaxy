"""
Database trigger installation and removal
"""

from sqlalchemy import DDL


def install_timestamp_triggers(engine):
    """Install update_time propagation triggers for history data tables"""
    statements = get_timestamp_install_sql(engine.name)
    execute_statements(engine, statements)


def drop_timestamp_triggers(engine):
    """Remove update_time propagation triggers for historydata tables"""
    statements = get_timestamp_drop_sql(engine.name)
    execute_statements(engine, statements)


def execute_statements(engine, statements):
    for sql in statements:
        cmd = DDL(sql)
        cmd.execute(bind=engine)


def get_timestamp_install_sql(variant):
    """Generate a list of sql statements for insalllation of timetamp triggers"""

    sql = get_timestamp_drop_sql(variant)

    if 'postgres' in variant:
        # Postgres has a separate function definition and a trigger
        # assignment. The first two statements the functions, and
        # the later assign those functions to triggers on tables

        fn_name = 'update_history_update_time'
        sql.append(build_pg_timestamp_fn(fn_name, 'history', source_key='history_id'))
        sql.append(build_pg_trigger('history_dataset_association', fn_name))
        sql.append(build_pg_trigger('history_dataset_collection_association', fn_name))

    else:
        # Other database variants are more granular. Requiring separate
        # statements for INSERT/UPDATE/DELETE, and the body of the trigger
        # is not necessarily reusable with a function

        for operation in ['INSERT', 'UPDATE', 'DELETE']:

            # change hda -> update history
            sql.append(build_timestamp_trigger(
                operation, 'history_dataset_association', 'history',
                source_key='history_id'))

            # change hdca -> update history
            sql.append(build_timestamp_trigger(
                operation, 'history_dataset_collection_association', 'history',
                source_key='history_id'))

    return sql


def get_timestamp_drop_sql(variant):
    """generate a list of statements to drop the timestammp update triggers"""

    sql = []

    if 'postgres' in variant:
        sql.append("DROP FUNCTION IF EXISTS update_history_update_time() CASCADE;")
    else:
        for operation in ['INSERT', 'UPDATE', 'DELETE']:
            sql.append(build_drop_trigger(operation, 'history_dataset_association'))
            sql.append(build_drop_trigger(operation, 'history_dataset_collection_association'))

    return sql


def build_pg_timestamp_fn(fn_name, table_name, local_key='id', source_key='id', stamp_column='update_time'):
    """Generates a postgres history update timestamp function"""

    sql = """
        CREATE OR REPLACE FUNCTION {fn_name}()
            RETURNS trigger
            LANGUAGE 'plpgsql'
        AS $BODY$
            BEGIN
                IF (TG_OP = 'DELETE') THEN
                    UPDATE {table_name}
                    SET {stamp_column} = (now() at time zone 'utc')
                    WHERE {local_key} = OLD.{source_key};
                    RETURN OLD;
                ELSEIF (TG_OP = 'UPDATE') THEN
                    UPDATE {table_name}
                    SET {stamp_column} = (now() at time zone 'utc')
                    WHERE {local_key} = NEW.{source_key} OR {local_key} = OLD.{source_key};
                    RETURN NEW;
                ELSIF (TG_OP = 'INSERT') THEN
                    UPDATE {table_name}
                    SET {stamp_column} = (now() at time zone 'utc')
                    WHERE {local_key} = NEW.{source_key};
                    RETURN NEW;
                END IF;
            END;
        $BODY$;
    """
    return sql.format(**locals())


def build_pg_trigger(table_name, fn_name):
    """assigns a postgres trigger to indicated table, calling user-defined function"""

    trigger_name = "trigger_{table_name}_biudr".format(**locals())
    tmpl = """
        CREATE TRIGGER {trigger_name}
            BEFORE INSERT OR DELETE OR UPDATE
            ON {table_name}
            FOR EACH ROW
            EXECUTE PROCEDURE {fn_name}();
    """
    return tmpl.format(**locals())


def build_timestamp_trigger(operation, source_table, target_table, source_key='id', target_key='id', when='BEFORE'):
    """creates a non-postgres update_time trigger"""

    trigger_name = get_trigger_name(operation, source_table, when)

    # three different update clauses depending on update/insert/delete
    clause = ""
    if operation == "DELETE":
        clause = "{target_key} = OLD.{source_key}"
    elif operation == "UPDATE":
        clause = "{target_key} = NEW.{source_key} OR {target_key} = OLD.{source_key}"
    else:
        clause = "{target_key} = NEW.{source_key}"
    clause = clause.format(**locals())

    tmpl = """
        CREATE TRIGGER {trigger_name}
            {when} {operation}
            ON {source_table}
            FOR EACH ROW
            BEGIN
                UPDATE {target_table}
                SET update_time = current_timestamp
                WHERE {clause};
            END;
    """
    return tmpl.format(**locals())


def build_drop_trigger(operation, source_table, when='BEFORE'):
    """drops a non-postgres trigger by name"""
    trigger_name = get_trigger_name(operation, source_table, when)
    return "DROP TRIGGER IF EXISTS {trigger_name}".format(**locals())


def get_trigger_name(operation, source_table, when='BEFORE'):
    """non-postgres trigger name"""
    op_initial = operation.lower()[0]
    when_initial = when.lower()[0]
    trigger_name = "trigger_{source_table}_{when_initial}{op_initial}r".format(**locals())
    return trigger_name
