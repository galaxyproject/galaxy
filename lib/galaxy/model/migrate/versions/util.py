import logging

from sqlalchemy import Table

log = logging.getLogger(__name__)


def engine_false(migrate_engine):
    if migrate_engine.name in ['postgres', 'postgresql']:
        return "FALSE"
    elif migrate_engine.name in ['mysql', 'sqlite']:
        return 0
    else:
        raise Exception('Unknown database type: %s' % migrate_engine.name)


def engine_true(migrate_engine):
    if migrate_engine.name in ['postgres', 'postgresql']:
        return "TRUE"
    elif migrate_engine.name in ['mysql', 'sqlite']:
        return 1
    else:
        raise Exception('Unknown database type: %s' % migrate_engine.name)


def nextval(migrate_engine, table, col='id'):
    if migrate_engine.name in ['postgres', 'postgresql']:
        return "nextval('%s_%s_seq')" % (table, col)
    elif migrate_engine.name in ['mysql', 'sqlite']:
        return "null"
    else:
        raise Exception('Unable to convert data for unknown database type: %s' % migrate_engine.name)


def localtimestamp(migrate_engine):
    if migrate_engine.name in ['mysql', 'postgres', 'postgresql']:
        return "LOCALTIMESTAMP"
    elif migrate_engine.name == 'sqlite':
        return "current_date || ' ' || current_time"
    else:
        raise Exception('Unable to convert data for unknown database type: %s' % migrate_engine.name)


def create_table(table):
    try:
        table.create()
    except Exception:
        log.exception("Creating table '%s' failed.", table)


def drop_table(table):
    try:
        table.drop()
    except Exception:
        log.exception("Dropping table '%s' failed.", table)


def add_column(column, table, metadata=None, **kwds):
    """
    :param table: Table to add the column to
    :type table: :class:`Table` or str

    :param metadata: Needed only if ``table`` is a table name
    :type metadata: :class:`Metadata`
    """
    try:
        if not isinstance(table, Table):
            assert metadata is not None
            table = Table(table, metadata, autoload=True)
        column.create(table, **kwds)
        assert column is getattr(table.c, column.name)
    except Exception:
        log.exception("Adding column '%s' to table '%s' failed.", column, table)


def alter_column(column_name, table, metadata=None, **kwds):
    """
    :param table: Table to drop the column from
    :type table: :class:`Table` or str

    :param metadata: Needed only if ``table`` is a table name
    :type metadata: :class:`Metadata`
    """
    try:
        if not isinstance(table, Table):
            assert metadata is not None
            table = Table(table, metadata, autoload=True)
        column = getattr(table.c, column_name)
        column.alter(**kwds)
    except Exception:
        log.exception("Modifying column '%s' of table '%s' failed.", column_name, table)


def drop_column(column_name, table, metadata=None):
    """
    :param table: Table to drop the column from
    :type table: :class:`Table` or str

    :param metadata: Needed only if ``table`` is a table name
    :type metadata: :class:`Metadata`
    """
    try:
        if not isinstance(table, Table):
            assert metadata is not None
            table = Table(table, metadata, autoload=True)
        column = getattr(table.c, column_name)
        column.drop()
    except Exception:
        log.exception("Dropping column '%s' from table '%s' failed.", column_name, table)
