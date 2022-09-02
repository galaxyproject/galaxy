from galaxy.util.resources import resource_path
from galaxy_test.base import api_asserts
from ..base.api import ShedApiTestCase

COLUMN_MAKER_PATH = resource_path(__package__, "../test_data/column_maker/column_maker.tar")


# Things seemingly *NOT* used by Galaxy, Planemo, or Ephemeris...
#   (perhaps we can delete instead of test?)...
# - reset_metadata_on_repository
# - reset_metadata_on_repositories
# - remove_repository_registry_entry
# - get_repository_revision_install_info
# - get_installable_revisions

# Non repositories API seemingly unused and seemingly better rewritten if wanted.
# - The whole Groups API.
# - The whole Repository Revisions API.
class ShedRepositoriesApiTestCase(ShedApiTestCase):
    def test_create(self):
        populator = self.populator
        category_id = populator.new_category(prefix="testcreate").id

        response = self.api_interactor.get(f"categories/{category_id}/repositories")
        api_asserts.assert_status_code_is_ok(response)
        repos = response.json()["repositories"]
        assert len(repos) == 0

        populator.new_repository(category_id)
        response = self.api_interactor.get(f"categories/{category_id}/repositories")
        api_asserts.assert_status_code_is_ok(response)
        repos = response.json()["repositories"]
        assert len(repos) == 1

    def test_update_repository(self):
        populator = self.populator
        prefix = "testupdate"
        category_id = populator.new_category(prefix=prefix).id
        repository = populator.new_repository(category_id, prefix=prefix)
        repository_id = repository.id
        repository_update = populator.upload_revision(
            repository_id,
            COLUMN_MAKER_PATH,
        )
        assert repository_update.is_ok

    # used by getRepository in TS client.
    def test_metadata_simple(self):
        populator = self.populator
        repository_id = populator.setup_column_maker_repo(prefix="repoformetadata").id
        metadata_response = self.api_interactor.get(f"repositories/{repository_id}/metadata")
        api_asserts.assert_status_code_is_ok(metadata_response)
        metadata_for_revisions = metadata_response.json()
        assert len(metadata_for_revisions) == 1
        only_key = list(metadata_for_revisions.keys())[0]
        assert only_key.startswith("0:")
        only_revision = list(metadata_for_revisions.values())[0]
        api_asserts.assert_has_keys(only_revision, "repository", "repository_dependencies", "numeric_revision")

    def test_index_simple(self):
        populator = self.populator
        repository_id = populator.setup_column_maker_repo(prefix="repoforindex").id
        show_response = self.api_interactor.get(f"repositories/{repository_id}")
        index_response = self.api_interactor.get("repositories")
        api_asserts.assert_status_code_is_ok(show_response)
        api_asserts.assert_status_code_is_ok(index_response)
        repository_ids = [r["id"] for r in index_response.json()]
        assert repository_id in repository_ids

    def test_get_ordered_installable_revisions(self):
        # Used in ephemeris...
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repoforindex")
        assert repository.owner
        assert repository.name
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.__root__) == 1
