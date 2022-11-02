import os
import tempfile

from galaxy.tool_util.parser import get_tool_source
from galaxy.util.compression_utils import CompressedFile
from galaxy.util.resources import resource_path
from galaxy_test.base import api_asserts
from tool_shed.test.base.populators import repo_tars
from ..base.api import ShedApiTestCase

COLUMN_MAKER_PATH = resource_path(__package__, "../test_data/column_maker/column_maker.tar")


class TestShedRepositoriesApi(ShedApiTestCase):
    def test_create(self):
        populator = self.populator
        category_id = populator.new_category(prefix="testcreate").id

        repos_by_category = populator.repositories_by_category(category_id)
        repos = repos_by_category.repositories
        assert len(repos) == 0

        populator.new_repository(category_id)
        repos_by_category = populator.repositories_by_category(category_id)
        repos = repos_by_category.repositories
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

    def test_repo_tars(self):
        for index, repo_path in enumerate(repo_tars("column_maker")):
            path = CompressedFile(repo_path).extract(tempfile.mkdtemp())
            tool_xml_path = os.path.join(path, "column_maker.xml")
            tool_source = get_tool_source(config_file=tool_xml_path)
            tool_version = tool_source.parse_version()
            if index == 0:
                assert tool_version == "1.1.0"
            elif index == 1:
                assert tool_version == "1.2.0"
            elif index == 2:
                assert tool_version == "1.3.0"
            else:
                raise AssertionError("Wrong number of repo tars returned...")

    def test_reset_on_simple_repository(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker")
        populator.assert_has_n_installable_revisions(repository, 3)
        response = self.api_interactor.post(
            "repositories/reset_metadata_on_repository", data={"repository_id": repository.id}
        )
        api_asserts.assert_status_code_is_ok(response)
        populator.assert_has_n_installable_revisions(repository, 3)

    def test_reset_with_uninstallable_revisions(self):
        populator = self.populator
        # setup a repository with 4 revisions but only 3 installable ones due to no version change in a tool
        repository = populator.setup_test_data_repo("column_maker_with_download_gaps")
        populator.assert_has_n_installable_revisions(repository, 3)
        response = self.api_interactor.post(
            "repositories/reset_metadata_on_repository", data={"repository_id": repository.id}
        )
        api_asserts.assert_status_code_is_ok(response)
        populator.assert_has_n_installable_revisions(repository, 3)

    def test_reset_all(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker_with_download_gaps")
        populator.assert_has_n_installable_revisions(repository, 3)
        # reseting one at a time or resetting everything via the web controllers works...
        # reseting all at once via the API does not work - it breaks the repository
        response = self.api_interactor.post(
            "repositories/reset_metadata_on_repositories",
            data={"payload": "can not be empty because bug in controller"},
        )
        api_asserts.assert_status_code_is_ok(response)
        populator.assert_has_n_installable_revisions(repository, 3)
