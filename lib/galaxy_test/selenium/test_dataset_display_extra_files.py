from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)


class TestDatasetDisplayExtraFiles(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_html_display_extra_files_relative_path(self):
        """Test that HTML datasets with extra files resolve relative paths correctly.

        Regression test for https://github.com/galaxyproject/galaxy/pull/21981.
        Without the trailing slash on the display URL, the browser resolves
        relative paths (like 'image.jpg') against the wrong directory, causing 404s.
        """
        history_id = self.current_history_id()
        run_response = self.dataset_populator.run_tool(
            "html_output_with_extra_files",
            {},
            history_id,
        )
        hda_id = run_response["outputs"][0]["id"]
        self.dataset_populator.wait_for_dataset(history_id, dataset_id=hda_id, assert_ok=True)

        self.navigate_to(self.build_url(f"datasets/{hda_id}/preview"))
        self.wait_for_selector_visible(".dataset-display")
        # Wait for the iframe to be present and loaded
        self.wait_for_selector_visible("iframe#frame")
        self.sleep_for(self.wait_types.UX_RENDER)
        # The critical assertion: verify the display URL has a trailing slash.
        # Without this slash, relative paths like 'image.jpg' in HTML extra files
        # resolve against /datasets/{id}/ instead of /datasets/{id}/display/,
        # causing 404 errors for sub-resources.
        iframe_src = self.execute_script('return document.getElementById("frame").src;')
        assert (
            "/display/" in iframe_src
        ), f"Expected iframe src to contain '/display/' (with trailing slash), got: {iframe_src}"
        # Verify the extra file is actually accessible via the correct relative path.
        # The browser would resolve 'image.jpg' relative to /datasets/{id}/display/
        # which should serve the extra file.
        extra_file_url = iframe_src.split("?")[0] + "image.jpg"
        extra_file_status = self.execute_script(f"""
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '{extra_file_url}', false);
            xhr.send();
            return xhr.status;
            """)
        assert extra_file_status == 200, f"Extra file not accessible at {extra_file_url}, got HTTP {extra_file_status}"
        self.screenshot("dataset_display_extra_files_loaded")
