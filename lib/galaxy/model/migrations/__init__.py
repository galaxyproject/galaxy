import logging
import os

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

from sqlalchemy import MetaData, Unicode

from sqlalchemy.types import TypeDecorator

from sqlalchemy_utils import (
    create_database,
    database_exists,
)

from galaxy.model.orm.engine_factory import build_engine


log = logging.getLogger(__name__)


ALEMBIC_TABLE = 'alembic_version'
MIGRATE_TABLE = 'migrate_version'
# sqlite does not work with 'default', 'key', 'unique', 'index', 'onupdate' column attributes
COLUMN_ATTRIBUTES_TO_VERIFY = ('name', 'primary_key', 'nullable')
TYPE_ATTRIBUTES_TO_VERIFY = ('length', 'precision', 'scale')
ALEMBIC_CONFIG_FILE = 'alembic.ini'
ALEMBIC_DIR = 'lib/galaxy/model/migrations/alembic'


def run(url, metadata, alembic_dir=None, engine_options=None, app=None,
        map_install_models=False, auto_migrate=False):
    """Handles the logic of verifying and modifying the database."""

    # Case 1: no database.
    if not database_exists(url):
        create_galaxy_database(url, app)

    # prevent redundant call to model.mapping.init()
    ts_metadata = None
    if map_install_models:
        from galaxy.model.tool_shed_install.mapping import metadata as ts_metadata  # noqa: F401

    alembic_dir = alembic_dir or ALEMBIC_DIR  # quick fix: pass dir to enable testing
    dbm = DBManager(url, metadata, ts_metadata, alembic_dir, engine_options)

    # Case 2: Database exists but not initialized.
    if not dbm.is_initialized():
        dbm.initialize_schema()
        dbm.initialize_alembic()
        if app:
            app.new_installation = True  # Skips the tool migration process.
        return

    # Case 3: Initialized, but no alembic.
    if not dbm.is_alembic_versioned():
        if not dbm.is_migrate_versioned():
            # TODO construct proper error message (no auto-migrate support here)
            raise NoMigrateVersioningError()
        else:
            if auto_migrate:
                # TODO auto_migrate is true when this is called from the db management script,
                #      or (TODO) when database_auto_migrate is set.
                # migrate_upgrade()  # to revision where alembic was introduced
                # init_alembic()
                # alembic_upgrade()
                return
            # TODO construct proper error message
            raise NoAlembicVersioningError()

    # Case 4. Initialized, has alembic, outdated.
    if not dbm.is_current():
        # if auto_migrate: # TODO
        #     alembic_upgrade()
        #     return
        # TODO construct proper error message
        raise DBOutdatedError()

    log.info('Database is up-to-date')  # add revision # to msg


def create_galaxy_database(url, app):
    template = app and getattr(app.config, "database_template", None)
    encoding = app and getattr(app.config, "database_encoding", None)
    create_kwds = {}

    message = "Creating database for URI [%s]" % url
    if template:
        message += " from template [%s]" % template
        create_kwds["template"] = template
    if encoding:
        message += " with encoding [%s]" % encoding
        create_kwds["encoding"] = encoding
    log.info(message)
    create_database(url, **create_kwds)

    create_database(url)
    assert database_exists(url)


class DBManager:
    """
    Handles all interactions w/db (except creating it) and alembic.
    Used by app at startup (and tests) + by db management script.
    """
    def __init__(self, url, metadata, ts_metadata, alembic_dir, engine_options):  # TODO do not pass alembic_dir; find better way
        self.url = url
        self.metadata = metadata        # loaded from galaxy mapping module
        self.ts_metadata = ts_metadata  # loaded from TS mapping module
        self.db_metadata = MetaData()   # to be loaded from database

        engine_options = engine_options or {}
        self.engine = build_engine(url, engine_options)

        with self.engine.connect() as conn:
            self._load_db_metadata(conn)
        alembic_dir = alembic_dir or ALEMBIC_DIR
        self._load_alembic_config(alembic_dir)

    def is_initialized(self):
        """Assume database is initialized if 'dataset' table exists."""
        return 'dataset' in self.db_metadata.tables

    def is_alembic_versioned(self):
        """Database is under Alembic version control if 'alembic_version' table exists."""
        return ALEMBIC_TABLE in self.db_metadata.tables

    def is_migrate_versioned(self):
        """Database is under SQLAlchemy version control if 'migrate_version' table exists."""
        return MIGRATE_TABLE in self.db_metadata.tables

    def is_current(self):
        script = ScriptDirectory.from_config(self.alembic_cfg)
        app_version = script.get_current_head()
        with self.engine.connect() as conn:
            context = MigrationContext.configure(conn)
            db_version = context.get_current_revision()
        return db_version == app_version

    def initialize_schema(self):
        log.info('Initializing database schema')
        with self.engine.connect() as conn:
            self.metadata.bind = conn
            self.metadata.create_all()
            self._load_db_metadata(conn)  # load again to get the updated metadata

            if self.ts_metadata:
                self.ts_metadata.bind = conn
                self.ts_metadata.create_all()
                self._load_db_metadata(conn)  # load again to get the updated metadata

    def initialize_alembic(self):
        log.info('Placing database under Alembic version control')
        command.stamp(self.alembic_cfg, "head")  # create alembic table in db; insert latest revision id.

    def _load_db_metadata(self, conn):
        self.db_metadata.bind = conn
        self.db_metadata.reflect()

    def _load_alembic_config(self, alembic_dir):
        config_file = os.path.join(alembic_dir, ALEMBIC_CONFIG_FILE)
        self.alembic_cfg = Config(config_file)
        self.alembic_cfg.set_main_option('script_location', alembic_dir)
        self.alembic_cfg.set_main_option('sqlalchemy.url', self.url)

    def alembic_upgrade(self):  # TODO this should work, but we also need to upgrade/downgrade to a specific revision
        log.info('Upgrading database / alembic head')
        command.upgrade(self.alembic_cfg, 'head')


def get_metadata_tables(metadata):
    tables = [table for table in metadata.sorted_tables if table.name != ALEMBIC_TABLE]
    return sorted(tables, key=lambda t: t.name)  # sort by table name


class MetaDataComparator:
    """Compares 2 SQLAlchemy MetaData objects."""
    # (This is hacky, but it's better than nothing, for now)

    def compare(self, metadata1, metadata2, column_attributes, type_attributes=None):
        tables1, tables2 = get_metadata_tables(metadata1), get_metadata_tables(metadata2)
        assert len(tables1) == len(tables2), 'Number of tables not the same'
        for (t1, t2) in zip(tables1, tables2):
            self.compare_indexes(t1, t2)
            assert len(t1.columns) == len(t2.columns), 'Different number of columns in table %s' % t1.name
            for (c1, c2) in zip(t1.columns, t2.columns):
                self.compare_types(c1, c2, type_attributes)
                self.compare_foreignkeys(c1, c2)
                self.compare_column_attributes(c1, c2, column_attributes)

    def compare_indexes(self, table1, table2):
        assert len(table1.indexes) == len(table2.indexes), \
            'Different number of indexes on table %s' % table1.name
        indexes1 = {i.name: i for i in table1.indexes}
        indexes2 = {i.name: i for i in table2.indexes}
        for (name1, name2) in zip(sorted(indexes1), sorted(indexes2)):
            assert name1 == name2, 'Different index names'
            assert indexes1[name1].unique == indexes2[name2].unique
            for (c1, c2) in zip(indexes1[name1].columns, indexes2[name2].columns):
                assert c1.name == c2.name

    def compare_types(self, column1, column2, type_attributes=None):
        type1, type2 = column1.type, column2.type

        if isinstance(type2, TypeDecorator) or isinstance(type2, Unicode):
            return  # handling these cases requires much pain and suffering

        assert isinstance(column1.type, type(type2)) or isinstance(column2.type, type(type1)), \
            'Different types on column %s: %s, %s' % (column1.name, type1, type2)

        if type_attributes:
            for key in type_attributes:
                if hasattr(type1, key) or hasattr(type2, key):
                    assert getattr(type1, key) == getattr(type2, key), \
                        "Type %s attributes don't match on attribute %s " % (type1, key)

    def compare_column_attributes(self, column1, column2, column_attributes):
        for key in column_attributes:
            attr1, attr2 = getattr(column1, key), getattr(column2, key)
            assert hasattr(attr1, 'arg') == hasattr(attr2, 'arg')
            if not hasattr(attr1, 'arg'):
                assert attr1 == attr2
            else:
                assert attr1.is_callable == attr2.is_callable
                if attr1.is_callable:
                    assert attr1.arg.__name__ == attr2.arg.__name__
                else:
                    assert attr1.arg == attr2.arg

    def compare_foreignkeys(self, c1, c2):
        assert len(c1.foreign_keys) == len(c2.foreign_keys)
        for (fk1, fk2) in zip(c1.foreign_keys, c2.foreign_keys):
            assert fk1.column.name == fk2.column.name
            assert fk1.column.table.name == fk2.column.table.name
            assert fk1.onupdate == fk2.onupdate
            assert fk1.ondelete == fk2.ondelete


class NoMigrateVersioningError(Exception):
    def __init__(self):
        super().__init__('not alembic, not migrate: upgrade manually')  # msg is tmp


class NoAlembicVersioningError(Exception):
    def __init__(self):
        super().__init__('not alembic, migrate: run migrate+alembic script')  # msg is tmp


class DBOutdatedError(Exception):
    def __init__(self):
        super().__init__('database is outdated: run alembic script')  # msg is tmp
