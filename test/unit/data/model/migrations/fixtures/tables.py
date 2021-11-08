"""
Fixture factories: metadata containing one table each.
Used to compose metadata representing database state.
(The `_factory` suffix is ommitted to keep the code less verbose)
"""
import pytest
import sqlalchemy as sa


@pytest.fixture
def gxy_table1():
    def make_table(metadata):
        return sa.Table('gxy_table1', metadata, sa.Column('id', sa.Integer, primary_key=True))
    return make_table


@pytest.fixture
def gxy_table2():
    def make_table(metadata):
        return sa.Table('gxy_table2', metadata, sa.Column('id', sa.Integer, primary_key=True))
    return make_table


@pytest.fixture
def gxy_table3():
    def make_table(metadata):
        return sa.Table('gxy_table3', metadata, sa.Column('id', sa.Integer, primary_key=True))
    return make_table


@pytest.fixture
def tsi_table1():
    def make_table(metadata):
        return sa.Table('tsi_table1', metadata, sa.Column('id', sa.Integer, primary_key=True))
    return make_table


@pytest.fixture
def tsi_table2():
    def make_table(metadata):
        return sa.Table('tsi_table2', metadata, sa.Column('id', sa.Integer, primary_key=True))
    return make_table


@pytest.fixture
def tsi_table3():
    def make_table(metadata):
        return sa.Table('tsi_table3', metadata, sa.Column('id', sa.Integer, primary_key=True))
    return make_table


@pytest.fixture
def alembic_table():
    def make_table(metadata):
        table = sa.Table('alembic_version', metadata,
            sa.Column('version_num', sa.String(250), primary_key=True))
        return table
    return make_table


@pytest.fixture
def sqlalchemymigrate_table():
    def make_table(metadata):
        table = sa.Table('migrate_version', metadata,
            sa.Column('repository_id', sa.String(250), primary_key=True),
            sa.Column('repository_path', sa.Text),
            sa.Column('version', sa.Integer),)
        return table
    return make_table
