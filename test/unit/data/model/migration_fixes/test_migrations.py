import pytest

from galaxy.model import User
from galaxy.model.unittest_utils.migration_scripts_testing_utils import (  # noqa: F401 - contains fixtures we have to import explicitly
    run_command,
    tmp_directory,
)

COMMAND = "manage_db.sh"


@pytest.fixture(autouse=True)
def upgrade_database_after_test():
    """Run after each test for proper cleanup"""
    yield
    run_command(f"{COMMAND} upgrade")


def test_1cf595475b58(monkeypatch, session, make_user, make_history):
    # Initialize db and migration environment
    dburl = str(session.bind.url)
    monkeypatch.setenv("GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION", dburl)
    monkeypatch.setenv("GALAXY_INSTALL_CONFIG_OVERRIDE_INSTALL_DATABASE_CONNECTION", dburl)
    run_command(f"{COMMAND} init")

    # STEP 0: Load pre-migration state
    run_command(f"{COMMAND} downgrade d619fdfa6168")

    # STEP 1: Load users with duplicate emails

    # Duplicate group 1: users have no histories
    # Expect: oldest user preserved
    u1_1 = make_user(email="a")
    u1_2 = make_user(email="a")
    u1_3 = make_user(email="a")
    original_email1 = u1_1.email
    assert u1_1.email == u1_2.email == u1_3.email
    assert u1_1.create_time < u1_2.create_time < u1_3.create_time  # u1_1 is oldest user

    # Duplicate group 2: oldest user does NOT have a history, another user has a history
    # Expect: user with history preserved
    u2_1 = make_user(email="b")
    u2_2 = make_user(email="b")
    u2_3 = make_user(email="b")
    original_email2 = u2_1.email
    assert u2_1.email == u2_2.email == u2_3.email
    assert u2_1.create_time < u2_2.create_time < u2_3.create_time  # u2_1 is oldest user

    make_history(user=u2_2)  # u2_2 has a history

    # Duplicate group 3: oldest user does NOT have a history, 2 users have a history
    # Expect: oldest user with history preserved
    u3_1 = make_user(email="c")
    u3_2 = make_user(email="c")
    u3_3 = make_user(email="c")
    original_email3 = u3_1.email
    assert u3_1.email == u3_2.email == u3_3.email
    assert u3_1.create_time < u3_2.create_time < u3_3.create_time  # u2_1 is oldest user

    make_history(user=u3_2)  # u3_2 has a history
    make_history(user=u3_3)  # u3_3 has a history

    # User w/o duplicate email
    u4 = make_user()
    original_email4 = u4.email

    # STEP 2: Run migration

    run_command(f"{COMMAND} upgrade 1cf595475b58")
    session.expire_all()

    # STEP 3: Verify deduplicated results

    # Duplicate group 1:
    u1_1_fixed = session.get(User, u1_1.id)
    u1_2_fixed = session.get(User, u1_2.id)
    u1_3_fixed = session.get(User, u1_3.id)

    # oldest user's email is preserved; the rest are deduplicated
    assert u1_1.email == original_email1
    assert u1_1.email != u1_2.email != u1_3.email
    # deduplicated users are marked as deleted
    assert u1_1_fixed.deleted is False
    assert u1_2_fixed.deleted is True
    assert u1_3_fixed.deleted is True

    # Duplicate group 2:
    u2_1_fixed = session.get(User, u2_1.id)
    u2_2_fixed = session.get(User, u2_2.id)
    u2_3_fixed = session.get(User, u2_3.id)

    # the email of the user with a history is preserved; the rest are deduplicated
    assert u2_2.email == original_email2
    assert u2_1.email != u1_2.email != u1_3.email
    # deduplicated users are marked as deleted
    assert u2_1_fixed.deleted is True
    assert u2_2_fixed.deleted is False
    assert u2_3_fixed.deleted is True

    # Duplicate group 3:
    u3_1_fixed = session.get(User, u3_1.id)
    u3_2_fixed = session.get(User, u3_2.id)
    u3_3_fixed = session.get(User, u3_3.id)

    # the email of the oldest user with a history is preserved; the rest are deduplicated
    assert u3_2.email == original_email3
    assert u3_1.email != u3_2.email != u3_3.email
    # deduplicated users are marked as deleted
    assert u3_1_fixed.deleted is True
    assert u3_2_fixed.deleted is False
    assert u3_3_fixed.deleted is True

    # User w/o duplicate email
    u4_no_change = session.get(User, u4.id)
    assert u4_no_change.email == original_email4
    assert u4_no_change.deleted is False


def test_d619fdfa6168(monkeypatch, session, make_user):
    # Initialize db and migration environment
    dburl = str(session.bind.url)
    monkeypatch.setenv("GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION", dburl)
    monkeypatch.setenv("GALAXY_INSTALL_CONFIG_OVERRIDE_INSTALL_DATABASE_CONNECTION", dburl)
    run_command(f"{COMMAND} init")

    # STEP 0: Load pre-migration state
    run_command(f"{COMMAND} downgrade d2d8f51ebb7e")

    # STEP 1: Load users with duplicate usernames

    # Expect: oldest user preserved
    u1 = make_user(username="a")
    u2 = make_user(username="a")
    u3 = make_user(username="a")
    original_username = u3.username
    assert u1.username == u2.username == u3.username
    assert u1.create_time < u2.create_time < u3.create_time  # u3 is newest user

    # STEP 2: Run migration
    run_command(f"{COMMAND} upgrade d619fdfa6168")
    session.expire_all()

    # STEP 3: Verify deduplicated results
    u1_fixed = session.get(User, u1.id)
    u2_fixed = session.get(User, u2.id)
    u3_fixed = session.get(User, u3.id)

    # oldest user's username is preserved; the rest are deduplicated
    assert u3_fixed.username == original_username
    assert u1.username != u2.username != u3.username
    # deduplicated users are marked as deleted
    assert u1_fixed.deleted is True
    assert u2_fixed.deleted is True
    assert u3_fixed.deleted is False
