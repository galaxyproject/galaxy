from galaxy.config import Configuration

# TODO This, of course, needs A LOT more tests...

def test_dabase_wait_default_values():
    config = Configuration()
    assert not config.database_wait
    assert config.database_wait_attempts == 60
    assert config.database_wait_sleep == 1


def test_database_wait_assigned_values():
    db_wait = True
    db_attempts = 42
    db_sleep = 999

    values = {}
    values['database_wait'] = db_wait
    values['database_wait_attempts'] = db_attempts
    values['database_wait_sleep'] = db_sleep

    config = Configuration(**values)
    assert config.database_wait == db_wait
    assert config.database_wait_attempts == db_attempts
    assert config.database_wait_sleep == db_sleep
