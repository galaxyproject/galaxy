from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class ManageInformationTestCase(SeleniumTestCase):
    @selenium_test
    def test_api_key(self):
        """
        This test views and resets the API key. In automated testing scenarios,
        this means the initial API key will be None, which renders as
        'Not available.'
        """
        self.login()
        self.assertEqual(self.get_api_key(), "Not available.")
        api_key = self.get_api_key()
        self.navigate_to_user_preferences()
        self.components.preferences.manage_api_key.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        new_key_button = self.driver.find_element_by_id("submit")
        api_key_input = self.driver.find_element_by_css_selector("[data-label='Current API key:'] > input")
        # Assert that what's rendered on screen is what the API is returning
        self.assertEqual(api_key_input.get_property("value"), api_key)
        self.action_chains().move_to_element(new_key_button).click().perform()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        new_api_key = self.get_api_key()
        api_key_input = self.driver.find_element_by_css_selector("[data-label='Current API key:'] > input")
        # And assert that this has now changed, and still renders correctly
        self.assertEqual(new_api_key, api_key_input.get_property("value"))

    @selenium_test
    def test_change_email(self):
        def assert_email(email_to_check):
            self.assertTrue(email_to_check == self.driver.find_element_by_id("user-preferences-current-email").text)

        email = self._get_random_email()
        self.register(email)
        self.navigate_to_user_preferences()
        self.sleep_for(self.wait_types.UX_RENDER)

        # rendered email should be equal
        assert_email(email)

        self.components.preferences.manage_information.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)

        new_email = self._get_random_email()
        # new email should be different from initially registered
        self.assertTrue(email != new_email)
        email_input_field = self.driver.find_element_by_css_selector("input[id='email']")

        self.clear_input_field_and_write(email_input_field, new_email)
        self.components.change_user_email.submit.wait_for_and_click()

        # UX_RENDER time sometimes is not enough
        self.sleep_for(self.wait_types.UX_TRANSITION)

        # email should be changed
        assert_email(new_email)

    @selenium_test
    def test_public_name(self):
        def get_name_input_field():
            return self.driver.find_element_by_css_selector("input[id='username']")

        def assert_public_name(expected_name):
            self.assertTrue(expected_name == get_name_input_field().get_attribute("value"))

        public_name = "user-public-name"
        self.register(username=public_name)
        self.navigate_to_manage_information()
        self.sleep_for(self.wait_types.UX_RENDER)

        # make sure that public name is the same as registered
        assert_public_name(public_name)
        new_public_name = "new-public-name"
        # change public name
        self.clear_input_field_and_write(get_name_input_field(), new_public_name)
        self.components.change_user_email.submit.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_TRANSITION)

        self.navigate_to_manage_information()
        self.sleep_for(self.wait_types.UX_RENDER)
        # public name field should render new public name
        assert_public_name(new_public_name)

    @selenium_test
    def test_user_address(self):
        def get_address_form():
            return self.driver.find_element_by_css_selector("div.ui-portlet-section > div.portlet-content")

        self.register(self._get_random_email())
        self.navigate_to_manage_information()
        self.components.change_user_address.address_button.wait_for_and_click()

        address_field_labels = [
            "Short address description",
            "Name",
            "Institution",
            "Address",
            "City",
            "State/Province/Region",
            "Postal Code",
            "Country",
            "Phone",
        ]

        address_fields = {}
        # fill address fields with random data
        for input_field_label in address_field_labels:
            input_value = self._get_random_name(prefix=input_field_label)
            address_fields[input_field_label] = input_value
            input_field = self.get_address_input_field(get_address_form(), input_field_label)
            self.clear_input_field_and_write(input_field, input_value)
        # save new address
        self.components.change_user_email.submit.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)

        self.navigate_to_manage_information()
        self.sleep_for(self.wait_types.UX_RENDER)

        # check if address was saved correctly
        for input_field_label in address_fields.keys():
            input_field = self.get_address_input_field(get_address_form(), input_field_label)
            self.assertTrue(input_field.get_attribute("value") == address_fields[input_field_label])

    def navigate_to_manage_information(self):
        self.navigate_to_user_preferences()
        self.components.preferences.manage_information.wait_for_and_click()

    def clear_input_field_and_write(self, element, new_input_text):
        element.clear()
        element.send_keys(new_input_text)

    def get_address_input_field(self, address_form, input_field_label):
        return address_form.find_element_by_css_selector(f"[data-label='{input_field_label}'] > input")


class DeleteCurrentAccountTestCase(SeleniumTestCase):
    @selenium_test
    def test_delete_account(self):
        email = self._get_random_email()
        self.register(email)
        self.navigate_to_user_preferences()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.components.preferences.delete_account.wait_for_and_click()
        delete_confirmation_field = self.components.preferences.delete_account_input.wait_for_visible()
        delete_confirmation_field.send_keys(email)
        self.components.preferences.delete_account_ok_btn.wait_for_and_click()
        self.submit_login(email=email, assert_valid=False)
        self.assert_error_message(
            contains="This account has been marked deleted, contact your local Galaxy"
            " administrator to restore the account."
        )
