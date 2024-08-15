import logging

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

log = logging.getLogger(__name__)

repository_name = "filtering_0420"
repository_description = "Galaxy filtering tool for test 0420"
repository_long_description = "Long description of Galaxy filtering tool for test 0420"

first_changeset_hash = ""

"""
1. Add and populate a repository to the tool shed with change set revision 0 (assume owner is test).
2. Add valid change set revision 1.
3. Visit the following url and check for appropriate strings: <tool shed base url>/view/user1
4. Visit the following url and check for appropriate strings: <tool shed base url>/view/user1/filtering_0420 .
   The resulting page should contain change set revision 1
5. Visit the following url and check for appropriate strings: <tool shed base url>/view/user1/filtering_0420/<revision 0> .
   The resulting page should not contain change set revision 1, but should contain change set revision 0.
6. Visit the following url and check for appropriate strings: <tool shed base url>/view/user1/filtering_0420/<invalid revision>
7. Visit the following url and check for appropriate strings: <tool shed base url>/view/user1/<invalid repository name>
8. Visit the following url and check for appropriate strings: <tool shed base url>/view/<invalid owner>
"""


class TestRepositoryCitableURLs(ShedTwillTestCase):
    """Test repository citable url features."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts and login as an admin user.

        Create all the user accounts that are needed for this test script to run independently of other tests.
        Previously created accounts will not be re-created.
        """
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username, explicit_logout=True)

    def test_0005_create_repository(self):
        """Create and populate the filtering_0420 repository

        We are at step 1.
        Add and populate a repository to the tool shed with change set revision 0 (assume owner is test_user_1).
        """
        global first_changeset_hash
        category = self.create_category(
            name="Test 0400 Repository Citable URLs", description="Test 0400 Repository Citable URLs category"
        )
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        strings_displayed = self.expect_repo_created_strings(repository_name)
        repository = self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=strings_displayed,
        )
        self.commit_tar_to_repository(
            repository,
            "filtering/filtering_2.2.0.tar",
            commit_message="Uploaded filtering 2.2.0 tarball.",
        )
        # We'll be checking for this hash later, after uploading another file to the repository, making get_repository_tip() not usable.
        first_changeset_hash = self.get_repository_tip(repository)

    def test_0010_upload_new_file_to_repository(self):
        """Upload a readme file to the repository in order to create a second changeset revision.

        We are at step 2.
        Add valid change set revision 1.
        The repository should now contain two changeset revisions, 0:<revision hash> and 1:<revision hash>.
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        self.add_file_to_repository(repository, "readme.txt")

    def test_0015_load_user_view_page(self):
        """Load the /view/<username> page amd check for strings.

        We are at step 3.
        Visit the following url and check for appropriate strings: <tool shed base url>/view/user1
        """
        test_user_1 = self.test_db_util.get_user(common.test_user_1_email)
        encoded_user_id = self.security.encode_id(test_user_1.id)
        # Since twill does not load the contents of an iframe, we need to check that the iframe has been generated correctly,
        # then directly load the url that the iframe should be loading and check for the expected strings.
        # The iframe should point to /repository/browse_repositories?user_id=<encoded user ID>&operation=repositories_by_user
        if self.is_v2:
            strings_displayed = []
        else:
            strings_displayed = ["/repository/browse_repositories", encoded_user_id, "operation=repositories_by_user"]
            strings_displayed.append(encoded_user_id)
        strings_displayed_in_iframe = ["user1", "filtering_0420", repository_description]
        self.load_citable_url(
            username="user1",
            repository_name=None,
            changeset_revision=None,
            encoded_user_id=encoded_user_id,
            encoded_repository_id=None,
            strings_displayed=strings_displayed,
            strings_displayed_in_iframe=strings_displayed_in_iframe,
        )

    def test_0020_load_repository_view_page(self):
        """Load the /view/<user>/<repository> page and check for the appropriate strings.

        We are at step 4.
        Visit the following url and check for strings: ``<tool shed base url>/view/user1/filtering_0420`` .
        The resulting page should contain change set revision 1
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        test_user_1 = self.test_db_util.get_user(common.test_user_1_email)
        encoded_user_id = self.security.encode_id(test_user_1.id)
        encoded_repository_id = repository.id
        # Since twill does not load the contents of an iframe, we need to check that the iframe has been generated correctly,
        # then directly load the url that the iframe should be loading and check for the expected strings.
        # The iframe should point to /repository/bview_repository?id=<encoded repository ID>
        if self.is_v2:
            strings_displayed = []
        else:
            strings_displayed = ["/repository", "view_repository", "id=", encoded_repository_id]
        strings_displayed_in_iframe = [
            "user1",
            "filtering_0420",
            self._escape_page_content_if_needed(repository_long_description),
        ]
        strings_displayed_in_iframe.append(self.get_repository_tip(repository))
        if not self.is_v2:
            strings_displayed_in_iframe.append("Link to this repository:")
            strings_displayed_in_iframe.append(f"{self.url}/view/user1/filtering_0420")
        self.load_citable_url(
            username="user1",
            repository_name="filtering_0420",
            changeset_revision=None,
            encoded_user_id=encoded_user_id,
            encoded_repository_id=encoded_repository_id,
            strings_displayed=strings_displayed,
            strings_displayed_in_iframe=strings_displayed_in_iframe,
        )

    def test_0025_load_view_page_for_previous_revision(self):
        """Load a citable url for a past changeset revision and verify that strings display.

        We are at step 5.
        Visit the following url and check for appropriate strings: ``<tool shed base url>/view/user1/filtering_0420/<revision 0>`` .
        The resulting page should not contain change set revision 1, but should contain change set revision 0.
        """
        global first_changeset_hash
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        test_user_1 = self.test_db_util.get_user(common.test_user_1_email)
        encoded_user_id = self.security.encode_id(test_user_1.id)
        encoded_repository_id = repository.id
        # Since twill does not load the contents of an iframe, we need to check that the iframe has been generated correctly,
        # then directly load the url that the iframe should be loading and check for the expected strings.
        # The iframe should point to /repository/view_repository?id=<encoded repository ID>
        if self.is_v2:
            strings_displayed = []
        else:
            strings_displayed = ["/repository", "view_repository", f"id={encoded_repository_id}"]
        strings_displayed_in_iframe = [
            "user1",
            "filtering_0420",
            self._escape_page_content_if_needed(repository_long_description),
            first_changeset_hash,
        ]
        if not self.is_v2:
            strings_displayed_in_iframe.append("Link to this repository revision:")
            strings_displayed_in_iframe.append(f"{self.url}/view/user1/filtering_0420/{first_changeset_hash}")
        self.load_citable_url(
            username="user1",
            repository_name="filtering_0420",
            changeset_revision=first_changeset_hash,
            encoded_user_id=encoded_user_id,
            encoded_repository_id=encoded_repository_id,
            strings_displayed=strings_displayed,
            strings_displayed_in_iframe=strings_displayed_in_iframe,
        )

    def test_0030_load_sharable_url_with_invalid_changeset_revision(self):
        """Load a citable url with an invalid changeset revision specified."""
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        test_user_1 = self.test_db_util.get_user(common.test_user_1_email)
        encoded_user_id = self.security.encode_id(test_user_1.id)
        encoded_repository_id = repository.id
        invalid_changeset_hash = "invalid"
        if not self.is_v2:
            # Since twill does not load the contents of an iframe, we need to check that the iframe has been generated correctly,
            # then directly load the url that the iframe should be loading and check for the expected strings.
            # The iframe should point to /repository/view_repository?id=<encoded repository ID>&status=error
            strings_displayed = ["/repository", "view_repository", f"id={encoded_repository_id}"]
            strings_displayed.extend(
                ["The+change+log", "does+not+include+revision", invalid_changeset_hash, "status=error"]
            )
        else:
            strings_displayed = ["The change log does not include revision " + invalid_changeset_hash]
        self.load_citable_url(
            username="user1",
            repository_name="filtering_0420",
            changeset_revision=invalid_changeset_hash,
            encoded_user_id=encoded_user_id,
            encoded_repository_id=encoded_repository_id,
            strings_displayed=strings_displayed,
        )

    def test_0035_load_sharable_url_with_invalid_repository_name(self):
        """Load a citable url with an invalid changeset revision specified.

        We are at step 7.
        Visit the following url and check for appropriate strings: <tool shed base url>/view/user1/!!invalid!!
        """
        test_user_1 = self.test_db_util.get_user(common.test_user_1_email)
        encoded_user_id = self.security.encode_id(test_user_1.id)
        # Since twill does not load the contents of an iframe, we need to check that the iframe has been generated correctly,
        # then directly load the url that the iframe should be loading and check for the expected strings.
        # The iframe should point to /repository/browse_repositories?user_id=<encoded user ID>&operation=repositories_by_user
        if not self.is_v2:
            strings_displayed = ["/repository", "browse_repositories", "user1"]
            strings_displayed.extend(
                ["list+of+repositories+owned", "does+not+include+one+named", "%21%21invalid%21%21", "status=error"]
            )
            strings_displayed_in_iframe = ["user1", "filtering_0420"]
            strings_displayed_in_iframe.append("Repositories Owned by user1")
        else:
            strings_displayed = ["Repository user1/!!invalid!! is not found"]
            strings_displayed_in_iframe = []
        self.load_citable_url(
            username="user1",
            repository_name="!!invalid!!",
            changeset_revision=None,
            encoded_user_id=encoded_user_id,
            encoded_repository_id=None,
            strings_displayed=strings_displayed,
            strings_displayed_in_iframe=strings_displayed_in_iframe,
        )

    def test_0040_load_sharable_url_with_invalid_owner(self):
        """Load a citable url with an invalid owner.

        We are at step 8.
        Visit the following url and check for appropriate strings: <tool shed base url>/view/!!invalid!!
        """
        if not self.is_v2:
            strings_displayed = ["The tool shed", self.url, "contains no repositories owned by", "!!invalid!!"]
        else:
            strings_displayed = ["No repositories found"]
        self.load_citable_url(
            username="!!invalid!!",
            repository_name=None,
            changeset_revision=None,
            encoded_user_id=None,
            encoded_repository_id=None,
            strings_displayed=strings_displayed,
        )
