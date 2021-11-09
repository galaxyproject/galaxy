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

    def __init__(self, db_url, *, engine=None, config_dict=None):
        self.url = db_url
        self.alembic_cfg = self._load_config(config_dict)
        self.script_directory = script.ScriptDirectory.from_config(self.alembic_cfg)
        self.engine = engine or create_engine(db_url)

    def _load_config(self, config_dict):
        alembic_root = os.path.dirname(__file__)
        _alembic_file = os.path.join(alembic_root, 'alembic.ini')
        config = Config(_alembic_file)
        config.set_main_option('sqlalchemy.url', self.url)
        if config_dict:
            for key, value in config_dict.items():
                config.set_main_option(key, value)
        return config

    def stamp(self, revision):
        """Partial proxy to alembic's stamp command."""
        command.stamp(self.alembic_cfg, revision)

    def upgrade(self, model):
        """Partial proxy to alembic's upgrade command."""
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


class DatabaseVerifier:

    def __init__(self, db1_url, db2_url=None, app_config=None):
        self.db1_url = db1_url
        self.db2_url = db2_url
        self.app_config = app_config
        self.is_combined = self._combine_databases(db1_url, db2_url)
        if self.is_combined:
            self.db2_url = db1_url  # use 1 database for both
        self.gxy_metadata = get_gxy_metadata()
        self.tsi_metadata = get_tsi_metadata()
        self._engines = self._load_engines()

    def verify(self):
        # 1. Check if database exists; if not, create new database.
        self._check_and_create_database()
        # 2. If database is empty, initialize it, upgrade to current, and mark as done.
        gxy_done, tsi_done = self._handle_empty_database()
        # 3: Handle non-empty database.
        if not gxy_done:
            self._handle_nonempty_database(self.db1_url, self.gxy_metadata, GXY)
        if not tsi_done:
            self._handle_nonempty_database(self.db2_url, self.tsi_metadata, TSI)

    def _check_and_create_database(self):
        if not database_exists(self.db1_url):
            self._create_galaxy_database(self.db1_url)
        if not self.is_combined and not database_exists(self.db2_url):
            self._create_galaxy_database(self.db2_url)

    def _handle_empty_database(self):

        def initialize_empty_database(db_url, metadata, model):
            load_metadata(db_url, metadata)
            am = get_alembic_manager(db_url)  # TODO reuse (do lazy init)
            am.stamp(f'{model}@head')

        gxy_done, tsi_done = False, False

        # if db1 is empty: initialize it for gxy and, if combined, for tsi.
        if self._is_database_empty(self.db1_url):
            initialize_empty_database(self.db1_url, self.gxy_metadata, GXY)
            gxy_done = True
            if self.is_combined:
                initialize_empty_database(self.db1_url, self.tsi_metadata, TSI)  # use same db_url
                tsi_done = True

        # if not combined, check db2. If it's empty: initialize it for tsi.
        if not self.is_combined and self._is_database_empty(self.db2_url):
            initialize_empty_database(self.db2_url, self.tsi_metadata, TSI)  # use same db_url
            tsi_done = True

        return gxy_done, tsi_done

    def _handle_nonempty_database(self, db_url, metadata, model):
        am = get_alembic_manager(db_url)  # TODO reuse (do lazy init)
        # first check if this model is up to date
        if am.is_up_to_date(model):
            # TODO: log message: db is up-to-date
            return
        # now check for alembic table
        elif self._has_alembic_version_table(db_url):
            # has alembic but outdated: try to upgrade
            if not self._is_automigrate_set():
                raise OutdatedDatabaseError()
            else:
                # TODO log message: upgrading
                am.upgrade(model)
                return
        # if no alembic: check for SAMigrate
        if not self._has_sqlalchemymigrate_version_table(db_url):
            raise NoVersionTableError()
        elif not self._is_last_sqlalchemymigrate_version(db_url):
            raise VersionTooOldError()
        elif not self._is_automigrate_set():
            raise OutdatedDatabaseError()
        else:
            # TODO log message: adding alembic + upgrading
            am.upgrade(model)
            return

    def _load_engines(self):
        engines = {}
        engines[self.db1_url] = create_engine(self.db1_url)
        if not self.is_combined:
            engines[self.db2_url] = create_engine(self.db2_url)
        return engines

    def _combine_databases(self, db1_url, db2_url=None):
        return not (db1_url and db2_url and db1_url != db2_url)

    def _create_galaxy_database(self, url):
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

    def _is_database_empty(self, db_url):
        with self._engines[db_url].connect() as conn:
            db_metadata = MetaData()
            db_metadata.reflect(bind=conn)
            return not bool(db_metadata.tables)

    def _has_alembic_version_table(self, db_url):
        with self._engines[db_url].connect() as conn:
            db_metadata = MetaData()
            db_metadata.reflect(bind=conn)
            return ALEMBIC_TABLE in db_metadata.tables

    def _is_automigrate_set(self):
        return False  # TODO fix this: env var?

    def _has_sqlalchemymigrate_version_table(self, db_url):
        with self._engines[db_url].connect() as conn:
            db_metadata = MetaData()
            db_metadata.reflect(bind=conn)
            return SQLALCHEMYMIGRATE_TABLE in db_metadata.tables

    def _is_last_sqlalchemymigrate_version(self, db_url):
        with self._engines[db_url].connect() as conn:
            sql = f"select version from {SQLALCHEMYMIGRATE_TABLE}"
            result = conn.execute(sql).scalar()
            return result == SQLALCHEMYMIGRATE_LAST_VERSION


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
