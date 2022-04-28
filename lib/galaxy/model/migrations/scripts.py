import os
import re
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

from galaxy.model.database_utils import is_one_database
from galaxy.model.migrations import (
    AlembicManager,
    DatabaseConfig,
    DatabaseStateCache,
    GXY,
    IncorrectVersionError,
    NoVersionTableError,
    SQLALCHEMYMIGRATE_LAST_VERSION_GXY,
    TSI,
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


def get_configuration(argv: List[str], cwd: str) -> Tuple[DatabaseConfig, DatabaseConfig, bool]:
    """
    Return a 3-item-tuple with configuration values used for managing databases.
    """
    config_file = _pop_config_file(argv)
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


def _pop_config_file(argv: List[str]) -> Optional[str]:
    if CONFIG_FILE_ARG in argv:
        pos = argv.index(CONFIG_FILE_ARG)
        argv.pop(pos)  # pop argument name
        return argv.pop(pos)  # pop and return argument value
    return None


def add_db_urls_to_command_arguments(argv: List[str], gxy_url: str, tsi_url: str) -> None:
    _insert_x_argument(argv, "tsi_url", tsi_url)
    _insert_x_argument(argv, "gxy_url", gxy_url)


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


class LegacyScriptsException(Exception):
    # Misc. errors caused by incorrect arguments passed to a legacy script.
    def __init__(self, message: str) -> None:
        super().__init__(message)


class LegacyScripts:

    LEGACY_CONFIG_FILE_ARG_NAMES = ["-c", "--config", "--config-file"]
    ALEMBIC_CONFIG_FILE_ARG = "--alembic-config"  # alembic config file, set in the calling script
    DEFAULT_DB_ARG = "default"

    def __init__(self, argv: List[str], cwd: Optional[str] = None) -> None:
        self.argv = argv
        self.cwd = cwd or os.getcwd()
        self.database = self.DEFAULT_DB_ARG

    def run(self) -> None:
        """
        Convert legacy arguments to current spec required by Alembic,
        then add db url arguments required by Alembic
        """
        self.convert_args()
        add_db_urls_to_command_arguments(self.argv, self.gxy_url, self.tsi_url)

    def convert_args(self) -> None:
        """
        Convert legacy arguments to current spec required by Alembic.

        Note: The following method calls must be done in this sequence.
        """
        self.pop_database_argument()
        self.rename_config_argument()
        self.rename_alembic_config_argument()
        self.load_db_urls()
        self.convert_version_argument()

    def pop_database_argument(self) -> None:
        """
        If last argument is a valid database name, pop and assign it; otherwise assign default.
        """
        arg = self.argv[-1]
        if arg in ["galaxy", "install"]:
            self.database = self.argv.pop()

    def rename_config_argument(self) -> None:
        """
        Rename the optional config argument: we can't use '-c' because that option is used by Alembic.
        """
        for arg in self.LEGACY_CONFIG_FILE_ARG_NAMES:
            if arg in self.argv:
                self._rename_arg(arg, CONFIG_FILE_ARG)
                return

    def rename_alembic_config_argument(self) -> None:
        """
        Rename argument name: `--alembic-config` to `-c`. There should be no `-c` argument present.
        """
        if "-c" in self.argv:
            raise LegacyScriptsException("Cannot rename alembic config argument: `-c` argument present.")
        self._rename_arg(self.ALEMBIC_CONFIG_FILE_ARG, "-c")

    def convert_version_argument(self) -> None:
        """
        Convert legacy version argument to current spec required by Alembic.
        """
        if "--version" in self.argv:
            # Just remove it: the following argument should be the version/revision identifier.
            pos = self.argv.index("--version")
            self.argv.pop(pos)
        else:
            # If we find --version=foo, extract foo and replace arg with foo (which is the revision identifier)
            p = re.compile(r"--version=([0-9A-Fa-f]+)")
            for i, arg in enumerate(self.argv):
                m = p.match(arg)
                if m:
                    self.argv[i] = m.group(1)
                    return
            # No version argument found: construct argument for an upgrade operation.
            # Raise exception otherwise.
            if "upgrade" not in self.argv:
                raise LegacyScriptsException("If no `--version` argument supplied, `upgrade` argument is requried")

            if self._is_one_database():  # upgrade both regardless of database argument
                self.argv.append("heads")
            else:  # for separate databases, choose one
                if self.database in ["galaxy", self.DEFAULT_DB_ARG]:
                    self.argv.append("gxy@head")
                elif self.database == "install":
                    self.argv.append("tsi@head")

    def _rename_arg(self, old_name, new_name) -> None:
        pos = self.argv.index(old_name)
        self.argv[pos] = new_name

    def load_db_urls(self) -> None:
        gxy_config, tsi_config, _ = get_configuration(self.argv, self.cwd)
        self.gxy_url = gxy_config.url
        self.tsi_url = tsi_config.url

    def _is_one_database(self):
        return is_one_database(self.gxy_url, self.tsi_url)


class LegacyManageDb:
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
                    raise IncorrectVersionError(GXY, SQLALCHEMYMIGRATE_LAST_VERSION_GXY)
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

    def _upgrade(self, db_url, model):
        try:
            engine = create_engine(db_url)
            am = get_alembic_manager(engine)
            am.upgrade(model)
        finally:
            engine.dispose()

    def _set_db_urls(self):
        ls = LegacyScripts(sys.argv, os.getcwd())
        ls.rename_config_argument()
        ls.load_db_urls()
        self.gxy_db_url = ls.gxy_url
        self.tsi_db_url = ls.tsi_url

    def _get_gxy_sam_db_version(self, engine):
        dbcache = DatabaseStateCache(engine)
        return dbcache.sqlalchemymigrate_version

    def _get_script_directory(self):
        alembic_cfg = self._get_alembic_cfg()
        return ScriptDirectory.from_config(alembic_cfg)

    def _get_alembic_cfg(self):
        config_file = os.path.join(os.path.dirname(__file__), "alembic.ini")
        config_file = os.path.abspath(config_file)
        return Config(config_file)

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


def get_alembic_manager(engine: Engine) -> AlembicManager:
    return AlembicManager(engine)
