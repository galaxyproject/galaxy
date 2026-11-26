import json
import os
import re
from datetime import (
    datetime,
    timedelta,
)
from typing import ClassVar
from urllib.parse import urlsplit

from selenium.webdriver.support import expected_conditions
from sqlalchemy import select

from galaxy import model
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestPasswordResetSeleniumIntegration(SeleniumIntegrationTestCase):
    email_path: ClassVar[str]

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.email_path = os.path.join(cls._test_driver.mkdtemp(), "email.json")
        config["email_from"] = "galaxy-noreply@example.org"
        config["smtp_server"] = f"mock_emails_to_path://{cls.email_path}"
        config["password_expiration_period"] = 365

    @selenium_test
    def test_reset_password_from_emailed_link(self):
        email = self._get_random_email(domain="example.org")
        self.register(email)
        self.logout_if_needed()
        assert "confirmation email" in self.request_password_reset(email)
        with open(self.email_path) as f:
            email_message = json.load(f)
        assert email_message["to"] == email
        assert email_message["subject"] == "Galaxy Password Reset"
        match = re.search(r"(?:https?://)?[^/\s]+/login/start\?token=\w+", email_message["body"])
        assert match, "Password reset email must contain a reset link"
        reset_link = match.group()
        # The 25.1 mail template emits a host/path without the scheme.
        if not reset_link.startswith(("http://", "https://")):
            reset_link = f"{urlsplit(self.url).scheme}://{reset_link}"
        self.get(reset_link)
        self.components.change_password.password.wait_for_visible()
        self.components.change_password.confirm.wait_for_visible()
        self.components.change_password.current.assert_absent()
        self.screenshot("password_reset_form")
        new_password = self._get_random_password()
        self.reset_password_from_link(reset_link, new_password)
        self._assert_changed_password_session(email, new_password, "password_reset_saved")

    @selenium_test
    def test_expired_password_requires_current_password(self):
        email = self._get_random_email(domain="example.org")
        self.register(email)
        self.logout_if_needed()
        session = self._app.model.context
        user = session.scalars(select(model.User).where(model.User.email == email)).one()
        user.last_password_change = datetime.today() - timedelta(days=366)
        session.commit()
        self.home()
        self.components.masthead.login_masthead_button.wait_for_and_click()
        login = self.components.login
        self.fill(login.form.wait_for_visible(), {"login": email, "password": self.default_password})
        login.submit.wait_for_and_click()
        alert = self._wait_on(expected_conditions.alert_is_present(), "expired password alert")
        assert "Your password has expired" in alert.text
        alert.accept()
        self.components.change_password.current.wait_for_visible()
        self.components.change_password.password.wait_for_visible()
        self.components.change_password.confirm.wait_for_visible()
        self.screenshot("password_expired_form")
        new_password = self._get_random_password()
        self.change_password(new_password, current_password=self.default_password)
        self._assert_changed_password_session(email, new_password, "password_expired_saved")

    def _assert_changed_password_session(self, email, password, screenshot_name):
        # The server logs the user in while saving; the masthead must agree.
        self.wait_for_logged_in()
        user = self.get_logged_in_user()
        assert user is not None
        assert user["email"] == email
        self.screenshot(screenshot_name)
        self.logout_if_needed()
        self.home()
        self.submit_login(email, password)
        self.assert_no_error_message()
