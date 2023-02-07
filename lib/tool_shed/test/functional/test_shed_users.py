from urllib.parse import urljoin

from requests import post

from galaxy_test.base import api_asserts
from tool_shed_client.schema import (
    CreateUserRequest,
    User,
)
from ..base.api import (
    email_to_username,
    ensure_user_with_email,
    ShedApiTestCase,
)
from ..base.api_util import get_admin_api_key


class TestShedUsersApi(ShedApiTestCase):
    def test_create_requires_admin(self):
        url = urljoin(self.url, "api/users")
        response = post(url)
        assert response.status_code == 403

    def test_create_user(self):
        url = urljoin(self.url, "api/users")
        headers = {
            "x-api-key": get_admin_api_key(),
        }
        email = "testcreateuser@bx.psu.edu"
        password = "mycoolpassword123"
        username = email_to_username(email)
        body = {
            "email": email,
            "password": password,
            "username": username,
        }
        request = CreateUserRequest(**body)
        response = post(url, json=request.dict(), headers=headers)
        api_asserts.assert_status_code_is_ok(response)
        self._verify_username_password(email, password)
        user = User(**response.json())
        assert user.id
        assert user.username == username

    def test_create_user_interactor(self):
        email = "testcreateuserinteractor@bx.psu.edu"
        password = "mycoolpassword123"
        body = {
            "email": email,
            "password": password,
            "username": email_to_username(email),
        }
        response = self.admin_api_interactor.post("users", json=body)
        api_asserts.assert_status_code_is_ok(response)
        self._verify_username_password(email, password)

    def test_ensure_user_with_email(self):
        email = "testcreateuserensure@bx.psu.edu"
        password = "mycoolpassword123"
        ensure_user_with_email(self.admin_api_interactor, email, password)
        self._verify_username_password(email, password)

    def test_simple_index_and_user(self):
        email = "testindexshow@bx.psu.edu"
        password = "mycoolpassword123"
        ensure_user_with_email(self.admin_api_interactor, email, password)
        user_response = self.admin_api_interactor.get("users")
        api_asserts.assert_status_code_is_ok(user_response)
        users = user_response.json()
        assert isinstance(users, list)
        username = email_to_username(email)
        filtered_users = [u for u in users if u["username"] == username]
        assert len(filtered_users) == 1
        user_id = filtered_users[0]["id"]
        show_response = self.admin_api_interactor.get(f"users/{user_id}")
        api_asserts.assert_status_code_is_ok(show_response)
        assert show_response.json()["username"] == username
        assert show_response.json()["id"] == user_id

    def _verify_username_password(self, email, password):
        self._api_key(email, password)
