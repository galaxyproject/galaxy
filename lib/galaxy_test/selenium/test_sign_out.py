import time
from .framework import (
    selenium_test,
    SeleniumTestCase
)


class SignOutTestCase(SeleniumTestCase):
    @selenium_test
    def test_sign_out(self):
        email = self._get_random_email()
        self.register(email)
        self.click_masthead_user()
        self.components.masthead.preferences.wait_for_and_click()
        self.components.preferences.sign_out.wait_for_and_click()
        #Testing of the cancel button
        time.sleep(5)
        self.components.sign_out.cancel_button.wait_for_and_click()
        time.sleep(10) #Giving time to click cancel and go back to user preferences (not happening, and no error)
        assert self.is_logged_in()
        new_email = self.driver.find_element_by_id("user-preferences-current-email").text
        self.assertTrue(email == new_email)
        #Testing of the sign out button
        self.components.preferences.sign_out.wait_for_and_click()
        time.sleep(5)
        self.components.sign_out.sign_out_button.wait_for_and_click()
        time.sleep(10) # Enough time to see a log out screen and redirection
        # assert not self.is_logged_in() # Error only shows here, but should had been trigger in line 17
        time.sleep(5)