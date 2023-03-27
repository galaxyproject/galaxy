from galaxy.util.resources import resource_path
from galaxy_test.base import api_asserts
from ..base.api import ShedApiTestCase

COLUMN_MAKER_PATH = resource_path(__package__, "../test_data/column_maker/column_maker.tar")


class TestShedRepositoriesApi(ShedApiTestCase):
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
        repository = populator.setup_column_maker_repo(prefix="repoformetadata")
        repository_metadata = populator.get_metadata(repository)
        metadata_for_revisions = repository_metadata.__root__
        assert len(metadata_for_revisions) == 1
        only_key = list(metadata_for_revisions.keys())[0]
        assert only_key.startswith("0:")
        only_revision = list(metadata_for_revisions.values())[0]
        assert only_revision
        assert only_revision.downloadable
        assert not only_revision.malicious

    def test_index_simple(self):
        populator = self.populator
        repo = populator.setup_column_maker_repo(prefix="repoforindex")
        repository_id = repo.id
        show_response = self.api_interactor.get(f"repositories/{repository_id}")
        index_response = self.api_interactor.get("repositories")
        api_asserts.assert_status_code_is_ok(show_response)
        api_asserts.assert_status_code_is_ok(index_response)
        repository_ids = [r["id"] for r in index_response.json()]
        assert repository_id in repository_ids

        repository = self.populator.get_repository_for(repo.owner, repo.name)
        assert repository.owner == repo.owner
        assert repository.name == repo.name

    def test_install_info(self):
        # actually installing requires a whole Galaxy setup and the install manager but
        # we can test the response validates against the future facing InstallInfo pydandic
        # models.
        populator = self.populator
        repo = populator.setup_column_maker_and_get_metadata(prefix="repoforinstallinfo")
        populator.get_install_info(repo)

    def test_get_ordered_installable_revisions(self):
        # Used in ephemeris...
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repoforindex")
        assert repository.owner
        assert repository.name
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.__root__) == 1

    def test_reset_on_repository(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repoforreseta")
        assert repository.owner
        assert repository.name
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.__root__) == 1
        metadata_response = populator.reset_metadata(repository)
        assert metadata_response.start_time
        assert metadata_response.stop_time
        assert metadata_response.status == "ok"
        assert len(metadata_response.repository_status) == 1
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.__root__) == 1

    def test_repository_search(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repoforreposearch")
        populator.reindex()
        results = populator.repo_search_query("repoforreposearch")
        assert len(results.hits) == 1
        first_hit = results.hits[0]
        assert first_hit.repository.name == repository.name
        assert first_hit.repository.times_downloaded == 0
