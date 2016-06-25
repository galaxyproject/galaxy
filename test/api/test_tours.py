from base import api


class TourApiTestCase( api.ApiTestCase ):

    def test_index(self):
        response = self._get( "tours" )
        self._assert_status_code_is( response, 200 )
        tours = response.json()
        tour_keys = map(lambda t: t["id"], tours)
        assert "core.history" in tour_keys

    def test_show(self):
        response = self._get( "tours/core.history" )
        self._assert_status_code_is( response, 200 )
        tour = response.json()
        self._assert_has_keys(tour, "name", "description", "title_default", "steps")
