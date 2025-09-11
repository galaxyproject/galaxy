from galaxy_test.base.populators import skip_without_tool
from ._framework import ApiTestCase


class TestToursApi(ApiTestCase):
    def test_index(self):
        response = self._get("tours")
        self._assert_status_code_is(response, 200)
        tours = response.json()
        tour_keys = (t["id"] for t in tours)
        assert "core.history" in tour_keys
        for tour in tours:
            self._assert_has_keys(tour, "id", "name", "description", "tags")

    def test_show(self):
        response = self._get("tours/core.history")
        self._assert_status_code_is(response, 200)
        tour = response.json()
        self._assert_tour(tour)

    def test_update(self):
        response = self._post("tours/core.history", admin=True)
        self._assert_status_code_is(response, 200)
        tour = response.json()
        self._assert_tour(tour)

    def test_generate_tour_tool_not_found(self):
        response = self._get("tours/generate?tool_id=nonexistent_tool_id&tool_version=1.0")
        self._assert_status_code_is(response, 404)
        assert 'Tool "nonexistent_tool_id" version "1.0" does not exist.' in response.json()["err_msg"]

    @skip_without_tool("cat1")
    def test_generate_tour_for_cat1(self):
        response = self._get("tours/generate?tool_id=cat1&tool_version=1.0.0&performs_upload=false")
        self._assert_status_code_is(response, 200)
        tour = response.json()["tour"]
        self._assert_tour(tour)
        tool_response = self._get("tools/cat1")
        tool_name = tool_response.json()["name"]
        assert tour["name"] == f"{tool_name} Tour"

    def _assert_tour(self, tour):
        self._assert_has_keys(tour, "name", "description", "title_default", "steps")
