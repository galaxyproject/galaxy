import base64
import os
import random
import string
from typing import (
    Dict,
    Optional,
)

DEFAULT_GALAXY_MASTER_API_KEY = "TEST123"
DEFAULT_GALAXY_USER_API_KEY = None

DEFAULT_TEST_USER = "user@bx.psu.edu"
DEFAULT_ADMIN_TEST_USER = "test@bx.psu.edu"
DEFAULT_OTHER_USER = "otheruser@bx.psu.edu"  # A second user for API testing.

TEST_USER = os.environ.get("GALAXY_TEST_USER_EMAIL", DEFAULT_TEST_USER)
ADMIN_TEST_USER = os.environ.get("GALAXY_TEST_ADMIN_USER_EMAIL", DEFAULT_ADMIN_TEST_USER)
OTHER_USER = os.environ.get("GALAXY_TEST_OTHER_USER_EMAIL", DEFAULT_OTHER_USER)


def get_admin_api_key() -> str:
    """Test admin API key to use for functional tests.

    This key should be configured as a admin API key and should be able
    to create additional users and keys.
    """
    for key in ["GALAXY_CONFIG_MASTER_API_KEY", "GALAXY_CONFIG_OVERRIDE_MASTER_API_KEY"]:
        value = os.environ.get(key, None)
        if value:
            return value
    return DEFAULT_GALAXY_MASTER_API_KEY


def get_user_api_key() -> Optional[str]:
    """Test user API key to use for functional tests.

    If set, this should drive API based testing - if not set an admin API key will
    be used to create a new user and API key for tests.
    """
    return os.environ.get("GALAXY_TEST_USER_API_KEY", DEFAULT_GALAXY_USER_API_KEY)


def baseauth_headers(username: str, password: str) -> Dict[str, str]:
    unencoded_credentials = f"{username}:{password}"
    authorization = base64.b64encode(unencoded_credentials.encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": authorization,
    }
    return headers


def random_name(prefix: Optional[str] = None, suffix: Optional[str] = None, len: int = 10) -> str:
    return "{}{}{}".format(
        prefix or "",
        "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(len)),
        suffix or "",
    )
