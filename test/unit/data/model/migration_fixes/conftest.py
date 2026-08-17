import tempfile
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
)
from sqlalchemy.orm import (
    make_transient_to_detached,
    Session,
)
from sqlalchemy.pool import NullPool

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

from galaxy import model as m
from galaxy.model.unittest_utils.model_testing_utils import (
    _generate_unique_database_name,
    _make_sqlite_db_url,
)
from galaxy.model.unittest_utils.utils import (
    random_email,
    random_str,
)


@pytest.fixture(scope="module")
def sqlite_url_factory():
    """Return a function that generates a sqlite url"""

    def url():
        database = _generate_unique_database_name()
        return _make_sqlite_db_url(tmp_dir, database)

    with tempfile.TemporaryDirectory() as tmp_dir:
        yield url


@pytest.fixture(scope="module")
def db_url(sqlite_url_factory):  # noqa: F811
    return sqlite_url_factory()


@pytest.fixture()
def engine(db_url: str) -> "Engine":
    # NullPool so each operation opens a fresh connection. These tests run
    # migrations in a separate process, and a pooled connection carries a cached
    # schema across that DDL - harmless while the model and the schema agree, but
    # it reads a stale table definition once a migration adds a column.
    return create_engine(db_url, poolclass=NullPool)


@pytest.fixture
def session(engine: "Engine") -> Session:
    # expire_on_commit is off because these tests hold instances across commits
    # while the schema is deliberately behind the model: an expired instance would
    # be re-SELECTed, naming columns the older schema does not have. The tests
    # call expire_all() explicitly once the migration has run, which is the point
    # at which a fresh read is wanted.
    return Session(engine, expire_on_commit=False)


@pytest.fixture
def make_user(session):
    """Create a user without the ORM naming columns the live schema may not have.

    These tests downgrade the schema below the current model, and the ORM always
    reflects the model at head. An ORM insert therefore names every mapped
    column, including any added after the revision under test, and fails.

    So the row is written through the reflected table - keeping the column list
    in step with whatever revision is applied - and the resulting instance is
    merged into the session with ``load=False``, which registers it as persistent
    without issuing a SELECT. Callers get an ordinary ORM object whose attributes
    are already populated, so assertions and relationship loads behave as before.

    When a future migration adds a column to another table used here, the same
    treatment will be needed for that table's fixture.
    """

    def f(**kwd):
        kwd.setdefault("username", random_str())
        kwd.setdefault("email", random_email())
        kwd.setdefault("password", random_str())
        now = datetime.utcnow()
        kwd.setdefault("create_time", now)
        kwd.setdefault("update_time", now)
        kwd.setdefault("external", False)
        kwd.setdefault("deleted", False)
        kwd.setdefault("purged", False)
        kwd.setdefault("active", False)

        table = Table("galaxy_user", MetaData(), autoload_with=session.get_bind())
        values = {key: value for key, value in kwd.items() if key in table.c}
        result = session.execute(table.insert().values(**values))

        user = m.User()
        for key, value in values.items():
            setattr(user, key, value)
        user.id = result.inserted_primary_key[0]
        # The row exists, so present the instance as detached rather than new;
        # merge(load=False) refuses transient objects and would otherwise SELECT.
        make_transient_to_detached(user)
        merged = session.merge(user, load=False)
        # Commit last, so no transaction is left open. These tests run migrations
        # in a separate process, and a connection held open across that DDL would
        # keep reading the pre-migration schema afterwards.
        session.commit()
        return merged

    return f
