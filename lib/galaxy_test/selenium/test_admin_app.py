from galaxy_test.base.populators import flakey
from galaxy_test.driver.integration_util import skip_if_jenkins
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class AdminAppTestCase(SeleniumTestCase):

    requires_admin = True

    @selenium_test
    @flakey  # This test relies on an external server that may or may not be available to the testing environment.
    def test_admin_toolshed(self):
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot('admin_landing')
        admin_component.index.toolshed.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot('admin_toolshed_landing')
        repo_search_input = self.driver.find_element_by_id('toolshed-repo-search')
        repo_search_input.clear()
        repo_search_input.send_keys('all_fasta')
        # If this hasn't succeeded after 30 seconds, the @flakey context should
        # allow the test to still pass, since there should definitely be results
        # after 30 seconds.
        self.sleep_for(self.wait_types.SHED_SEARCH)
        self.screenshot('admin_toolshed_search')
        admin_component.toolshed.search_results.wait_for_visible()
        # It's very unlikely that this data manager will ever stop existing.
        repository_row = self.driver.find_element_by_link_text('data_manager_fetch_genome_dbkeys_all_fasta')
        repository_row.click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot('admin_toolshed_repo_details')
        install_button = self.driver.find_element_by_xpath("(//button[contains(., 'Install')])[1]")
        install_button.click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot('admin_toolshed_repo_install_settings')
        ok_button = self.driver.find_element_by_xpath("//*[@id='repo-install-settings___BV_modal_footer_']/button[contains(., 'OK')]")
        ok_button.click()
        self.sleep_for(self.wait_types.REPO_INSTALL)
        self.screenshot('admin_toolshed_repo_installed')
        # Unfortunately reusing the element isn't feasible, since the div
        # containing the button gets replaced with a new div and button.
        uninstall_button = self.driver.find_element_by_xpath("(//button[contains(., 'Uninstall')])[1]")
        uninstall_button.click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot('admin_toolshed_repo_uninstalled')

    @selenium_test
    @skip_if_jenkins  # Jenkins currently does not have docker available, which is required for testing containers
    def test_admin_dependencies_display(self):
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()
        self.screenshot("admin_landing")
        admin_component.index.dependencies.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.driver.find_element_by_link_text('Dependencies')
        containers_link = self.driver.find_element_by_link_text('Containers')
        unused_link = self.driver.find_element_by_link_text('Unused')
        # Ensure that #manage-resolver-type is visible.
        admin_component.manage_dependencies.resolver_type.wait_for_visible()
        self.screenshot("admin_dependencies_landing")
        self.action_chains().move_to_element(containers_link).click().perform()
        self.sleep_for(self.wait_types.UX_RENDER)
        # Ensure that #manage-container-type is visible.
        admin_component.manage_dependencies.container_type.wait_for_visible()
        self.screenshot("admin_dependencies_containers")
        self.action_chains().move_to_element(unused_link).click().perform()
        self.sleep_for(self.wait_types.UX_RENDER)
        # Ensure that the unused paths table is visible.
        admin_component.manage_dependencies.unused_paths.wait_for_visible()
        self.screenshot("admin_dependencies_unused")

    @selenium_test
    def test_admin_jobs_display(self):
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_landing")
        admin_component.index.jobs.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_jobs_landing")
        # Since both get_property and get_attribute always return true, use the
        # label for the job lock toggle to verify that job locking actually happens
        label = self.driver.find_element_by_xpath("//label[@for='prevent-job-dispatching']/strong")
        lock = self.driver.find_element_by_id("prevent-job-dispatching")
        previous_label = label.text
        self.action_chains().move_to_element_with_offset(lock, -20, 5).click().perform()
        # Make sure the job lock has been toggled.
        self.assertNotEqual(label.text, previous_label)
        new_label = label.text
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_jobs_locked")
        self.action_chains().move_to_element_with_offset(lock, -20, 5).click().perform()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_jobs_unlocked")
        # And confirm that it has toggled back to what it was.
        self.assertEqual(label.text, previous_label)

    @selenium_test
    def test_admin_server_display(self):
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()
        self.screenshot("admin_landing")
        admin_component.index.datatypes.wait_for_and_click()
        admin_component.datatypes_grid.wait_for_visible()
        self.screenshot("admin_datatypes")

        admin_component.index.data_tables.wait_for_and_click()
        admin_component.data_tables_grid.wait_for_visible()
        self.screenshot("admin_data_tables")

        admin_component.index.display_applications.wait_for_and_click()
        self.assert_warning_message("No display applications available.")
        self.screenshot("admin_display_applications")

        admin_component.index.jobs.wait_for_and_click()
        admin_component.update_jobs.wait_for_visible()
        self.screenshot("admin_manage_jobs")

        admin_component.index.local_data.wait_for_and_click()
        title_element = admin_component.dm_title.wait_for_visible()
        assert title_element.text == "Local Data"
        self.screenshot("admin_local_data")

    @selenium_test
    def test_admin_user_display(self):
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()

        admin_component.index.users.wait_for_and_click()
        admin_component.users_grid.wait_for_visible()
        self.screenshot("admin_users")
        admin_component.users_grid_create_button.wait_for_and_click()
        admin_component.registration_form.wait_for_visible()
        self.screenshot("admin_user_registration")

        self.admin_open()
        admin_component.index.groups.wait_for_and_click()
        admin_component.groups_grid.wait_for_visible()
        self.screenshot("admin_groups")

        admin_component.groups_grid_create_button.wait_for_and_click()
        admin_component.groups_create_view.wait_for_visible()
        self.screenshot("admin_groups_create")

        self.admin_open()
        admin_component.index.roles.wait_for_and_click()
        admin_component.roles_grid.wait_for_visible()
        self.screenshot("admin_roles")

    @selenium_test
    def test_admin_data_manager(self):
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()
        admin_component.index.local_data.wait_for_and_click()
        title_element = admin_component.dm_title.wait_for_visible()
        assert title_element.text == "Local Data"
        admin_component.dm_data_managers_card.wait_for_visible()
        admin_component.dm_jobs_button(data_manager="test-data-manager").wait_for_visible()
        self.screenshot("admin_data_manager")

        with self.dataset_populator.test_history() as history_id:
            run_response = self.dataset_populator.run_tool(tool_id="data_manager",
                                                           inputs={"ignored_value": "test"},
                                                           history_id=history_id,
                                                           assert_ok=False)
            job_id = run_response.json()["jobs"][0]["id"]
            self.dataset_populator.wait_for_tool_run(history_id=history_id,
                                                     run_response=run_response,
                                                     assert_ok=False)

        admin_component.dm_jobs_button(data_manager="test-data-manager").wait_for_and_click()
        admin_component.dm_jobs_breadcrumb.wait_for_visible()
        admin_component.dm_jobs_table.wait_for_visible()
        self.screenshot("admin_data_manager_jobs")

        admin_component.dm_job(job_id=job_id).wait_for_and_click()
        admin_component.dm_job_breadcrumb.wait_for_visible()
        admin_component.dm_job_data_manager_card.wait_for_visible()
        admin_component.dm_job_data_card(hda_index=0).wait_for_visible()
        self.screenshot("admin_data_manager_job")

        admin_component.index.local_data.wait_for_and_click()
        admin_component.dm_table_button(data_table="testbeta").wait_for_and_click()
        admin_component.dm_table_card.wait_for_visible()
        self.screenshot("admin_data_manager_table")
