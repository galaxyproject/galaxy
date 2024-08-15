from typing import (
    Any,
    cast,
)

from requests import (
    get,
    put,
)

from galaxy.model.db.user import get_user_by_email
from galaxy_test.driver import integration_util

TEST_USER_EMAIL = "test_user_preferences@bx.psu.edu"


class TestUserPreferences(integration_util.IntegrationTestCase):
    def test_user_theme(self):
        user = self._setup_user(TEST_USER_EMAIL)
        url = self._api_url(f"users/{user['id']}/theme/test_theme", params=dict(key=self.master_api_key))
        app = cast(Any, self._test_driver.app if self._test_driver else None)

        db_user = get_user_by_email(app.model.session, user["email"])

        # create some initial data
        put(url)

        # retrieve saved data
        url = self._api_url(f"users/{user['id']}", params=dict(key=self.master_api_key))
        response = get(url).json()

        # value should be what we saved and should be part of the user response
        assert db_user.preferences["theme"] == "test_theme"
        assert response["preferences"]["theme"] == "test_theme"
