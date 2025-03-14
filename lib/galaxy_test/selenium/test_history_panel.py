from galaxy.selenium.navigates_galaxy import edit_details
from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)

NEW_HISTORY_NAME = "New History Name"
HISTORY_PANEL_AXE_IMPACT_LEVEL = "moderate"

# the heading is now nested in `ClickToEdit`, and it conditionally replaces the label for the input
HISTORY_PANEL_VIOLATION_EXCEPTIONS = ["heading-order", "label"]


class TestHistoryPanel(SeleniumTestCase):
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
        close_tag_buttons = tags.tag_close_btn.all()
        current_tags_size = len(close_tag_buttons)
        errmsg = f"there are more tags than expected! current {current_tags_size}, expected {expected_tags_size}"
        assert expected_tags_size == current_tags_size, errmsg
        for close_btn in reversed(close_tag_buttons):
            close_btn.click()
            self.sleep_for(self.wait_types.UX_RENDER)

    @selenium_test
    def test_refresh_preserves_state(self):
        self.perform_upload(self.get_filename("1.txt"))
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
        self.history_panel_click_item_title(hid=1, wait=False)
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
