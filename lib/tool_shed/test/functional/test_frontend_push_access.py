from playwright.sync_api import expect

from galaxy_test.base import api_asserts
from tool_shed_client.schema import (
    Repository,
    UpdateRepositoryRequest,
)
from ..base.api_util import email_to_username
from ..base.playwrightbrowser import Locators
from ..base.playwrighttestcase import PlaywrightTestCase

TEST_PASSWORD = "testpass"
OWNER_EMAIL = "guipushowner@galaxyproject.org"
COLLABORATOR_EMAIL = "guipushcollaborator@galaxyproject.org"
TEST_PREFIX = "guitestpushaccess"


class TestFrontendPushAccess(PlaywrightTestCase):
    """Frontend tests for delegating publishing rights from the repository page."""

    def test_owner_delegates_push_access(self):
        owner = email_to_username(OWNER_EMAIL)
        collaborator = email_to_username(COLLABORATOR_EMAIL)
        collaborator_populator = self.user_populator(email=COLLABORATOR_EMAIL, password=TEST_PASSWORD)
        repository = self._new_repository()
        request = UpdateRepositoryRequest(description="Published by a push collaborator")

        # Before the grant the collaborator cannot update repository metadata.
        api_asserts.assert_status_code_is(collaborator_populator.update_raw(repository, request), 403)

        self.login(OWNER_EMAIL, TEST_PASSWORD, username=owner)
        self.display_manage_repository_page(repository)
        page = self._page
        expect(page.locator(Locators.push_access_owner)).to_have_text(f"{owner} (owner)")
        expect(self._playwright_browser.push_access_entry(collaborator)).to_have_count(0)

        self._browser.grant_users_access([collaborator])
        expect(self._playwright_browser.push_access_entry(collaborator)).to_have_count(1)

        # The grant made in the UI delegates publishing, not repository management.
        collaborator_populator.update(repository, request)
        updated = self.populator.get_repository(repository.id)
        assert updated.owner == owner
        assert updated.description == request.description
        api_asserts.assert_status_code_is(collaborator_populator.add_admin_user_raw(repository, collaborator), 403)

        self._browser.revoke_user_access(collaborator)
        expect(self._playwright_browser.push_access_entry(collaborator)).to_have_count(0)
        revoked_request = UpdateRepositoryRequest(description="Should not be applied after revocation")
        api_asserts.assert_status_code_is(collaborator_populator.update_raw(repository, revoked_request), 403)
        assert self.populator.get_repository(repository.id).description == request.description

    def test_push_access_lists_repository_owner_not_viewer(self):
        owner = email_to_username(OWNER_EMAIL)
        repository = self._new_repository()

        # Site admins can manage any repository - the list must name the owner, not the viewer.
        self.login()
        self.display_manage_repository_page(repository)
        page = self._page
        expect(page.locator(Locators.push_access_owner)).to_have_text(f"{owner} (owner)")
        expect(page.locator(Locators.push_access)).not_to_contain_text("admin-user")

    def _new_repository(self) -> Repository:
        owner_populator = self.user_populator(email=OWNER_EMAIL, password=TEST_PASSWORD)
        category = owner_populator.new_category(prefix=TEST_PREFIX)
        return owner_populator.new_repository(category.id, prefix=TEST_PREFIX)
