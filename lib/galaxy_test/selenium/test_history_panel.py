from galaxy.selenium.navigates_galaxy import edit_details
from .framework import (
    managed_history,
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)
from .upload_activity_helpers import UsesUploadActivity

NEW_HISTORY_NAME = "New History Name"
HISTORY_PANEL_AXE_IMPACT_LEVEL = "moderate"

# the heading is now nested in `ClickToEdit`, and it conditionally replaces the label for the input
HISTORY_PANEL_VIOLATION_EXCEPTIONS = ["heading-order", "label"]


class TestHistoryPanel(SeleniumTestCase, UsesUploadActivity):
    ensure_registered = True

    @selenium_test
    def test_history_panel_landing_state(self):
        self.assert_initial_history_panel_state_correct()
        editor = self.components.history_panel.editor.selector(scope=".history-index")
        self.components.history_panel._.assert_no_axe_violations_with_impact_of_at_least(
            HISTORY_PANEL_AXE_IMPACT_LEVEL, HISTORY_PANEL_VIOLATION_EXCEPTIONS
        )
        toggle = editor.toggle
        toggle.wait_for_visible()

    @selenium_test
    def test_history_panel_rename(self):
        self.history_panel_rename(NEW_HISTORY_NAME)
        self.assert_name_changed()

    @selenium_test
    def test_history_rename_cancel_with_escape(self):
        editable_text_input_element = self.history_panel_name_input()
        editable_text_input_element.send_keys(NEW_HISTORY_NAME)
        self.components.history_panel._.assert_no_axe_violations_with_impact_of_at_least(
            HISTORY_PANEL_AXE_IMPACT_LEVEL, HISTORY_PANEL_VIOLATION_EXCEPTIONS
        )
        self.send_escape(editable_text_input_element)
        self.components.history_panel.name_edit_input.wait_for_absent_or_hidden()
        assert NEW_HISTORY_NAME not in self.history_panel_name()

    @selenium_test
    @edit_details
    def test_history_tags_and_annotations_buttons(self):
        history_editor = self.components.history_panel.editor.selector(scope=".history-index")
        history_editor.annotation_input.wait_for_clickable()
        history_editor.tags_input.wait_for_clickable()

    @selenium_test
    @managed_history
    def test_delete_undelete_and_purge_items(self):
        history_id = self.current_history_id()
        for content in ("1\n", "2\n", "3\n", "4\n"):
            self.dataset_populator.new_dataset(history_id, content=content, wait=True)
        self.home()
        self.history_panel_wait_for_hid_ok(4)

        self.history_panel_item_delete(1)
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_multi_operations_show()
        self.history_panel_muli_operation_select_hid(2)
        self.history_panel_delete_selected()
        self.history_panel_wait_for_hid_hidden(2)
        # A bulk delete ends selection mode.
        self.history_panel_multi_operations_show()
        self.history_panel_muli_operation_select_hid(3)
        self.history_panel_delete_selected(purge=True)
        self.history_panel_wait_for_hid_hidden(3)
        self._wait_for_history_item_states(
            history_id,
            ("deleted", "purged"),
            {1: (True, False), 2: (True, False), 3: (True, True), 4: (False, False)},
            "hids 1 and 2 to be deleted and hid 3 purged",
        )

        self.history_panel_include_deleted()
        self.history_panel_item_component(hid=2).undelete_button.wait_for_visible()
        # a purged item can't be undeleted
        self.history_panel_wait_for_hid_visible(3)
        self.history_panel_item_component(hid=3).undelete_button.assert_absent()
        self.screenshot("history_panel_deleted_items_shown")
        self.history_panel_item_undelete(1)
        self.history_panel_wait_for_hid_visible(1)
        self.history_panel_item_component(hid=1).delete_button.wait_for_visible()
        self.screenshot("history_panel_undeleted_item_still_listed")
        # a deleted item stays listed while Include deleted is on
        self.history_panel_item_delete(4)
        self.history_panel_item_component(hid=4).undelete_button.wait_for_visible()
        self._wait_for_history_item_states(
            history_id,
            ("deleted", "purged"),
            {1: (False, False), 2: (True, False), 3: (True, True), 4: (True, False)},
            "hid 1 to be undeleted and hid 4 deleted",
        )

        self.history_panel_include_deleted()
        self.history_panel_wait_for_hid_visible(1)
        self.history_panel_item_component(hid=1).delete_button.wait_for_visible()
        self.history_panel_wait_for_hid_hidden(2)
        self.history_panel_wait_for_hid_hidden(3)
        self.history_panel_wait_for_hid_hidden(4)

        self.history_panel_filter("deleted:true")
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_wait_for_and_select([2])
        self.history_panel_undelete_selected()
        # an undeleted item no longer matches deleted:true
        self.history_panel_wait_for_hid_hidden(2)
        self.history_panel_wait_for_hid_visible(4)
        self._wait_for_history_item_states(
            history_id,
            ("deleted", "purged"),
            {1: (False, False), 2: (False, False), 3: (True, True), 4: (True, False)},
            "hid 2 to be undeleted",
        )

    @selenium_test
    @managed_history
    def test_unhide_item_with_include_hidden(self):
        history_id = self.current_history_id()
        self.dataset_populator.new_dataset(history_id, content="1\n", wait=True)
        hda2 = self.dataset_populator.new_dataset(history_id, content="2\n", wait=True)
        self.dataset_populator.hide_dataset(hda2["id"])
        self.home()
        self.history_panel_wait_for_hid_ok(1)
        self.history_panel_wait_for_hid_hidden(2)

        self.history_panel_include_hidden()
        self.history_panel_item_unhide(2)
        # an unhidden item stays listed while Include hidden is on
        self.history_panel_item_component(hid=2).unhide_button.wait_for_absent_or_hidden()
        self.history_panel_item_component(hid=2).delete_button.wait_for_visible()
        self.screenshot("history_panel_hidden_item_unhidden")
        # a deleted item still leaves the list
        self.history_panel_item_delete(1)
        self.history_panel_wait_for_hid_hidden(1)
        self._wait_for_history_item_states(
            history_id,
            ("deleted", "visible"),
            {1: (True, True), 2: (False, True)},
            "hid 1 to be deleted and hid 2 unhidden",
        )

    @selenium_test
    @managed_history
    def test_hide_and_unhide_items(self):
        history_id = self.current_history_id()
        for content in ("1\n", "2\n", "3\n"):
            self.dataset_populator.new_dataset(history_id, content=content, wait=True)
        self.home()
        self.history_panel_wait_for_hid_ok(3)

        self.history_panel_wait_for_and_select([1, 2])
        self.history_panel_hide_selected()
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_wait_for_hid_hidden(2)
        self._wait_for_history_item_states(
            history_id, ("visible",), {1: (False,), 2: (False,), 3: (True,)}, "hids 1 and 2 to be hidden"
        )

        self.history_panel_include_hidden()
        self.history_panel_wait_for_and_select([1])
        self.history_panel_hide_selected(unhide=True)
        self._wait_for_history_item_states(
            history_id, ("visible",), {1: (True,), 2: (False,), 3: (True,)}, "hid 1 to be unhidden"
        )
        self.screenshot("history_panel_hidden_items_shown")

        self.history_panel_filter("visible:hidden")
        self.history_panel_wait_for_hid_hidden(1)
        self.history_panel_item_unhide(2)
        # an unhidden item no longer matches visible:hidden
        self.history_panel_wait_for_hid_hidden(2)
        self._wait_for_history_item_states(
            history_id, ("visible",), {1: (True,), 2: (True,), 3: (True,)}, "hid 2 to be unhidden"
        )

    def _wait_for_history_item_states(self, history_id, keys, expected, description):
        """Wait until the API reports ``{hid: (values of keys)}`` equal to ``expected``."""
        data = {"v": "dev", "keys": ",".join(("hid", *keys))}

        def states():
            contents = self.dataset_populator.get_history_contents(history_id, data=data)
            return {item["hid"]: tuple(item[key] for key in keys) for item in contents}

        self._wait_on(lambda: states() == expected, description)

    @selenium_test
    def test_history_panel_annotations_change(self):
        history_panel = self.components.history_panel

        @retry_assertion_during_transitions
        def assert_current_annotation(expected, error_message="History annotation", is_equal=True):
            text_component = history_panel.annotation_editable_text
            current_annotation = text_component.wait_for_visible()
            error_message += " given: [%s] expected [%s] "
            if is_equal:
                assert current_annotation.text == expected, error_message % (current_annotation.text, expected)
            else:
                assert current_annotation.text != expected, error_message % (current_annotation.text, expected)

        def set_random_annotation(clear_text=True):
            random_annotation = self._get_random_name(prefix="arbitrary_annotation_")
            self.set_history_annotation(random_annotation, clear_text)
            return random_annotation

        # assert that annotation wasn't set before
        history_panel.annotation_area.assert_absent_or_hidden()

        # assign annotation random text
        initial_annotation = set_random_annotation()
        assert_current_annotation(initial_annotation)

        # change annotation text
        changed_annotation = set_random_annotation()

        assert_current_annotation(
            initial_annotation, error_message="History annotation was not changed!", is_equal=False
        )
        assert_current_annotation(
            changed_annotation,
            error_message="History annotation was changed, but annotation text is wrong!",
            is_equal=True,
        )

    @selenium_test
    def test_history_panel_switch_history(self):
        target_id = self.dataset_populator.new_history("switch target")
        self.home()
        self.history_panel_switch_to(target_id)

        @retry_assertion_during_transitions
        def assert_switched():
            assert self.history_panel_name() == "switch target"

        assert_switched()
        self.screenshot("history_panel_switched_history")

    @selenium_test
    def test_history_panel_tags_change(self):
        def create_tags(size):
            history_panel_tags = []
            for i in range(size):
                history_panel_tags.append(self._get_random_name(prefix="arbitrary_tag_%s_") % i)
            return history_panel_tags

        def add_tags(tags_size):
            tags = create_tags(tags_size)
            self.history_panel_add_tags(tags)
            return tags

        # check tags against list
        def assert_current_tags(expected_tags):
            current_tags = self.open_tags()
            errmsg = f"tags [{current_tags}] are not the same as expected [{expected_tags}]"
            assert [tag.text for tag in current_tags.all()] == expected_tags, errmsg

        # looks like this is intended to check if the tag editor is open
        def assert_no_tags():
            tags_component = self.components.history_panel.tag_editor.selector(scope=".history-index")
            tags_component.display.assert_absent_or_hidden()

        assert_no_tags()

        # add new tags to empty tags area
        tags_size = 6
        tags = add_tags(tags_size)
        assert_current_tags(tags)

        # add more tags to non-empty tags area
        tags += add_tags(tags_size)
        self.sleep_for(self.wait_types.UX_RENDER)
        tags.sort()
        assert_current_tags(tags)

        # delete all tags
        expected_tags_len = len(tags)
        self.clear_tags(expected_tags_len)
        self.sleep_for(self.wait_types.UX_RENDER)
        assert_no_tags()

    # after about 5 tags, a toggle link shows up and you have to click it to see the full list
    def open_tags(self):
        tags_component = self.components.history_panel.tag_editor.selector(scope=".history-index")
        if tags_component.tag_area.is_absent:
            tags_component.toggle.wait_for_and_click()
        tags_component.display.wait_for_visible()
        return tags_component.display

    @edit_details
    def clear_tags(self, expected_tags_size):
        self.open_tags()
        tags = self.components.history_panel.tag_editor.selector(scope=".history-index")
        tags.show_more_button.wait_for_and_click()
        close_tag_buttons = tags.tag_close_btn.all()
        current_tags_size = len(close_tag_buttons)
        errmsg = f"there are more tags than expected! current {current_tags_size}, expected {expected_tags_size}"
        assert expected_tags_size == current_tags_size, errmsg
        for close_btn in reversed(close_tag_buttons):
            close_btn.click()
            self.sleep_for(self.wait_types.UX_RENDER)

    @selenium_test
    def test_refresh_preserves_state(self):
        self.upload_context("local-file").stage_local_file(self.get_filename("1.txt")).start()
        self.wait_for_history()

        # Open the details, verify they are open and do a refresh.
        self.history_panel_ensure_showing_item_details(hid=1)
        self.history_panel_item_body_component(1, wait=True)

        self._refresh()
        self.wait_for_history()

        # After the refresh, verify the details are still open.
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.wait_for_selector_clickable(self.history_panel_item_selector(hid=1))
        assert self.history_panel_item_showing_details(hid=1)

        # Close the detailed display, refresh, and ensure they are still closed.
        self.history_panel_click_item_title(hid=1, wait=True)
        assert not self.history_panel_item_showing_details(hid=1)

        self._refresh()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.wait_for_selector_clickable(self.history_panel_item_selector(hid=1))
        assert not self.history_panel_item_showing_details(hid=1)

    @retry_assertion_during_transitions
    def assert_name_changed(self):
        name = self.history_panel_name()
        assert name == NEW_HISTORY_NAME

    def _refresh(self):
        self.home()
