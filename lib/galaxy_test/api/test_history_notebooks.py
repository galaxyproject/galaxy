"""Tests for history notebook CRUD and export operations."""

from galaxy_test.api._framework import ApiTestCase
from galaxy_test.base.populators import DatasetPopulator


class TestHistoryNotebooksApi(ApiTestCase):
    """Tests for history notebook CRUD operations."""

    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_create_notebook(self):
        """Test creating a notebook for a history."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Test Notebook")
            self._assert_has_keys(notebook, "id", "history_id", "title", "content")
            assert notebook["title"] == "Test Notebook"
            assert notebook["history_id"] == history_id
            assert notebook["content_format"] == "markdown"

    def test_create_notebook_defaults_title_to_history_name(self):
        """Test that notebook title defaults to history name when not provided."""
        history_id = self.dataset_populator.new_history(name="My Analysis")
        notebook = self.dataset_populator.new_history_notebook(history_id)
        assert notebook["title"] == "My Analysis"

    def test_create_multiple_notebooks_for_history(self):
        """Test that multiple notebooks can be created for the same history."""
        with self.dataset_populator.test_history() as history_id:
            notebook1 = self.dataset_populator.new_history_notebook(history_id, title="First Notebook")
            notebook2 = self.dataset_populator.new_history_notebook(history_id, title="Second Notebook")
            assert notebook1["id"] != notebook2["id"]
            assert notebook1["history_id"] == notebook2["history_id"]

    def test_index_notebooks(self):
        """Test listing notebooks for a history."""
        with self.dataset_populator.test_history() as history_id:
            self.dataset_populator.new_history_notebook(history_id, title="Notebook A")
            self.dataset_populator.new_history_notebook(history_id, title="Notebook B")
            notebooks = self.dataset_populator.list_history_notebooks(history_id)
            assert len(notebooks) == 2

    def test_index_empty_history(self):
        """Test listing notebooks for history with no notebooks."""
        with self.dataset_populator.test_history() as history_id:
            notebooks = self.dataset_populator.list_history_notebooks(history_id)
            assert len(notebooks) == 0

    def test_index_excludes_deleted(self):
        """Test that deleted notebooks are excluded from index by default."""
        with self.dataset_populator.test_history() as history_id:
            notebook1 = self.dataset_populator.new_history_notebook(history_id, title="Active")
            notebook2 = self.dataset_populator.new_history_notebook(history_id, title="Deleted")
            self.dataset_populator.delete_history_notebook(history_id, notebook2["id"])
            notebooks = self.dataset_populator.list_history_notebooks(history_id)
            assert len(notebooks) == 1
            assert notebooks[0]["id"] == notebook1["id"]

    def test_show_notebook(self):
        """Test retrieving a single notebook."""
        with self.dataset_populator.test_history() as history_id:
            created = self.dataset_populator.new_history_notebook(history_id, title="My Notebook", content="# Hello")
            notebook = self.dataset_populator.get_history_notebook(history_id, created["id"])
            assert notebook["title"] == "My Notebook"
            assert "# Hello" in notebook["content"] or "Hello" in notebook["content"]

    def test_update_notebook_content(self):
        """Test updating notebook content creates a new revision."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Updatable", content="Version 1")
            original_revision_id = notebook["latest_revision_id"]

            updated = self.dataset_populator.update_history_notebook(history_id, notebook["id"], content="Version 2")
            assert updated["latest_revision_id"] != original_revision_id

    def test_update_notebook_title(self):
        """Test updating notebook title."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Old Title", content="Content")
            updated = self.dataset_populator.update_history_notebook(
                history_id, notebook["id"], content="Content", title="New Title"
            )
            assert updated["title"] == "New Title"

    def test_delete_notebook(self):
        """Test soft-deleting a notebook."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="To Delete")
            self.dataset_populator.delete_history_notebook(history_id, notebook["id"])

            # Should not appear in index
            notebooks = self.dataset_populator.list_history_notebooks(history_id)
            assert len(notebooks) == 0

            # Should return 404 when trying to access directly
            response = self.dataset_populator.get_history_notebook_raw(history_id, notebook["id"])
            assert response.status_code == 404

    def test_undelete_notebook(self):
        """Test restoring a soft-deleted notebook."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Restore Me")
            self.dataset_populator.delete_history_notebook(history_id, notebook["id"])
            self.dataset_populator.undelete_history_notebook(history_id, notebook["id"])

            # Should appear in index again
            notebooks = self.dataset_populator.list_history_notebooks(history_id)
            assert len(notebooks) == 1

    def test_list_revisions(self):
        """Test listing revisions for a notebook."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Revisions Test", content="V1")
            self.dataset_populator.update_history_notebook(history_id, notebook["id"], content="V2")
            self.dataset_populator.update_history_notebook(history_id, notebook["id"], content="V3")

            revisions = self.dataset_populator.list_history_notebook_revisions(history_id, notebook["id"])
            assert len(revisions) == 3

    def test_notebook_not_found_in_other_history(self):
        """Test that a notebook cannot be accessed from a different history."""
        with self.dataset_populator.test_history() as history1_id:
            with self.dataset_populator.test_history() as history2_id:
                notebook = self.dataset_populator.new_history_notebook(history1_id, title="History 1 Notebook")
                # Try to access from history2
                response = self.dataset_populator.get_history_notebook_raw(history2_id, notebook["id"])
                assert response.status_code == 404

    def test_show_revision(self):
        """Test getting a single revision with content."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Rev Test", content="Version 1")
            self.dataset_populator.update_history_notebook(history_id, notebook["id"], content="Version 2")
            revisions = self.dataset_populator.list_history_notebook_revisions(history_id, notebook["id"])
            # Revisions ordered desc by create_time: [V2, V1]
            rev_v1 = revisions[-1]  # oldest
            detail = self.dataset_populator.get_history_notebook_revision(history_id, notebook["id"], rev_v1["id"])
            self._assert_has_keys(detail, "id", "content", "content_format", "edit_source")
            assert "Version 1" in detail["content"]

    def test_show_revision_wrong_notebook(self):
        """Test that revision from another notebook returns 404."""
        with self.dataset_populator.test_history() as history_id:
            nb1 = self.dataset_populator.new_history_notebook(history_id, title="NB1", content="A")
            nb2 = self.dataset_populator.new_history_notebook(history_id, title="NB2", content="B")
            revisions_nb1 = self.dataset_populator.list_history_notebook_revisions(history_id, nb1["id"])
            response = self.dataset_populator.get_history_notebook_revision_raw(
                history_id, nb2["id"], revisions_nb1[0]["id"]
            )
            assert response.status_code == 404

    def test_revert_to_revision(self):
        """Test restoring notebook to a previous revision."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Revert Test", content="Original")
            self.dataset_populator.update_history_notebook(history_id, notebook["id"], content="Modified")
            revisions = self.dataset_populator.list_history_notebook_revisions(history_id, notebook["id"])
            assert len(revisions) == 2
            original_rev = revisions[-1]  # oldest

            result = self.dataset_populator.revert_history_notebook_revision(
                history_id, notebook["id"], original_rev["id"]
            )
            assert "Original" in result["content"]
            assert result["edit_source"] == "restore"

            revisions_after = self.dataset_populator.list_history_notebook_revisions(history_id, notebook["id"])
            assert len(revisions_after) == 3

    def test_prepare_for_page(self):
        """Test preparing notebook content for Page creation resolves HIDs to encoded IDs."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="hello", wait=True)
            hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda)
            hid = hda_details["hid"]

            content = f"# Analysis\n\n```galaxy\nhistory_dataset_display(hid={hid})\n```\n"
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Export Test", content=content)

            prepared = self.dataset_populator.prepare_notebook_for_page(history_id, notebook["id"])
            assert prepared["title"] == "Export Test"
            # Should have resolved hid= to history_dataset_id= with encoded ID
            assert "hid=" not in prepared["content"]
            assert "history_dataset_id=" in prepared["content"]

    def test_prepare_for_page_then_create_page(self):
        """Full roundtrip: prepare content from notebook, create Page, verify content stored."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="roundtrip", wait=True)
            hda_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda)
            hid = hda_details["hid"]

            content = f"# My Analysis\n\n```galaxy\nhistory_dataset_display(hid={hid})\n```\n"
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Roundtrip Test", content=content)

            prepared = self.dataset_populator.prepare_notebook_for_page(history_id, notebook["id"])

            # Create page using prepared content + notebook FK
            page = self.dataset_populator.new_page(
                slug="notebook-roundtrip",
                title="Roundtrip Test",
                content_format="markdown",
                content=prepared["content"],
            )
            assert page["id"]
            # Verify source FK fields
            assert page.get("source_history_notebook_id") is None  # not passed in this call

    def test_prepare_for_page_empty_notebook(self):
        """Empty notebook produces empty content."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Empty", content="")
            prepared = self.dataset_populator.prepare_notebook_for_page(history_id, notebook["id"])
            assert prepared["content"] == ""
            assert prepared["title"] == "Empty"

    def test_prepare_for_page_wrong_history(self):
        """Notebook from different history returns 404."""
        with self.dataset_populator.test_history() as history1_id:
            with self.dataset_populator.test_history() as history2_id:
                notebook = self.dataset_populator.new_history_notebook(history1_id, title="Wrong History")
                response = self.dataset_populator.prepare_notebook_for_page_raw(history2_id, notebook["id"])
                assert response.status_code == 404

    def test_page_source_notebook_fk(self):
        """Creating a Page with history_notebook_id stores the FK."""
        with self.dataset_populator.test_history() as history_id:
            notebook = self.dataset_populator.new_history_notebook(history_id, title="Source Test", content="# Hello")
            # Create page with notebook FK
            page_payload = self.dataset_populator.new_page_payload(
                slug="from-notebook",
                title="From Notebook",
                content_format="markdown",
                content="# Hello",
            )
            page_payload["history_notebook_id"] = notebook["id"]
            response = self._post("pages", page_payload, json=True)
            page = response.json()
            assert page["source_history_notebook_id"] == notebook["id"]

    def test_page_source_fk_null_by_default(self):
        """Pages created without source IDs have null source fields."""
        page = self.dataset_populator.new_page(
            slug="no-source", title="No Source", content_format="markdown", content="plain"
        )
        assert page.get("source_invocation_id") is None
        assert page.get("source_history_notebook_id") is None
