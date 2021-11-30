import logging
import os

from alembic import command, script
from alembic.config import Config
from alembic.runtime import migration
from sqlalchemy import create_engine, MetaData

from galaxy.model import Base as gxy_base
from galaxy.model.database_utils import create_database, database_exists
from galaxy.model.tool_shed_install import Base as tsi_base

# These identifiers are used throughout the migrations system to distinquish
# between the two models; they refer to version directories, branch labels, etc.
# (if you rename these, you need to rename branch labels in alembic version directories)
GXY = 'gxy'  # galaxy model identifier
TSI = 'tsi'  # tool_shed_install model identifier

ALEMBIC_TABLE = 'alembic_version'  # TODO this should come from alembic config
SQLALCHEMYMIGRATE_TABLE = 'migrate_version'
SQLALCHEMYMIGRATE_LAST_VERSION = 999  # TODO this should be the actual last SA-M revision

log = logging.getLogger(__name__)


class NoVersionTableError(Exception):
    def __init__(self):
        super().__init__('Database has no version table')  # TODO edit message


class VersionTooOldError(Exception):
    def __init__(self):
        super().__init__('Database version is too old and cannot be upgraded automatically')  # TODO edit message


class OutdatedDatabaseError(Exception):
    def __init__(self):
        super().__init__('Database version is outdated. Can be upgraded automatically if auto-migrate is set')  # TODO edit message


class AlembicManager:
    """
    Alembic operations on one database.
    """
    def __init__(self, db_url, *, engine=None, config_dict=None):
        self.alembic_cfg = self._load_config(config_dict, db_url)
        self.script_directory = script.ScriptDirectory.from_config(self.alembic_cfg)
        self.engine = engine or create_engine(db_url)

    def _load_config(self, config_dict, db_url):
        alembic_root = os.path.dirname(__file__)
        _alembic_file = os.path.join(alembic_root, 'alembic.ini')
        config = Config(_alembic_file)
        config.set_main_option('sqlalchemy.url', db_url)
        if config_dict:
            for key, value in config_dict.items():
                config.set_main_option(key, value)
        return config

    def stamp(self, revision):
        """Partial proxy to alembic's stamp command."""
        command.stamp(self.alembic_cfg, revision)

    def upgrade(self, model):
        """Partial proxy to alembic's upgrade command."""
        # This works with or without an existing alembic version table.
        command.upgrade(self.alembic_cfg, f'{model}@head')

    def is_at_revision(self, revision):
        """
        True if revision is a subset of the set of version heads stored in the database.
        """
        revision = listify(revision)
        with self.engine.connect() as conn:
            context = migration.MigrationContext.configure(conn)
            db_version_heads = context.get_current_heads()
            return set(revision) <= set(db_version_heads)

    def is_up_to_date(self, model):
        """
        True if the `model` version head stored in the database is in the heads
        stored in the script directory. Neither can be empty because the
        concept of up-to-date would be meaningless for that state.
        """
        version_heads = self.script_directory.get_heads()
        if not version_heads:
            return False
        with self.engine.connect() as conn:
            context = migration.MigrationContext.configure(conn)
            db_version_heads = context.get_current_heads()
            if not db_version_heads:
                return False
            db_version_heads = listify(db_version_heads)

            # Verify that db_version_heads contains a head for the passed model:
            # if the head in the database is for gxy, but we are checking for tsi
            # this should return False.
            for head in db_version_heads:
                revision = self.script_directory.get_revision(head)
                if model in revision.branch_labels and head in version_heads:
                    return True
            return False


class DatabaseStateCache:
    """
    Snapshot of database state.
    """
    def __init__(self, engine):
        self._load_db(engine)

    def is_database_empty(self):
        return not bool(self.db_metadata.tables)

    def has_alembic_version_table(self):
        return ALEMBIC_TABLE in self.db_metadata.tables

    def has_sqlalchemymigrate_version_table(self):
        return SQLALCHEMYMIGRATE_TABLE in self.db_metadata.tables

    def is_last_sqlalchemymigrate_version(self):
        return self.sqlalchemymigrate_version == SQLALCHEMYMIGRATE_LAST_VERSION

    def _load_db(self, engine):
        with engine.connect() as conn:
            self.db_metadata = self._load_db_metadata(conn)
            self.sqlalchemymigrate_version = self._load_sqlalchemymigrate_version(conn)

    def _load_db_metadata(self, conn):
        metadata = MetaData()
        metadata.reflect(bind=conn)
        return metadata

    def _load_sqlalchemymigrate_version(self, conn):
        if self.has_sqlalchemymigrate_version_table():
            sql = f"select version from {SQLALCHEMYMIGRATE_TABLE}"
            return conn.execute(sql).scalar()


class DatabaseVerifier:

    def __init__(self, db_url, install_db_url=None, app_config=None):
        self.gxy_url = db_url
        self.tsi_url = install_db_url or db_url
        assert self.gxy_url and self.tsi_url
        self.app_config = app_config
        self._load()

    def _load(self):
        self.is_combined = self._is_one_database(self.gxy_url, self.tsi_url)
        self.gxy_metadata = get_gxy_metadata()
        self.tsi_metadata = get_tsi_metadata()
        self.engines = self._load_engines()
        self.db_state = self._load_database_state()

    def _load_engines(self):
        engines = {}
        engines[GXY] = create_engine(self.gxy_url)
        if not self.is_combined:
            engines[TSI] = create_engine(self.tsi_url)
        else:
            engines[TSI] = engines[GXY]  # combined = same engine
        return engines

    def _load_database_state(self):
        db = {}
        db[GXY] = DatabaseStateCache(engine=self.engines[GXY])
        if not self.is_combined:
            db[TSI] = DatabaseStateCache(engine=self.engines[TSI])
        else:
            db[TSI] = db[GXY]  # combined = same database
        return db

    def verify(self):
        # 1. Check if database exists; if not, create new database.
        self._handle_no_databases()
        # 2. If database is empty, initialize it, upgrade to current, and mark as done.
        gxy_done, tsi_done = self._handle_empty_databases()
        # 3: Handle nonempty databases that were not initialized in the previous step.
        if not gxy_done:
            self._handle_nonempty_database(GXY)
        if not tsi_done:
            if self.is_combined:  # If same database, Alembic has been initialized in the previous step.
                self._handle_with_alembic(TSI)
            else:
                self._handle_nonempty_database(TSI)

    def _handle_no_databases(self):
        # If galaxy-model database doesn't exist: create it.
        # If database not combined and install-model database doesn't exist: create it.
        if not database_exists(self.gxy_url):
            self._create_database(self.gxy_url)
        if not self.is_combined and not database_exists(self.tsi_url):
            self._create_database(self.tsi_url)

    def _handle_empty_databases(self):
        # For each database: True if it has been initialized.
        gxy_done = tsi_done = False
        if self.is_combined:
            if self._is_database_empty(GXY):
                self._initialize_database(GXY)
                self._initialize_database(TSI)
                gxy_done = tsi_done = True
        else:
            if self._is_database_empty(GXY):
                self._initialize_database(GXY)
                gxy_done = True
            if self._is_database_empty(TSI):
                self._initialize_database(TSI)
                tsi_done = True
        return gxy_done, tsi_done

    def _handle_nonempty_database(self, model):
        if self._has_alembic(model):
            self._handle_with_alembic(model)
        elif self._has_sqlalchemymigrate(model):
            if self._is_last_sqlalchemymigrate_version(model):
                self._handle_with_alembic(model, skip_version_check=True)
            else:
                self._handle_version_too_old(model)
        else:
            self._handle_no_version_table(model)

    def _has_alembic(self, model):
        return self.db_state[model].has_alembic_version_table()

    def _has_sqlalchemymigrate(self, model):
        return self.db_state[model].has_sqlalchemymigrate_version_table()

    def _is_last_sqlalchemymigrate_version(self, model):
        return self.db_state[model].is_last_sqlalchemymigrate_version()

    def _handle_with_alembic(self, model, skip_version_check=False):
        url = self._get_url(model)
        am = get_alembic_manager(url)
        # first check if this model is up to date
        if not skip_version_check and am.is_up_to_date(model):
            # TODO: log message: db is up-to-date
            return
        # is outdated: try to upgrade
        if not self._is_automigrate_set():
            raise OutdatedDatabaseError()
        else:
            # TODO log message: upgrading
            am.upgrade(model)
            return

    def _handle_version_too_old(self, model):
        log.error('version too old')  # TODO edit message
        raise VersionTooOldError()

    def _handle_no_version_table(self, model):
        log.error('no version table')  # TODO edit message
        raise NoVersionTableError()

    def _get_url(self, model):
        if model == GXY:
            return self.gxy_url
        else:
            return self.tsi_url

    def _is_automigrate_set(self):
        return False  # TODO fix this: env var?

    def _initialize_database(self, model):

        def initialize_database(url, metadata, engine):
            load_metadata(url, metadata, engine)
            am = get_alembic_manager(url)
            am.stamp(f'{model}@head')

        if model == GXY:
            initialize_database(self.gxy_url, self.gxy_metadata, self.engines[GXY])
        elif model == TSI:
            initialize_database(self.tsi_url, self.tsi_metadata, self.engines[TSI])
        return True

    def _is_database_empty(self, model):
        return self.db_state[model].is_database_empty()

    def _create_database(self, url):
        template, encoding = None, None
        if self.app_config:
            template = self.app_config.database_template
            encoding = self.app_config.database_encoding  # TODO add to config_schema
        create_kwds = {}
        message = f'Creating database for URI [{url}]'
        if template:
            message += f' from template [{template}]'
            create_kwds['template'] = template
        if encoding:
            message += f' with encoding [{encoding}]'
            create_kwds['encoding'] = encoding
        log.info(message)
        create_database(url, **create_kwds)

    def _is_one_database(self, url1, url2):
        return not (url1 and url2 and url1 != url2)


def load_metadata(db_url, metadata, engine=None):
    metadata = listify(metadata)
    engine = engine or create_engine(db_url)
    with engine.connect() as conn:
        for md in metadata:
            md.create_all(bind=conn)


# TODO galaxy has this (reuse, don't test)
def listify(data):
    if not isinstance(data, (list, tuple)):
        return [data]
    return data


def get_alembic_manager(db_url):
    return AlembicManager(db_url)


def get_gxy_metadata():
    return gxy_base.metadata


def get_tsi_metadata():
    return tsi_base.metadata
