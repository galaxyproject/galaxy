import unittest

from .framework import selenium_test, SeleniumTestCase


class ToolDescribingToursTestCase(SeleniumTestCase):

    def setUp(self):
        super(ToolDescribingToursTestCase, self).setUp()
        self.home()

    @selenium_test
    def test_generate_tour_no_data(self):
        """Ensure a tour without data is generated and pops up."""
        self._ensure_tdt_available()

        self.tool_open('environment_variables')

        self.tool_form_generate_tour()

        popover_component = self.components.tour.popover._
        popover_component.wait_for_visible()

        title = popover_component.title.wait_for_visible().text
        assert title == "environment_variables Tour", title

        # Run tool
        self.tool_form_execute()
        self.history_panel_wait_for_hid_ok(1)

    @selenium_test
    def test_generate_tour_with_data(self):
        """Ensure a tour with data populates history."""
        self._ensure_tdt_available()

        self.tool_open('md5sum')

        self.tool_form_generate_tour()

        self.history_panel_wait_for_hid_ok(1)

        popover_component = self.components.tour.popover._
        popover_component.wait_for_visible()

        title = popover_component.title.wait_for_visible().text
        assert title == "md5sum Tour", title
        self.screenshot("tool_describing_tour_0_start")

        popover_component.next.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)

        text = popover_component.content.wait_for_visible().text
        assert "Select dataset" in text, text
        self.screenshot("tool_describing_tour_1_select")

        popover_component.next.wait_for_and_click()

        self.sleep_for(self.wait_types.UX_RENDER)

        title = popover_component.title.wait_for_visible().text
        assert title == "Execute tool"
        self.screenshot("tool_describing_tour_2_execute")

        popover_component.end.wait_for_and_click()
        popover_component.wait_for_absent_or_hidden()

        # Run tool
        self.tool_form_execute()
        self.history_panel_wait_for_hid_ok(2)
        self.screenshot("tool_describing_tour_3_after_execute")

    def _ensure_tdt_available(self):
        """ Skip a test if the webhook TDT doesn't appear. """
        response = self.api_get('webhooks', raw=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        webhooks = [x['id'] for x in data]
        if 'tour_generator' not in webhooks:
            raise unittest.SkipTest('Skipping test, webhook "Tool-Describing-Tours" doesn\'t appear to be configured.')
