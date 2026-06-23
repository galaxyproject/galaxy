from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestSignOut(SeleniumTestCase):
    @selenium_test
    def test_sign_out(self):
        email = self._get_random_email()
        self.register(email)
        self.navigate_to_user_preferences()
        self.components.preferences.sign_out.wait_for_and_click()
        self.components.confirm_dialog.cancel_button.wait_for_and_click()
        assert self.is_logged_in()
        new_email = self.find_element_by_id("user-preferences-current-email").text
        assert email == new_email
        self.components.preferences.sign_out.wait_for_and_click()
        self.components.confirm_dialog.ok_button.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        assert not self.is_logged_in()
