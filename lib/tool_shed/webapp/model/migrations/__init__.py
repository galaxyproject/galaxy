import logging
import os
from typing import (
    cast,
    Iterable,
    Optional,
)

import alembic
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from galaxy.model.database_utils import (
    create_database,
    database_exists,
)
from galaxy.model.migrations.base import (
    BaseAlembicManager,
    DatabaseStateCache,
    get_url_string,
    load_metadata,
)
from galaxy.model.migrations.exceptions import (
    IncorrectSAMigrateVersionError,
    NoVersionTableError,
    OutdatedDatabaseError,
    SAMigrateError,
)
from tool_shed.webapp.model import Base

SQLALCHEMYMIGRATE_LAST_VERSION = 27
TOOLSHED = "tool shed"

log = logging.getLogger(__name__)


class RevisionNotFoundError(Exception):
    # The database has an Alembic version table; however, that table is either empty,
    # or it does not contain a revision id that matches a revision in the code base.
    # As a result, it is impossible to determine the state of the database.
    def __init__(self) -> None:
        msg = f"The {TOOLSHED} database has an alembic version table, but that table does not contain "
        msg += "a revision id that matches a revision in the code base."
        super().__init__(msg)


def verify_database(url, engine_options=None) -> None:
    engine_options = engine_options or {}
    engine = create_engine(url, **engine_options)
    verifier = DatabaseStateVerifier(engine)
    verifier.run()
    engine.dispose()


class AlembicManager(BaseAlembicManager):
    def _get_alembic_root(self) -> str:
        return os.path.dirname(__file__)

    def stamp_head(self) -> None:
        self.stamp_revision("head")

    def is_up_to_date(self) -> bool:
        """
        True if the head revision in the script directory is stored in the database.
        """
        head_id = self.get_script_head()
        return bool(self.db_heads and head_id in self.db_heads)

    def is_under_version_control(self) -> bool:
        """
        True if the database version table contains a revision that corresponds to a revision
        in the script directory.
        """
        if self.db_heads:
            for db_head in self.db_heads:
                try:
                    revision = self._get_revision(db_head)
                    if revision:
                        log.info(f"The version in the database is {db_head}.")
                        return True
                except alembic.util.exc.CommandError:  # No need to raise exception.
                    log.info(f"Revision {db_head} does not exist in the script directory.")
        return False

    def get_db_head(self) -> Optional[str]:
        return self._get_head_revision(cast(Iterable[str], self.db_heads))

    def get_script_head(self) -> Optional[str]:
        return self.script_directory.get_current_head()

    def _get_head_revision(self, heads: Iterable[str]) -> Optional[str]:
        for head in heads:
            if self._get_revision(head):
                return head
        return None


class DatabaseStateVerifier:
    def __init__(self, engine):
        self.engine = engine
        self.metadata = Base.metadata
        # These values may or may not be required, so do a lazy load.
        self._db_state: Optional[DatabaseStateCache] = None
        self._alembic_manager: Optional[AlembicManager] = None

    @property
    def db_state(self) -> DatabaseStateCache:
        if not self._db_state:
            self._db_state = DatabaseStateCache(engine=self.engine)
        return self._db_state

    @property
    def alembic_manager(self) -> AlembicManager:
        if not self._alembic_manager:
            self._alembic_manager = AlembicManager(self.engine)
        return self._alembic_manager

    def run(self) -> None:
        if self._handle_no_database():
            return
        if self._handle_empty_database():
            return
        self._handle_nonempty_database()

    def _handle_no_database(self) -> bool:
        url = get_url_string(self.engine)

        try:
            # connect using the database name from the sqlalchemy engine
            exists = database_exists(url, database=self.engine.url.database)
        except OperationalError:
            exists = False

        if not exists:
            self._create_database(url)
            self._initialize_database()
            return True
        return False

    def _handle_empty_database(self) -> bool:
        if self._is_database_empty():
            self._initialize_database()
            return True
        return False

    def _handle_nonempty_database(self) -> None:
        if self._has_alembic_version_table():
            self._handle_with_alembic()
        elif self._has_sqlalchemymigrate_version_table():
            if self._is_last_sqlalchemymigrate_version():
                script = self._upgrade_script()
                raise SAMigrateError(TOOLSHED, script)
            else:
                raise IncorrectSAMigrateVersionError(TOOLSHED, SQLALCHEMYMIGRATE_LAST_VERSION)
        else:
            raise NoVersionTableError(TOOLSHED)

    def _handle_with_alembic(self) -> None:
        am = self.alembic_manager
        if am.is_up_to_date():
            log.info(f"Your {TOOLSHED} database is up-to-date")
            return
        if am.is_under_version_control():
            code_version = am.get_script_head()
            db_version = am.get_db_head()
            script = self._upgrade_script()
            raise OutdatedDatabaseError(TOOLSHED, cast(str, db_version), cast(str, code_version), script)
        else:
            raise RevisionNotFoundError()

    def _create_database(self, url: str) -> None:
        log.info(f"Creating database for URI [{url}]")
        create_database(url)

    def _initialize_database(self) -> None:
        load_metadata(self.metadata, self.engine)
        self.alembic_manager.stamp_head()

    def _is_database_empty(self) -> bool:
        return self.db_state.is_database_empty()

    def _has_alembic_version_table(self) -> bool:
        return self.db_state.has_alembic_version_table()

    def _has_sqlalchemymigrate_version_table(self) -> bool:
        return self.db_state.has_sqlalchemymigrate_version_table()

    def _is_last_sqlalchemymigrate_version(self) -> bool:
        return self.db_state.is_last_sqlalchemymigrate_version(SQLALCHEMYMIGRATE_LAST_VERSION)

    def _upgrade_script(self) -> str:
        return "manage_toolshed_db.sh upgrade"
