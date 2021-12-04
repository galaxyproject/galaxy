import logging
import os

from alembic import command, script
from alembic.config import Config
from alembic.runtime import migration
from sqlalchemy import MetaData

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
SQLALCHEMYMIGRATE_LAST_VERSION = 179
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
    def __init__(self, engine, config_dict=None):
        self.engine = engine
        self.alembic_cfg = self._load_config(config_dict)
        self.script_directory = script.ScriptDirectory.from_config(self.alembic_cfg)

    def _load_config(self, config_dict):
        alembic_root = os.path.dirname(__file__)
        _alembic_file = os.path.join(alembic_root, 'alembic.ini')
        config = Config(_alembic_file)
        url = str(self.engine.url)
        config.set_main_option('sqlalchemy.url', url)
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

    def __init__(self, engine, install_engine=None, app_config=None):
        # Assume separate databases for `galaxy model` and `install_model` if install_engine is set.
        # Caller is responsible for verifying engines are not referring to the same database.
        self.is_combined = install_engine is None
        self.gxy_engine = engine
        self.tsi_engine = install_engine if not self.is_combined else engine
        self.app_config = app_config
        self.gxy_metadata = get_gxy_metadata()
        self.tsi_metadata = get_tsi_metadata()
        # self.db_state is loaded after missing databases are created.

    def _load_database_state(self):
        db = {}
        db[GXY] = DatabaseStateCache(engine=self.gxy_engine)
        if not self.is_combined:
            db[TSI] = DatabaseStateCache(engine=self.tsi_engine)
        else:
            db[TSI] = db[GXY]  # combined = same database
        return db

    def verify(self):
        # 1. Check if database exists; if not, create new database.
        is_gxy_new, is_tsi_new = self._handle_no_databases()

        # 2. Now we can load database state.
        self.db_state = self._load_database_state()

        # 3. If database is empty, initialize it, upgrade to current, and mark as done.
        gxy_done, tsi_done = self._handle_empty_databases()

        # 4: Handle nonempty databases that were not initialized in the previous step.
        if not gxy_done:
            self._handle_nonempty_database(GXY)
        if not tsi_done:
            if self.is_combined:  # If same database, Alembic has been initialized in the previous step.
                self._handle_with_alembic(TSI)
            else:
                self._handle_nonempty_database(TSI)

    def _handle_no_databases(self):
        # If galaxy-model database doesn't exist: create it and set is_gxy_new.
        # If database not combined and install-model database doesn't exist: create it and set is_tsi_new.
        # Return "is new" status for both databases
        gxy_url = str(self.gxy_engine.url)
        tsi_url = str(self.tsi_engine.url)
        is_gxy_new = is_tsi_new = False

        if not database_exists(gxy_url):
            template = self.app_config.database_template if self.app_config else None
            encoding = self.app_config.database_encoding if self.app_config else None
            self._create_database(gxy_url, template, encoding)
            is_gxy_new = True
        if not self.is_combined and not database_exists(tsi_url):
            self._create_database(tsi_url)
            is_tsi_new = True
        return is_gxy_new, is_tsi_new

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
        engine = self.gxy_engine if model == GXY else self.tsi_engine
        am = get_alembic_manager(engine)
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

    def _is_automigrate_set(self):
        if self.app_config:
            return self.app_config.database_auto_migrate
        return False

    def _initialize_database(self, model):

        def initialize_database(metadata, engine):
            load_metadata(metadata, engine)
            am = get_alembic_manager(engine)
            am.stamp(f'{model}@head')

        if model == GXY:
            initialize_database(self.gxy_metadata, self.gxy_engine)
        elif model == TSI:
            initialize_database(self.tsi_metadata, self.tsi_engine)
        return True

    def _is_database_empty(self, model):
        return self.db_state[model].is_database_empty()

    def _create_database(self, url, template=None, encoding=None):
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


def load_metadata(metadata, engine):
    with engine.connect() as conn:
        metadata.create_all(bind=conn)


# TODO galaxy has this (reuse, don't test)
def listify(data):
    if not isinstance(data, (list, tuple)):
        return [data]
    return data


def get_alembic_manager(engine):
    return AlembicManager(engine)


def get_gxy_metadata():
    return gxy_base.metadata


def get_tsi_metadata():
    return tsi_base.metadata
