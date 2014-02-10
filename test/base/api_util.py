import os

DEFAULT_GALAXY_MASTER_API_KEY = "TEST123"
DEFAULT_GALAXY_USER_API_KEY = None


def get_master_api_key():
    """ Test master API key to use for functional test. This key should be
    configured as a master API key and should be able to create additional
    users and keys.
    """
    return os.environ.get( "GALAXY_TEST_MASTER_API_KEY", DEFAULT_GALAXY_MASTER_API_KEY )


def get_user_api_key():
    """ Test user API key to use for functional tests. If set, this should drive
    API based testing - if not set master API key should be used to create a new
    user and API key for tests.
    """
    return os.environ.get( "GALAXY_TEST_USER_API_KEY", DEFAULT_GALAXY_USER_API_KEY )
