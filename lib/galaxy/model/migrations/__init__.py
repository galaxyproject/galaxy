import logging
import os
import urllib.parse
from typing import (
    cast,
    Dict,
    Iterable,
    NamedTuple,
    NewType,
    NoReturn,
    Optional,
    Union,
)

import alembic
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from alembic.script.base import Script
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    text,
)
from sqlalchemy.engine import (
    Connection,
    CursorResult,
    Engine,
)

from galaxy.model import Base as gxy_base
from galaxy.model.database_utils import (
    create_database,
    database_exists,
)
from galaxy.model.mapping import create_additional_database_objects
from galaxy.model.tool_shed_install import Base as tsi_base

ModelId = NewType("ModelId", str)
# These identifiers are used throughout the migrations system to distinquish
# between the two models; they refer to version directories, branch labels, etc.
# (if you rename these, you need to rename branch labels in alembic version directories)
GXY = ModelId("gxy")  # galaxy model identifier
TSI = ModelId("tsi")  # tool_shed_install model identifier

ALEMBIC_TABLE = "alembic_version"
SQLALCHEMYMIGRATE_TABLE = "migrate_version"
SQLALCHEMYMIGRATE_LAST_VERSION_GXY = 180
SQLALCHEMYMIGRATE_LAST_VERSION_TSI = 17
log = logging.getLogger(__name__)


class DatabaseConfig(NamedTuple):
    url: str
    template: str
    encoding: str


class NoVersionTableError(Exception):
    # The database has no version table (neither SQLAlchemy Migrate, nor Alembic), so it is
    # impossible to automatically determine the state of the database. Manual update required.
    def __init__(self, model: str) -> None:
        super().__init__(f"Your {model} database has no version table; manual update is required")


class IncorrectVersionError(Exception):
    # The database has a SQLAlchemy Migrate version table, but its version is either older or more recent
    # than {SQLALCHEMYMIGRATE_LAST_VERSION_GXY/TSI}, so it cannot be upgraded with Alembic.
    # (A more recent version may indicate that something has changed in the database past the point
    # where we can automatically migrate from SQLAlchemy Migrate to Alembic.)
    # Manual update required.
    def __init__(self, model: str, expected_version: int) -> None:
        msg = f"Your {model} database version is incorrect; version {expected_version} is expected. "
        msg += "Manual update is required. "
        msg += "Please see this issue: https://github.com/galaxyproject/galaxy/issues/13528"
        super().__init__(msg)


class OutdatedDatabaseError(Exception):
    # The database is under Alembic version control, but is out-of-date. Automatic upgrade possible.
    def __init__(self, model: str) -> None:
        msg = f"Your {model} database is out-of-date; automatic update requires setting `database_auto_migrate`"
        super().__init__(msg)


class InvalidModelIdError(Exception):
    def __init__(self, model: str) -> None:
        super().__init__(f"Invalid model: {model}")


class RevisionNotFoundError(Exception):
    # The database has an Alembic version table; however, that table does not contain a revision identifier
    # for the given model. As a result, it is impossible to determine the state of the database for this model
    # (gxy or tsi).
    def __init__(self, model: str) -> None:
        msg = "The database has an alembic version table, but that table does not contain "
        msg += f"a revision for the {model} model"
        super().__init__(msg)


class AlembicManager:
    """
    Alembic operations on one database.
    """

    @staticmethod
    def is_at_revision(engine: Engine, revision: Union[str, Iterable[str]]) -> bool:
        """
        True if revision is a subset of the set of version heads stored in the database.
        """
        revision = listify(revision)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            db_version_heads = context.get_current_heads()
            return set(revision) <= set(db_version_heads)

    def __init__(self, engine: Engine, config_dict: Optional[dict] = None) -> None:
        self.engine = engine
        self.alembic_cfg = self._load_config(config_dict)
        self.script_directory = ScriptDirectory.from_config(self.alembic_cfg)
        self._db_heads: Optional[Iterable[str]]
        self._reset_db_heads()

    def _load_config(self, config_dict: Optional[dict]) -> Config:
        alembic_root = os.path.dirname(__file__)
        _alembic_file = os.path.join(alembic_root, "alembic.ini")
        config = Config(_alembic_file)
        url = get_url_string(self.engine)
        config.set_main_option("sqlalchemy.url", url)
        if config_dict:
            for key, value in config_dict.items():
                config.set_main_option(key, value)
        return config

    def stamp_model_head(self, model: ModelId) -> None:
        """Partial proxy to alembic's stamp command."""
        command.stamp(self.alembic_cfg, f"{model}@head")
        self._reset_db_heads()

    def stamp_revision(self, revision: Union[str, Iterable[str]]) -> None:
        """Partial proxy to alembic's stamp command."""
        command.stamp(self.alembic_cfg, revision)  # type: ignore[arg-type]  # https://alembic.sqlalchemy.org/en/latest/api/commands.html#alembic.command.stamp.params.revision
        self._reset_db_heads()

    def upgrade(self, model: ModelId) -> None:
        """Partial proxy to alembic's upgrade command."""
        # This works with or without an existing alembic version table.
        command.upgrade(self.alembic_cfg, f"{model}@head")
        self._reset_db_heads()

    def is_under_version_control(self, model: ModelId) -> bool:
        """
        True if the database version table contains a revision that corresponds to a revision
        in the script directory that has branch label `model`.
        """
        if self.db_heads:
            for db_head in self.db_heads:
                try:
                    revision = self._get_revision(db_head)
                    if revision and model in revision.branch_labels:
                        log.info(f"The version of the {model} model in the database is {db_head}.")
                        return True
                except alembic.util.exc.CommandError:  # No need to raise exception.
                    log.info(f"Revision {db_head} does not exist in the script directory.")
        return False

    def is_up_to_date(self, model: ModelId) -> bool:
        """
        True if the head revision for `model` in the script directory is stored
        in the database.
        """
        head_id = self.get_model_script_head(model)
        return bool(self.db_heads and head_id in self.db_heads)

    def get_model_db_head(self, model: ModelId) -> Optional[str]:
        return self._get_head_revision(model, cast(Iterable[str], self.db_heads))

    def get_model_script_head(self, model: ModelId) -> Optional[str]:
        return self._get_head_revision(model, self.script_directory.get_heads())

    def _get_head_revision(self, model: ModelId, heads: Iterable[str]) -> Optional[str]:
        for head in heads:
            revision = self._get_revision(head)
            if revision and model in revision.branch_labels:
                return head
        return None

    @property
    def db_heads(self) -> Iterable:
        if self._db_heads is None:  # Explicitly check for None: could be an empty tuple.
            with self.engine.connect() as conn:
                context: MigrationContext = MigrationContext.configure(conn)
                self._db_heads = context.get_current_heads()
            # We get a tuple as long as we use branches. Otherwise, we'd get a single value.
            # listify() is a safeguard in case we stop using branches.
            self._db_heads = listify(self._db_heads)
        return self._db_heads

    def _get_revision(self, revision_id: str) -> Optional[Script]:
        try:
            return self.script_directory.get_revision(revision_id)
        except alembic.util.exc.CommandError as e:
            log.error(f"Revision {revision_id} not found in the script directory")
            raise e

    def _reset_db_heads(self) -> None:
        self._db_heads = None


class DatabaseStateCache:
    """
    Snapshot of database state.
    """

    def __init__(self, engine: Engine) -> None:
        self._load_db(engine)

    @property
    def tables(self) -> Dict[str, Table]:
        return self.db_metadata.tables

    def is_database_empty(self) -> bool:
        return not bool(self.db_metadata.tables)

    def contains_only_kombu_tables(self) -> bool:
        return metadata_contains_only_kombu_tables(self.db_metadata)

    def has_alembic_version_table(self) -> bool:
        return ALEMBIC_TABLE in self.db_metadata.tables

    def has_sqlalchemymigrate_version_table(self) -> bool:
        return SQLALCHEMYMIGRATE_TABLE in self.db_metadata.tables

    def is_last_sqlalchemymigrate_version(self, last_version: int) -> bool:
        return self.sqlalchemymigrate_version == last_version

    def _load_db(self, engine: Engine) -> None:
        with engine.connect() as conn:
            self.db_metadata = self._load_db_metadata(conn)
            self.sqlalchemymigrate_version = self._load_sqlalchemymigrate_version(conn)

    def _load_db_metadata(self, conn: Connection) -> MetaData:
        metadata = MetaData()
        metadata.reflect(bind=conn)
        return metadata

    def _load_sqlalchemymigrate_version(self, conn: Connection) -> CursorResult:
        if self.has_sqlalchemymigrate_version_table():
            sql = text(f"select version from {SQLALCHEMYMIGRATE_TABLE}")
            return conn.execute(sql).scalar()


def metadata_contains_only_kombu_tables(metadata: MetaData) -> bool:
    """
    Return True if metadata contains only kombu-related tables.
    (ref: https://github.com/galaxyproject/galaxy/issues/13689)
    """
    return all(table.startswith("kombu_") or table.startswith("sqlite_") for table in metadata.tables.keys())


def verify_databases_via_script(
    gxy_config: DatabaseConfig,
    tsi_config: DatabaseConfig,
    is_auto_migrate: bool = False,
) -> None:
    # This function serves a use case when an engine has not been created yet
    # (e.g. when called from a script).
    gxy_engine = create_engine(gxy_config.url)
    tsi_engine = None
    if tsi_config.url and tsi_config.url != gxy_config.url:
        tsi_engine = create_engine(tsi_config.url)

    verify_databases(
        gxy_engine,
        gxy_config.template,
        gxy_config.encoding,
        tsi_engine,
        tsi_config.template,
        tsi_config.encoding,
        is_auto_migrate,
    )
    gxy_engine.dispose()
    if tsi_engine:
        tsi_engine.dispose()


def verify_databases(
    gxy_engine: Engine,
    gxy_template: Optional[str],
    gxy_encoding: Optional[str],
    tsi_engine: Optional[Engine],
    tsi_template: Optional[str],
    tsi_encoding: Optional[str],
    is_auto_migrate: bool,
) -> None:
    # Verify gxy model.
    gxy_verifier = DatabaseStateVerifier(gxy_engine, GXY, gxy_template, gxy_encoding, is_auto_migrate)
    gxy_verifier.run()

    # New database = one engine or same engine, and gxy model has just been initialized.
    is_new_database = (not tsi_engine or gxy_engine == tsi_engine) and gxy_verifier.is_new_database

    # Determine engine for tsi model.
    tsi_engine = tsi_engine or gxy_engine

    # Verify tsi model model.
    tsi_verifier = DatabaseStateVerifier(tsi_engine, TSI, tsi_template, tsi_encoding, is_auto_migrate, is_new_database)
    tsi_verifier.run()


class DatabaseStateVerifier:
    def __init__(
        self,
        engine: Engine,
        model: ModelId,
        database_template: Optional[str],
        database_encoding: Optional[str],
        is_auto_migrate: bool,
        is_new_database: Optional[bool] = False,
    ) -> None:
        self.engine = engine
        self.model = model
        self.database_template = database_template
        self.database_encoding = database_encoding
        self._is_auto_migrate = is_auto_migrate
        self.metadata = get_metadata(model)
        # True if database has been initialized for another model.
        self.is_new_database = is_new_database
        # These values may or may not be required, so do a lazy load.
        self._db_state: Optional[DatabaseStateCache] = None
        self._alembic_manager: Optional[AlembicManager] = None

    @property
    def is_auto_migrate(self) -> bool:
        return self._is_auto_migrate

    @property
    def db_state(self) -> DatabaseStateCache:
        if not self._db_state:
            self._db_state = DatabaseStateCache(engine=self.engine)
        return self._db_state

    @property
    def alembic_manager(self) -> AlembicManager:
        if not self._alembic_manager:
            self._alembic_manager = get_alembic_manager(self.engine)
        return self._alembic_manager

    def run(self) -> None:
        if self._handle_no_database():
            return
        if self._handle_empty_database():
            return
        self._handle_nonempty_database()

    def _handle_no_database(self) -> bool:
        url = get_url_string(self.engine)
        if not database_exists(url):
            self._create_database(url)
            self._initialize_database()
            return True
        return False

    def _handle_empty_database(self) -> bool:
        if self.is_new_database or self._is_database_empty() or self._contains_only_kombu_tables():
            self._initialize_database()
            return True
        return False

    def _handle_nonempty_database(self) -> None:
        if self._has_alembic_version_table():
            self._handle_with_alembic()
        elif self._has_sqlalchemymigrate_version_table():
            if self._is_last_sqlalchemymigrate_version():
                self._try_to_upgrade()
            else:
                self._handle_wrong_sqlalchemymigrate_version()
        else:
            self._handle_no_version_table()

    def _handle_with_alembic(self) -> None:
        am = self.alembic_manager
        model = self._get_model_name()

        if am.is_up_to_date(self.model):
            log.info(f"Your {model} database is up-to-date")
            return
        if am.is_under_version_control(self.model):
            # Model is under version control, but outdated. Try to upgrade.
            self._try_to_upgrade()
        else:
            # Model is not under version control. We fail for the gxy model because we can't guess
            # what the state of the database is if there is an alembic table without a gxy revision.
            # For the tsi model, we can guess. If there are no tsi tables in the database, we  treat it
            # as a new install; but if there is at least one table, we assume it is the same version as gxy.
            # See more details in this PR description: https://github.com/galaxyproject/galaxy/pull/13108
            if self.model == TSI:
                if self._no_model_tables_exist():
                    self._initialize_database()
                else:
                    self._try_to_upgrade()
            else:
                raise RevisionNotFoundError(model)

    def _try_to_upgrade(self):
        am = self.alembic_manager
        model = self._get_model_name()
        code_version = am.get_model_script_head(self.model)
        if not self.is_auto_migrate:
            db_version = am.get_model_db_head(self.model)
            msg = self._get_upgrade_message(model, cast(str, db_version), cast(str, code_version))
            log.warning(msg)
            raise OutdatedDatabaseError(model)
        else:
            log.info("Database is being upgraded to current version: {code_version}")
            am.upgrade(self.model)
            return

    def _get_upgrade_message(self, model: str, db_version: str, code_version: str) -> str:
        msg = f"Your {model} database has version {db_version}, but this code expects "
        msg += f"version {code_version}. "
        msg += "This database can be upgraded automatically if database_auto_migrate is set. "
        msg += "To upgrade manually, run `run_alembic.sh` (see instructions in that file). "
        msg += "Please remember to backup your database before migrating."
        return msg

    def _get_model_name(self) -> str:
        return "galaxy" if self.model == GXY else "tool shed install"

    def _no_model_tables_exist(self) -> bool:
        # True if there are no tables from `self.model` in the database.
        db_tables = self.db_state.tables
        for tablename in set(self.metadata.tables) - {ALEMBIC_TABLE}:
            if tablename in db_tables:
                return False
        return True

    def _create_database(self, url: str) -> None:
        create_kwds = {}
        message = f"Creating database for URI [{url}]"
        if self.database_template:
            message += f" from template [{self.database_template}]"
            create_kwds["template"] = self.database_template
        if self.database_encoding:
            message += f" with encoding [{self.database_encoding}]"
            create_kwds["encoding"] = self.database_encoding
        log.info(message)
        create_database(url, **create_kwds)

    def _initialize_database(self) -> None:
        load_metadata(self.metadata, self.engine)
        if self.model == GXY:
            self._create_additional_database_objects()
        self.alembic_manager.stamp_model_head(self.model)
        self.is_new_database = True

    def _create_additional_database_objects(self) -> None:
        create_additional_database_objects(self.engine)

    def _is_database_empty(self) -> bool:
        return self.db_state.is_database_empty()

    def _contains_only_kombu_tables(self) -> bool:
        return self.db_state.contains_only_kombu_tables()

    def _has_alembic_version_table(self) -> bool:
        return self.db_state.has_alembic_version_table()

    def _has_sqlalchemymigrate_version_table(self) -> bool:
        return self.db_state.has_sqlalchemymigrate_version_table()

    def _is_last_sqlalchemymigrate_version(self) -> bool:
        last_version = get_last_sqlalchemymigrate_version(self.model)
        return self.db_state.is_last_sqlalchemymigrate_version(last_version)

    def _handle_no_version_table(self) -> NoReturn:
        model = self._get_model_name()
        raise NoVersionTableError(model)

    def _handle_wrong_sqlalchemymigrate_version(self) -> NoReturn:
        if self.model == GXY:
            expected_version = SQLALCHEMYMIGRATE_LAST_VERSION_GXY
        else:
            expected_version = SQLALCHEMYMIGRATE_LAST_VERSION_TSI
        model = self._get_model_name()
        raise IncorrectVersionError(model, expected_version)


def get_last_sqlalchemymigrate_version(model: ModelId) -> int:
    if model == GXY:
        return SQLALCHEMYMIGRATE_LAST_VERSION_GXY
    elif model == TSI:
        return SQLALCHEMYMIGRATE_LAST_VERSION_TSI
    else:
        raise InvalidModelIdError(model)


def get_url_string(engine: Engine) -> str:
    db_url = engine.url.render_as_string(hide_password=False)
    return urllib.parse.unquote(db_url)


def get_alembic_manager(engine: Engine) -> AlembicManager:
    return AlembicManager(engine)


def get_metadata(model: ModelId) -> MetaData:
    if model == GXY:
        return get_gxy_metadata()
    elif model == TSI:
        return get_tsi_metadata()
    else:
        raise InvalidModelIdError(model)


def load_metadata(metadata: MetaData, engine: Engine) -> None:
    with engine.connect() as conn:
        metadata.create_all(bind=conn)


def listify(data: Union[str, Iterable[str]]) -> Iterable[str]:
    if not isinstance(data, (list, tuple)):
        return [cast(str, data)]
    return data


def get_gxy_metadata() -> MetaData:
    return gxy_base.metadata


def get_tsi_metadata() -> MetaData:
    return tsi_base.metadata
