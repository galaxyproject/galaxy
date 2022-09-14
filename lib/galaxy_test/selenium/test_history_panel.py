import pytest

from galaxy.selenium.navigates_galaxy import edit_details
from .framework import (
    retry_assertion_during_transitions,
    selenium_test,
    SeleniumTestCase,
)

NEW_HISTORY_NAME = "New History Name"


class HistoryPanelTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_history_panel_landing_state(self):
        self.assert_initial_history_panel_state_correct()
        name_element = self.history_panel_name_element()
        if self.is_beta_history():
            # look for the editor icon
            editor = self.components.history_panel.editor.selector(scope=".history-index")
            toggle = editor.toggle
            toggle.wait_for_visible()
        else:
            tag_icon_selector = self.navigation.history_panel.selectors.tag_icon
            annotation_icon_selector = self.navigation.history_panel.selectors.annotation_icon
            self.wait_for_visible(tag_icon_selector)
            self.wait_for_visible(annotation_icon_selector)
            self.assert_tooltip_text(name_element, self.navigation.history_panel.text.tooltip_name)

    @selenium_test
    def test_history_panel_rename(self):
        self.history_panel_rename(NEW_HISTORY_NAME)
        self.assert_name_changed()

    @selenium_test
    def test_history_rename_confirm_with_click(self):
        if self.is_beta_history():
            raise pytest.skip(
                "Beta History Panel has explicit editing toggle mode, so can not click off to the side to save"
            )
        editable_text_input_element = self.history_panel_name_input()
        editable_text_input_element.send_keys(NEW_HISTORY_NAME)
        self.click_center()
        self.assert_absent(self.navigation.history_panel.selectors.name_edit_input)
        self.assert_name_changed()

    @selenium_test
    def test_history_rename_cancel_with_escape(self):
        self.open_history_editor()
        editable_text_input_element = self.history_panel_name_input()
        editable_text_input_element.send_keys(NEW_HISTORY_NAME)
        self.send_escape(editable_text_input_element)
        self.components.history_panel.name_edit_input.wait_for_absent_or_hidden()
        assert NEW_HISTORY_NAME not in self.history_panel_name()

    @selenium_test
    @edit_details
    def test_history_tags_and_annotations_buttons(self):
        if self.is_beta_history():
            history_editor = self.components.history_panel.editor.selector(scope=".history-index")
            history_editor.annotation_input.wait_for_clickable()
            history_editor.tags_input.wait_for_clickable()
        else:
            tag_icon_selector = self.navigation.history_panel.selectors.tag_icon
            annotation_icon_selector = self.navigation.history_panel.selectors.annotation_icon

            tag_area_selector = self.navigation.history_panel.selectors.tag_area
            annotation_area_selector = self.navigation.history_panel.selectors.annotation_area

            tag_icon = self.wait_for_clickable(tag_icon_selector)
            annon_icon = self.wait_for_clickable(annotation_icon_selector)

            self.assert_absent_or_hidden(tag_area_selector)
            self.assert_absent_or_hidden(annotation_area_selector)

            tag_icon.click()

            self.wait_for_visible(tag_area_selector)
            self.assert_absent_or_hidden(annotation_area_selector)

            tag_icon.click()
            self.sleep_for(self.wait_types.UX_TRANSITION)
            annon_icon.click()

            self.wait_for_visible(annotation_area_selector)
            self.assert_absent_or_hidden(tag_area_selector)

            annon_icon.click()
            self.sleep_for(self.wait_types.UX_TRANSITION)

            self.assert_absent_or_hidden(tag_area_selector)
            self.assert_absent_or_hidden(annotation_area_selector)

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
            history_panel_tags = list()
            for i in range(size):
                history_panel_tags.append(self._get_random_name(prefix="arbitrary_tag_%s_") % i)
            return history_panel_tags

        def add_tags(tags_size):
            tags = create_tags(tags_size)
            self.history_panel_add_tags(tags)
            return tags

        # check tags against list
        def assert_current_tags(expected_tags):
            if self.is_beta_history():
                current_tags = self.open_tags()
            else:
                current_tags = self.components.history_panel.tags
            errmsg = f"tags [{current_tags}] are not the same as expected [{expected_tags}]"
            assert [tag.text for tag in current_tags.all()] == expected_tags, errmsg

        # looks like this is intended to check if the tag editor is open
        def assert_no_tags():
            if self.is_beta_history():
                tags_component = self.components.history_panel.tag_editor.selector(scope=".history-index")
                tags_component.display.assert_absent_or_hidden()
            else:
                self.components.history_panel.tag_area.assert_absent_or_hidden()

        assert_no_tags()

        # add new tags to empty tags area
        tags_size = 5
        tags = add_tags(tags_size)
        assert_current_tags(tags)

        # add more tags to non-empty tags area
        tags += add_tags(tags_size)
        self.sleep_for(self.wait_types.UX_RENDER)
        if self.is_beta_history():
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
        if self.is_beta_history():
            self.open_tags()
            tags = self.components.history_panel.tag_editor.selector(scope=".history-index")
            close_tag_buttons = tags.tag_close_btn.all()
        else:
            close_tag_buttons = self.components.history_panel.tag_close_btn.all()

        current_tags_size = len(close_tag_buttons)

        errmsg = f"there are more tags than expected! current {current_tags_size}, expected {expected_tags_size}"
        assert expected_tags_size == current_tags_size, errmsg

        for close_btn in reversed(close_tag_buttons):
            close_btn.click()
            self.sleep_for(self.wait_types.UX_RENDER)

        if not self.is_beta_history():
            self.components.history_panel.tag_icon.wait_for_and_click()
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
        wait = not self.is_beta_history()
        self.history_panel_click_item_title(hid=1, wait=wait)
        assert not self.history_panel_item_showing_details(hid=1)

        self._refresh()

        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.wait_for_selector_clickable(self.history_panel_item_selector(hid=1))
        assert not self.history_panel_item_showing_details(hid=1)

    @retry_assertion_during_transitions
    def assert_name_changed(self):
        name = self.history_panel_name()
        self.assertEqual(name, NEW_HISTORY_NAME)

    def _refresh(self):
        if self.is_beta_history():
            # beta history has no refresh button
            self.home()
        else:
            self.history_panel_refresh_click()
