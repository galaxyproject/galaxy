import logging
import os

import alembic
from alembic import command, script
from alembic.config import Config
from alembic.runtime import migration
from sqlalchemy import MetaData

from galaxy.model import Base as gxy_base
from galaxy.model.database_utils import create_database, database_exists
from galaxy.model.mapping import create_additional_database_objects
from galaxy.model.tool_shed_install import Base as tsi_base

# These identifiers are used throughout the migrations system to distinquish
# between the two models; they refer to version directories, branch labels, etc.
# (if you rename these, you need to rename branch labels in alembic version directories)
GXY = 'gxy'  # galaxy model identifier
TSI = 'tsi'  # tool_shed_install model identifier

ALEMBIC_TABLE = 'alembic_version'  # TODO this should come from alembic config
SQLALCHEMYMIGRATE_TABLE = 'migrate_version'
SQLALCHEMYMIGRATE_LAST_VERSION_GXY = 180
SQLALCHEMYMIGRATE_LAST_VERSION_TSI = 17
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
    @staticmethod
    def is_at_revision(engine, revision):
        """
        True if revision is a subset of the set of version heads stored in the database.
        """
        revision = listify(revision)
        with engine.connect() as conn:
            context = migration.MigrationContext.configure(conn)
            db_version_heads = context.get_current_heads()
            return set(revision) <= set(db_version_heads)

    def __init__(self, engine, config_dict=None):
        self.engine = engine
        self.alembic_cfg = self._load_config(config_dict)
        self.script_directory = script.ScriptDirectory.from_config(self.alembic_cfg)
        self._reset_db_heads()

    def _load_config(self, config_dict):
        alembic_root = os.path.dirname(__file__)
        _alembic_file = os.path.join(alembic_root, 'alembic.ini')  # TODO can we make this more flexible so we can call it from multiple locations?
        config = Config(_alembic_file)
        url = get_url_string(self.engine)
        config.set_main_option('sqlalchemy.url', url)
        if config_dict:
            for key, value in config_dict.items():
                config.set_main_option(key, value)  # TODO consider: can also use config.attributes dictionary
        return config

    def stamp_model_head(self, model):
        """Partial proxy to alembic's stamp command."""
        command.stamp(self.alembic_cfg, f'{model}@head')
        self._reset_db_heads()

    def stamp_revision(self, revision):
        """Partial proxy to alembic's stamp command."""
        command.stamp(self.alembic_cfg, revision)
        self._reset_db_heads()

    def upgrade(self, model):
        """Partial proxy to alembic's upgrade command."""
        # This works with or without an existing alembic version table.
        command.upgrade(self.alembic_cfg, f'{model}@head')
        self._reset_db_heads()

    def is_under_version_control(self, model):
        """
        True if version table contains a revision that represents `model`.
        (checked via revision's branch labels)
        """
        if self.db_heads:
            for head in self.db_heads:
                revision = self._get_revision(head)
                if revision and model in revision.branch_labels:
                    return True
        return False

    def is_up_to_date(self, model):
        """
        True if the `model` version head stored in the database is in the heads
        stored in the script directory. Neither can be empty because the
        concept of up-to-date would be meaningless for that state.
        """
        version_heads = self.script_directory.get_heads()
        if not version_heads or not self.db_heads:
            return False
        # Verify that db_version_heads contains a head for the passed model:
        # if the head in the database is for gxy, but we are checking for tsi
        # this should return False.
        for head in self.db_heads:
            revision = self._get_revision(head)
            if revision and model in revision.branch_labels and head in version_heads:
                return True
        return False

    @property
    def db_heads(self):
        if self._db_heads is None:  # Explicitly check for None: could be an empty tuple.
            with self.engine.connect() as conn:
                context = migration.MigrationContext.configure(conn)
                self._db_heads = context.get_current_heads()
            # We get a tuple as long as we use branches. Otherwise, we'd get a single value.
            # listify() is a safeguard in case we stop using branches.
            self._db_heads = listify(self._db_heads)
        return self._db_heads

    def _get_revision(self, revision_id):
        try:
            return self.script_directory.get_revision(revision_id)
        except alembic.util.exc.CommandError as e:
            log.error('TODO: explaining message')  # TODO fix message
            raise e

    def _reset_db_heads(self):
        self._db_heads = None


class DatabaseStateCache:
    """
    Snapshot of database state.
    """
    def __init__(self, engine):
        self._load_db(engine)

    @property
    def tables(self):
        return self.db_metadata.tables

    def is_database_empty(self):
        return not bool(self.db_metadata.tables)

    def has_alembic_version_table(self):
        return ALEMBIC_TABLE in self.db_metadata.tables

    def has_sqlalchemymigrate_version_table(self):
        return SQLALCHEMYMIGRATE_TABLE in self.db_metadata.tables

    def is_last_sqlalchemymigrate_version(self, last_version):
        return self.sqlalchemymigrate_version == last_version

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


def verify_databases(engine, install_engine=None, app_config=None):
    # verify galaxy (gxy) model
    gxy_dsv = DatabaseStateVerifier(engine, GXY, app_config)
    gxy_dsv.run()
    # determine install_engine, and whether it's a new database
    install_engine = install_engine or engine
    is_new_database = install_engine == engine and gxy_dsv.is_new_database
    # verify tool_shed_install model (tsi) model
    tsi_dsv = DatabaseStateVerifier(install_engine, TSI, app_config, is_new_database)
    tsi_dsv.run()


class DatabaseStateVerifier:

    def __init__(self, engine, model, app_config, is_new_database=None):
        self.engine = engine
        self.model = model
        self.app_config = app_config  # TODO gxy vs tsi: need a way to easily use the right options
        self.metadata = get_metadata(model)
        self.is_new_database = is_new_database  # True if database has been created and/or initialized for another model.
        # These values may or may not be required, so do a lazy load.
        self._db_state = None
        self._alembic_manager = None

    @property
    def db_state(self):
        if not self._db_state:
            self._db_state = DatabaseStateCache(engine=self.engine)
        return self._db_state

    @property
    def alembic_manager(self):
        if not self._alembic_manager:
            self._alembic_manager = get_alembic_manager(self.engine)
        return self._alembic_manager

    def run(self):
        if self._handle_no_database():
            return
        if self._handle_empty_database():
            return
        self._handle_nonempty_database()

    def _handle_no_database(self):
        url = get_url_string(self.engine)
        if not database_exists(url):
            self._create_database(url)
            self._initialize_database()
            return True
        return False

    def _handle_empty_database(self):
        if self.is_new_database or self._is_database_empty():
            self._initialize_database()
            return True
        return False

    def _handle_nonempty_database(self):
        if self._has_alembic_version_table():
            am = self.alembic_manager
            if am.is_under_version_control(self.model):
                self._handle_with_alembic()
            else:
                if self._no_model_tables_exist():
                    self._initialize_database()
                else:
                    self._handle_with_alembic()
        elif self._has_sqlalchemymigrate_version_table():
            if self._is_last_sqlalchemymigrate_version():
                self._handle_with_alembic()
            else:
                self._handle_version_too_old()
        else:
            self._handle_no_version_table()

    def _handle_with_alembic(self):
        # we know model is under alembic version control
        am = self.alembic_manager
        # first check if this model is up to date
        if am.is_up_to_date(self.model):
            # TODO: log message: db is up-to-date
            return
        # is outdated: try to upgrade
        if not self._is_automigrate_set():
            raise OutdatedDatabaseError()
        else:
            # TODO log message: upgrading
            am.upgrade(self.model)
            return

    def _no_model_tables_exist(self):
        # True if there are no tables from `self.model` in the database.
        db_tables = self.db_state.tables
        for tablename in set(self.metadata.tables) - {ALEMBIC_TABLE}:
            if tablename in db_tables:
                return False
        return True

    def _create_database(self, url):
        template = self.app_config.database_template if self.app_config else None  # TODO: this should be different for TSI? or not?
        encoding = self.app_config.database_encoding if self.app_config else None
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

    def _initialize_database(self):
        load_metadata(self.metadata, self.engine)
        if self.model == GXY:
            self._create_additional_database_objects()
        self.alembic_manager.stamp_model_head(self.model)  # create version table if not exists, stamp with head  #TODO rename method
        self.is_new_database = True

    def _create_additional_database_objects(self):
        create_additional_database_objects(self.engine)

    def _is_database_empty(self):
        return self.db_state.is_database_empty()

    def _is_automigrate_set(self):
        if self.app_config:
            return self.app_config.database_auto_migrate
        return False

    def _has_alembic_version_table(self):
        return self.db_state.has_alembic_version_table()

    def _has_sqlalchemymigrate_version_table(self):
        return self.db_state.has_sqlalchemymigrate_version_table()

    def _is_last_sqlalchemymigrate_version(self):
        last_version = get_last_sqlalchemymigrate_version(self.model)
        return self.db_state.is_last_sqlalchemymigrate_version(last_version)

    def _handle_no_version_table(self):
        log.error('no version table')  # TODO edit message
        raise NoVersionTableError()

    def _handle_version_too_old(self):
        log.error('version too old')  # TODO edit message
        raise VersionTooOldError()


def get_last_sqlalchemymigrate_version(model):
    if model == GXY:
        return SQLALCHEMYMIGRATE_LAST_VERSION_GXY
    elif model == TSI:
        return SQLALCHEMYMIGRATE_LAST_VERSION_TSI


def get_url_string(engine):
    return engine.url.render_as_string(hide_password=False)


def get_alembic_manager(engine):
    return AlembicManager(engine)


def get_metadata(model):
    if model == GXY:
        return get_gxy_metadata()
    elif model == TSI:
        return get_tsi_metadata()


def load_metadata(metadata, engine):
    with engine.connect() as conn:
        metadata.create_all(bind=conn)


# TODO galaxy has this (reuse, don't test)
def listify(data):
    if not isinstance(data, (list, tuple)):
        return [data]
    return data


def get_gxy_metadata():
    return gxy_base.metadata


def get_tsi_metadata():
    return tsi_base.metadata
