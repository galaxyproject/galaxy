class NoVersionTableError(Exception):
    # The database has no version table (neither SQLAlchemy Migrate, nor Alembic), so it is
    # impossible to automatically determine the state of the database. Manual update required.
    def __init__(self, db_or_model: str) -> None:
        super().__init__(f"Your {db_or_model} database has no version table; manual update is required")


class SAMigrateError(Exception):
    def __init__(self, db_or_model: str, upgrade_script: str) -> None:
        msg = f"Your {db_or_model} database is currently under SQLAlchemy Migrate version control "
        msg += "and must be upgraded to Alembic."
        msg += f"\nTo upgrade your database, run `{upgrade_script}`. "
        super().__init__(msg)


class IncorrectSAMigrateVersionError(Exception):
    # The database has a SQLAlchemy Migrate version table, but its version is either older or more recent
    # than {SQLALCHEMYMIGRATE_LAST_VERSION_GXY/TSI}, so it cannot be upgraded with Alembic.
    # (A more recent version may indicate that something has changed in the database past the point
    # where we can automatically migrate from SQLAlchemy Migrate to Alembic.)
    # Manual update required.
    def __init__(self, db_or_model: str, expected_version: int) -> None:
        msg = f"Your {db_or_model} database is currently under SQLAlchemy Migrate version control and must be upgraded."
        msg += "\nThe upgrade process consists of two steps:"
        msg += f"\nStep 1: Upgrade to the correct version under SQLAlchemy Migrate (version {expected_version})"
        msg += "\nStep 2: Upgrade to the current version under Alembic."
        msg += "\nManual update is required. "
        msg += "\nPlease see documentation: https://docs.galaxyproject.org/en/master/admin/db_migration.html#how-to-handle-migrations-incorrectversionerror"
        super().__init__(msg)


class OutdatedDatabaseError(Exception):
    # The database is (or can be placed) under Alembic version control, but is out-of-date.
    # Automatic upgrade possible.
    def __init__(self, db_or_model: str, db_version: str, code_version: str, upgrade_script: str) -> None:
        msg = f"Your {db_or_model} database has version {db_version}, but this code expects "
        msg += f"version {code_version}. "
        msg += f"To upgrade your database, run `{upgrade_script}`. "
        msg += "For more options (e.g. upgrading/downgrading to a specific version) see instructions in that file. "
        msg += "Please remember to backup your database before migrating."
        super().__init__(msg)


class RevisionNotFoundError(Exception):
    # The database has an Alembic version table; however, that table does not contain a revision identifier
    # for the given model. As a result, it is impossible to determine the state of the database for this model
    # (gxy or tsi).
    def __init__(self, db_or_model: str) -> None:
        msg = "The database has an alembic version table, but that table does not contain "
        msg += f"a revision for the {db_or_model} model"
        super().__init__(msg)


class DatabaseDoesNotExistError(Exception):
    def __init__(self, db_url: str) -> None:
        super().__init__(
            f"""The database at {db_url} does not exist. You must
            create and initialize the database before running this script. You
            can do so by (a) running `create_db.sh`; or by (b) starting Galaxy,
            in which case Galaxy will create and initialize the database
            automatically."""
        )


class DatabaseNotInitializedError(Exception):
    def __init__(self, db_url: str) -> None:
        super().__init__(
            f"""The database at {db_url} is empty. You must
            initialize the database before running this script. You can do so by
            (a) running `create_db.sh`; or by (b) starting Galaxy, in which case
            Galaxy will initialize the database automatically."""
        )
