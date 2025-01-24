import logging
import os

from ..base import common
from ..base.twilltestcase import ShedTwillTestCase

log = logging.getLogger(__name__)

repository_name = "filtering_0310"
repository_description = "Galaxy's filtering tool for test 0310"
repository_long_description = "Long description of Galaxy's filtering tool for test 0310"

category_name = "Test 0310 - HTTP Repo features"
category_description = "Test 0310 for verifying the tool shed http interface to mercurial."

"""
1. Create a repository.
2. Clone the repository to a local path.
"""


class TestHgWebFeatures(ShedTwillTestCase):
    """Test http mercurial interface."""

    def test_0000_initiate_users(self):
        """Create necessary user accounts and login as an admin user."""
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        self.login(email=common.test_user_2_email, username=common.test_user_2_name)
        self.login(email=common.admin_email, username=common.admin_username)

    def test_0005_create_filtering_repository(self):
        """Create and populate the filtering_0310 repository.

        We are at step 1 - Create a repository.
        Create and populate the filtering_0310 repository.
        """
        category = self.create_category(name=category_name, description=category_description)
        self.login(email=common.test_user_1_email, username=common.test_user_1_name)
        repository = self.get_or_create_repository(
            name=repository_name,
            description=repository_description,
            long_description=repository_long_description,
            owner=common.test_user_1_name,
            category=category,
            strings_displayed=[],
        )
        self.commit_tar_to_repository(
            repository,
            "filtering/filtering_1.1.0.tar",
            commit_message="Uploaded filtering 1.1.0.",
        )

    def test_0010_clone(self):
        """Clone the repository to a local path.

        We are at step 2 - Clone the repository to a local path.
        The repository should have the following files:

        filtering.py
        filtering.xml
        test-data/
        test-data/1.bed
        test-data/7.bed
        test-data/filter1_in3.sam
        test-data/filter1_inbad.bed
        test-data/filter1_test1.bed
        test-data/filter1_test2.bed
        test-data/filter1_test3.sam
        test-data/filter1_test4.bed
        """
        repository = self._get_repository_by_name_and_owner(repository_name, common.test_user_1_name)
        clone_path = self.generate_temp_path("test_0310", additional_paths=["filtering_0310", "user2"])
        self.clone_repository(repository, clone_path)
        files_in_repository = os.listdir(clone_path)
        assert "filtering.py" in files_in_repository, "File not found in repository: filtering.py"
