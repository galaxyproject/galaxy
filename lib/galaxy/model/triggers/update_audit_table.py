from galaxy.model.triggers.utils import execute_statements

# function name prefix
fn_prefix = "fn_audit_history_by"

# map between source table and associated incoming id field
trigger_config = {
    "history_dataset_association": "history_id",
    "history_dataset_collection_association": "history_id",
    "history": "id",
}


def install(engine):
    """Install history audit table triggers"""
    sql = _postgres_install(engine) if "postgres" in engine.name else _sqlite_install()
    execute_statements(engine, sql)


def remove(engine):
    """Uninstall history audit table triggers"""
    sql = _postgres_remove() if "postgres" in engine.name else _sqlite_remove()
    execute_statements(engine, sql)


# Postgres trigger installation


def _postgres_remove():
    """postgres trigger removal sql"""

    sql = []
    sql.append(f"DROP FUNCTION IF EXISTS {fn_prefix}_history_id() CASCADE;")
    sql.append(f"DROP FUNCTION IF EXISTS {fn_prefix}_id() CASCADE;")

    return sql


def _postgres_install(engine):
    """postgres trigger installation sql"""

    sql = []

    # postgres trigger function template
    # need to make separate functions purely because the incoming history_id field name will be
    # different for different source tables. There may be a fancier way to dynamically choose
    # between incoming fields, but having 2 triggers fns seems straightforward

    def statement_trigger_fn(id_field):
        fn = f"{fn_prefix}_{id_field}"

        return f"""
            CREATE OR REPLACE FUNCTION {fn}()
                RETURNS TRIGGER
                LANGUAGE 'plpgsql'
            AS $BODY$
                BEGIN
                    INSERT INTO history_audit (history_id, update_time)
                    SELECT DISTINCT {id_field}, CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                    FROM new_table
                    WHERE {id_field} IS NOT NULL
                    ON CONFLICT DO NOTHING;
                    RETURN NULL;
                END;
            $BODY$
        """

    def row_trigger_fn(id_field):
        fn = f"{fn_prefix}_{id_field}"

        return f"""
            CREATE OR REPLACE FUNCTION {fn}()
                RETURNS TRIGGER
                LANGUAGE 'plpgsql'
            AS $BODY$
                BEGIN
                    INSERT INTO history_audit (history_id, update_time)
                    VALUES (NEW.{id_field}, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                    ON CONFLICT DO NOTHING;
                    RETURN NULL;
                END;
            $BODY$
        """

    def statement_trigger_def(source_table, id_field, operation, when="AFTER", function_keyword="FUNCTION"):
        fn = f"{fn_prefix}_{id_field}"

        # Postgres supports many triggers per operation/table so the label can
        # be indicative of what's happening
        label = f"history_audit_by_{id_field}"
        trigger_name = get_trigger_name(label, operation, when, statement=True)

        return f"""
            CREATE TRIGGER {trigger_name}
            {when} {operation} ON {source_table}
            REFERENCING NEW TABLE AS new_table
            FOR EACH STATEMENT EXECUTE {function_keyword} {fn}();
        """

    def row_trigger_def(source_table, id_field, operation, when="AFTER", function_keyword="FUNCTION"):
        fn = f"{fn_prefix}_{id_field}"

        label = f"history_audit_by_{id_field}"
        trigger_name = get_trigger_name(label, operation, when, statement=True)

        return f"""
            CREATE TRIGGER {trigger_name}
            {when} {operation} ON {source_table}
            FOR EACH ROW
            WHEN (NEW.{id_field} IS NOT NULL)
            EXECUTE {function_keyword} {fn}();
        """

    # pick row or statement triggers depending on postgres version
    version = engine.dialect.server_version_info[0]
    trigger_fn = statement_trigger_fn if version > 10 else row_trigger_fn
    trigger_def = statement_trigger_def if version > 10 else row_trigger_def
    # In the syntax of CREATE TRIGGER, the keywords FUNCTION and PROCEDURE are equivalent,
    # but the referenced function must in any case be a function, not a procedure.
    # The use of the keyword PROCEDURE here is historical and deprecated (https://www.postgresql.org/docs/11/sql-createtrigger.html).
    function_keyword = "FUNCTION" if version > 10 else "PROCEDURE"

    for id_field in ["history_id", "id"]:
        sql.append(trigger_fn(id_field))

    for source_table, id_field in trigger_config.items():
        for operation in ["UPDATE", "INSERT"]:
            sql.append(trigger_def(source_table, id_field, operation, function_keyword=function_keyword))

    return sql


def _sqlite_remove():
    sql = []

    for source_table in trigger_config:
        for operation in ["UPDATE", "INSERT"]:
            trigger_name = get_trigger_name(source_table, operation, "AFTER")
            sql.append(f"DROP TRIGGER IF EXISTS {trigger_name};")

    return sql


def _sqlite_install():
    # delete old stuff first
    sql = _sqlite_remove()

    def trigger_def(source_table, id_field, operation, when="AFTER"):

        # only one trigger per operation/table in simple databases, so
        # trigger name is less descriptive
        trigger_name = get_trigger_name(source_table, operation, when)

        return f"""
            CREATE TRIGGER {trigger_name}
                {when} {operation}
                ON {source_table}
                FOR EACH ROW
                BEGIN
                    INSERT INTO history_audit (history_id, update_time)
                    SELECT NEW.{id_field}, strftime('%%Y-%%m-%%d %%H:%%M:%%f', 'now')
                    WHERE NEW.{id_field} IS NOT NULL;
                END;
        """

    for source_table, id_field in trigger_config.items():
        for operation in ["UPDATE", "INSERT"]:
            sql.append(trigger_def(source_table, id_field, operation))

    return sql


def get_trigger_name(label, operation, when, statement=False):
    op_initial = operation.lower()[0]
    when_initial = when.lower()[0]
    rs = "s" if statement else "r"
    return f"trigger_{label}_{when_initial}{op_initial}{rs}"
