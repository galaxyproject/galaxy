from ._framework import ApiTestCase


class TestToursApi(ApiTestCase):
    def test_index(self):
        response = self._get("tours")
        self._assert_status_code_is(response, 200)
        tours = response.json()
        tour_keys = map(lambda t: t["id"], tours)
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

    def _assert_tour(self, tour):
        self._assert_has_keys(tour, "name", "description", "title_default", "steps")
