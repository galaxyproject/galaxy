from .framework import (
    selenium_test,
    SharedStateSeleniumTestCase,
)


class TestCustomBuilds(SharedStateSeleniumTestCase):
    user_email: str

    @selenium_test
    def test_build_add(self):
        build_name = self._get_random_name()
        self._login()
        self.navigate_to_custom_builds_page()
        self.add_custom_build(build_name, self._get_random_name(len=5))
        self.assert_custom_build_listed(build_name)

    @selenium_test
    def test_build_delete(self):
        build_name = self._get_random_name()
        self._login()
        self.navigate_to_custom_builds_page()
        self.add_custom_build(build_name, self._get_random_name(len=5))
        self.assert_custom_build_listed(build_name)
        self.delete_custom_build(build_name)
        self.assert_custom_build_not_listed(build_name)

    @selenium_test
    def test_build_add_from_fasta(self):
        build_name = self._get_random_name()
        self._login()
        self.dataset_populator.new_dataset(
            self.current_history_id(), content=">chr1\nACGT\n>chr2\nAC\n", file_type="fasta", wait=True
        )
        self.navigate_to_custom_builds_page()
        custom_builds = self.components.custom_builds
        custom_builds.name.wait_for_and_send_keys(build_name)
        custom_builds.key.wait_for_and_send_keys(self._get_random_name(len=5))
        assert custom_builds.definition.wait_for_value() == "fasta"
        # Enabled once a history FASTA dataset is selected.
        custom_builds.fasta_file.wait_for_clickable()
        custom_builds.save.wait_for_and_click()
        assert "Successfully added" in custom_builds.success_alert.wait_for_text()
        # A FASTA build is listed once its jobs count the chromosomes; the page doesn't
        # refresh when they finish (#24309), so reload it.
        self.wait_for_history()
        self.navigate_to_custom_builds_page()
        assert custom_builds.row_count(name=build_name).wait_for_text() == "2"
        self.screenshot("custom_builds_from_fasta")

    def assert_custom_build_listed(self, build_name):
        self.components.custom_builds.row(name=build_name).wait_for_visible()

    def assert_custom_build_not_listed(self, build_name):
        custom_builds = self.components.custom_builds
        # Wait for the table so absence isn't checked against an unloaded page.
        custom_builds.table.wait_for_visible()
        custom_builds.row(name=build_name).wait_for_absent()

    def _login(self):
        self.home()  # ensure Galaxy is loaded
        self.submit_login(self.user_email, retries=2)

    def add_custom_build(self, build_name, build_key):
        custom_builds = self.components.custom_builds
        custom_builds.name.wait_for_and_send_keys(build_name)
        custom_builds.key.wait_for_and_send_keys(build_key)
        custom_builds.definition.select_by_value("text")
        custom_builds.len_text.wait_for_and_send_keys("content")
        custom_builds.save.wait_for_and_click()

    def delete_custom_build(self, build_name):
        self.components.custom_builds.row_delete(name=build_name).wait_for_and_click()

    def navigate_to_custom_builds_page(self):
        self.home()
        self.navigate_to_user_preferences()
        self.components.preferences.custom_builds.wait_for_and_click()

    def setup_shared_state(self):
        TestCustomBuilds.user_email = self._get_random_email()
        self.register(self.user_email)
