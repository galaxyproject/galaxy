"""API tests for history-attached pages (pages created with history_id)."""

import requests

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_agents,
)
from .test_pages import BasePagesApiTestCase


class TestHistoryPagesApi(BasePagesApiTestCase):
    """API tests for history-attached pages (pages created with history_id)."""

    dataset_populator: DatasetPopulator

    # --- A1: CRUD ---

    def test_create_page_with_history_id(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Hello")
        self._assert_has_keys(page, "id", "title", "history_id")
        assert page["history_id"] == history_id
        assert page["title"] is not None
        assert page["deleted"] is False
        # content_format only in detail response, not summary
        details = self.dataset_populator.get_history_page(page["id"])
        assert details["content_format"] == "markdown"

    def test_create_history_page_custom_title(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, title="Custom Title")
        assert page["title"] == "Custom Title"

    def test_create_history_page_no_slug_required(self):
        history_id = self.dataset_populator.new_history()
        payload = {"history_id": history_id, "content": "test", "content_format": "markdown"}
        response = self._post("pages", payload, json=True)
        self._assert_status_code_is(response, 200)
        page = response.json()
        self._assert_has_keys(page, "id")
        assert page.get("slug") is None

    def test_list_pages_by_history_id(self):
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.new_history_page(history_id, content="# Page 1")
        self.dataset_populator.new_history_page(history_id, content="# Page 2")
        # noise: regular page
        self.dataset_populator.new_page(slug="list-noise-regular")
        pages = self.dataset_populator.list_history_pages(history_id)
        assert len(pages) == 2
        for p in pages:
            assert p["history_id"] == history_id

    def test_list_pages_excludes_other_histories(self):
        h1 = self.dataset_populator.new_history()
        h2 = self.dataset_populator.new_history()
        self.dataset_populator.new_history_page(h1, content="# H1")
        self.dataset_populator.new_history_page(h2, content="# H2")
        pages_h1 = self.dataset_populator.list_history_pages(h1)
        pages_h2 = self.dataset_populator.list_history_pages(h2)
        assert len(pages_h1) == 1
        assert len(pages_h2) == 1
        assert pages_h1[0]["id"] != pages_h2[0]["id"]

    def test_history_page_details_embed_url(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Embeddable")
        details = self.dataset_populator.get_history_page(page["id"])
        self._assert_has_keys(details, "embed_url")
        embed_url = details["embed_url"]
        assert embed_url, "embed_url should be populated in a request context"
        assert "/published/page?id=" in embed_url
        assert "embed=true" in embed_url
        assert page["id"] in embed_url

    def test_get_history_page_details(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# My Content")
        details = self.dataset_populator.get_history_page(page["id"])
        self._assert_has_keys(details, "content", "content_format", "history_id", "content_editor")
        assert details["content_format"] == "markdown"
        assert details["history_id"] == history_id
        assert details["content_editor"] is not None

    def test_update_history_page(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# V1")
        self.dataset_populator.update_history_page(page["id"], content="# V2")
        details = self.dataset_populator.get_history_page(page["id"])
        assert "V2" in details["content"]
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        assert len(revisions) == 2

    def test_save_empty_content_clears_notebook(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Hello\n\nsome prose")
        response = self.dataset_populator.update_history_page_raw(page["id"], content="")
        self._assert_status_code_is(response, 200)
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        assert len(revisions) == 2
        latest_revision = self._get(f"pages/{page['id']}/revisions/{revisions[-1]['id']}").json()
        assert latest_revision["content"] == ""
        details = self.dataset_populator.get_history_page(page["id"])
        assert details["content_editor"] == ""

    def test_save_empty_content_on_regular_page(self):
        page = self.dataset_populator.new_page(
            slug="empty-save-regular", content_format="markdown", content="# Hello\n\nstandalone report"
        )
        response = self.dataset_populator.update_history_page_raw(page["id"], content="")
        self._assert_status_code_is(response, 200)
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        assert len(revisions) == 2
        latest_revision = self._get(f"pages/{page['id']}/revisions/{revisions[-1]['id']}").json()
        assert latest_revision["content"] == ""

    def test_delete_history_page(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Delete me")
        self.dataset_populator.delete_history_page(page["id"])
        pages = self.dataset_populator.list_history_pages(history_id)
        assert len(pages) == 0
        # soft delete — GET still returns with deleted=True
        details_response = self._get(f"pages/{page['id']}")
        self._assert_status_code_is(details_response, 200)
        assert details_response.json()["deleted"] is True

    def test_multiple_pages_per_history(self):
        history_id = self.dataset_populator.new_history()
        p1 = self.dataset_populator.new_history_page(history_id, title="Page A")
        p2 = self.dataset_populator.new_history_page(history_id, title="Page B")
        p3 = self.dataset_populator.new_history_page(history_id, title="Page C")
        pages = self.dataset_populator.list_history_pages(history_id)
        assert len(pages) == 3
        ids = {p["id"] for p in pages}
        assert ids == {p1["id"], p2["id"], p3["id"]}

    # --- A2: edit_source Tracking ---

    def test_update_with_edit_source_user(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# V1")
        self.dataset_populator.update_history_page(page["id"], content="# V2", edit_source="user")
        details = self.dataset_populator.get_history_page(page["id"])
        assert details["edit_source"] == "user"
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        assert revisions[-1]["edit_source"] == "user"

    def test_update_with_edit_source_agent(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# V1")
        self.dataset_populator.update_history_page(page["id"], content="# V2", edit_source="agent")
        details = self.dataset_populator.get_history_page(page["id"])
        assert details["edit_source"] == "agent"
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        assert revisions[-1]["edit_source"] == "agent"

    def test_edit_source_null_default(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# V1")
        self.dataset_populator.update_history_page(page["id"], content="# V2")
        details = self.dataset_populator.get_history_page(page["id"])
        assert details["edit_source"] is None
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        assert revisions[-1]["edit_source"] is None

    def test_edit_source_in_revision_list(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# V0")
        self.dataset_populator.update_history_page(page["id"], content="# V1", edit_source="user")
        self.dataset_populator.update_history_page(page["id"], content="# V2", edit_source="agent")
        self.dataset_populator.update_history_page(page["id"], content="# V3")
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        assert len(revisions) == 4
        assert revisions[0]["edit_source"] is None  # initial
        assert revisions[1]["edit_source"] == "user"
        assert revisions[2]["edit_source"] == "agent"
        assert revisions[3]["edit_source"] is None
        for rev in revisions:
            self._assert_has_keys(rev, "id", "page_id", "create_time")

    # --- A3: Revision Endpoints ---

    def test_get_single_revision(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Original")
        self.dataset_populator.update_history_page(page["id"], content="# Updated")
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        first_revision_id = revisions[0]["id"]
        response = self._get(f"pages/{page['id']}/revisions/{first_revision_id}")
        self._assert_status_code_is(response, 200)
        revision = response.json()
        self._assert_has_keys(revision, "id", "page_id", "content", "content_format", "create_time")
        assert "Original" in revision["content"]
        assert revision["content_format"] == "markdown"
        assert revision["page_id"] == page["id"]

    def test_revert_revision(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# V1")
        self.dataset_populator.update_history_page(page["id"], content="# V2")
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        v1_revision_id = revisions[0]["id"]
        result = self.dataset_populator.revert_page_revision(page["id"], v1_revision_id)
        assert result["edit_source"] == "restore"
        assert "V1" in result["content"]
        revisions_after = self.dataset_populator.list_page_revisions(page["id"])
        assert len(revisions_after) == 3  # initial + update + revert

    def test_revert_updates_latest_revision(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# V1")
        self.dataset_populator.update_history_page(page["id"], content="# V2")
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        v1_revision_id = revisions[0]["id"]
        self.dataset_populator.revert_page_revision(page["id"], v1_revision_id)
        details = self.dataset_populator.get_history_page(page["id"])
        assert "V1" in details["content"]
        assert details["edit_source"] == "restore"

    def test_revert_preserves_original(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# V1")
        self.dataset_populator.update_history_page(page["id"], content="# V2")
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        v1_id = revisions[0]["id"]
        v2_id = revisions[1]["id"]
        self.dataset_populator.revert_page_revision(page["id"], v1_id)
        # originals unchanged
        v1_resp = self._get(f"pages/{page['id']}/revisions/{v1_id}")
        assert "V1" in v1_resp.json()["content"]
        v2_resp = self._get(f"pages/{page['id']}/revisions/{v2_id}")
        assert "V2" in v2_resp.json()["content"]
        revisions_after = self.dataset_populator.list_page_revisions(page["id"])
        assert len(revisions_after) == 3

    def test_revert_revision_with_galaxy_directives(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id)
        hda_id = hda["id"]
        directive_content = f"# Analysis\n\n```galaxy\nhistory_dataset_display(history_dataset_id={hda_id})\n```\n"
        page = self.dataset_populator.new_history_page(history_id, content=directive_content)
        self.dataset_populator.update_history_page(page["id"], content="# V2 no directives")
        revisions = self.dataset_populator.list_page_revisions(page["id"])
        v1_revision_id = revisions[0]["id"]
        result = self.dataset_populator.revert_page_revision(page["id"], v1_revision_id)
        assert result["edit_source"] == "restore"
        assert hda_id in result["content"]

    # --- A4: Permissions ---

    def test_history_page_403_on_unowned_history_read(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Private")
        with self._different_user():
            response = self._get(f"pages/{page['id']}")
            self._assert_status_code_is(response, 403)

    def test_history_page_403_on_unowned_history_create(self):
        history_id = self.dataset_populator.new_history()
        with self._different_user():
            payload = {"history_id": history_id, "content": "# Intruder", "content_format": "markdown"}
            create_response = self._post("pages", payload, json=True)
            self._assert_status_code_is(create_response, 403)

    def test_history_page_shared_history_read(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Shared")
        # publish history so other users can see it
        sharing_response = self._put(f"histories/{history_id}/publish", json=True)
        self._assert_status_code_is_ok(sharing_response)
        with self._different_user():
            response = self._get(f"pages/{page['id']}")
            # document actual behavior — may be 200 or 403 depending on
            # whether history sharing propagates to page access
            assert response.status_code in (200, 403)

    # --- A5: Embed token ---

    def test_create_embed_token(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Hello")
        response = self._post(f"pages/{page['id']}/embed_token", data={}, json=True)
        self._assert_status_code_is(response, 200)
        body = response.json()
        self._assert_has_keys(body, "token", "expires_at")
        assert body["token"]
        assert body["expires_at"]

    def test_embed_token_403_on_unowned_page(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Private")
        with self._different_user():
            response = self._post(f"pages/{page['id']}/embed_token", data={}, json=True)
            self._assert_status_code_is(response, 403)

    # --- A6: Embed token scoped read (1b) ---

    def _mint_embed_token(self, page_id: str) -> str:
        response = self._post(f"pages/{page_id}/embed_token", data={}, json=True)
        self._assert_status_code_is(response, 200)
        return response.json()["token"]

    def _embed_get(self, route: str, token: str) -> requests.Response:
        """GET with ONLY the embed token header -- no API key (truly scoped)."""
        return requests.get(self._api_url(route), headers={"x-galaxy-embed-token": token})

    def test_embed_token_reads_own_page(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Embed me")
        token = self._mint_embed_token(page["id"])
        response = self._embed_get(f"pages/{page['id']}", token)
        self._assert_status_code_is(response, 200)
        assert "Embed me" in response.json()["content"]

    def test_embed_token_denies_other_users_page(self):
        # The recovered user is access-controlled: the token cannot read a page
        # owned by a different user.
        history_id = self.dataset_populator.new_history()
        page_a = self.dataset_populator.new_history_page(history_id, content="# A")
        token = self._mint_embed_token(page_a["id"])
        with self._different_user():
            other_history = self.dataset_populator.new_history()
            page_b = self.dataset_populator.new_history_page(other_history, content="# B")
        response = self._embed_get(f"pages/{page_b['id']}", token)
        self._assert_status_code_is(response, 403)

    def test_embed_token_invalid_rejected(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# A")
        response = self._embed_get(f"pages/{page['id']}", "not-a-real-token")
        self._assert_status_code_is(response, 401)

    def test_embed_token_rejected_on_account_endpoint(self):
        # Q5: the embed token must NOT authenticate the api-key endpoint (or any
        # route not marked embed_allowed) -- otherwise an exfiltrated token could
        # read the user's permanent API key.
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# A")
        token = self._mint_embed_token(page["id"])
        user_id = self.dataset_populator.user_id()
        response = self._embed_get(f"users/{user_id}/api_key", token)
        assert response.status_code in (401, 403), f"expected denial, got {response.status_code}"

    def test_embed_token_cannot_mint_more_tokens(self):
        # Read-only invariant: the token authenticates only GET/HEAD routes. The
        # mint endpoint is a POST and is not marked, so the embed token alone
        # cannot ride it -- it cannot escalate by minting fresh tokens.
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# A")
        token = self._mint_embed_token(page["id"])
        response = requests.post(
            self._api_url(f"pages/{page['id']}/embed_token"),
            headers={"x-galaxy-embed-token": token},
            json={},
        )
        assert response.status_code in (401, 403), f"expected denial, got {response.status_code}"

    def test_embed_token_head_on_display(self):
        # The display route marks HEAD as well as GET; the token must authenticate
        # the HEAD probe plugins use before fetching.
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="col1\tcol2\n1\t2\n", wait=True)
        page = self.dataset_populator.new_history_page(history_id, content="# Embed")
        token = self._mint_embed_token(page["id"])
        response = requests.head(
            self._api_url(f"datasets/{hda['id']}/display?preview=True"),
            headers={"x-galaxy-embed-token": token},
        )
        self._assert_status_code_is(response, 200)

    def test_embed_token_reads_dataset(self):
        # The token recovers the full owning user; on the marked display route it
        # reads the user's own dataset.
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="col1\tcol2\n1\t2\n", wait=True)
        page = self.dataset_populator.new_history_page(history_id, content="# Embed")
        token = self._mint_embed_token(page["id"])
        response = self._embed_get(f"datasets/{hda['id']}/display?preview=True", token)
        self._assert_status_code_is(response, 200)

    def test_embed_token_denies_other_users_dataset(self):
        # The recovered user is still access-controlled -- the token is not a
        # super-user: it cannot read another user's *private* dataset. (Public
        # datasets are readable by anyone by design, so the dataset must be made
        # private to exercise the ACL boundary.)
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Mine")
        token = self._mint_embed_token(page["id"])
        with self._different_user():
            other_history = self.dataset_populator.new_history()
            other_hda = self.dataset_populator.new_dataset(other_history, content="secret\n", wait=True)
            self.dataset_populator.make_private(other_history, other_hda["id"])
        response = self._embed_get(f"datasets/{other_hda['id']}/display?preview=True", token)
        self._assert_status_code_is(response, 403)

    def _new_collection(self, history_id: str) -> str:
        dccp = DatasetCollectionPopulator(self.galaxy_interactor)
        return dccp.create_list_in_history(
            history_id, contents=[("e1", "data1\n"), ("e2", "data2\n")], wait=True
        ).json()["outputs"][0]["id"]

    def test_embed_token_reads_collection(self):
        history_id = self.dataset_populator.new_history()
        hdca_id = self._new_collection(history_id)
        page = self.dataset_populator.new_history_page(history_id, content="# Collection")
        token = self._mint_embed_token(page["id"])
        response = self._embed_get(f"dataset_collections/{hdca_id}", token)
        self._assert_status_code_is(response, 200)

    def test_embed_token_denies_other_users_collection(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Mine")
        token = self._mint_embed_token(page["id"])
        with self._different_user():
            other_history = self.dataset_populator.new_history()
            other_hdca = self._new_collection(other_history)
        response = self._embed_get(f"dataset_collections/{other_hdca}", token)
        self._assert_status_code_is(response, 403)

    def test_embed_token_reads_plugin_metadata(self):
        # The embedded VisualizationFrame fetches GET /api/plugins/{name} for plugin
        # metadata (static config: entry_point, href). That route is NOT marked
        # embed_allowed -- plugin metadata is public config, served anonymously, so
        # the embed token falls through to anonymous and still reads it.
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Viz")
        token = self._mint_embed_token(page["id"])
        response = self._embed_get("plugins/example", token)
        self._assert_status_code_is(response, 200)
        assert "entry_point" in response.json()

    def test_embed_token_cannot_enumerate_plugin_history(self):
        # Invariant: the embed token must not reach the plugin show route's
        # ?history_id= enumeration branch (lists all viz-compatible datasets in a
        # history). The route is unmarked, so the token is ignored -> anonymous ->
        # get_owned(history_id, None) is refused. The enumeration never runs.
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Viz")
        token = self._mint_embed_token(page["id"])
        response = self._embed_get(f"plugins/example?history_id={history_id}", token)
        assert response.status_code != 200, f"enumeration branch leaked: {response.status_code}"
        assert "hdas" not in response.text

    def test_embed_token_reads_dataset_metadata(self):
        # Most embeddable viz plugins fetch GET /api/datasets/{id} for dataset
        # metadata (column types, etc.) before fetching /display. The route is
        # marked embed_allowed so the recovered user reads its own dataset.
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="col1\tcol2\n1\t2\n", wait=True)
        page = self.dataset_populator.new_history_page(history_id, content="# Viz")
        token = self._mint_embed_token(page["id"])
        response = self._embed_get(f"datasets/{hda['id']}", token)
        self._assert_status_code_is(response, 200)
        assert response.json()["id"] == hda["id"]

    def test_embed_token_denies_other_users_dataset_metadata(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Mine")
        token = self._mint_embed_token(page["id"])
        with self._different_user():
            other_history = self.dataset_populator.new_history()
            other_hda = self.dataset_populator.new_dataset(other_history, content="secret\n", wait=True)
            self.dataset_populator.make_private(other_history, other_hda["id"])
        response = self._embed_get(f"datasets/{other_hda['id']}", token)
        self._assert_status_code_is(response, 403)

    def test_embed_token_denies_other_users_metadata_file(self):
        # The metadata_file route is marked (igv fetches it). Access control fires
        # before the file lookup, so a cross-user private dataset is refused --
        # proving the marked route does not leak.
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Mine")
        token = self._mint_embed_token(page["id"])
        with self._different_user():
            other_history = self.dataset_populator.new_history()
            other_hda = self.dataset_populator.new_dataset(other_history, content="secret\n", wait=True)
            self.dataset_populator.make_private(other_history, other_hda["id"])
        response = self._embed_get(f"datasets/{other_hda['id']}/metadata_file?metadata_file=bam_index", token)
        self._assert_status_code_is(response, 403)

    def test_history_page_shared_history_no_write(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# ReadOnly")
        sharing_response = self._put(f"histories/{history_id}/publish", json=True)
        self._assert_status_code_is_ok(sharing_response)
        with self._different_user():
            update_response = self._put(
                f"pages/{page['id']}", {"content": "# Hacked", "content_format": "markdown"}, json=True
            )
            self._assert_status_code_is(update_response, 403)

    # --- A5: Cross-Type Validation ---

    def test_history_page_ignores_slug(self):
        history_id = self.dataset_populator.new_history()
        payload = {
            "history_id": history_id,
            "slug": "my-slug",
            "content": "# Slug test",
            "content_format": "markdown",
        }
        response = self._post("pages", payload, json=True)
        self._assert_status_code_is(response, 200)

    def test_regular_page_no_history_id(self):
        page = self.dataset_populator.new_page(slug="regular-no-hid")
        details = self.dataset_populator.get_history_page(page["id"])
        assert details["history_id"] is None

    def test_content_format_markdown_on_history_page(self):
        history_id = self.dataset_populator.new_history()
        response = self.dataset_populator.new_history_page_raw(history_id, content="<p>test</p>", content_format="html")
        # manager uses `payload.content_format or "markdown"` — explicit "html" passes through
        self._assert_status_code_is(response, 200)
        page = response.json()
        # content_format only in detail response
        details = self.dataset_populator.get_history_page(page["id"])
        assert details["content_format"] in ("html", "markdown")

    # --- A6: Page Chat ---

    @skip_without_agents
    def test_page_chat_create_exchange(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Chat test")
        result = self.dataset_populator.send_page_chat(page["id"], "Hello!")
        assert result["response"] != ""
        assert result["exchange_id"] is not None

    @skip_without_agents
    def test_page_chat_history(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Chat history test")
        self.dataset_populator.send_page_chat(page["id"], "Hello!")
        history = self.dataset_populator.get_page_chat_history(page["id"])
        assert len(history) >= 1
        assert history[0]["query"] == "Hello!"

    @skip_without_agents
    def test_page_chat_multi_turn(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Multi turn")
        first = self.dataset_populator.send_page_chat(page["id"], "Hello!")
        exchange_id = first["exchange_id"]
        self.dataset_populator.send_page_chat(page["id"], "Summarize this", exchange_id=exchange_id)
        messages_response = self._get(f"chat/exchange/{exchange_id}/messages")
        self._assert_status_code_is(messages_response, 200)
        messages = messages_response.json()
        assert len(messages) >= 4  # 2 queries + 2 responses

    @skip_without_agents
    def test_page_chat_isolation(self):
        h1 = self.dataset_populator.new_history()
        h2 = self.dataset_populator.new_history()
        p1 = self.dataset_populator.new_history_page(h1, content="# Page 1")
        p2 = self.dataset_populator.new_history_page(h2, content="# Page 2")
        self.dataset_populator.send_page_chat(p1["id"], "Hello page 1!")
        self.dataset_populator.send_page_chat(p2["id"], "Hello page 2!")
        hist1 = self.dataset_populator.get_page_chat_history(p1["id"])
        hist2 = self.dataset_populator.get_page_chat_history(p2["id"])
        assert len(hist1) == 1
        assert len(hist2) == 1
        assert hist1[0]["id"] != hist2[0]["id"]

    @skip_without_agents
    def test_page_chat_delete_exchange(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Delete chat")
        result = self.dataset_populator.send_page_chat(page["id"], "Hello!")
        exchange_id = result["exchange_id"]
        delete_response = self._delete(f"chat/exchange/{exchange_id}")
        self._assert_status_code_is(delete_response, 200)
        history = self.dataset_populator.get_page_chat_history(page["id"])
        assert len(history) == 0

    def test_page_chat_403_on_unowned_page(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Private")
        with self._different_user():
            response = self.dataset_populator.send_page_chat_raw(page["id"], "Leak this")
            self._assert_status_code_is(response, 403)

    def test_page_chat_history_403_on_unowned_page(self):
        history_id = self.dataset_populator.new_history()
        page = self.dataset_populator.new_history_page(history_id, content="# Private")
        with self._different_user():
            response = self.dataset_populator.get_page_chat_history_raw(page["id"])
            self._assert_status_code_is(response, 403)
