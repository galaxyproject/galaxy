"""
Database trigger installation and removal

Recommended trigger naming convention: tr_{table name}_{when}_{operation}_{action details}, where:
    table_name: table on which the trigger is created
    when: b|a|i for before, after, or instead of
    operation: i|u|d for insert, update, or delete
    action details: specify what the trigger does
"""

from sqlalchemy import DDL


def create_triggers(engine):
    DatasetJobTrigger(engine).create()
    install_timestamp_triggers(engine)


class Trigger(object):
    """
    Base class for triggers. A concrete trigger class should extend this class and override
    the `get_sql_create_postgres_trigger()` and `get_sql_create_sqlite_trigger()` methods.
    """
    POSTGRES = 0
    SQLITE = 1

    def __init__(self, engine, table_name, trigger_name):
        self.engine = engine
        self.table = table_name
        self.trigger = trigger_name  # for postgres, used for both trigger and function name
        self._set_db_type()

    def create(self):
        if self.db == Trigger.POSTGRES:
            sql = self.get_sql_create_postgres_trigger()
        else:
            sql = self.get_sql_create_sqlite_trigger()
        self.engine.execute(sql)

    def drop(self):
        if self.db == Trigger.POSTGRES:
            sql = self.get_sql_drop_postgres_trigger()
        else:
            sql = self.get_sql_drop_sqlite_trigger()
        self.engine.execute(sql)

    def get_sql_create_postgres_trigger(self):
        raise Exception('Not implemented')

    def get_sql_create_sqlite_trigger(self):
        raise Exception('Not implemented')

    def get_sql_drop_postgres_trigger(self):
        sql = []
        sql.append('DROP TRIGGER IF EXISTS {trigger} on {table};'.format(
            trigger=self.trigger, table=self.table))
        sql.append('DROP FUNCTION IF EXISTS {trigger};'.format(trigger=self.trigger))
        return '\n'.join(sql)

    def get_sql_drop_sqlite_trigger(self):
        return 'DROP TRIGGER IF EXISTS {trigger};'.format(trigger=self.trigger)

    def _set_db_type(self):
        if self.engine.name in ['postgres', 'postgresql']:
            self.db = Trigger.POSTGRES
        elif self.engine.name in ['sqlite']:
            self.db = Trigger.SQLITE
        else:
            raise Exception('Unsupported database type: %s' % self.engine.name)


class DatasetJobTrigger(Trigger):
    """ Launches on job_to_output_dataset record creation. Populates job_id column in each
    output dataset following: job_to_output_dataset > history_dataset_association > dataset.

    Note: 'dataset' in job_to_output_dataset is a dataset instance, not a dataset, but it
    has a reference to a dataset, which is what we need.
    """

    def __init__(self, engine):
        super().__init__(engine, 'job_to_output_dataset', 'tr_job_to_output_dataset_ai_update_dataset')

    def get_sql_create_postgres_trigger(self):

        def get_function():
            sql = '''
                CREATE FUNCTION {trigger}() RETURNS trigger AS $$
                    BEGIN
                        UPDATE dataset d
                        SET
                            job_id = NEW.job_id
                        FROM history_dataset_association hda
                        WHERE NEW.dataset_id = hda.id AND hda.dataset_id = d.id;

                        RETURN NULL;
                    END;
                $$ LANGUAGE plpgsql;
            '''.format(trigger=self.trigger)
            return sql

        def get_trigger():
            sql = '''
                CREATE TRIGGER {trigger}
                    AFTER INSERT
                    ON {table}
                    FOR EACH ROW
                    EXECUTE FUNCTION {function}();
            '''.format(trigger=self.trigger, table=self.table, function=self.trigger)
            return sql

        sql = []
        sql.append(self.get_sql_drop_postgres_trigger())
        sql.append(get_function())
        sql.append(get_trigger())
        return '\n'.join(sql)

    def get_sql_create_sqlite_trigger(self):
        sql = '''
            CREATE TRIGGER IF NOT EXISTS {trigger}
                AFTER INSERT
                ON {table}
                FOR EACH ROW
                BEGIN
                    UPDATE dataset
                    SET
                        job_id = NEW.job_id
                    WHERE id IN (
                        SELECT hda.dataset_id FROM history_dataset_association hda
                        WHERE hda.id = NEW.dataset_id
                    );
                END;
        '''.format(trigger=self.trigger, table=self.table)
        return sql


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
