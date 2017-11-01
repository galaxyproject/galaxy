import unittest

from .framework import selenium_test, SeleniumTestCase


class ToolDescribingToursTestCase(SeleniumTestCase):
    """
    export GALAXY_CONFIG_OVERRIDE_WEBHOOKS_DIR=$GALAXY_DIRECTORY/config/plugins/webhooks/demo
    """

    def setUp(self):
        super(ToolDescribingToursTestCase, self).setUp()
        self.home()

    @selenium_test
    def test_generate_tour(self):
        """ Ensure generate a tour behaves correctly. """
        self._ensure_tdt_available()

        self.wait_for_and_click_selector('#title_textutil a')
        self.tool_open('Cut1')

        # Run Tour generation
        self.wait_for_and_click_selector('#options .dropdown-toggle')
        self.click_label('Generate Tour')
        self.history_panel_wait_for_hid_ok(1)

        tour_popup_selector = '#step-0.popover.tour-tour'
        self.wait_for_selector_visible(tour_popup_selector)
        self.assert_selector(tour_popup_selector)

        # Run tool
        self.tool_execute()
        self.history_panel_wait_for_hid_ok(2)

    def _ensure_tdt_available(self):
        """ Skip a test if the webhook TDT doesn't appear. """
        response = self.api_get('webhooks/tool-menu/all', raw=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        webhooks = [x['name'] for x in data]
        if 'tour_generator' not in webhooks:
            raise unittest.SkipTest('Skipping test, webhook "Tool-Describing-Tours" doesn\'t appear to be configured.')
