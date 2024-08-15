import logging

from ..base import common
from ..base.api import skip_if_api_v2
from ..base.twilltestcase import ShedTwillTestCase

log = logging.getLogger(__name__)

repository_name = "htseq_count_0140"
repository_description = "Converter: BED to GFF"
repository_long_description = "Convert bed to gff"

category_name = "Test 0140 Tool Help Images"
category_description = "Test 0140 Tool Help Images"

"""
1) Create and populate the htseq_count_0140 repository.
2) Visit the manage_repository page.
3) Simulate clicking the htseq_count tool button.
4) On the resulting display tool page, look for the image string similar to the following string where the encoded repository_id is previously determined:

src="/repository/static/images/<id>/count_modes.png"
"""


class TestToolHelpImages(ShedTwillTestCase):
    """Test features related to tool help images."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_htseq_count_repository(self):
        """Create and populate htseq_count_0140.

        We are at step 1 - Create and populate the htseq_count_0140 repository.
        Create the htseq_count_0140 repository and upload the tarball.
        """
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        # Create a repository named htseq_count_0140 owned by user1.
        repository = self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        # Upload htseq_count.tar to the repository.
        self.commit_tar_to_repository(
            repository,
            "htseq_count/htseq_count.tar",
            commit_message="Uploaded htseq_count.tar.",
        )

    @skip_if_api_v2
    def test_0010_load_tool_page(self):
        """Load the tool page and check for the image.

        We are at step 2
        Visit the manage_repository page and the tool page, and look for the image url
        similar to the following string:

        src="/repository/static/images/<id>/count_modes.png"
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        # Get the repository tip.
        changeset_revision = self.get_repository_tip(repository)
        self.display_manage_repository_page(repository)
        # Generate the image path.
        image_path = f'src="/repository/static/images/{repository.id}/count_modes.png"'
        # The repository uploaded in this test should only have one metadata revision, with one tool defined, which
        # should be the tool that contains a link to the image.
        repository_metadata = self._db_repository(repository).metadata_revisions[0].metadata
        tool_path = repository_metadata["tools"][0]["tool_config"]
        self.load_display_tool_page(
            repository, tool_path, changeset_revision, strings_displayed=[image_path], strings_not_displayed=[]
        )
