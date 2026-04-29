from galaxy_test.base.populators import skip_without_agents
from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_only,
    selenium_test,
    SeleniumTestCase,
)


class TestHistoryPages(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_navigate_to_pages(self):
        """Navigate to pages via direct URL."""
        self.navigate_to_history_pages()
        self.screenshot("history_pages_list_empty")
        self.components.pages.history.empty_state.wait_for_visible()

    @selenium_test
    @managed_history
    def test_navigate_via_page_icon(self):
        """Click page icon in history counter bar opens page editor.

        When no pages exist, resolveCurrentPage auto-creates one.
        """
        self.history_panel_click_edit_current_page()
        self.components.pages.history.editor.wait_for_visible()
        self.screenshot("history_page_icon_auto_create")

    @selenium_test
    @managed_history
    def test_page_icon_opens_existing(self):
        """Click page icon navigates to existing page."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Existing", content="# Hello")

        self.history_panel_click_edit_current_page()
        self.components.pages.history.editor.wait_for_visible()
        editor = self.components.pages.history.markdown_editor
        assert "Hello" in editor.wait_for_value()
        self.screenshot("history_page_icon_existing")

    @selenium_test
    @managed_history
    def test_create_page(self):
        """Create a new page and verify editor appears."""
        self.navigate_to_history_pages()
        self.history_page_create(screenshot_name="history_page_create")
        self.components.pages.history.editor.wait_for_visible()
        title_text = self.components.pages.history.toolbar_title.wait_for_text()
        assert "Untitled" in title_text or title_text != ""
        self.screenshot("history_page_editor_new")

    @selenium_test
    @managed_history
    def test_page_empty_history(self):
        """Create page for an empty history."""
        self.navigate_to_history_pages()
        self.history_page_create()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_editor_set_content("# Empty History Notes\n\nNo datasets yet.")
        self.history_page_save()

        self.history_page_manage()
        self.history_page_assert_item_count(1)
        self.screenshot("history_page_empty_history")

    @selenium_test
    @managed_history
    def test_edit_and_save_page(self):
        """Edit page content, save, reload, verify persistence."""
        self.navigate_to_history_pages()
        self.history_page_create()

        test_content = "# My Analysis\n\nThis is a test page."
        self.history_page_editor_set_content(test_content)

        self.components.pages.history.unsaved_indicator.wait_for_visible()
        self.screenshot("history_page_unsaved")

        self.history_page_save()
        self.screenshot("history_page_saved")

        self.history_page_manage()
        self.history_page_assert_item_count(1)

        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        editor = self.components.pages.history.markdown_editor
        content = editor.wait_for_value()
        assert "My Analysis" in content
        self.screenshot("history_page_reloaded")

    @selenium_test
    @managed_history
    def test_save_button_disabled_when_clean(self):
        """Verify save button is disabled when no changes exist."""
        self.navigate_to_history_pages()
        self.history_page_create()
        self.components.pages.history.editor.wait_for_visible()

        save_button = self.components.pages.history.save_button
        save_button.assert_disabled()

        self.components.pages.history.unsaved_indicator.assert_absent_or_hidden()

        self.history_page_editor_set_content("some content")

        @retry_assertion_during_transitions
        def assert_save_enabled():
            assert not save_button.has_class("disabled")

        assert_save_enabled()

        self.history_page_save()

        @retry_assertion_during_transitions
        def assert_save_disabled_again():
            save_button.assert_disabled()

        assert_save_disabled_again()
        self.screenshot("history_page_save_disabled")

    @selenium_test
    @managed_history
    def test_multiple_pages_per_history(self):
        """Create multiple pages for the same history."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="First Page", content="# First")
        self.dataset_populator.new_history_page(history_id, title="Second Page", content="# Second")

        self.navigate_to_history_pages()
        self.screenshot("history_pages_list_multiple")

        self.history_page_assert_item_count(2)

    @selenium_test
    @managed_history
    def test_delete_page(self):
        """Delete a page via API and verify it disappears from list."""
        history_id = self.current_history_id()

        self.dataset_populator.new_history_page(history_id, title="Keep This")
        nb2 = self.dataset_populator.new_history_page(history_id, title="Delete This")

        self.navigate_to_history_pages()
        self.history_page_assert_item_count(2)

        # Delete via API, then go home and navigate back
        self.dataset_populator.delete_history_page(nb2["id"])
        self.home()
        self.navigate_to_history_pages()

        @retry_assertion_during_transitions
        def assert_one_page():
            items = self.components.pages.history.item.all()
            assert len(items) == 1

        assert_one_page()
        self.screenshot("history_page_after_delete")

    @selenium_test
    @managed_history
    def test_page_permissions_shared_history(self):
        """Verify pages visible on shared history -- publish and check API."""
        history_id = self.current_history_id()

        page = self.dataset_populator.new_history_page(history_id, title="Shared Page", content="# Shared Content")

        self.current_history_publish()

        fetched = self.dataset_populator.get_history_page(page["id"])
        assert fetched["title"] == "Shared Page"
        self.screenshot("history_page_shared_view")

    # --- Window Manager Integration Tests ---

    @selenium_test
    @managed_history
    def test_page_opens_in_window_when_wm_active(self):
        """With WM active, clicking page icon opens it in a WinBox."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Window Test", content="# Windowed Page")

        with self.window_manager_active():
            assert self.window_manager_window_count() == 0

            self.history_panel_click_view_current_page()

            self.window_manager_wait_for_window_count(1)
            with self.winbox_frame(0):
                self.wait_for_selector_visible(".markdown-wrapper")

            self.screenshot("history_page_in_winbox")

    @selenium_test
    @managed_history
    def test_page_window_shows_rendered_content(self):
        """Windowed page shows rendered markdown, not editor."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(
            history_id, title="Render Test", content="# Hello World\n\nSome analysis notes."
        )

        with self.window_manager_active():
            assert self.window_manager_window_count() == 0
            self.history_panel_click_view_current_page()
            self.window_manager_wait_for_window_count(1)

            with self.winbox_frame(0):
                self.wait_for_selector_visible(".markdown-wrapper")
                self.wait_for_selector_absent_or_hidden("[data-description='page editor toolbar']")
                self.wait_for_selector_absent_or_hidden("[data-description='page editor view']")
                self.screenshot("history_page_window_rendered")

    @selenium_test
    @managed_history
    def test_page_normal_navigation_when_wm_disabled(self):
        """With WM disabled, selecting page navigates to editor normally."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Normal Nav", content="# Editor Test")

        self.window_manager_disable()

        self.navigate_to_history_pages()
        self.history_page_assert_item_count(1)
        self.components.pages.history.item.wait_for_and_click()

        self.components.pages.history.editor.wait_for_visible()
        assert self.window_manager_window_count() == 0
        self.screenshot("history_page_normal_nav_wm_off")

    @selenium_test
    @managed_history
    def test_page_window_with_embedded_dataset(self):
        """Windowed page renders embedded dataset displays."""
        history_id = self.current_history_id()
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        # Get the dataset ID for the directive
        datasets = self.dataset_populator.get_history_dataset_details(history_id, hid=1)
        dataset_id = datasets["dataset_id"]
        content = f"# Analysis\n\n```galaxy\nhistory_dataset_display(history_dataset_id={dataset_id})\n```\n"
        self.dataset_populator.new_history_page(history_id, title="Dataset Embed", content=content)

        with self.window_manager_active():
            assert self.window_manager_window_count() == 0
            self.history_panel_click_view_current_page()
            self.window_manager_wait_for_window_count(1)

            with self.winbox_frame(0):
                self.wait_for_selector_visible(".markdown-wrapper")
                self.wait_for_selector_visible(".embedded-dataset")
                self.screenshot("history_page_window_dataset_embedded")

    # --- Revision UI Tests ---

    @selenium_test
    @managed_history
    def test_revision_list_visible_after_save(self):
        """After saving, revision button shows count; click opens revision list."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Rev Test", content="V1")

        self.navigate_to_history_pages()
        self.history_page_assert_item_count(1)
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_open_revisions()
        self.history_page_assert_revision_count(1)
        self.screenshot("history_page_revision_list")

    @selenium_test
    @managed_history
    def test_revision_restore(self):
        """Restore to old revision updates editor content."""
        history_id = self.current_history_id()
        nb = self.dataset_populator.new_history_page(history_id, title="Restore Test", content="Original")
        self.dataset_populator.update_history_page(nb["id"], content="Modified")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_open_revisions()
        # Click restore on the oldest revision (last in the list)
        restore_buttons = self.components.pages.history.restore_revision_button.all()
        restore_buttons[-1].click()

        editor = self.components.pages.history.markdown_editor

        @retry_assertion_during_transitions
        def assert_restored():
            assert "Original" in editor.wait_for_value()

        assert_restored()
        self.screenshot("history_page_revision_restored")

    @selenium_test
    @managed_history
    def test_revision_count_increases_after_save(self):
        """Saving creates a new revision, count increases."""
        self.navigate_to_history_pages()
        self.history_page_create()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_editor_set_content("First save")
        self.history_page_save()

        self.history_page_editor_set_content("Second save")
        self.history_page_save()

        self.history_page_open_revisions()
        self.history_page_assert_revision_count(3)  # initial + 2 saves
        self.screenshot("history_page_revision_count")

    @selenium_test
    @managed_history
    def test_revision_preview(self):
        """Clicking a revision shows its rendered content."""
        history_id = self.current_history_id()
        nb = self.dataset_populator.new_history_page(history_id, title="Preview", content="# Old Content")
        self.dataset_populator.update_history_page(nb["id"], content="# New Content")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_open_revisions()
        # Click the oldest revision row to preview
        items = self.components.pages.history.revision_item.all()
        items[-1].click()
        self.components.pages.history.revision_view.wait_for_visible()
        self.screenshot("history_page_revision_preview")

    # --- Drag-and-Drop Tests ---

    @selenium_only("seletools drag_and_drop requires Selenium webdriver")
    @selenium_test
    @managed_history
    def test_drag_dataset_to_page_editor(self):
        """Drag a dataset from history panel and drop on page editor."""
        from seletools.actions import drag_and_drop

        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        self.navigate_to_history_pages()
        self.history_page_create()
        self.components.pages.history.editor.wait_for_visible()

        dataset_selector = self.history_panel_wait_for_hid_state(1, "ok")
        dataset_element = dataset_selector.wait_for_visible()

        editor = self.components.pages.history.markdown_editor.wait_for_visible()

        drag_and_drop(self.driver, source=dataset_element, target=editor)
        self.sleep_for(self.wait_types.UX_RENDER)

        value = self.components.pages.history.markdown_editor.wait_for_value()
        assert "history_dataset_display" in value
        self.screenshot("history_page_drag_drop_dataset")

    @selenium_only("seletools drag_and_drop requires Selenium webdriver")
    @selenium_test
    @managed_history
    def test_drag_drop_visual_feedback(self):
        """Verify visual feedback during drag over page editor."""
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        self.navigate_to_history_pages()
        self.history_page_create()
        self.components.pages.history.editor.wait_for_visible()

        dataset_selector = self.history_panel_wait_for_hid_state(1, "ok")
        dataset_element = dataset_selector.wait_for_visible()
        editor = self.components.pages.history.markdown_editor.wait_for_visible()

        ac = self.action_chains()
        ac.click_and_hold(dataset_element).move_to_element(editor).perform()
        self.sleep_for(self.wait_types.UX_RENDER)

        classes = editor.get_attribute("class")
        assert "page-dragover-success" in classes
        self.screenshot("history_page_drag_over_highlight")

        ac.release().perform()

    # --- View / Preview / Rename Tests ---

    @selenium_test
    @managed_history
    def test_view_button_opens_display_mode(self):
        """Click view icon on page list item opens displayOnly mode."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="View Test", content="# Hello Display")

        self.navigate_to_history_pages()
        self.history_page_assert_item_count(1)

        self.components.pages.history.view_button.wait_for_and_click()

        self.components.pages.history.display_toolbar.wait_for_visible()
        self.components.pages.history.rendered_view.wait_for_visible()
        self.components.pages.history.editor.assert_absent_or_hidden()
        self.screenshot("history_page_view_button_display")

    @selenium_test
    @managed_history
    def test_preview_and_edit_toggle(self):
        """Toggle between editor and preview mode."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Toggle Test", content="# Preview Me")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        self.components.pages.history.preview_button.wait_for_and_click()

        self.components.pages.history.display_toolbar.wait_for_visible()
        self.components.pages.history.rendered_view.wait_for_visible()
        self.components.pages.history.editor.assert_absent_or_hidden()
        self.screenshot("history_page_preview_mode")

        self.components.pages.history.edit_button.wait_for_and_click()

        self.components.pages.history.toolbar.wait_for_visible()
        self.components.pages.history.editor.wait_for_visible()
        self.components.pages.history.display_toolbar.assert_absent_or_hidden()
        self.screenshot("history_page_edit_mode_after_preview")

    @selenium_test
    @managed_history
    def test_inline_rename_page(self):
        """Rename page title via ClickToEdit, save, verify persistence."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Original Name", content="# Content")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_rename("Renamed Page")

        self.components.pages.history.unsaved_indicator.wait_for_visible()
        self.screenshot("history_page_renamed_unsaved")

        self.history_page_save()

        self.history_page_manage()
        self.history_page_assert_item_count(1)

        title_text = self.components.pages.history.item_title.wait_for_text()
        assert "Renamed Page" in title_text

        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()
        toolbar_title = self.components.pages.history.toolbar_title.wait_for_text()
        assert "Renamed Page" in toolbar_title
        self.screenshot("history_page_renamed_persisted")

    @selenium_test
    @managed_history
    def test_display_only_shows_expanded_content(self):
        """DisplayOnly mode renders embedded dataset from directive."""
        history_id = self.current_history_id()
        self.perform_upload(self.get_filename("1.fasta"))
        self.history_panel_wait_for_hid_ok(1)

        datasets = self.dataset_populator.get_history_dataset_details(history_id, hid=1)
        dataset_id = datasets["dataset_id"]
        content = f"# Analysis\n\n```galaxy\nhistory_dataset_display(history_dataset_id={dataset_id})\n```\n"
        self.dataset_populator.new_history_page(history_id, title="Display Embed", content=content)

        self.navigate_to_history_pages()
        self.history_page_assert_item_count(1)

        self.components.pages.history.view_button.wait_for_and_click()

        self.components.pages.history.display_toolbar.wait_for_visible()
        self.components.pages.history.rendered_view.wait_for_visible()

        self.wait_for_selector_visible(".markdown-wrapper")
        self.wait_for_selector_visible(".embedded-dataset")
        self.screenshot("history_page_display_embedded_dataset")

    @selenium_test
    @managed_history
    def test_revision_diff_view(self):
        """Two diff modes: compare to previous and compare to current."""
        history_id = self.current_history_id()
        nb = self.dataset_populator.new_history_page(history_id, title="Diff Test", content="# V1\n\nOriginal content")
        self.dataset_populator.update_history_page(nb["id"], content="# V1\n\nModified content\n\nNew section")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_open_revisions()
        self.history_page_assert_revision_count(2)

        # Click newest revision (first in list)
        items = self.components.pages.history.revision_item.all()
        items[0].click()
        self.components.pages.history.revision_view.wait_for_visible()

        # Newest: "Compare to Current" should be hidden, "Compare to Previous" visible
        self.components.pages.history.revision_compare_current_button.assert_absent_or_hidden()
        self.components.pages.history.revision_compare_previous_button.wait_for_visible()

        # Click "Compare to Previous"
        self.components.pages.history.revision_compare_previous_button.wait_for_and_click()
        self.components.pages.history.revision_diff_view.wait_for_visible()

        # Diff should show changes from V1 to V2
        diff_text = self.components.pages.history.revision_diff_view.wait_for_visible().text
        assert "Modified content" in diff_text or "New section" in diff_text

        # Go back, click oldest revision
        self.components.pages.history.revision_back_button.wait_for_and_click()
        items = self.components.pages.history.revision_item.all()
        items[-1].click()
        self.components.pages.history.revision_view.wait_for_visible()

        # Oldest: "Compare to Previous" should be hidden, "Compare to Current" visible
        self.components.pages.history.revision_compare_previous_button.assert_absent_or_hidden()
        self.components.pages.history.revision_compare_current_button.wait_for_visible()

        # Click "Compare to Current"
        self.components.pages.history.revision_compare_current_button.wait_for_and_click()
        self.components.pages.history.revision_diff_view.wait_for_visible()
        self.screenshot("history_page_revision_diff_view")

    @selenium_test
    @managed_history
    def test_history_toolbar_shows_history_controls_not_standalone(self):
        """History-attached editor shows correct toolbar: no permissions, no save-view."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Toolbar Test", content="# Toolbar")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        # History-page controls visible
        self.components.pages.history.save_button.wait_for_visible()
        self.components.pages.history.revisions_button.wait_for_visible()
        self.components.pages.history.preview_button.wait_for_visible()

        # Standalone-only controls absent
        self.components.pages.history.permissions_button.assert_absent_or_hidden()
        self.components.pages.history.save_view_button.assert_absent_or_hidden()

        # Back button says "This History's Pages" not "Back to Pages"
        back_text = self.components.pages.history.back_button.wait_for_text()
        assert "This History's Notebooks" in back_text
        assert "Back to Reports" not in back_text
        self.screenshot("history_toolbar_controls")

    # --- Page Chat Panel Tests ---

    @skip_without_agents
    @selenium_test
    @managed_history
    def test_chat_panel_toggle(self):
        """Open page, click chat button, verify panel visible; click again, verify hidden."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Chat Toggle", content="# Test")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        # Open chat panel
        self.history_page_open_chat()
        self.screenshot("history_page_chat_open")

        # Close chat panel
        self.components.pages.history.chat_button.wait_for_and_click()
        self.components.pages.history.chat_panel.assert_absent_or_hidden()
        self.screenshot("history_page_chat_closed")

    @skip_without_agents
    @selenium_test
    @managed_history
    def test_page_chat_greeting_flow(self):
        """Send greeting, verify query cell and response content."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Chat Greeting", content="# Test")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_open_chat()
        self.history_page_chat_ensure_new()
        self.history_page_chat_send_message("Hello!")

        chat = self.components.pages.history
        assert chat.chat_query_cell.wait_for_text() == "Hello!"

        @retry_assertion_during_transitions
        def assert_response():
            text = chat.chat_response_content.wait_for_text()
            assert len(text) > 0

        assert_response()
        self.screenshot("history_page_chat_greeting")

    @skip_without_agents
    @selenium_test
    @managed_history
    def test_page_chat_multi_turn(self):
        """Send two messages, assert 2 query cells and 2 response cells."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Chat Multi", content="# Test")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_open_chat()
        self.history_page_chat_ensure_new()
        self.history_page_chat_send_message("Hello!")
        self.history_page_chat_send_message("Summarize this history")

        chat = self.components.pages.history

        @retry_assertion_during_transitions
        def assert_two_exchanges():
            assert len(chat.chat_query_cell.all()) == 2
            assert len(chat.chat_response_content.all()) >= 2

        assert_two_exchanges()
        self.screenshot("history_page_chat_multi_turn")

    @skip_without_agents
    @selenium_test
    @managed_history
    def test_page_chat_new_conversation(self):
        """Send message, click new conversation, assert chat is empty."""
        history_id = self.current_history_id()
        self.dataset_populator.new_history_page(history_id, title="Chat New Conv", content="# Test")

        self.navigate_to_history_pages()
        self.components.pages.history.item.wait_for_and_click()
        self.components.pages.history.editor.wait_for_visible()

        self.history_page_open_chat()
        self.history_page_chat_ensure_new()
        self.history_page_chat_send_message("Hello!")

        # Verify message exists
        chat = self.components.pages.history
        assert len(chat.chat_query_cell.all()) >= 1

        # New conversation
        chat.chat_new_conversation.wait_for_and_click()
        self._history_page_chat_assert_empty()
        self.screenshot("history_page_chat_new_conversation")
