from galaxy_test.base.api_asserts import assert_status_code_is
from .framework import (
    managed_history,
    selenium_test,
    SeleniumTestCase,
)

COLUMN_DEFINITIONS = [
    {"type": "int", "name": "replicate", "default_value": 0, "optional": False},
    {"type": "string", "name": "treatment", "default_value": "control", "optional": False},
]


class TestCollectionSheet(SeleniumTestCase):
    ensure_registered = True

    @selenium_test
    @managed_history
    def test_view_sample_sheet(self):
        response = self.dataset_collection_populator.create_sample_sheet(
            self.current_history_id(),
            contents=[("sample1", "1 2 3"), ("sample2", "4 5 6")],
            column_definitions=COLUMN_DEFINITIONS,
            rows={"sample1": [1, "treated"], "sample2": [2, "control"]},
        )
        assert_status_code_is(response, 200)

        self.go_to_collection_sheet(response.json()["id"])

        sheet = self.components.collection_sheet
        expected_rows = [("sample1", "1", "treated"), ("sample2", "2", "control")]
        for row_index, expected_row in enumerate(expected_rows):
            row = tuple(
                sheet.grid_cell(row_index=row_index, column_name=column_name).wait_for_text()
                for column_name in ("__model_object", "replicate", "treatment")
            )
            assert row == expected_row
        self.screenshot("collection_sheet_view")

    @selenium_test
    def test_view_sample_sheet_load_error(self):
        self.go_to_collection_sheet("badbadbadbadbad1")

        sheet = self.components.collection_sheet
        sheet.error.wait_for_visible()
        sheet.loading.assert_absent()
