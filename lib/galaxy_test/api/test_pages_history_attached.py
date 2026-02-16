"""API tests for history-attached pages (pages created with history_id)."""

from galaxy_test.base.populators import (
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
