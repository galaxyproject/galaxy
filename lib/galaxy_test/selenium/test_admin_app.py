from galaxy_test.base.decorators import requires_admin
from galaxy_test.base.populators import flakey
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class TestAdminApp(SeleniumTestCase):
    run_as_admin = True

    @selenium_test
    @requires_admin
    def test_html_allowlist(self):
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_landing")
        admin_component.index.allowlist.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_allowlist_landing")
        admin_component.allowlist.local.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_allowlist_local_landing")
        # This should be updated if the list of built-in converters is changed.
        render_button = self.find_element_by_xpath("//td[.='CONVERTER_bam_to_bigwig_0']/following::td/button")
        render_button.click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_allowlist_converter_html_rendered")
        admin_component.allowlist.rendered_active.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_allowlist_render_landing")
        self.sleep_for(self.wait_types.UX_RENDER)
        sanitize_button = self.find_element_by_xpath("//td[.='CONVERTER_bam_to_bigwig_0']/following::td/button")
        sanitize_button.click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_allowlist_converter_sanitized")

    @selenium_test
    @flakey
    @requires_admin
    def test_admin_toolshed(self):
        """
        This tests installing a repository, checking for upgrades, and uninstalling.

        A repository named a_selenium_test_repo has been created for this test,
        owned by devteam@galaxyproject.org. The repository contains a tool with two versions,
        and the oldest version gets installed so that there will be an upgrade available
        on the 'Installed Only' view. Unfortunately, since this test relies on the presence
        of the toolshed server, in some cases it will fail even if the galaxy code is correct,
        necessitating the use of the @flakey decorator.
        """
        repository_name = "a_selenium_test_repo"
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_landing")
        admin_component.index.toolshed.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_toolshed_landing")
        repo_search_input = self.find_element_by_id("toolshed-repo-search")
        repo_search_input.clear()
        repo_search_input.send_keys(repository_name)
        # If this hasn't succeeded after 30 seconds, the @flakey context should
        # allow the test to still pass, since there should definitely be results
        # after 30 seconds.
        self.sleep_for(self.wait_types.SHED_SEARCH)
        self.screenshot("admin_toolshed_search")
        admin_component.toolshed.search_results.wait_for_visible()
        repository_row = self.find_element_by_link_text(repository_name)
        repository_row.click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_toolshed_repo_details")
        install_button = self.find_element_by_xpath("(//button[contains(., 'Install')])[2]")
        install_button.click()
        self.sleep_for(self.wait_types.UX_RENDER)
        self.screenshot("admin_toolshed_repo_install_settings")
        self.sleep_for(self.wait_types.UX_TRANSITION)
        ok_button = self.find_element_by_xpath(
            "//*[@id='repo-install-settings___BV_modal_footer_']/button[contains(., 'OK')]"
        )
        ok_button.click()
        self.sleep_for(self.wait_types.REPO_INSTALL)
        installed_only = self.find_element_by_xpath("//span[contains(. ,'Installed Only')]/../../input")
        self.action_chains().move_to_element(installed_only).click().perform()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        # This serves as a check for the presence of the upgrade notification.
        admin_component.toolshed.upgrade_notification.wait_for_visible()
        self.screenshot("admin_toolshed_repo_installed")
        repository_row = self.find_element_by_xpath(f"//div[contains(text(), '{repository_name}')]/..")
        repository_row.click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("admin_toolshed_installed_only")
        # Unfortunately reusing the element isn't feasible, since the div
        # containing the button gets replaced with a new div and button.
        uninstall_button = self.find_element_by_xpath("(//button[contains(., 'Uninstall')])[1]")
        uninstall_button.click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("admin_toolshed_repo_uninstalled")

    @selenium_test
    @requires_admin
    def test_admin_dependencies_display(self):
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()
        self.screenshot("admin_landing")
        admin_component.index.dependencies.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        # Ensure that tabs are visible
        self.find_element_by_link_text("Dependencies")
        self.find_element_by_link_text("Containers")
        unused_link = self.find_element_by_link_text("Unused")
        # Ensure that #manage-resolver-type is visible.
        admin_component.manage_dependencies.resolver_type.wait_for_visible()
        self.screenshot("admin_dependencies_landing")
        self.action_chains().move_to_element(unused_link).click().perform()
        self.sleep_for(self.wait_types.UX_RENDER)
        # Ensure that the unused paths table is visible.
        admin_component.manage_dependencies.unused_paths.wait_for_visible()
        self.screenshot("admin_dependencies_unused")

    @selenium_test
    @requires_admin
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
        manage_jobs = admin_component.manage_jobs
        lock_label = manage_jobs.job_lock_label
        original_label = lock_label.wait_for_text()
        lock_label.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        # Make sure the job lock has been toggled.
        new_label = lock_label.wait_for_text()
        assert new_label != original_label
        self.screenshot("admin_jobs_locked")
        lock_label.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.screenshot("admin_jobs_unlocked")
        # And confirm that it has toggled back to what it was.
        assert lock_label.wait_for_text() == original_label

    @selenium_test
    @requires_admin
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
        self.assert_message(self.components.admin.warning, "No display applications available.")
        self.screenshot("admin_display_applications")

        admin_component.index.jobs.wait_for_and_click()
        admin_component.update_jobs.wait_for_visible()
        self.screenshot("admin_manage_jobs")

        admin_component.index.local_data.wait_for_and_click()
        title_element = admin_component.dm_title.wait_for_visible()
        assert title_element.text == "Local Data"
        self.screenshot("admin_local_data")

    @selenium_test
    @requires_admin
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
    @requires_admin
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
            run_response = self.dataset_populator.run_tool_raw(
                tool_id="data_manager",
                inputs={"ignored_value": "test"},
                history_id=history_id,
            )
            job_id = run_response.json()["jobs"][0]["id"]
            self.dataset_populator.wait_for_tool_run(history_id=history_id, run_response=run_response, assert_ok=False)

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
