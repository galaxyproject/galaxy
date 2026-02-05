import json
import os
import tempfile

from galaxy.tool_util.parser import get_tool_source
from galaxy.util.compression_utils import CompressedFile
from galaxy.util.resources import resource_path
from galaxy_test.base import api_asserts
from tool_shed.test.base.api_util import create_user
from tool_shed.test.base.hg_operations import HgRepositoryOperations
from tool_shed.test.base.populators import (
    HasRepositoryId,
    repo_tars,
)
from tool_shed_client.schema import (
    RepositoryIndexRequest,
    RepositoryPaginatedIndexRequest,
    RepositoryRevisionMetadata,
    UpdateRepositoryRequest,
)
from ..base.api import (
    ShedApiTestCase,
    skip_if_api_v1,
    skip_if_api_v2,
)

COLUMN_MAKER_PATH = resource_path(__name__, "../test_data/column_maker/column_maker.tar")


# test_0000 tests commit_message  - find a way to test it here
class TestShedRepositoriesApi(ShedApiTestCase):
    def test_create(self):
        populator = self.populator
        category1_id = populator.new_category(prefix="testcreate").id
        populator.assert_category_has_n_repositories(category1_id, 0)

        populator.new_repository(category1_id)
        populator.assert_category_has_n_repositories(category1_id, 1)

        # Test creating repository with multiple categories
        category2_id = populator.new_category(prefix="testcreate").id
        populator.assert_category_has_n_repositories(category2_id, 0)
        populator.new_repository([category1_id, category2_id])
        populator.assert_category_has_n_repositories(category1_id, 2)
        populator.assert_category_has_n_repositories(category2_id, 1)

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

    def test_update_repository_info(self):
        populator = self.populator
        prefix = "testupdateinfo"
        category_id = populator.new_category(prefix=prefix).id
        repository = populator.new_repository(category_id, prefix=prefix)
        repository_id = repository.id
        request = UpdateRepositoryRequest(homepage_url="https://www.google.com")
        update = populator.update(repository_id, request)
        assert update.homepage_url == "https://www.google.com"
        assert populator.get_repository(repository_id).homepage_url == "https://www.google.com"

    def test_update_category(self):
        populator = self.populator
        prefix = "testupdatecategory"

        old_category_id = populator.new_category(prefix=prefix).id
        new_category_id = populator.new_category(prefix=prefix).id

        populator.assert_category_has_n_repositories(old_category_id, 0)
        populator.assert_category_has_n_repositories(new_category_id, 0)

        repository = populator.new_repository(old_category_id, prefix=prefix)
        repository_id = repository.id

        populator.assert_category_has_n_repositories(old_category_id, 1)
        populator.assert_category_has_n_repositories(new_category_id, 0)

        request = UpdateRepositoryRequest(category_ids=[new_category_id])
        populator.update(repository_id, request)

        # does this mean we cannot remove categories?
        populator.assert_category_has_n_repositories(old_category_id, 0)
        populator.assert_category_has_n_repositories(new_category_id, 1)

    # used by getRepository in TS client.
    def test_metadata_simple(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repoformetadata")
        repository_metadata = populator.get_metadata(repository)
        metadata_for_revisions = repository_metadata.root
        assert len(metadata_for_revisions) == 1
        only_key = list(metadata_for_revisions.keys())[0]
        assert only_key.startswith("0:")
        only_revision = list(metadata_for_revisions.values())[0]
        assert only_revision
        assert only_revision.downloadable
        assert not only_revision.malicious

    def test_metadata_invalid_tools(self):
        populator = self.populator
        repository = populator.setup_bismark_repo()
        repository_metadata = populator.get_metadata(repository)
        assert repository_metadata
        for _, value in repository_metadata.root.items():
            assert value.invalid_tools

    def test_index_simple(self):
        # Logic and typing is pretty different if given a tool id to search for - this should
        # be tested or dropped in v2.
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
        assert repository
        assert repository.owner == repo.owner
        assert repository.name == repo.name

    @skip_if_api_v1
    def test_index_pagination(self):
        populator = self.populator
        category1 = populator.new_category(prefix="paginatecat1")
        category2 = populator.new_category(prefix="paginatecat2")
        populator.setup_column_maker_repo(prefix="repoforindexpagination1", category_id=category1.id)
        populator.setup_column_maker_repo(prefix="repoforindexpagination2", category_id=category1.id)
        populator.setup_column_maker_repo(prefix="repoforindexpagination3", category_id=category2.id)
        populator.setup_column_maker_repo(prefix="repoforindexpagination4", category_id=category2.id)
        populator.setup_column_maker_repo(prefix="repoforindexpagination5", category_id=category2.id)
        request = RepositoryPaginatedIndexRequest(
            page=1,
            page_size=2,
            category_id=category1.id,
        )
        response = populator.repository_index_paginated(request)
        assert len(response.hits) == 2
        assert response.total_results == 2
        assert response.page == 1
        assert response.page_size == 2

        request.category_id = category2.id
        response = populator.repository_index_paginated(request)
        assert response.total_results == 3
        assert response.page == 1
        assert response.page_size == 2

        request.filter = "repoforindexpagination4"
        response = populator.repository_index_paginated(request)
        assert response.total_results == 1

    @skip_if_api_v1
    def test_index_sorting(self):
        populator = self.populator
        category1 = populator.new_category(prefix="paginatecat1")
        populator.setup_column_maker_repo(prefix="repoforsort_z", category_id=category1.id)
        populator.setup_column_maker_repo(prefix="repoforsort_a", category_id=category1.id)

        response = populator.repository_index(RepositoryIndexRequest())
        order_of_these = [r.name for r in response.root if r.name.startswith("repoforsort")]
        assert "_a" in order_of_these[0]
        assert "_z" in order_of_these[1]

        response = populator.repository_index(RepositoryIndexRequest(sort_desc=True))
        order_of_these = [r.name for r in response.root if r.name.startswith("repoforsort")]
        assert "_z" in order_of_these[0]
        assert "_a" in order_of_these[1]

        # test recently created query
        response = populator.repository_index(RepositoryIndexRequest(sort_desc=True, sort_by="create_time"))
        order_of_these = [r.name for r in response.root if r.name.startswith("repoforsort")]
        assert "_a" in order_of_these[0]
        assert "_z" in order_of_these[1]

    @skip_if_api_v1
    def test_allow_push(self):
        populator = self.populator
        request = {
            "email": "sharewith@galaxyproject.org",
            "username": "sharewith",
            "password": "pAssworD1",
        }
        create_user(self.admin_api_interactor, request)
        request = {
            "email": "alsosharewith@galaxyproject.org",
            "username": "alsosharewith",
            "password": "pAssworD2",
        }
        create_user(self.admin_api_interactor, request)

        repo = populator.setup_column_maker_repo(prefix="repoforindex")
        assert "sharewith" not in populator.get_usernames_allowed_to_push(repo)
        assert "alsosharewith" not in populator.get_usernames_allowed_to_push(repo)

        populator.allow_user_to_push(repo, "sharewith")
        assert "sharewith" in populator.get_usernames_allowed_to_push(repo)
        assert "alsosharewith" not in populator.get_usernames_allowed_to_push(repo)

        populator.allow_user_to_push(repo, "alsosharewith")
        assert "sharewith" in populator.get_usernames_allowed_to_push(repo)
        assert "alsosharewith" in populator.get_usernames_allowed_to_push(repo)

        populator.disallow_user_to_push(repo, "sharewith")
        assert "sharewith" not in populator.get_usernames_allowed_to_push(repo)
        assert "alsosharewith" in populator.get_usernames_allowed_to_push(repo)

    @skip_if_api_v1
    def test_set_malicious(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repoformalicious")

        only_revision = self._get_only_revision(repository)
        assert only_revision.downloadable
        assert not only_revision.malicious

        assert not populator.tip_is_malicious(repository)
        populator.set_malicious(repository, only_revision.changeset_revision)
        assert populator.tip_is_malicious(repository)
        populator.unset_malicious(repository, only_revision.changeset_revision)
        assert not populator.tip_is_malicious(repository)

    @skip_if_api_v1
    def test_set_deprecated(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repofordeprecated")
        assert not repository.deprecated
        assert not populator.is_deprecated(repository)
        populator.set_deprecated(repository)
        assert populator.is_deprecated(repository)
        populator.unset_deprecated(repository)
        assert not populator.is_deprecated(repository)

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
        assert len(revisions.root) == 1

    def test_reset_on_repository(self):
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="repoforreseta")
        assert repository.owner
        assert repository.name
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.root) == 1
        metadata_response = populator.reset_metadata(repository)
        assert metadata_response.start_time
        assert metadata_response.stop_time
        assert metadata_response.status == "ok"
        assert len(metadata_response.repository_status) == 1
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.root) == 1

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
            with CompressedFile(repo_path) as cf:
                path = cf.extract(tempfile.mkdtemp())
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

    @skip_if_api_v1
    def test_readmes(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker_with_readme")
        only_revision = self._get_only_revision(repository)
        populator.assert_has_n_installable_revisions(repository, 1)
        response = self.api_interactor.get(
            f"repositories/{repository.id}/revisions/{only_revision.changeset_revision}/readmes"
        )
        api_asserts.assert_status_code_is_ok(response)
        readme_dicts = response.json()
        assert "readme.txt" in readme_dicts

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

    @skip_if_api_v2
    def test_reset_all_v1(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker_with_download_gaps")
        populator.assert_has_n_installable_revisions(repository, 3)
        # resetting one at a time or resetting everything via the web controllers works...
        # resetting all at once via the API does not work - it breaks the repository
        response = self.api_interactor.post(
            "repositories/reset_metadata_on_repositories",
            data={"payload": "can not be empty because bug in controller"},
        )
        api_asserts.assert_status_code_is_ok(response)
        populator.assert_has_n_installable_revisions(repository, 3)

    @skip_if_api_v1
    def test_reset_all_v2(self):
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker_with_download_gaps")
        populator.assert_has_n_installable_revisions(repository, 3)
        response = self.api_interactor.post("repositories/reset_metadata_on_repositories", json={})
        api_asserts.assert_status_code_is_ok(response)
        populator.assert_has_n_installable_revisions(repository, 3)

    @skip_if_api_v1
    def test_reset_metadata_dry_run(self):
        """Verify dry_run=True returns success but doesn't modify repository."""
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker")
        populator.assert_has_n_installable_revisions(repository, 3)

        response = self.api_interactor.post(
            f"repositories/{repository.id}/reset_metadata",
            params={"dry_run": True},
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()
        assert result["status"] == "ok"
        assert result["dry_run"] is True
        assert "Would reset" in result["repository_status"][0]
        # changeset_details should be None when verbose=False (default)
        assert result.get("changeset_details") is None

        # Revisions should still be there (nothing changed)
        populator.assert_has_n_installable_revisions(repository, 3)

    @skip_if_api_v1
    def test_reset_metadata_verbose(self):
        """Verify verbose=True returns per-changeset details."""
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker")

        response = self.api_interactor.post(
            f"repositories/{repository.id}/reset_metadata",
            params={"verbose": True},
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()
        assert result["status"] == "ok"
        assert result["changeset_details"] is not None
        assert len(result["changeset_details"]) >= 1

        # Verify changeset detail structure
        for detail in result["changeset_details"]:
            assert "changeset_revision" in detail
            assert "numeric_revision" in detail
            assert "comparison_result" in detail or "error" in detail

    @skip_if_api_v1
    def test_reset_metadata_dry_run_and_verbose(self):
        """Verify dry_run + verbose returns details without persisting."""
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker_with_download_gaps")
        populator.assert_has_n_installable_revisions(repository, 3)

        response = self.api_interactor.post(
            f"repositories/{repository.id}/reset_metadata",
            params={"dry_run": True, "verbose": True},
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()

        assert result["dry_run"] is True
        assert result["changeset_details"] is not None
        assert len(result["changeset_details"]) > 0

        # Verify repo unchanged
        populator.assert_has_n_installable_revisions(repository, 3)

    @skip_if_api_v1
    def test_reset_metadata_legacy_endpoint_with_dry_run(self):
        """Verify legacy endpoint supports dry_run in request body."""
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker")

        response = self.api_interactor.post(
            "repositories/reset_metadata_on_repository",
            json={"repository_id": repository.id, "dry_run": True, "verbose": True},
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()

        assert result["dry_run"] is True
        assert result["changeset_details"] is not None

    @skip_if_api_v1
    def test_reset_metadata_verbose_includes_before_after(self):
        """Verify verbose=True returns repository_metadata_before and after snapshots."""
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker")

        response = self.api_interactor.post(
            f"repositories/{repository.id}/reset_metadata",
            params={"verbose": True},
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()

        # Verify before/after are present
        assert "repository_metadata_before" in result
        assert "repository_metadata_after" in result
        assert result["repository_metadata_before"] is not None
        assert result["repository_metadata_after"] is not None

        # Verify structure - should have revision keys
        before = result["repository_metadata_before"]
        after = result["repository_metadata_after"]
        assert len(before) > 0
        assert len(after) > 0

        # Verify each revision has tools with tool_config
        for _rev_key, rev_data in after.items():
            if rev_data.get("tools"):
                for tool in rev_data["tools"]:
                    assert "tool_config" in tool

    @skip_if_api_v1
    def test_reset_metadata_non_verbose_omits_before_after(self):
        """Verify verbose=False (default) omits before/after metadata."""
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker")

        response = self.api_interactor.post(
            f"repositories/{repository.id}/reset_metadata",
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()

        # Before/after should be None when not verbose
        assert result.get("repository_metadata_before") is None
        assert result.get("repository_metadata_after") is None

    def _get_only_revision(self, repository: HasRepositoryId) -> RepositoryRevisionMetadata:
        populator = self.populator
        repository_metadata = populator.get_metadata(repository)
        metadata_for_revisions = repository_metadata.root
        assert len(metadata_for_revisions) == 1
        only_key = list(metadata_for_revisions.keys())[0]
        assert only_key.startswith("0:")
        only_revision = list(metadata_for_revisions.values())[0]
        assert only_revision
        return only_revision

    @skip_if_api_v1
    def test_generate_frontend_fixtures(self):
        """Generate JSON fixture files for frontend unit tests.

        This test captures real API responses and writes them to JSON files that can be
        used as typed mock data in Vitest unit tests for MetadataInspector components.

        By default, fixtures are written to a temp directory and the path is printed.
        To write fixtures to the frontend test directory, set:

            TOOL_SHED_FIXTURE_OUTPUT_DIR=lib/tool_shed/webapp/frontend/src/components/MetadataInspector/__fixtures__

        The generated fixtures include:
        - repository_metadata_column_maker.json: Multi-revision repo with tools (RepositoryMetadata)
        - repository_metadata_bismark.json: Repo with invalid_tools (RepositoryMetadata)
        - reset_metadata_preview.json: Dry-run reset response for column_maker (ResetMetadataOnRepositoryResponse)
        - reset_metadata_applied.json: Applied reset response for column_maker (ResetMetadataOnRepositoryResponse)
        - reset_metadata_bismark.json: Dry-run reset response for bismark (ResetMetadataOnRepositoryResponse)
        """
        populator = self.populator
        output_dir = os.environ.get("TOOL_SHED_FIXTURE_OUTPUT_DIR", tempfile.mkdtemp(prefix="ts_fixtures_"))
        os.makedirs(output_dir, exist_ok=True)

        # 1. RepositoryMetadata - column_maker (multi-revision with tools)
        column_maker_repo = populator.setup_test_data_repo("column_maker")
        metadata_response = self.api_interactor.get(
            f"repositories/{column_maker_repo.id}/metadata?downloadable_only=false"
        )
        api_asserts.assert_status_code_is_ok(metadata_response)
        column_maker_metadata = metadata_response.json()
        assert len(column_maker_metadata) >= 3, "column_maker should have 3+ revisions"

        with open(os.path.join(output_dir, "repository_metadata_column_maker.json"), "w") as f:
            json.dump(column_maker_metadata, f, indent=2)

        # 2. RepositoryMetadata - bismark (with invalid_tools)
        bismark_repo = populator.setup_bismark_repo()
        assert not isinstance(bismark_repo, str)  # type narrowing for mypy
        bismark_response = self.api_interactor.get(f"repositories/{bismark_repo.id}/metadata?downloadable_only=false")
        api_asserts.assert_status_code_is_ok(bismark_response)
        bismark_metadata = bismark_response.json()
        # Verify it has invalid_tools
        has_invalid = any(rev.get("invalid_tools") for rev in bismark_metadata.values())
        assert has_invalid, "bismark should have invalid_tools"

        with open(os.path.join(output_dir, "repository_metadata_bismark.json"), "w") as f:
            json.dump(bismark_metadata, f, indent=2)

        # 3. ResetMetadataOnRepositoryResponse - dry_run preview
        preview_response = self.api_interactor.post(
            f"repositories/{column_maker_repo.id}/reset_metadata",
            params={"dry_run": True, "verbose": True},
        )
        api_asserts.assert_status_code_is_ok(preview_response)
        preview_data = preview_response.json()
        assert preview_data["dry_run"] is True
        assert preview_data["changeset_details"] is not None

        with open(os.path.join(output_dir, "reset_metadata_preview.json"), "w") as f:
            json.dump(preview_data, f, indent=2)

        # 4. ResetMetadataOnRepositoryResponse - applied (non-dry-run)
        # Use a fresh repo so we don't affect other tests
        apply_repo = populator.setup_test_data_repo("column_maker")
        apply_response = self.api_interactor.post(
            f"repositories/{apply_repo.id}/reset_metadata",
            params={"dry_run": False, "verbose": True},
        )
        api_asserts.assert_status_code_is_ok(apply_response)
        apply_data = apply_response.json()
        assert apply_data["dry_run"] is False
        assert apply_data["changeset_details"] is not None

        with open(os.path.join(output_dir, "reset_metadata_applied.json"), "w") as f:
            json.dump(apply_data, f, indent=2)

        # 5. ResetMetadataOnRepositoryResponse - bismark (has invalid_tools, tool dependencies)
        bismark_reset_response = self.api_interactor.post(
            f"repositories/{bismark_repo.id}/reset_metadata",
            params={"dry_run": True, "verbose": True},
        )
        api_asserts.assert_status_code_is_ok(bismark_reset_response)
        bismark_reset_data = bismark_reset_response.json()
        assert bismark_reset_data["dry_run"] is True
        assert bismark_reset_data["changeset_details"] is not None

        with open(os.path.join(output_dir, "reset_metadata_bismark.json"), "w") as f:
            json.dump(bismark_reset_data, f, indent=2)

        # 6. ResetMetadataOnRepositoryResponse - unchanged (has "equal" comparison_result)
        # This repo has identical tool XML in revisions 1 and 2, producing comparison_result: "equal"
        unchanged_repo = populator.setup_test_data_repo("column_maker_unchanged")
        unchanged_reset_response = self.api_interactor.post(
            f"repositories/{unchanged_repo.id}/reset_metadata",
            params={"dry_run": True, "verbose": True},
        )
        api_asserts.assert_status_code_is_ok(unchanged_reset_response)
        unchanged_reset_data = unchanged_reset_response.json()
        assert unchanged_reset_data["dry_run"] is True
        assert unchanged_reset_data["changeset_details"] is not None
        # Verify we got an "equal" comparison - this is the whole point of this fixture
        has_equal = any(d.get("comparison_result") == "equal" for d in unchanged_reset_data["changeset_details"])
        assert has_equal, "column_maker_unchanged should produce 'equal' comparison_result"

        with open(os.path.join(output_dir, "reset_metadata_unchanged.json"), "w") as f:
            json.dump(unchanged_reset_data, f, indent=2)

        # 7. ResetMetadataOnRepositoryResponse - subset (has "subset" comparison_result)
        # This repo adds a new tool in revision 2 without changing existing tool,
        # so revision 1's metadata is a subset of revision 2's metadata
        subset_repo = populator.setup_test_data_repo("column_maker_subset")
        subset_reset_response = self.api_interactor.post(
            f"repositories/{subset_repo.id}/reset_metadata",
            params={"dry_run": True, "verbose": True},
        )
        api_asserts.assert_status_code_is_ok(subset_reset_response)
        subset_reset_data = subset_reset_response.json()
        assert subset_reset_data["dry_run"] is True
        assert subset_reset_data["changeset_details"] is not None
        # Verify we got a "subset" comparison - this is the whole point of this fixture
        has_subset = any(d.get("comparison_result") == "subset" for d in subset_reset_data["changeset_details"])
        assert has_subset, "column_maker_subset should produce 'subset' comparison_result"

        with open(os.path.join(output_dir, "reset_metadata_subset.json"), "w") as f:
            json.dump(subset_reset_data, f, indent=2)

        # 8. ResetMetadataOnRepositoryResponse - direct_push (has "created" record_operation)
        # This repo is created via API (creates metadata), then modified via direct hg push
        # (no metadata created). Reset should show record_operation: "created" for the pushed changeset.
        # NOTE: Requires TOOL_SHED_CONFIG_CONFIG_HG_FOR_DEV=1 when starting the tool shed.
        direct_push_repo = populator.setup_test_data_repo("column_maker_direct_push")
        # Clone the repo locally
        clone_dir = tempfile.mkdtemp(prefix="hg_clone_")
        hg_ops = HgRepositoryOperations(
            shed_url=self.url,
            username=direct_push_repo.owner,
            password="testpass",  # Default test password
        )
        hg_ops.clone_repo(direct_push_repo.owner, direct_push_repo.name, clone_dir)
        # Modify the tool and push via hg - this creates a changeset WITHOUT metadata
        updated_tool_xml = """<tool id="Add_a_column1" name="Compute" version="1.1.0">
  <description>an expression on every row</description>
  <command interpreter="python">
    column_maker.py $input $out_file1 "$cond" $round ${input.metadata.columns} "${input.metadata.column_types}"
  </command>
  <inputs>
    <param name="cond" size="40" type="text" value="c3-c2" label="Add expression"/>
    <param format="tabular" name="input" type="data" label="as a new column to" help="Query missing? See TIP below"/>
    <param name="round" type="select" label="Round result?">
      <option value="no">NO</option>
      <option value="yes">YES</option>
    </param>
  </inputs>
  <outputs>
    <data format="input" name="out_file1" metadata_source="input"/>
  </outputs>
  <help>
Computes an expression for every row and appends result as new column.
Now with improved help text!
</help>
</tool>
"""
        hg_ops.add_and_commit(
            clone_dir,
            {"column_maker.xml": updated_tool_xml},
            "Update to version 1.1.0",
        )
        try:
            hg_ops.push(clone_dir, direct_push_repo.owner, direct_push_repo.name)
        except Exception as e:
            if "authorization failed" in str(e):
                print("\n  WARNING: Skipping fixture #8 (reset_metadata_direct_push.json)")
                print("  Push authorization failed. Start tool shed with:")
                print("    TOOL_SHED_CONFIG_CONFIG_HG_FOR_DEV=1")
            else:
                raise
        else:
            # Reset metadata - should show "created" for the pushed changeset
            direct_push_reset_response = self.api_interactor.post(
                f"repositories/{direct_push_repo.id}/reset_metadata",
                params={"dry_run": True, "verbose": True},
            )
            api_asserts.assert_status_code_is_ok(direct_push_reset_response)
            direct_push_reset_data = direct_push_reset_response.json()
            assert direct_push_reset_data["dry_run"] is True
            assert direct_push_reset_data["changeset_details"] is not None
            # Verify we got a "created" record_operation - this is the whole point of this fixture
            has_created = any(
                d.get("record_operation") == "created" for d in direct_push_reset_data["changeset_details"]
            )
            assert has_created, "direct_push should produce 'created' record_operation"

            with open(os.path.join(output_dir, "reset_metadata_direct_push.json"), "w") as f:
                json.dump(direct_push_reset_data, f, indent=2)

        print(f"\nFixtures written to: {output_dir}")
        print("Files generated:")
        for filename in sorted(os.listdir(output_dir)):
            filepath = os.path.join(output_dir, filename)
            size = os.path.getsize(filepath)
            print(f"  - {filename} ({size} bytes)")
