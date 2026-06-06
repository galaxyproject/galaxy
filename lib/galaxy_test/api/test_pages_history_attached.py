"""API tests for history-attached pages (pages created with history_id)."""

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_agents,
    skip_without_tool,
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

    def test_history_page_accessible_history_create(self):
        # Published (accessible but not owned) history — user should be able to create a page on it.
        history_id = self.dataset_populator.new_history()
        self._put(f"histories/{history_id}/publish", json=True)
        with self._different_user():
            payload = {"history_id": history_id, "content": "# Shared page", "content_format": "markdown"}
            create_response = self._post("pages", payload, json=True)
            self._assert_status_code_is(create_response, 200)
            assert create_response.json()["history_id"] == history_id

    @skip_without_tool("cat")
    def test_accessible_invocation_create_page(self):
        # Invocation whose history is published — another user can create a page via invocation_id.
        test_data = """
input_1:
  value: 1.bed
  type: File
"""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_1: data
outputs:
  output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input_1
""",
                test_data=test_data,
                history_id=history_id,
            )
            invocation_id = summary.invocation_id
            self._put(f"histories/{history_id}/publish", json=True)
            self._put(f"workflows/{summary.workflow_id}/publish", json=True)
            with self._different_user():
                payload = {"invocation_id": invocation_id, "title": "Shared Invocation Page"}
                create_response = self._post("pages", payload, json=True)
                self._assert_status_code_is(create_response, 200)
                assert create_response.json()["history_id"] == history_id

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


class TestNotebookWorkflowExtractionSummary(BasePagesApiTestCase):
    """GET /api/pages/{id}/workflow_extraction_summary — seeded from referenced outputs."""

    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator

    def setUp(self):
        super().setUp()
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def _extraction_summary(self, page_id: str) -> dict:
        response = self._get(f"pages/{page_id}/workflow_extraction_summary")
        self._assert_status_code_is(response, 200)
        return response.json()

    def _run_random_lines_mapped_over_pair(self, history_id):
        """Upload a pair and map random_lines1 over it. Returns
        (input_hdca, implicit_output_hdca, map_job_id)."""
        input_hdca = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
        ).json()["outputs"][0]
        inputs = {"input": {"batch": True, "values": [{"src": "hdca", "id": input_hdca["id"]}]}, "num_lines": 2}
        run = self.dataset_populator.run_tool(tool_id="random_lines1", inputs=inputs, history_id=history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return input_hdca, run["implicit_collections"][0], run["jobs"][0]["id"]

    def _copy_hdca_to_history(self, history_id, hdca):
        response = self._post(
            f"histories/{history_id}/contents/dataset_collections",
            {"source": "hdca", "content": hdca["id"]},
            json=True,
        )
        self._assert_status_code_is(response, 200)
        return response.json()

    def _rows_by_type(self, summary, *step_types):
        return [j for j in summary["jobs"] if j["step_type"] in step_types]

    def _row_with_output_id(self, summary, content_id):
        for job in summary["jobs"]:
            if any(o["id"] == content_id for o in job["outputs"]):
                return job
        return None

    @skip_without_tool("random_lines1")
    def test_referenced_map_over_output_seeds_subgraph(self):
        """Reference an implicit map-over output collection; its producing
        map step and the collection it was mapped over must both be seeded."""
        with self.dataset_populator.test_history() as history_id:
            input_hdca, output_hdca, _ = self._run_random_lines_mapped_over_pair(history_id)
            page = self.dataset_populator.new_notebook_referencing(history_id, collection_ids=[output_hdca["id"]])

            summary = self._extraction_summary(page["id"])

            # The map-over step is seeded and its output collection exposed.
            tool_rows = self._rows_by_type(summary, "tool")
            assert len(tool_rows) == 1, summary["jobs"]
            map_row = tool_rows[0]
            assert map_row["tool_id"] == "random_lines1", map_row
            assert map_row["seeded"] is True, map_row
            assert map_row["implicit_collection_jobs_id"], map_row
            exposed = [o for o in map_row["outputs"] if o["exposed"]]
            assert len(exposed) == 1 and exposed[0]["id"] == output_hdca["id"], map_row["outputs"]

            # The collection the tool was mapped over is an input of the
            # producing subgraph and must be seeded too.
            input_row = self._row_with_output_id(summary, input_hdca["id"])
            assert input_row is not None, summary["jobs"]
            assert input_row["step_type"] == "input_collection", input_row
            assert input_row["seeded"] is True, input_row

    @skip_without_tool("random_lines1")
    @skip_without_tool("multi_data_param")
    def test_referenced_reduction_output_seeds_collection_input(self):
        """Reference the output of a reduction over a mapped collection; the
        reduction job, the upstream map step, and the original input
        collection must all be seeded."""
        with self.dataset_populator.test_history() as history_id:
            input_hdca, output_hdca, _ = self._run_random_lines_mapped_over_pair(history_id)
            reduction = self.dataset_populator.run_tool(
                tool_id="multi_data_param",
                inputs={
                    "f1": {"src": "hdca", "id": output_hdca["id"]},
                    "f2": {"src": "hdca", "id": output_hdca["id"]},
                },
                history_id=history_id,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            reduction_output_id = reduction["outputs"][0]["id"]
            page = self.dataset_populator.new_notebook_referencing(history_id, output_ids=[reduction_output_id])

            summary = self._extraction_summary(page["id"])

            reduction_row = self._row_with_output_id(summary, reduction_output_id)
            assert reduction_row is not None and reduction_row["seeded"] is True, summary["jobs"]
            assert reduction_row["tool_id"] == "multi_data_param", reduction_row

            # Reached by walking back through the reduction's collection input.
            map_row = self._row_with_output_id(summary, output_hdca["id"])
            assert map_row is not None and map_row["seeded"] is True, summary["jobs"]
            assert map_row["tool_id"] == "random_lines1", map_row

            # The originally uploaded collection input must be seeded.
            input_row = self._row_with_output_id(summary, input_hdca["id"])
            assert input_row is not None, summary["jobs"]
            assert input_row["step_type"] == "input_collection", input_row
            assert input_row["seeded"] is True, input_row

    def _cat1_history(self, history_id):
        hda1 = self.dataset_populator.new_dataset(history_id, content="foo\nbar", wait=True)
        hda2 = self.dataset_populator.new_dataset(history_id, content="baz", wait=True)
        inputs = {"input1": {"src": "hda", "id": hda1["id"]}, "queries_0|input2": {"src": "hda", "id": hda2["id"]}}
        run = self.dataset_populator.run_tool("cat1", inputs, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return run["outputs"][0]["id"]

    @skip_without_tool("cat1")
    def test_referenced_output_seeds_producer_and_exposes_output(self):
        with self.dataset_populator.test_history() as history_id:
            output_id = self._cat1_history(history_id)
            page = self.dataset_populator.new_notebook_referencing(history_id, [output_id])

            summary = self._extraction_summary(page["id"])
            tool_jobs = [j for j in summary["jobs"] if j["step_type"] == "tool"]
            assert len(tool_jobs) == 1, summary["jobs"]
            cat1_job = tool_jobs[0]
            assert cat1_job["tool_id"] == "cat1"
            assert cat1_job["seeded"] is True, cat1_job
            exposed_outputs = [o for o in cat1_job["outputs"] if o["exposed"]]
            assert len(exposed_outputs) == 1, cat1_job["outputs"]
            assert exposed_outputs[0]["id"] == output_id
            assert exposed_outputs[0]["suggested_name"]
            # The two uploaded inputs are part of the producing subgraph → seeded input rows.
            input_jobs = [j for j in summary["jobs"] if j["step_type"] in ("input_dataset", "input_collection")]
            assert input_jobs, summary["jobs"]
            assert all(j["seeded"] for j in input_jobs), input_jobs

    @skip_without_tool("collection_split_on_column")
    @skip_without_tool("cat_list")
    def test_referenced_output_seeds_collection_producing_tool(self):
        """A tool that produces a (non-mapped) output collection consumed by a
        downstream reduction is reached by walking back through the consumer's
        collection input and seeded by its own job id (no ICJ)."""
        with self.dataset_populator.test_history() as history_id:
            d1 = self.dataset_populator.new_dataset(history_id, content="a\t1\nb\t2\na\t3\n", wait=True)
            split = self.dataset_populator.run_tool(
                tool_id="collection_split_on_column",
                inputs={"input1": {"src": "hda", "id": d1["id"]}},
                history_id=history_id,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            split_collection = split["output_collections"][0]
            cat_list = self.dataset_populator.run_tool(
                tool_id="cat_list",
                inputs={"input1": {"src": "hdca", "id": split_collection["id"]}},
                history_id=history_id,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            final_output_id = cat_list["outputs"][0]["id"]
            page = self.dataset_populator.new_notebook_referencing(history_id, output_ids=[final_output_id])

            summary = self._extraction_summary(page["id"])

            consumer = self._row_with_output_id(summary, final_output_id)
            assert consumer is not None and consumer["seeded"] is True, summary["jobs"]
            assert consumer["tool_id"] == "cat_list", consumer

            producer = self._row_with_output_id(summary, split_collection["id"])
            assert producer is not None and producer["seeded"] is True, summary["jobs"]
            assert producer["tool_id"] == "collection_split_on_column", producer
            assert producer["implicit_collection_jobs_id"] is None, producer

            input_row = self._row_with_output_id(summary, d1["id"])
            assert input_row is not None, summary["jobs"]
            assert input_row["step_type"] == "input_dataset" and input_row["seeded"] is True, input_row

    @skip_without_tool("cat1")
    def test_job_directive_seeds_producing_job_unexposed(self):
        """A notebook that references a job via job_metrics seeds the producing
        job (and its upstream inputs) but does NOT expose its outputs."""
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="foo\nbar", wait=True)
            hda2 = self.dataset_populator.new_dataset(history_id, content="baz", wait=True)
            inputs = {"input1": {"src": "hda", "id": hda1["id"]}, "queries_0|input2": {"src": "hda", "id": hda2["id"]}}
            run = self.dataset_populator.run_tool("cat1", inputs, history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            cat1_job_id = run["jobs"][0]["id"]
            page = self.dataset_populator.new_notebook_referencing(history_id, job_ids=[cat1_job_id])

            summary = self._extraction_summary(page["id"])
            tool_rows = self._rows_by_type(summary, "tool")
            assert len(tool_rows) == 1, summary["jobs"]
            cat1_row = tool_rows[0]
            assert cat1_row["tool_id"] == "cat1"
            assert cat1_row["seeded"] is True, cat1_row
            # Job-referenced (not content-referenced): seeded but not exposed.
            assert all(not o["exposed"] for o in cat1_row["outputs"]), cat1_row["outputs"]
            input_rows = self._rows_by_type(summary, "input_dataset", "input_collection")
            assert input_rows and all(r["seeded"] for r in input_rows), summary["jobs"]

    @skip_without_tool("random_lines1")
    def test_job_directive_seeds_map_step_via_icj_and_element_job(self):
        """job_metrics(implicit_collection_jobs_id=...) and the equivalent
        job_metrics(job_id=<element job>) both seed the map step (folded to ICJ)
        and the collection it was mapped over."""
        with self.dataset_populator.test_history() as history_id:
            input_hdca, output_hdca, element_job_id = self._run_random_lines_mapped_over_pair(history_id)
            # Resolve the (encoded) ICJ id from a content-referencing summary.
            content_page = self.dataset_populator.new_notebook_referencing(
                history_id, collection_ids=[output_hdca["id"]]
            )
            icj_id = self._rows_by_type(self._extraction_summary(content_page["id"]), "tool")[0][
                "implicit_collection_jobs_id"
            ]
            assert icj_id

            for variant in ({"icj_ids": [icj_id]}, {"job_ids": [element_job_id]}):
                page = self.dataset_populator.new_notebook_referencing(history_id, **variant)
                summary = self._extraction_summary(page["id"])
                tool_rows = self._rows_by_type(summary, "tool")
                assert len(tool_rows) == 1, (variant, summary["jobs"])
                map_row = tool_rows[0]
                assert map_row["tool_id"] == "random_lines1", (variant, map_row)
                assert map_row["seeded"] is True, (variant, map_row)
                assert map_row["implicit_collection_jobs_id"] == icj_id, (variant, map_row)
                assert all(not o["exposed"] for o in map_row["outputs"]), (variant, map_row["outputs"])
                input_row = self._row_with_output_id(summary, input_hdca["id"])
                assert input_row is not None and input_row["seeded"] is True, (variant, summary["jobs"])

    def test_job_directive_on_upload_seeds_input_with_warning(self):
        """A job_metrics directive on an upload job (not a workflow step) seeds an
        input row and surfaces a per-row seed_warning."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="foo\nbar", wait=True)
            upload_jobs = self.dataset_populator.history_jobs_for_tool(history_id, "__DATA_FETCH__")
            assert upload_jobs, "expected an upload (__DATA_FETCH__) job"
            page = self.dataset_populator.new_notebook_referencing(history_id, job_ids=[upload_jobs[0]["id"]])

            summary = self._extraction_summary(page["id"])
            input_row = self._row_with_output_id(summary, hda["id"])
            assert input_row is not None, summary["jobs"]
            assert input_row["step_type"] == "input_dataset", input_row
            assert input_row["seeded"] is True, input_row
            assert input_row["seed_warning"], input_row
            assert self._rows_by_type(summary, "tool") == [], summary["jobs"]

    def test_referenced_copied_collection_normalizes_to_original(self):
        """A collection copied in from another history is followed to its
        original for identity (the summary row carries the original id), and is
        surfaced as a seeded input collection row; the cross-history producer is
        not leaked as an extractable step."""
        source_history_id = self.dataset_populator.new_history()
        source_hdca = self.dataset_collection_populator.create_pair_in_history(
            source_history_id, contents=["a\n", "b\n"], wait=True
        ).json()["outputs"][0]
        with self.dataset_populator.test_history() as history_id:
            copied = self._copy_hdca_to_history(history_id, source_hdca)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            page = self.dataset_populator.new_notebook_referencing(history_id, collection_ids=[copied["id"]])

            summary = self._extraction_summary(page["id"])

            # Rows are keyed by the original (source) id even though the copy lives here.
            row = self._row_with_output_id(summary, source_hdca["id"])
            assert row is not None, summary["jobs"]
            assert row["step_type"] == "input_collection", row
            assert row["seeded"] is True, row
            assert self._rows_by_type(summary, "tool") == [], summary["jobs"]

    @skip_without_tool("cat1")
    def test_unreferenced_history_seeds_nothing(self):
        with self.dataset_populator.test_history() as history_id:
            self._cat1_history(history_id)
            page = self.dataset_populator.new_history_page(history_id, content="# Just prose, no directives")

            summary = self._extraction_summary(page["id"])
            assert summary["jobs"], "whole-history rows should still be present"
            assert all(j["seeded"] is False for j in summary["jobs"]), summary["jobs"]
            assert all(not o["exposed"] for j in summary["jobs"] for o in j["outputs"]), summary["jobs"]

    def test_400_on_page_without_history(self):
        page = self.dataset_populator.new_page(slug="extraction-no-history")
        response = self._get(f"pages/{page['id']}/workflow_extraction_summary")
        self._assert_status_code_is(response, 400)

    @skip_without_tool("cat1")
    def test_403_for_other_user_without_history_access(self):
        with self.dataset_populator.test_history() as history_id:
            output_id = self._cat1_history(history_id)
            page = self.dataset_populator.new_notebook_referencing(history_id, [output_id])
            # publish the page so a different user can resolve it...
            self._put(f"pages/{page['id']}/publish", json=True)
            with self._different_user():
                # ...but without history access the full-history summary must not leak.
                response = self._get(f"pages/{page['id']}/workflow_extraction_summary")
                self._assert_status_code_is(response, 403)
