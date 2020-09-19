from .framework import (
    selenium_test,
    SeleniumTestCase
)


class HistoryPanelTestCase(SeleniumTestCase):

    ensure_registered = True

    @selenium_test
    def test_history_panel_landing_state(self):
        self.assert_initial_history_panel_state_correct()

        tag_icon_selector = self.navigation.history_panel.selectors.tag_icon
        annotation_icon_selector = self.navigation.history_panel.selectors.annotation_icon

        self.wait_for_visible(tag_icon_selector)
        self.wait_for_visible(annotation_icon_selector)

        name_element = self.history_panel_name_element()
        self.assert_tooltip_text(name_element, self.navigation.history_panel.text.tooltip_name)

    @selenium_test
    def test_history_panel_rename(self):
        editable_text_input_element = self.history_panel_click_to_rename()
        editable_text_input_element.send_keys("New History Name")
        self.send_enter(editable_text_input_element)

        assert "New History Name" in self.history_panel_name()

    @selenium_test
    def test_history_rename_confirm_with_click(self):
        editable_text_input_element = self.history_panel_click_to_rename()
        editable_text_input_element.send_keys("New History Name")
        self.click_center()
        self.assert_absent(self.navigation.history_panel.selectors.name_edit_input)
        assert "New History Name" in self.history_panel_name()

    @selenium_test
    def test_history_rename_cancel_with_escape(self):
        editable_text_input_element = self.history_panel_click_to_rename()
        editable_text_input_element.send_keys("New History Name")
        self.send_escape(editable_text_input_element)
        self.assert_absent(self.navigation.history_panel.selectors.name_edit_input)
        assert "New History Name" not in self.history_panel_name()

    @selenium_test
    def test_history_tags_and_annotations_buttons(self):
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

        def assert_current_annotation(expected, error_message="History annotation",
                                      is_equal=True):
            current_annotation = self.components.history_panel.annotation_editable_text.wait_for_visible()
            error_message += " given: [%s] expected [%s] "
            if is_equal:
                assert current_annotation.text == expected, error_message % (
                    current_annotation.text, expected)
            else:
                assert current_annotation.text != expected, error_message % (
                    current_annotation.text, expected)

        def set_random_annotation(clear_text=True):
            random_annotation = self._get_random_name(prefix="arbitrary_annotation_")
            self.set_history_annotation(random_annotation, clear_text)
            return random_annotation

        # assert that annotation wasn't set before
        self.components.history_panel.annotation_area.assert_absent_or_hidden()

        # assign annotation random text
        initial_annotation = set_random_annotation()
        assert_current_annotation(initial_annotation)

        # change annotation text
        changed_annotation = set_random_annotation()

        assert_current_annotation(initial_annotation, error_message="History annotation was not changed!",
                                  is_equal=False)
        assert_current_annotation(changed_annotation,
                                  error_message="History annotation was changed, but annotation text is wrong!",
                                  is_equal=True)

    @selenium_test
    def test_history_panel_tags_change(self):

        def add_tags(size):
            history_panel_tags = list()

            for i in range(size):
                history_panel_tags.append(self._get_random_name(prefix="arbitrary_tag_%s_") % i)

            self.history_panel_add_tags(history_panel_tags)
            return history_panel_tags

        def assert_current_tags(expected_tags):
            current_tags = self.components.history_panel.tags
            current_tags.wait_for_visible()
            assert [tag.text for tag in
                    current_tags.all()] == expected_tags, "tags [{}] are not the same as expected [{}]".format(current_tags, expected_tags)

        def clear_tags(expected_tags_size):

            close_tag_buttons = self.components.history_panel.tag_close_btn.all()
            current_tags_size = len(close_tag_buttons)

            assert expected_tags_size == current_tags_size, "there are more tags than expected! current {}, expected {}".format(
                current_tags_size, expected_tags_size)
            for close_btn in reversed(close_tag_buttons):
                close_btn.click()
                self.sleep_for(self.wait_types.UX_RENDER)

        tags_size = 5

        self.components.history_panel.tag_area.assert_absent_or_hidden()

        # add new tags to empty tags area
        tags = add_tags(tags_size)
        assert_current_tags(tags)

        # add more tags to non-empty tags area
        tags += add_tags(tags_size)
        assert_current_tags(tags)

        # delete all tags
        expected_tags_len = len(tags)
        clear_tags(expected_tags_len)
        self.components.history_panel.tags.assert_absent_or_hidden()

    @selenium_test
    def test_refresh_preserves_state(self):
        self.perform_upload(self.get_filename("1.txt"))
        self.wait_for_history()

        # Open the details, verify they are open and do a refresh.
        self.history_panel_ensure_showing_item_details(hid=1)
        self.history_panel_item_body_component(1, wait=True)
        self.history_panel_refresh_click()

        # After the refresh, verify the details are still open.
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.wait_for_selector_clickable(self.history_panel_item_selector(hid=1))
        assert self.history_panel_item_showing_details(hid=1)

        # Close the detailed display, refresh, and ensure they are still closed.
        self.history_panel_click_item_title(hid=1, wait=True)
        assert not self.history_panel_item_showing_details(hid=1)
        self.history_panel_refresh_click()
        self.sleep_for(self.wait_types.UX_TRANSITION)
        self.wait_for_selector_clickable(self.history_panel_item_selector(hid=1))
        assert not self.history_panel_item_showing_details(hid=1)
