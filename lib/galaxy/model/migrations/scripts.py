import os
import sys
from typing import (
    List,
    Optional,
    Tuple,
)

import alembic.config
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from galaxy.model.database_utils import database_exists
from galaxy.model.migrations import (
    AlembicManager,
    DatabaseConfig,
    GXY,
    SQLALCHEMYMIGRATE_LAST_VERSION_GXY,
    TSI,
)
from galaxy.model.migrations.base import (
    DatabaseStateCache,
    pop_arg_from_args,
)
from galaxy.model.migrations.exceptions import (
    DatabaseDoesNotExistError,
    DatabaseNotInitializedError,
    IncorrectSAMigrateVersionError,
    NoVersionTableError,
)
from galaxy.util.properties import (
    find_config_file,
    get_data_dir,
    load_app_properties,
)

DEFAULT_CONFIG_NAMES = ["galaxy", "universe_wsgi"]
CONFIG_FILE_ARG = "--galaxy-config"
CONFIG_DIR_NAME = "config"
GXY_CONFIG_PREFIX = "GALAXY_CONFIG_"
TSI_CONFIG_PREFIX = "GALAXY_INSTALL_CONFIG_"


def verify_database_is_initialized(db_url: str) -> None:
    """
    Intended for use by scripts that run database migrations (manage_db.sh,
    run_alembic.sh). Those scripts are meant to run on a database that has been
    initialized with the appropriate metadata (e.g. galaxy or install model).

    This function will raise an error if the database does not exist or has not
    been initialized*.

    *NOTE: this function cannot determine whether a database has been properly
    initialized; it can only tell when a database has *not* been initialized.
    """
    if not database_exists(db_url):
        raise DatabaseDoesNotExistError(db_url)

    engine = create_engine(db_url)
    try:
        db_state = DatabaseStateCache(engine=engine)
        if db_state.is_database_empty() or db_state.contains_only_kombu_tables():
            raise DatabaseNotInitializedError(db_url)
    finally:
        engine.dispose()


def get_configuration(argv: List[str], cwd: str) -> Tuple[DatabaseConfig, DatabaseConfig, bool]:
    """
    Return a 3-item-tuple with configuration values used for managing databases.
    """
    config_file = pop_arg_from_args(argv, CONFIG_FILE_ARG)
    return get_configuration_from_file(cwd, config_file)


def get_configuration_from_file(
    cwd: str, config_file: Optional[str] = None
) -> Tuple[DatabaseConfig, DatabaseConfig, bool]:
    if config_file is None:
        cwds = [cwd, os.path.join(cwd, CONFIG_DIR_NAME)]
        config_file = find_config_file(DEFAULT_CONFIG_NAMES, dirs=cwds)

    # load gxy properties and auto-migrate
    properties = load_app_properties(config_file=config_file, config_prefix=GXY_CONFIG_PREFIX)
    default_url = f"sqlite:///{os.path.join(get_data_dir(properties), 'universe.sqlite')}?isolation_level=IMMEDIATE"
    url = properties.get("database_connection", default_url)
    template = properties.get("database_template", None)
    encoding = properties.get("database_encoding", None)
    is_auto_migrate = properties.get("database_auto_migrate", False)
    gxy_config = DatabaseConfig(url, template, encoding)

    # load tsi properties
    properties = load_app_properties(config_file=config_file, config_prefix=TSI_CONFIG_PREFIX)
    default_url = gxy_config.url
    url = properties.get("install_database_connection", default_url)
    template = properties.get("database_template", None)
    encoding = properties.get("database_encoding", None)
    tsi_config = DatabaseConfig(url, template, encoding)

    return (gxy_config, tsi_config, is_auto_migrate)


def add_db_urls_to_command_arguments(argv: List[str], gxy_url: str, tsi_url: str) -> None:
    _insert_x_argument(argv, f"{TSI}_url", tsi_url)
    _insert_x_argument(argv, f"{GXY}_url", gxy_url)


def _insert_x_argument(argv, key: str, value: str) -> None:
    # `_insert_x_argument('mykey', 'myval')` transforms `foo -a 1` into `foo -x mykey=myval -a 42`
    argv.insert(1, f"{key}={value}")
    argv.insert(1, "-x")


def invoke_alembic() -> None:
    """
    Invoke the Alembic command line runner.

    Accept 'heads' as the target revision argument to enable upgrading both gxy and tsi in one command.
    This is consistent with Alembic's CLI, which allows `upgrade heads`. However, this would not work for
    separate gxy and tsi databases: we can't attach a database url to a revision after Alembic has been
    invoked with the 'upgrade' command and the 'heads' argument. So, instead we invoke Alembic for each head.
    """
    if "heads" in sys.argv and "upgrade" in sys.argv:
        i = sys.argv.index("heads")
        sys.argv[i] = f"{GXY}@head"
        alembic.config.main()
        sys.argv[i] = f"{TSI}@head"
        alembic.config.main()
    else:
        alembic.config.main()


class LegacyManageDb:
    LEGACY_CONFIG_FILE_ARG_NAMES = ["-c", "--config", "--config-file"]

    def __init__(self):
        self._set_db_urls()

    def get_gxy_version(self):
        """
        Get the head revision for the gxy branch from the Alembic script directory.
        (previously referred to as "max/repository version")
        """
        script_directory = self._get_script_directory()
        heads = script_directory.get_heads()
        for head in heads:
            revision = script_directory.get_revision(head)
            if revision and GXY in revision.branch_labels:
                return head
        return None

    def get_gxy_db_version(self, gxy_db_url=None):
        """
        Get the head revision for the gxy branch from the galaxy database. If there
        is no alembic_version table, get the sqlalchemy migrate version. Raise error
        if that version is not the latest.
        (previously referred to as "database version")
        """
        db_url = gxy_db_url or self.gxy_db_url
        try:
            engine = create_engine(db_url)
            version = self._get_gxy_alembic_db_version(engine)
            if not version:
                version = self._get_gxy_sam_db_version(engine)
                if version is None:
                    raise NoVersionTableError(GXY)
                elif version != SQLALCHEMYMIGRATE_LAST_VERSION_GXY:
                    raise IncorrectSAMigrateVersionError(GXY, SQLALCHEMYMIGRATE_LAST_VERSION_GXY)
            return version
        finally:
            engine.dispose()

    def run_upgrade(self, gxy_db_url=None, tsi_db_url=None):
        """
        Alembic will upgrade both branches, gxy and tsi, to their head revisions.
        """
        gxy_db_url = gxy_db_url or self.gxy_db_url
        tsi_db_url = tsi_db_url or self.tsi_db_url
        self._upgrade(gxy_db_url, GXY)
        self._upgrade(tsi_db_url, TSI)

    def rename_config_argument(self, argv: List[str]) -> None:
        """
        Rename the optional config argument: we can't use '-c' because that option is used by Alembic.
        """
        for arg in self.LEGACY_CONFIG_FILE_ARG_NAMES:
            if arg in argv:
                self._rename_arg(argv, arg, CONFIG_FILE_ARG)
                return

    def _rename_arg(self, argv, old_name, new_name) -> None:
        pos = argv.index(old_name)
        argv[pos] = new_name

    def _upgrade(self, db_url, model):
        try:
            engine = create_engine(db_url)
            am = get_alembic_manager(engine)
            am.upgrade(model)
        finally:
            engine.dispose()

    def _set_db_urls(self):
        self.rename_config_argument(sys.argv)
        self._load_db_urls()

    def _load_db_urls(self):
        gxy_config, tsi_config, _ = get_configuration(sys.argv, os.getcwd())
        self.gxy_db_url = gxy_config.url
        self.tsi_db_url = tsi_config.url

    def _get_gxy_sam_db_version(self, engine):
        dbcache = DatabaseStateCache(engine)
        return dbcache.sqlalchemymigrate_version

    def _get_script_directory(self):
        alembic_cfg = get_alembic_cfg()
        return ScriptDirectory.from_config(alembic_cfg)

    def _get_gxy_alembic_db_version(self, engine):
        # We may get 2 values, one for each branch (gxy and tsi). So we need to
        # determine which one is the gxy head.
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            db_heads = context.get_current_heads()
            if db_heads:
                gxy_revisions = self._get_all_gxy_revisions()
                for db_head in db_heads:
                    if db_head in gxy_revisions:
                        return db_head
        return None

    def _get_all_gxy_revisions(self):
        gxy_revisions = set()
        script_directory = self._get_script_directory()
        for rev in script_directory.walk_revisions():
            if GXY in rev.branch_labels:
                gxy_revisions.add(rev.revision)
        return gxy_revisions


def get_alembic_cfg():
    config_file = os.path.join(os.path.dirname(__file__), "alembic.ini")
    config_file = os.path.abspath(config_file)
    return Config(config_file)


def get_alembic_manager(engine: Engine) -> AlembicManager:
    return AlembicManager(engine)
