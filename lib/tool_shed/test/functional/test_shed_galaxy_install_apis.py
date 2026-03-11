"""Tests for the legacy Galaxy→ToolShed install protocol endpoints.

These endpoints are called by Galaxy's install infrastructure to resolve
repositories, check for updates, and retrieve dependency information during
installs. They live at /repository/{action} (NOT under /api/) and return
plain text or encoded dictionaries.

Endpoints tested:
  GET  /repository/get_ctx_rev
  GET  /repository/get_changeset_revision_and_ctx_rev
  GET  /repository/get_repository_dependencies
  POST /repository/get_required_repo_info_dict
  GET  /repository/next_installable_changeset_revision
  GET  /repository/previous_changeset_revisions
  GET  /repository/updated_changeset_revisions
  GET  /repository/get_repository_type
  GET  /repository/get_tool_dependencies
  GET  /repository/static/images/{repository_id}/{image_file}
  GET  /repository/status_for_installed_repository (301 → /api/repositories/updates/)
"""

import json

import requests

from galaxy.util.tool_shed.encoding_util import (
    encoding_sep,
    tool_shed_decode,
    tool_shed_encode,
)
from galaxy_test.base import api_asserts
from ..base.api import ShedApiTestCase
from ..base.populators import TEST_DATA_REPO_FILES


class TestGalaxyInstallApis(ShedApiTestCase):
    """Test the legacy /repository/* endpoints used by Galaxy install code."""

    # ---- helpers --------------------------------------------------------

    def _legacy_get(self, action: str, params: dict) -> requests.Response:
        """GET /repository/{action} with query params (bypasses /api/ prefix)."""
        url = f"{self.url}/repository/{action}"
        return requests.get(url, params=params)

    def _legacy_post(self, action: str, data: dict) -> requests.Response:
        """POST /repository/{action} with form data."""
        url = f"{self.url}/repository/{action}"
        return requests.post(url, data=data)

    def _repo_params(self, repo, changeset_revision: str) -> dict:
        return dict(name=repo.name, owner=repo.owner, changeset_revision=changeset_revision)

    def _setup_multi_revision_repo(self):
        """Setup column_maker repo with 3 installable revisions (and return revisions list)."""
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker")
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.root) == 3
        return repository, revisions.root

    def _setup_single_revision_repo(self):
        """Setup a simple column_maker repo with 1 revision (uploads 1 tar)."""
        populator = self.populator
        repository = populator.setup_column_maker_repo(prefix="installapi")
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.root) == 1
        return repository, revisions.root[0]

    def _setup_repo_with_dependency(self):
        """Create two repos and wire up a repository dependency between them.

        Returns (dependent_repo, dependency_repo, dependent_tip, dependency_tip).
        """
        populator = self.populator
        category_id = populator.new_category(prefix="installdep").id
        # Create the dependency target repo
        dependency_repo = populator.setup_column_maker_repo(prefix="deptarget", category_id=category_id)
        dep_tip = populator.get_tip_changeset(dependency_repo)
        # Create the dependent repo
        dependent_repo = populator.setup_column_maker_repo(prefix="depsource", category_id=category_id)
        # Wire up the dependency
        populator.create_repository_dependency(
            dependent_repo,
            [(self.url, dependency_repo.name, dependency_repo.owner, dep_tip)],
        )
        dependent_tip = populator.get_tip_changeset(dependent_repo)
        return dependent_repo, dependency_repo, dependent_tip, dep_tip

    # ---- get_ctx_rev ----------------------------------------------------

    def test_get_ctx_rev_returns_numeric_revision(self):
        repository, changeset = self._setup_single_revision_repo()
        response = self._legacy_get("get_ctx_rev", self._repo_params(repository, changeset))
        api_asserts.assert_status_code_is_ok(response)
        ctx_rev = response.text
        assert ctx_rev.strip()
        # ctx.rev() is a numeric index (e.g. "0", "1", ...)
        assert ctx_rev.strip().isdigit()

    def test_get_ctx_rev_multi_revision(self):
        repository, revisions = self._setup_multi_revision_repo()
        # Each installable revision should produce a different ctx_rev
        ctx_revs = []
        for changeset in revisions:
            response = self._legacy_get("get_ctx_rev", self._repo_params(repository, changeset))
            api_asserts.assert_status_code_is_ok(response)
            ctx_rev = response.text.strip()
            assert ctx_rev.isdigit()
            ctx_revs.append(int(ctx_rev))
        # ctx revs should be strictly increasing
        assert ctx_revs == sorted(ctx_revs)
        assert len(set(ctx_revs)) == len(ctx_revs)

    # ---- get_changeset_revision_and_ctx_rev -----------------------------

    def test_get_changeset_revision_and_ctx_rev_at_tip(self):
        repository, revisions = self._setup_multi_revision_repo()
        tip_changeset = revisions[-1]
        response = self._legacy_get(
            "get_changeset_revision_and_ctx_rev",
            self._repo_params(repository, tip_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        decoded = tool_shed_decode(response.text.strip())
        assert isinstance(decoded, dict)
        assert decoded["changeset_revision"] == tip_changeset
        assert "ctx_rev" in decoded
        assert decoded["ctx_rev"].isdigit()
        # Verify galaxy utility flags are present
        for key in [
            "includes_data_managers",
            "includes_datatypes",
            "includes_tools",
            "includes_tools_for_display_in_tool_panel",
            "includes_tool_dependencies",
            "has_repository_dependencies",
            "has_repository_dependencies_only_if_compiling_contained_td",
            "includes_workflows",
        ]:
            assert key in decoded

    def test_get_changeset_revision_and_ctx_rev_at_installable_non_tip(self):
        """When changeset is in repository_metadata table but not tip, should return same revision."""
        repository, revisions = self._setup_multi_revision_repo()
        first_changeset = revisions[0]
        response = self._legacy_get(
            "get_changeset_revision_and_ctx_rev",
            self._repo_params(repository, first_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        decoded = tool_shed_decode(response.text.strip())
        assert isinstance(decoded, dict)
        # first revision has metadata entry, so it should return itself
        assert decoded["changeset_revision"] == first_changeset

    def test_get_changeset_revision_and_ctx_rev_includes_tools_flag(self):
        """Column maker repo has tools, so includes_tools should be True."""
        repository, changeset = self._setup_single_revision_repo()
        response = self._legacy_get(
            "get_changeset_revision_and_ctx_rev",
            self._repo_params(repository, changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        decoded = tool_shed_decode(response.text.strip())
        assert decoded["includes_tools"] is True

    def test_get_changeset_revision_and_ctx_rev_with_gaps(self):
        """Test with a repo that has non-installable revisions (download gaps).

        column_maker_with_download_gaps has 4 total revisions but only 3 installable.
        """
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker_with_download_gaps")
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.root) == 3
        for changeset in revisions.root:
            response = self._legacy_get(
                "get_changeset_revision_and_ctx_rev",
                self._repo_params(repository, changeset),
            )
            api_asserts.assert_status_code_is_ok(response)
            decoded = tool_shed_decode(response.text.strip())
            assert isinstance(decoded, dict)
            assert "changeset_revision" in decoded
            assert "ctx_rev" in decoded

    # ---- next_installable_changeset_revision ----------------------------

    def test_next_installable_changeset_revision_from_first(self):
        repository, revisions = self._setup_multi_revision_repo()
        first_changeset = revisions[0]
        response = self._legacy_get(
            "next_installable_changeset_revision",
            self._repo_params(repository, first_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        next_rev = response.text.strip()
        # Should return the second installable revision
        assert next_rev == revisions[1]

    def test_next_installable_changeset_revision_from_middle(self):
        repository, revisions = self._setup_multi_revision_repo()
        second_changeset = revisions[1]
        response = self._legacy_get(
            "next_installable_changeset_revision",
            self._repo_params(repository, second_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        next_rev = response.text.strip()
        assert next_rev == revisions[2]

    def test_next_installable_changeset_revision_from_tip(self):
        """At tip, there's no next installable revision - should return empty."""
        repository, revisions = self._setup_multi_revision_repo()
        tip_changeset = revisions[-1]
        response = self._legacy_get(
            "next_installable_changeset_revision",
            self._repo_params(repository, tip_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        # No next revision available
        assert response.text.strip() == ""

    def test_next_installable_changeset_revision_single_revision(self):
        """Repo with only one revision has no next installable."""
        repository, changeset = self._setup_single_revision_repo()
        response = self._legacy_get(
            "next_installable_changeset_revision",
            self._repo_params(repository, changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        assert response.text.strip() == ""

    def test_next_installable_changeset_revision_with_gaps(self):
        """With download gaps, should skip non-installable revisions."""
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker_with_download_gaps")
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.root) == 3
        # From first installable, next should be second installable (skipping gaps)
        response = self._legacy_get(
            "next_installable_changeset_revision",
            self._repo_params(repository, revisions.root[0]),
        )
        api_asserts.assert_status_code_is_ok(response)
        next_rev = response.text.strip()
        assert next_rev == revisions.root[1]

    # ---- previous_changeset_revisions -----------------------------------

    def test_previous_changeset_revisions_from_second(self):
        repository, revisions = self._setup_multi_revision_repo()
        second_changeset = revisions[1]
        response = self._legacy_get(
            "previous_changeset_revisions",
            self._repo_params(repository, second_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.text.strip()
        # Between first and second installable revision there should be changesets
        assert result, "Expected changeset hashes between first and second installable revision"
        previous_hashes = result.split(",")
        assert len(previous_hashes) >= 1
        for h in previous_hashes:
            # Each should be a valid hex hash
            assert len(h) >= 12

    def test_previous_changeset_revisions_from_tip(self):
        repository, revisions = self._setup_multi_revision_repo()
        tip_changeset = revisions[-1]
        response = self._legacy_get(
            "previous_changeset_revisions",
            self._repo_params(repository, tip_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.text.strip()
        # Between second-to-last and tip there should be changesets
        assert result, "Expected changeset hashes between previous metadata revision and tip"
        hashes = result.split(",")
        assert len(hashes) >= 1

    def test_previous_changeset_revisions_from_first(self):
        """First installable revision may have no previous metadata revision."""
        repository, revisions = self._setup_multi_revision_repo()
        first_changeset = revisions[0]
        response = self._legacy_get(
            "previous_changeset_revisions",
            self._repo_params(repository, first_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        # May return empty or some hashes - just verify it doesn't error

    def test_previous_changeset_revisions_with_from_tip_flag(self):
        """Test from_tip=True uses repository tip as upper bound."""
        repository, revisions = self._setup_multi_revision_repo()
        # Pass any changeset_revision (it will be overridden by from_tip)
        params = self._repo_params(repository, revisions[0])
        params["from_tip"] = "true"
        response = self._legacy_get("previous_changeset_revisions", params)
        api_asserts.assert_status_code_is_ok(response)
        result = response.text.strip()
        assert result, "Expected changeset hashes when using from_tip=true"
        hashes = result.split(",")
        assert len(hashes) >= 1

    # ---- updated_changeset_revisions ------------------------------------

    def test_updated_changeset_revisions_from_first(self):
        """From first revision, should list revisions available to update to."""
        repository, revisions = self._setup_multi_revision_repo()
        first_changeset = revisions[0]
        response = self._legacy_get(
            "updated_changeset_revisions",
            self._repo_params(repository, first_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.text.strip()
        # With 3 installable revisions, first revision should have updates
        assert result, "Expected update revisions from first installable revision"
        updated_hashes = result.split(",")
        assert len(updated_hashes) >= 1
        for h in updated_hashes:
            assert len(h) >= 12

    def test_updated_changeset_revisions_from_tip(self):
        """At tip, there should be no further updates."""
        repository, revisions = self._setup_multi_revision_repo()
        tip_changeset = revisions[-1]
        response = self._legacy_get(
            "updated_changeset_revisions",
            self._repo_params(repository, tip_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        # No updates from tip
        assert response.text.strip() == ""

    def test_updated_changeset_revisions_from_middle(self):
        repository, revisions = self._setup_multi_revision_repo()
        second_changeset = revisions[1]
        response = self._legacy_get(
            "updated_changeset_revisions",
            self._repo_params(repository, second_changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.text.strip()
        # Second revision should have at least the tip as an update target
        assert result, "Expected update revisions from second installable revision"
        updated_hashes = result.split(",")
        assert revisions[-1] in updated_hashes

    # ---- get_repository_dependencies ------------------------------------

    def test_get_repository_dependencies_simple_repo(self):
        """Column maker has no repo dependencies, should return empty."""
        repository, changeset = self._setup_single_revision_repo()
        response = self._legacy_get(
            "get_repository_dependencies",
            self._repo_params(repository, changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        # @web.json wraps the empty string return as '""'
        text = response.text.strip()
        assert text == '""'

    def test_get_repository_dependencies_multi_revision(self):
        """Each installable revision should return a valid response."""
        repository, revisions = self._setup_multi_revision_repo()
        for changeset in revisions:
            response = self._legacy_get(
                "get_repository_dependencies",
                self._repo_params(repository, changeset),
            )
            api_asserts.assert_status_code_is_ok(response)

    def test_get_repository_dependencies_with_actual_dependency(self):
        """Repo with repository_dependencies.xml should return encoded dependency dict."""
        dependent_repo, dependency_repo, dependent_tip, dep_tip = self._setup_repo_with_dependency()
        response = self._legacy_get(
            "get_repository_dependencies",
            self._repo_params(dependent_repo, dependent_tip),
        )
        api_asserts.assert_status_code_is_ok(response)
        text = response.text.strip()
        # @web.json wraps the return, so decode the JSON string first
        encoded_value = json.loads(text)
        assert encoded_value, "Expected non-empty encoded dependency dict"
        decoded = tool_shed_decode(encoded_value)
        assert isinstance(decoded, dict)
        # Dict has a root_key and dependency tuples keyed by compound keys
        assert "root_key" in decoded
        # Find dependency tuples - they're lists of [shed_url, name, owner, changeset, ...]
        found_dep = False
        for _key, value in decoded.items():
            if isinstance(value, list):
                for entry in value:
                    if isinstance(entry, list) and dependency_repo.name in entry:
                        found_dep = True
                        break
        assert found_dep, f"Expected {dependency_repo.name} in dependency dict: {decoded}"

    # ---- get_required_repo_info_dict ------------------------------------

    def test_get_required_repo_info_dict_empty(self):
        """POST with no encoded_str should return empty dict."""
        response = self._legacy_post("get_required_repo_info_dict", {})
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()
        assert result == {}

    def test_get_required_repo_info_dict_get_returns_empty(self):
        """GET on this endpoint should return empty dict."""
        response = self._legacy_get("get_required_repo_info_dict", {})
        api_asserts.assert_status_code_is_ok(response)
        assert response.json() == {}

    def test_get_required_repo_info_dict_with_encoded_str(self):
        """POST with a real encoded_str should return repo info dicts.

        Simulates what Galaxy does: encode a dependency tuple and POST it.
        The tuple format is: shed_url, name, owner, changeset, prior_install, only_if_compiling
        joined by encoding_sep, with multiple tuples joined by encoding_sep2.
        """
        dependent_repo, dependency_repo, dependent_tip, dep_tip = self._setup_repo_with_dependency()
        # Build the encoded_str the same way Galaxy's install code does
        dep_tuple_str = encoding_sep.join(
            [
                self.url,
                dependency_repo.name,
                dependency_repo.owner,
                dep_tip,
                "False",  # prior_installation_required
                "False",  # only_if_compiling_contained_td
            ]
        )
        # For a single dependency, there's just one tuple (no encoding_sep2 needed)
        encoded_str = tool_shed_encode(dep_tuple_str)

        response = self._legacy_post(
            "get_required_repo_info_dict",
            {"encoded_str": encoded_str},
        )
        api_asserts.assert_status_code_is_ok(response)
        result = response.json()
        assert result, "Expected non-empty repo info dict"
        assert "repo_info_dicts" in result
        assert len(result["repo_info_dicts"]) >= 1
        # Verify boolean flags are present
        for key in [
            "includes_tools",
            "includes_tools_for_display_in_tool_panel",
            "has_repository_dependencies",
            "has_repository_dependencies_only_if_compiling_contained_td",
            "includes_tool_dependencies",
        ]:
            assert key in result

    # ---- get_repository_type ---------------------------------------------

    def test_get_repository_type(self):
        """Should return the repository type string (e.g. 'unrestricted')."""
        repository, changeset = self._setup_single_revision_repo()
        response = self._legacy_get(
            "get_repository_type",
            dict(name=repository.name, owner=repository.owner),
        )
        api_asserts.assert_status_code_is_ok(response)
        repo_type = response.text.strip()
        assert repo_type == "unrestricted"

    # ---- get_tool_dependencies ------------------------------------------

    def test_get_tool_dependencies_simple_repo(self):
        """Column maker has no tool dependencies, should return empty."""
        repository, changeset = self._setup_single_revision_repo()
        response = self._legacy_get(
            "get_tool_dependencies",
            self._repo_params(repository, changeset),
        )
        api_asserts.assert_status_code_is_ok(response)
        # No tool dependencies → empty string
        assert response.text.strip() == ""

    # ---- get_changeset_revision_and_ctx_rev (update-path branch) --------

    def test_get_changeset_revision_and_ctx_rev_non_metadata_changeset(self):
        """Test the complex 'find update target' branch.

        column_maker_with_download_gaps has 4 hg changesets but only 3 with metadata.
        If we can identify a non-metadata changeset between installable ones,
        the endpoint should find the next metadata changeset as update target.
        """
        populator = self.populator
        repository = populator.setup_test_data_repo("column_maker_with_download_gaps")
        revisions = populator.get_ordered_installable_revisions(repository.owner, repository.name)
        assert len(revisions.root) == 3
        # Get all metadata to find the metadata changeset hashes
        metadata = populator.get_metadata(repository, downloadable_only=False)
        metadata_changesets = set()
        for key in metadata.root:
            # Keys are "N:changeset_hash" format
            changeset_hash = key.split(":", 1)[1] if ":" in key else key
            metadata_changesets.add(changeset_hash)
        # The non-metadata changeset is the one that's not in the metadata
        # but is in the hg changelog. We can find it by checking all revisions
        # from the repository. If we have it, use it; otherwise skip this test.
        all_changesets_response = self._legacy_get(
            "previous_changeset_revisions",
            {
                "name": repository.name,
                "owner": repository.owner,
                "changeset_revision": revisions.root[0],
                "from_tip": "true",
            },
        )
        if all_changesets_response.status_code == 200 and all_changesets_response.text.strip():
            all_changesets = all_changesets_response.text.strip().split(",")
            non_metadata = [c for c in all_changesets if c not in metadata_changesets]
            if non_metadata:
                gap_changeset = non_metadata[0]
                response = self._legacy_get(
                    "get_changeset_revision_and_ctx_rev",
                    self._repo_params(repository, gap_changeset),
                )
                api_asserts.assert_status_code_is_ok(response)
                decoded = tool_shed_decode(response.text.strip())
                assert isinstance(decoded, dict)
                # Should redirect to a metadata changeset as update target
                assert decoded["changeset_revision"] in metadata_changesets

    # ---- cross-endpoint consistency tests --------------------------------

    def test_ctx_rev_matches_changeset_revision_and_ctx_rev(self):
        """The ctx_rev from get_ctx_rev should match the one from get_changeset_revision_and_ctx_rev."""
        repository, changeset = self._setup_single_revision_repo()

        ctx_response = self._legacy_get("get_ctx_rev", self._repo_params(repository, changeset))
        api_asserts.assert_status_code_is_ok(ctx_response)
        standalone_ctx_rev = ctx_response.text.strip()

        combo_response = self._legacy_get(
            "get_changeset_revision_and_ctx_rev",
            self._repo_params(repository, changeset),
        )
        api_asserts.assert_status_code_is_ok(combo_response)
        decoded = tool_shed_decode(combo_response.text.strip())
        assert decoded["ctx_rev"] == standalone_ctx_rev

    def test_next_and_updated_revisions_consistency(self):
        """next_installable_changeset_revision result should appear in updated_changeset_revisions."""
        repository, revisions = self._setup_multi_revision_repo()
        first_changeset = revisions[0]

        # Get next installable
        next_response = self._legacy_get(
            "next_installable_changeset_revision",
            self._repo_params(repository, first_changeset),
        )
        api_asserts.assert_status_code_is_ok(next_response)
        next_rev = next_response.text.strip()
        assert next_rev  # Should have a next revision

        # Get updated revisions
        updated_response = self._legacy_get(
            "updated_changeset_revisions",
            self._repo_params(repository, first_changeset),
        )
        api_asserts.assert_status_code_is_ok(updated_response)
        updated_text = updated_response.text.strip()
        if updated_text:
            updated_revisions = updated_text.split(",")
            # The next installable should be reachable from the update path
            assert next_rev in updated_revisions

    # ---- display_image_in_repository (static images) ----------------------

    def _setup_htseq_count_repo(self):
        """Setup htseq_count repo which contains static/images/count_modes.png."""
        populator = self.populator
        category_id = populator.new_category(prefix="imagetest").id
        repository = populator.new_repository(category_id, prefix="imagetest")
        htseq_tar = TEST_DATA_REPO_FILES.joinpath("htseq_count/htseq_count.tar")
        populator.upload_revision(repository, htseq_tar)
        return repository

    def test_display_image_in_repository(self):
        """Image endpoint should serve a PNG with correct MIME type."""
        repository = self._setup_htseq_count_repo()
        url = f"{self.url}/repository/static/images/{repository.id}/count_modes.png"
        response = requests.get(url)
        api_asserts.assert_status_code_is_ok(response)
        assert len(response.content) > 0, "Expected non-empty image content"
        content_type = response.headers.get("content-type", "")
        assert "image/png" in content_type, f"Expected image/png content-type, got {content_type}"

    def test_display_image_nonexistent_file(self):
        """Requesting a nonexistent image should return empty/error."""
        repository = self._setup_htseq_count_repo()
        url = f"{self.url}/repository/static/images/{repository.id}/nonexistent.png"
        response = requests.get(url)
        # Should either 404 or return empty
        assert response.status_code >= 400 or len(response.content) == 0

    def test_display_image_nonexistent_repo(self):
        """Requesting an image from a nonexistent repo should fail."""
        url = f"{self.url}/repository/static/images/invalid_id_xyz/count_modes.png"
        response = requests.get(url)
        assert response.status_code >= 400

    def test_display_image_path_traversal_rejected(self):
        """Path traversal attempts should not serve files outside the repo."""
        repository = self._setup_htseq_count_repo()
        url = f"{self.url}/repository/static/images/{repository.id}/..%2F..%2F..%2Fetc%2Fpasswd"
        response = requests.get(url)
        assert response.status_code >= 400 or len(response.content) == 0

    def test_display_image_rejects_non_image_files(self):
        """Endpoint only serves image MIME types, rejects .xml etc."""
        repository = self._setup_htseq_count_repo()
        # htseq_count.tar contains htseq-count.xml — a non-image file
        url = f"{self.url}/repository/static/images/{repository.id}/htseq-count.xml"
        response = requests.get(url)
        assert response.status_code >= 400, f"Expected rejection of non-image file, got {response.status_code}"

    def test_status_for_installed_repository_redirects(self):
        """Legacy endpoint should 301 redirect to /api/repositories/updates/ with query string preserved."""
        params = dict(name="test_repo", owner="test_owner", changeset_revision="abc123")
        url = f"{self.url}/repository/status_for_installed_repository"
        response = requests.get(url, params=params, allow_redirects=False)
        assert response.status_code == 301, f"Expected 301, got {response.status_code}"
        location = response.headers.get("location", "")
        assert "/api/repositories/updates/" in location
        assert "name=test_repo" in location
        assert "owner=test_owner" in location
        assert "changeset_revision=abc123" in location

    def test_status_for_installed_repository_follows_redirect(self):
        """Following the redirect should reach the updates endpoint."""
        repository, changeset = self._setup_single_revision_repo()
        params = dict(name=repository.name, owner=repository.owner, changeset_revision=changeset)
        url = f"{self.url}/repository/status_for_installed_repository"
        response = requests.get(url, params=params)
        api_asserts.assert_status_code_is_ok(response)

    def test_all_endpoints_reject_nonexistent_repo(self):
        """All endpoints should fail gracefully for a nonexistent repository."""
        bogus_params = dict(
            name="nonexistent_repo_xyzzy_12345",
            owner="nonexistent_owner_xyzzy",
            changeset_revision="0" * 40,
        )
        for action in [
            "get_ctx_rev",
            "get_changeset_revision_and_ctx_rev",
            "next_installable_changeset_revision",
            "previous_changeset_revisions",
            "updated_changeset_revisions",
            "get_repository_dependencies",
            "get_repository_type",
            "get_tool_dependencies",
        ]:
            response = self._legacy_get(action, bogus_params)
            # Should get an error status (404 or 500), not silently succeed
            assert response.status_code >= 400, f"{action} returned {response.status_code} for nonexistent repo"
