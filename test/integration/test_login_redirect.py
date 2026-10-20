"""Password login returns validated post-login destinations under ``galaxy_url_prefix``."""

import re

import pytest

from galaxy.util import requests
from galaxy_test.driver import integration_util

EMAIL = "login_redirect@galaxy.org"
PASSWORD = "testpass"


class TestPasswordLoginRedirectIntegration(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["galaxy_url_prefix"] = "/galaxypf"
        config["allowed_login_redirect_hosts"] = "tools.example.org"

    def _login_redirect(self, redirect):
        self._setup_user(EMAIL, password=PASSWORD)
        session = requests.Session()
        response = session.get(f"{self.url}login/start")
        match = re.search(r'session_csrf_token = "(.*)"', response.text)
        assert match
        response = session.post(
            f"{self.url}user/login",
            data={"login": EMAIL, "password": PASSWORD, "redirect": redirect, "session_csrf_token": match.group(1)},
        )
        self._assert_status_code_is(response, 200)
        return response.json()["redirect"]

    @pytest.mark.parametrize(
        "redirect",
        ["https://tools.example.org/back?next=%2Fx", "/workflows/list"],
    )
    def test_allowed_destination_is_returned(self, redirect):
        assert self._login_redirect(redirect) == redirect

    def test_absolute_url_back_to_galaxy_is_returned(self):
        assert self._login_redirect(f"{self.url}workflows/list") == f"{self.url}workflows/list"

    def test_absolute_logout_url_falls_back_to_root(self):
        assert self._login_redirect(f"{self.url}user/logout") == self.url

    @pytest.mark.parametrize(
        "redirect",
        [
            "https://evil.example.com/",
            "https://tools.example.org@evil.example.com/",
            "/\\evil.example.com/",
            "/user/logout",
        ],
    )
    def test_refused_destination_falls_back_to_root(self, redirect):
        assert self._login_redirect(redirect) == self.url
