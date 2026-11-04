import os

from galaxy_test.driver.integration_util import ConfiguresMockEmails
from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestUserActivationSeleniumIntegration(SeleniumIntegrationTestCase, ConfiguresMockEmails):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_mock_emails(config)
        config["user_activation_on"] = True

    @selenium_test
    def test_register_resend_and_activate(self):
        # user_activation_on also turns on a DNS check of the email's domain.
        email = self._get_random_email(domain="example.org")
        self.register(email, via_masthead=True)
        inactivity_box = self.components.inactivity_box
        inactivity_box._.wait_for_visible()
        self.screenshot("user_activation_inactive")
        self._read_activation_link(email)

        os.remove(self.email_path)
        inactivity_box.resend_verification.wait_for_and_click()
        self.assert_success_message("activation link has been sent again")
        self.screenshot("user_activation_resent")
        link = self._read_activation_link(email)

        self.navigate_to(link)
        self.assert_success_message("successfully activated")
        self.screenshot("user_activation_activated")
        self.home()
        # The banner only renders once the user has loaded, so wait for that first.
        self.wait_for_logged_in()
        inactivity_box._.assert_absent_or_hidden()
