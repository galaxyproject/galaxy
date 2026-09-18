import json
import os
import re
from urllib.parse import urljoin

from requests import (
    post,
    put,
)

from galaxy_test.base import api_asserts
from tool_shed_client.schema import (
    CreateUserRequest,
    User,
)
from ..base.api import ShedApiTestCase
from ..base.api_util import (
    email_to_username,
    ensure_user_with_email,
    get_admin_api_key,
)


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
        response = post(url, json=request.model_dump(), headers=headers)
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

    def test_api_key_endpoints(self):
        email = "testindexapi@bx.psu.edu"
        password = "mycoolpassword123"
        ensure_user_with_email(self.admin_api_interactor, email, password)
        api_key = self._verify_username_password(email, password)
        second_try_api_key = self._verify_username_password(email, password)
        assert api_key == second_try_api_key

        user_populator = self.populator_for_key(api_key)
        user_populator.delete_api_key()
        new_api_key = self._verify_username_password(email, password)
        assert api_key != new_api_key

        user_populator = self.populator_for_key(new_api_key)
        another_new_api_key = user_populator.create_new_api_key()
        assert new_api_key != another_new_api_key
        assert new_api_key != api_key

    def test_password_reset(self):
        email = "testpasswordreset@bx.psu.edu"
        ensure_user_with_email(self.admin_api_interactor, email, "mycoolpassword123")
        self._request_password_reset(email)

        new_password = "mynewcoolpassword456"
        response = self._redeem_reset_token(self._reset_token_from_email(), new_password)
        api_asserts.assert_status_code_is(response, 204)
        self._verify_username_password(email, new_password)

    def test_password_reset_token_cannot_be_redeemed_twice(self):
        email = "testpasswordresettwice@bx.psu.edu"
        ensure_user_with_email(self.admin_api_interactor, email, "mycoolpassword123")
        self._request_password_reset(email)
        token = self._reset_token_from_email()

        api_asserts.assert_status_code_is(self._redeem_reset_token(token, "mynewcoolpassword456"), 204)
        second_response = self._redeem_reset_token(token, "anotherpassword789")
        api_asserts.assert_status_code_is(second_response, 400)
        self._verify_username_password(email, "mynewcoolpassword456")

    def test_password_reset_does_not_disclose_unknown_email(self):
        email_path = self._email_path()
        if os.path.exists(email_path):
            os.remove(email_path)
        self._request_password_reset("neverregistered@bx.psu.edu")
        assert not os.path.exists(email_path)

    def test_password_reset_rejects_mismatched_confirmation(self):
        email = "testpasswordresetconfirm@bx.psu.edu"
        password = "mycoolpassword123"
        ensure_user_with_email(self.admin_api_interactor, email, password)
        self._request_password_reset(email)

        url = urljoin(self.url, "api_internal/change_password")
        body = {"token": self._reset_token_from_email(), "password": "mynewcoolpassword456", "confirm": "typo789"}
        api_asserts.assert_status_code_is(put(url, json=body), 400)
        self._verify_username_password(email, password)

    def test_admin_can_set_password(self):
        email = "testadminsetpassword@bx.psu.edu"
        ensure_user_with_email(self.admin_api_interactor, email, "mycoolpassword123")
        new_password = "mynewcoolpassword456"
        response = self.admin_api_interactor.put(
            f"users/{self._user_id(email)}/password",
            json={"password": new_password, "confirm": new_password},
        )
        api_asserts.assert_status_code_is(response, 204)
        self._verify_username_password(email, new_password)

    def test_set_password_requires_admin(self):
        email = "testnonadminsetpassword@bx.psu.edu"
        password = "mycoolpassword123"
        ensure_user_with_email(self.admin_api_interactor, email, password)
        response = self.api_interactor.put(
            f"users/{self._user_id(email)}/password",
            json={"password": "mynewcoolpassword456", "confirm": "mynewcoolpassword456"},
        )
        api_asserts.assert_status_code_is(response, 403)
        self._verify_username_password(email, password)

    def _request_password_reset(self, email: str) -> None:
        url = urljoin(self.url, "api_internal/reset_password")
        api_asserts.assert_status_code_is(post(url, json={"email": email, "bear_field": ""}), 204)

    def _redeem_reset_token(self, token: str, password: str):
        url = urljoin(self.url, "api_internal/change_password")
        return put(url, json={"token": token, "password": password, "confirm": password})

    def _reset_token_from_email(self) -> str:
        with open(self._email_path()) as f:
            email = json.load(f)
        assert email["subject"] == "Tool Shed Password Reset"
        match = re.search(r"https?://\S+/user/reset_password\?token=(\w+)", email["body"])
        assert match, f"No password reset link found in email body:\n{email['body']}"
        return match.group(1)

    def _email_path(self) -> str:
        email_path = os.environ.get("TOOL_SHED_TEST_EMAIL_PATH")
        assert email_path, "Tool shed test driver did not configure a mock mailbox"
        return email_path

    def _user_id(self, email: str) -> str:
        username = email_to_username(email)
        users = self.admin_api_interactor.get("users").json()
        return next(user["id"] for user in users if user["username"] == username)

    def _verify_username_password(self, email: str, password: str) -> str:
        return self.api_interactor.create_api_key(email, password)
