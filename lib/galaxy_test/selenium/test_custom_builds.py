from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SharedStateSeleniumTestCase,
)


class CustomBuildsTestcase(SharedStateSeleniumTestCase):
    @selenium_test
    def test_build_add(self):
        self._login()
        self.navigate_to_custom_builds_page()
        self.add_custom_build(self.build_name1, self.build_key1)
        self.assert_custom_builds_in_grid([self.build_name1])

    @selenium_test
    def test_build_delete(self):
        self._login()
        self.navigate_to_custom_builds_page()
        self.add_custom_build(self.build_name2, self.build_key2)
        self.assert_custom_builds_in_grid([self.build_name2])
        self.delete_custom_build(self.build_name2)
        self.assert_custom_builds_in_grid([self.build_name2], False)

    @retry_assertion_during_transitions
    def assert_custom_builds_in_grid(self, expected_builds, present=True):
        actual_builds = self.get_custom_builds()
        intersection = set(actual_builds).intersection(expected_builds)
        if present:
            self.assertEqual(intersection, set(expected_builds))
        else:
            self.assertEqual(intersection, set())

    def _login(self):
        self.home()  # ensure Galaxy is loaded
        self.submit_login(self.user_email, retries=2)

    def add_custom_build(self, build_name, build_key):
        name_input = self.wait_for_selector('input[id="name"]')
        name_input.send_keys(build_name)

        key_input = self.wait_for_selector('input[id="id"]')
        key_input.send_keys(build_key)

        len_type_select = self.wait_for_selector('select[id="type"]')
        len_type_select.click()

        option = self.wait_for_sizzle_selector_clickable('option[value="text"]')
        option.click()
        content_area = self.wait_for_and_click_selector('textarea[id="len-file-text-area"]')
        content_area.send_keys("content")

        self.wait_for_and_click_selector("button#save")

    def delete_custom_build(self, build_name):
        delete_button = None
        grid = self.wait_for_selector("table.grid > tbody")
        for row in grid.find_elements_by_tag_name("tr"):
            td = row.find_elements_by_tag_name("td")
            name = td[0].text
            if name == build_name:
                delete_button = td[3].find_element_by_css_selector(".fa-trash-o")
                break

        if delete_button is None:
            raise AssertionError(f"Failed to find custom build with name [{build_name}]")

        delete_button.click()

    def get_custom_builds(self):
        self.sleep_for(self.wait_types.UX_RENDER)
        builds = []
        grid = self.wait_for_selector("table.grid > tbody")
        for row in grid.find_elements_by_tag_name("tr"):
            name = row.find_elements_by_tag_name("td")[0].text
            builds.append(name)
        return builds

    def navigate_to_custom_builds_page(self):
        self.home()
        self.click_masthead_user()  # Open masthead menu
        self.components.masthead.custom_builds.wait_for_and_click()

    def setup_shared_state(self):
        CustomBuildsTestcase.user_email = self._get_random_email()
        self.register(self.user_email)

        CustomBuildsTestcase.build_name1 = self._get_random_name()
        CustomBuildsTestcase.build_name2 = self._get_random_name()
        CustomBuildsTestcase.build_key1 = self._get_random_name(len=5)
        CustomBuildsTestcase.build_key2 = self._get_random_name(len=5)
