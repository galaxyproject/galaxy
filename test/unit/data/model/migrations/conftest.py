import pytest
import sqlalchemy as sa

# Fixtures: metadata containing one or more tables and representing database state.
# Used to load a database with a given state.
# Each state has 3 versions, distinguished by suffix:
# - gxy (galaxy database that holds gxy* and migration version tables)
# - tsi (tool_shed_install database that holds tsi* and migration version tables)
# - combined (combined database that holds gxy*, tsi*, and migration version tables)
#
# The following states are represented:
#
# State 1: Non-empty database, no version table.
#          (Most ancient state)
# State 2: SQLAlchemy Migrate version table added.
#          (Oldest state versioned with SQLAlchemy Migrate)
# State 3: New table added.
#          (Last (most recent) state versioned with SQLAlchemy Migrate)
# State 4: Alembic version table added.
#          (Oldest state versioned with Alembic)
# State 5: SQLAlchemy Migrate version table removed.
#          (Oldest state versioned with Alembic that does not include the SQLAchemy Migrate version table)
# State 6: New table added.
#          (Most recent state versioned with Alembic. This is the current state)
#
# Additional edge case: gxy at state3, tsi has no SQLAlchemy Migrate table.
#
# (State 0 assumes an empty database, so it needs no state fixtures.)


# state 0-kombu
@pytest.fixture
def metadata_state0kombu(kombu_message_table, kombu_queue_table):
    metadata = sa.MetaData()
    kombu_message_table(metadata)
    kombu_queue_table(metadata)
    return metadata


# state 1
@pytest.fixture
def metadata_state1_gxy(gxy_table1):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    return metadata


@pytest.fixture
def metadata_state1_tsi(tsi_table1):
    metadata = sa.MetaData()
    tsi_table1(metadata)
    return metadata


@pytest.fixture
def metadata_state1_combined(gxy_table1, tsi_table1):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    tsi_table1(metadata)
    return metadata


# state 2
@pytest.fixture
def metadata_state2_gxy(gxy_table1, sqlalchemymigrate_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    sqlalchemymigrate_table(metadata)
    return metadata


@pytest.fixture
def metadata_state2_tsi(tsi_table1, sqlalchemymigrate_table):
    metadata = sa.MetaData()
    tsi_table1(metadata)
    sqlalchemymigrate_table(metadata)
    return metadata


@pytest.fixture
def metadata_state2_combined(gxy_table1, tsi_table1, sqlalchemymigrate_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    tsi_table1(metadata)
    sqlalchemymigrate_table(metadata)
    return metadata


# state 3
@pytest.fixture
def metadata_state3_gxy(gxy_table1, gxy_table2, sqlalchemymigrate_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    gxy_table2(metadata)
    sqlalchemymigrate_table(metadata)
    return metadata


@pytest.fixture
def metadata_state3_tsi(tsi_table1, tsi_table2, sqlalchemymigrate_table):
    metadata = sa.MetaData()
    tsi_table1(metadata)
    tsi_table2(metadata)
    sqlalchemymigrate_table(metadata)
    return metadata


@pytest.fixture
def metadata_state3_combined(gxy_table1, gxy_table2, tsi_table1, tsi_table2, sqlalchemymigrate_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    gxy_table2(metadata)
    tsi_table1(metadata)
    tsi_table2(metadata)
    sqlalchemymigrate_table(metadata)
    return metadata


# state 4
@pytest.fixture
def metadata_state4_gxy(gxy_table1, gxy_table2, sqlalchemymigrate_table, alembic_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    gxy_table2(metadata)
    sqlalchemymigrate_table(metadata)
    alembic_table(metadata)
    return metadata


@pytest.fixture
def metadata_state4_tsi(tsi_table1, tsi_table2, sqlalchemymigrate_table, alembic_table):
    metadata = sa.MetaData()
    tsi_table1(metadata)
    tsi_table2(metadata)
    sqlalchemymigrate_table(metadata)
    alembic_table(metadata)
    return metadata


@pytest.fixture
def metadata_state4_combined(gxy_table1, gxy_table2, tsi_table1, tsi_table2, sqlalchemymigrate_table, alembic_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    gxy_table2(metadata)
    tsi_table1(metadata)
    tsi_table2(metadata)
    sqlalchemymigrate_table(metadata)
    alembic_table(metadata)
    return metadata


# state 5
@pytest.fixture
def metadata_state5_gxy(gxy_table1, gxy_table2, alembic_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    gxy_table2(metadata)
    alembic_table(metadata)
    return metadata


@pytest.fixture
def metadata_state5_tsi(tsi_table1, tsi_table2, alembic_table):
    metadata = sa.MetaData()
    tsi_table1(metadata)
    tsi_table2(metadata)
    alembic_table(metadata)
    return metadata


@pytest.fixture
def metadata_state5_combined(gxy_table1, gxy_table2, tsi_table1, tsi_table2, alembic_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    gxy_table2(metadata)
    tsi_table1(metadata)
    tsi_table2(metadata)
    alembic_table(metadata)
    return metadata


# state 6
@pytest.fixture
def metadata_state6_gxy(gxy_table1, gxy_table2, gxy_table3, alembic_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    gxy_table2(metadata)
    gxy_table3(metadata)
    alembic_table(metadata)
    return metadata


@pytest.fixture
def metadata_state6_tsi(tsi_table1, tsi_table2, tsi_table3, alembic_table):
    metadata = sa.MetaData()
    tsi_table1(metadata)
    tsi_table2(metadata)
    tsi_table3(metadata)
    alembic_table(metadata)
    return metadata


@pytest.fixture
def metadata_state6_combined(gxy_table1, gxy_table2, gxy_table3, tsi_table1, tsi_table2, tsi_table3, alembic_table):
    metadata = sa.MetaData()
    gxy_table1(metadata)
    gxy_table2(metadata)
    gxy_table3(metadata)
    tsi_table1(metadata)
    tsi_table2(metadata)
    tsi_table3(metadata)
    alembic_table(metadata)
    return metadata


@pytest.fixture
def metadata_state6_gxy_state3_tsi_no_sam(
    gxy_table1, gxy_table2, gxy_table3, tsi_table1, tsi_table2, tsi_table3, alembic_table
):
    # This does NOT include sqlalchemymigrate_table (sam)
    metadata = sa.MetaData()
    gxy_table1(metadata)
    gxy_table2(metadata)
    gxy_table3(metadata)
    tsi_table1(metadata)
    tsi_table2(metadata)
    alembic_table(metadata)
    return metadata


# Fixture factories: metadata containing one table each.
# Used to compose metadata representing database state.
# (The `_factory` suffix is ommitted to keep the code less verbose)


@pytest.fixture
def gxy_table1():
    def make_table(metadata):
        return sa.Table("gxy_table1", metadata, sa.Column("id", sa.Integer, primary_key=True))

    return make_table


@pytest.fixture
def gxy_table2():
    def make_table(metadata):
        return sa.Table("gxy_table2", metadata, sa.Column("id", sa.Integer, primary_key=True))

    return make_table


@pytest.fixture
def gxy_table3():
    def make_table(metadata):
        return sa.Table("gxy_table3", metadata, sa.Column("id", sa.Integer, primary_key=True))

    return make_table


@pytest.fixture
def tsi_table1():
    def make_table(metadata):
        return sa.Table("tsi_table1", metadata, sa.Column("id", sa.Integer, primary_key=True))

    return make_table


@pytest.fixture
def tsi_table2():
    def make_table(metadata):
        return sa.Table("tsi_table2", metadata, sa.Column("id", sa.Integer, primary_key=True))

    return make_table


@pytest.fixture
def tsi_table3():
    def make_table(metadata):
        return sa.Table("tsi_table3", metadata, sa.Column("id", sa.Integer, primary_key=True))

    return make_table


@pytest.fixture
def alembic_table():
    def make_table(metadata):
        table = sa.Table("alembic_version", metadata, sa.Column("version_num", sa.String(250), primary_key=True))
        return table

    return make_table


@pytest.fixture
def sqlalchemymigrate_table():
    def make_table(metadata):
        table = sa.Table(
            "migrate_version",
            metadata,
            sa.Column("repository_id", sa.String(250), primary_key=True),
            sa.Column("repository_path", sa.Text),
            sa.Column("version", sa.Integer),
        )
        return table

    return make_table


@pytest.fixture
def kombu_message_table():
    def make_table(metadata):
        return sa.Table("kombu_message", metadata, sa.Column("id", sa.Integer, primary_key=True))

    return make_table


@pytest.fixture
def kombu_queue_table():
    def make_table(metadata):
        return sa.Table("kombu_queue", metadata, sa.Column("id", sa.Integer, primary_key=True))

    return make_table
