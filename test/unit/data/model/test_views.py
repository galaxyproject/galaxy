import pytest
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
)
from sqlalchemy.sql import (
    column,
    text,
)

from galaxy.model.database_utils import (
    create_database,
    sqlalchemy_engine,
)
from galaxy.model.view.utils import (
    CreateView,
    View,
)
from .testing_utils import (
    drop_database,
    replace_database_in_url,
    skip_if_not_mysql_uri,
    skip_if_not_postgres_uri,
)


@pytest.fixture
def view():
    # A View class we would add to galaxy.model.view
    class TestView(View):
        name = "testview"
        __view__ = text("SELECT id, foo FROM testfoo").columns(column("id", Integer), column("foo", Integer))
        pkeys = {"id"}
        View._make_table(name, __view__, pkeys)

    return TestView


@skip_if_not_postgres_uri
def test_postgres_create_view(database_name, postgres_url, view):
    metadata = MetaData()
    make_table(metadata)  # table from which the view will select
    url = replace_database_in_url(postgres_url, database_name)
    query = f"SELECT 1 FROM information_schema.views WHERE table_name = '{view.name}'"
    create_database(postgres_url, database_name)
    run_view_test(url, metadata, view, query)
    drop_database(postgres_url, database_name)


def test_sqlite_create_view(sqlite_memory_url, view):
    metadata = MetaData()
    make_table(metadata)  # table from which the view will select
    url = sqlite_memory_url
    query = f"SELECT 1 FROM sqlite_master WHERE type='view' AND name='{view.name}'"
    run_view_test(url, metadata, view, query)


@skip_if_not_mysql_uri
def test_mysql_create_view(database_name, mysql_url, view):
    metadata = MetaData()
    make_table(metadata)  # table from which the view will select
    url = replace_database_in_url(mysql_url, database_name)
    query = f"SELECT 1 FROM information_schema.views WHERE table_name = '{view.name}'"
    create_database(mysql_url, database_name)
    run_view_test(url, metadata, view, query)
    drop_database(mysql_url, database_name)


def make_table(metadata):
    users = Table(
        "testfoo", metadata, Column("id", Integer, primary_key=True), Column("foo", Integer), Column("bar", Integer)
    )
    return users


def run_view_test(url, metadata, view, query):
    with sqlalchemy_engine(url) as engine:
        with engine.begin() as conn:
            metadata.create_all(conn)  # create table in database
            conn.execute(CreateView(view.name, view.__view__))  # create view in database
            result = conn.execute(text(query)).fetchall()
            assert len(result) == 1  # assert that view exists in database
