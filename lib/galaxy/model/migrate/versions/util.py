import hashlib
import logging

from sqlalchemy import (
    BLOB,
    Index,
    Table,
    Text
)
from sqlalchemy.dialects.mysql import MEDIUMBLOB

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
        return "nextval('{}_{}_seq')".format(table, col)
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


def truncate_index_name(index_name, engine):
    # does what sqlalchemy does, see https://github.com/sqlalchemy/sqlalchemy/blob/8455a11bcc23e97afe666873cd872b0f204848d8/lib/sqlalchemy/sql/compiler.py#L4696
    max_index_name_length = engine.dialect.max_index_name_length or engine.dialect.max_identifier_length
    if len(index_name) > max_index_name_length:
        suffix = hashlib.md5(index_name.encode('utf-8')).hexdigest()[-4:]
        index_name = "{trunc}_{suffix}".format(trunc=index_name[0 : max_index_name_length - 8], suffix=suffix)
    return index_name


def create_table(table):
    try:
        table.create()
    except Exception:
        log.exception("Creating table '%s' failed.", table)


def drop_table(table, metadata=None):
    """
    :param table: Table to drop
    :type table: :class:`Table` or str
    """
    try:
        if not isinstance(table, Table):
            assert metadata is not None
            table = Table(table, metadata, autoload=True)
        table.drop()
    except Exception:
        log.exception("Dropping table '%s' failed.", table)


def add_column(column, table, metadata, **kwds):
    """
    :param table: Table to add the column to
    :type table: :class:`Table` or str

    :type metadata: :class:`Metadata`
    """
    try:
        index_to_create = None
        migrate_engine = metadata.bind
        if not isinstance(table, Table):
            table = Table(table, metadata, autoload=True)
        if migrate_engine.name == 'sqlite' and column.index and column.foreign_keys:
            # SQLAlchemy Migrate has a bug when adding a column with both a
            # ForeignKey and an index in SQLite. Since SQLite creates an index
            # anyway, we can drop the explicit index creation.
            # TODO: this is hacky, but it solves this^ problem. Needs better solution.
            index_to_create = (kwds['index_name'], table, column.name)
            del kwds['index_name']
            column.index = False
        column.create(table, **kwds)
        assert column is table.c[column.name]
        if index_to_create:
            add_index(*index_to_create)
    except Exception:
        log.exception("Adding column '%s' to table '%s' failed.", column, table)


def alter_column(column_name, table, metadata=None, **kwds):
    """
    :param table: Table to alter
    :type table: :class:`Table` or str

    :param metadata: Needed only if ``table`` is a table name
    :type metadata: :class:`Metadata`
    """
    try:
        if not isinstance(table, Table):
            assert metadata is not None
            table = Table(table, metadata, autoload=True)
        column = table.c[column_name]
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
        column = table.c[column_name]
        column.drop()
    except Exception:
        log.exception("Dropping column '%s' from table '%s' failed.", column_name, table)


def add_index(index_name, table, column_name, metadata=None, **kwds):
    """
    :param table: Table to add the index to
    :type table: :class:`Table` or str

    :param metadata: Needed only if ``table`` is a table name
    :type metadata: :class:`Metadata`
    """
    try:
        if not isinstance(table, Table):
            assert metadata is not None
            table = Table(table, metadata, autoload=True)
        index_name = truncate_index_name(index_name, table.metadata.bind)
        if index_name not in [ix.name for ix in table.indexes]:
            column = table.c[column_name]
            # MySQL cannot index a TEXT/BLOB column without specifying mysql_length
            if isinstance(column.type, (BLOB, MEDIUMBLOB, Text)):
                kwds.setdefault('mysql_length', 200)
            index = Index(index_name, column, **kwds)
            index.create()
        else:
            log.debug("Index '%s' on column '%s' in table '%s' already exists.", index_name, column_name, table)
    except Exception:
        log.exception("Adding index '%s' on column '%s' to table '%s' failed.", index_name, column_name, table)


def drop_index(index, table, column_name=None, metadata=None):
    """
    :param index: Index to drop
    :type index: :class:`Index` or str

    :param table: Table to drop the index from
    :type table: :class:`Table` or str

    :param metadata: Needed only if ``table`` is a table name
    :type metadata: :class:`Metadata`
    """
    try:
        if not isinstance(index, Index):
            if not isinstance(table, Table):
                assert metadata is not None
                table = Table(table, metadata, autoload=True)
            index_name = truncate_index_name(index, table.metadata.bind)
            if index_name in [ix.name for ix in table.indexes]:
                index = Index(index_name, table.c[column_name])
            else:
                log.debug("Index '%s' in table '%s' does not exist.", index, table)
                return
        index.drop()
    except Exception:
        log.exception("Dropping index '%s' from table '%s' failed", index, table)
