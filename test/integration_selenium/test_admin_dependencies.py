from .framework import (
    selenium_test,
    SeleniumIntegrationTestCase,
)


class TestAdminDependencyContainers(SeleniumIntegrationTestCase):
    run_as_admin = True

    @selenium_test
    def test_admin_containers_display(self):
        admin_component = self.components.admin
        self.admin_login()
        self.admin_open()
        self.screenshot("admin_landing")
        admin_component.index.dependencies.wait_for_and_click()
        self.sleep_for(self.wait_types.UX_RENDER)
        # Make sure the tabs are visible
        self.find_element_by_link_text("Dependencies")
        self.find_element_by_link_text("Unused")
        containers_link = self.find_element_by_link_text("Containers")
        # Ensure that #manage-resolver-type is visible.
        admin_component.manage_dependencies.resolver_type.wait_for_visible()
        self.screenshot("admin_dependencies_landing")
        self.move_to_and_click(containers_link)
        self.sleep_for(self.wait_types.UX_RENDER)
        # Ensure that #manage-container-type is visible.
        self.sleep_for(self.wait_types.UX_TRANSITION)
        admin_component.manage_dependencies.container_type.wait_for_visible()
        self.screenshot("admin_dependencies_containers")
