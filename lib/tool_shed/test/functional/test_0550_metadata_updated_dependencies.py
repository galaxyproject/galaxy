import logging

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

log = logging.getLogger(__name__)

repositories = dict(
    freebayes=dict(
        name="package_freebayes_0550",
        description="Description for package_freebayes_0550",
        long_description="Long description for package_freebayes_0550",
    ),
    samtools=dict(
        name="package_samtools_0550",
        description="Description for package_samtools_0550",
        long_description="Long description for package_samtools_0550",
    ),
    filtering=dict(
        name="filtering_0550",
        description="Description for filtering_0550",
        long_description="Long description for filtering_0550",
    ),
)

category_name = "Test 0550"
category_description = "Verify metadata updates"

"""
1. Create repository package_freebayes_0550.

2. Create repository package_samtools_0550.

3. Create repository filtering_0550.

4. Create dependency on package_freebayes_0550 for filtering_0550.

5. Create dependency on package_samtools_0550 for filtering_0550.

6. Update package_freebayes_0550 and package_samtools_0550.

5. Load /api/repositories/{filtering_0550}.id/metadata and verify contents.
"""


class TestGetUpdatedMetadata(ShedTwillTestCase):
    """Verify that updated repositories still have correct dependency links."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_freebayes_repository(self):
        """Create and populate package_freebayes_0550."""
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        # Create a repository named package_freebayes_0550 owned by user1.
        freebayes_repository = self.get_or_create_repository(
            name=repositories["freebayes"]["name"],
            description=repositories["freebayes"]["description"],
            long_description=repositories["freebayes"]["long_description"],
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.commit_tar_to_repository(
            freebayes_repository,
            "0550_files/package_freebayes_1_0550.tgz",
        )
        if not self.is_v2:
            # Visit the manage repository page for package_freebayes_0_5_9_0100.
            self.display_manage_repository_page(
                freebayes_repository, strings_displayed=["Tool dependencies", "will not be", "to this repository"]
            )

    def test_0010_create_samtools_repository(self):
        """Create and populate the package_samtools_0550 repository."""
        category = self.create_category(name=category_name, description=category_description)
        samtools_repository = self.get_or_create_repository(
            name=repositories["samtools"]["name"],
            description=repositories["samtools"]["description"],
            long_description=repositories["samtools"]["long_description"],
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.commit_tar_to_repository(
            samtools_repository,
            "0550_files/package_samtools_1_0550.tgz",
            commit_message="Uploaded samtools 1.0.",
        )

    def test_0015_create_filtering_repository(self):
        """Create the filtering_0550 repository."""
        category = self.create_category(name=category_name, description=category_description)
        repository = self.get_or_create_repository(
            name=repositories["filtering"]["name"],
            description=repositories["filtering"]["description"],
            long_description=repositories["filtering"]["long_description"],
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.commit_tar_to_repository(
            repository,
            "0550_files/filtering_1.0.tgz",
            commit_message="Uploaded filtering 1.0.",
        )

    def test_0020_check_repository_dependency(self):
        """Make filtering depend on samtools and freebayes."""
        freebayes = self._get_repository_by_name_and_owner(repositories["freebayes"]["name"], common.test_user_1_name)
        samtools = self._get_repository_by_name_and_owner(repositories["samtools"]["name"], common.test_user_1_name)
        filtering = self._get_repository_by_name_and_owner(repositories["filtering"]["name"], common.test_user_1_name)
        strings_displayed = [freebayes.id, samtools.id]
        if not self.is_v2:
            self.display_manage_repository_page(filtering, strings_displayed=strings_displayed)

    def test_0025_update_dependent_repositories(self):
        """
        Update freebayes and samtools, load the API endpoint again.
        """
        freebayes = self._get_repository_by_name_and_owner(repositories["freebayes"]["name"], common.test_user_1_name)
        samtools = self._get_repository_by_name_and_owner(repositories["samtools"]["name"], common.test_user_1_name)
        filtering = self._get_repository_by_name_and_owner(repositories["filtering"]["name"], common.test_user_1_name)
        self.commit_tar_to_repository(
            freebayes,
            "0550_files/package_freebayes_2_0550.tgz",
            commit_message="Uploaded freebayes 2.0.",
        )
        self.commit_tar_to_repository(
            samtools,
            "0550_files/package_samtools_2_0550.tgz",
            commit_message="Uploaded samtools 2.0.",
        )
        strings_displayed = [
            repositories["freebayes"]["name"],
            repositories["samtools"]["name"],
            repositories["filtering"]["name"],
        ]
        self.fetch_repository_metadata(filtering, strings_displayed=strings_displayed, strings_not_displayed=None)
