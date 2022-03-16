from sqlalchemy import DDL


def execute_statements(engine, raw_sql):
    statements = raw_sql if isinstance(raw_sql, list) else [raw_sql]
    with engine.begin() as connection:
        for sql in statements:
            cmd = DDL(sql)
            connection.execute(cmd)
