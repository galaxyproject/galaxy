from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from .framework import (
    selenium_test,
    SeleniumTestCase,
)


class WorkflowSharingTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_share_workflow_with_login_redirect(self):
        user_email = self.get_logged_in_user()["email"]
        workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_SIMPLE_CAT_TWICE)
        self.logout()
        sharing_url = f"workflow/sharing?id={workflow_id}"
        self.get(sharing_url)
        modal = self.components._.messages.error.wait_for_present()
        assert modal.text == "You must be logged in to Share or export Galaxy workflows."
        login_link = modal.find_element_by_tag_name("a")
        assert login_link.text == "logged in"
        self.sleep_for(self.wait_types.UX_RENDER)
        login_link.click()
        form = self.wait_for_visible(self.navigation.login.selectors.form)
        self.fill(form, {"login": user_email, "password": self.default_password})
        self.wait_for_and_click(self.navigation.login.selectors.submit)
        self.wait_for_logged_in()
        accessible_via_link_button = self.wait_for_selector(".make-accessible")
        accessible_via_link_button.click()
        self.wait_for_xpath('//strong[text()="accessible via link"]')
