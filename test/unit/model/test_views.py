import pytest
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
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
from .common import (
    drop_database,
    replace_database_in_url,
    skip_if_not_postgres_uri,
)


@pytest.fixture
def view():
    # A View class we would add to galaxy.model.view
    class TestView(View):
        name = 'testview'
        __view__ = text('select id, first_name from testusers').columns(
            column('id', Integer),
            column('first_name', String)
        )
        pkeys = {'id'}
        View._make_table(name, __view__, pkeys)

    return TestView


@skip_if_not_postgres_uri
def test_postgres_create_view(database_name, postgres_url, view):
    metadata = MetaData()
    make_table(metadata)  # table from which the view will select
    create_database(postgres_url, database_name)

    url = replace_database_in_url(postgres_url, database_name)
    with sqlalchemy_engine(url) as engine:
        with engine.connect() as conn:
            metadata.create_all(conn)  # create table in database
            conn.execute(CreateView(view.name, view.__view__))  # create view in database
            query = f"select * from information_schema.tables where table_name = '{view.name}' and table_type = 'VIEW'"
            result = conn.execute(query)
            assert result.rowcount == 1  # assert that view exists in database

    drop_database(postgres_url, database_name)


def test_sqlite_create_view(sqlite_memory_url, view):
    metadata = MetaData()
    make_table(metadata)  # table from which the view will select

    with sqlalchemy_engine(sqlite_memory_url) as engine:
        with engine.connect() as conn:
            metadata.create_all(conn)  # create table in database
            conn.execute(CreateView(view.name, view.__view__))  # create view in database
            query = f"SELECT name FROM sqlite_master WHERE type='view' AND name='{view.name}'"
            result = conn.execute(query).fetchall()
            assert len(result) == 1  # assert that view exists in database


def make_table(metadata):
    users = Table('testusers', metadata,
        Column('id', Integer, primary_key=True),
        Column('first_name', String),
        Column('last_name', String)
    )
    return users
