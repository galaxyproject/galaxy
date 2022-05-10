from galaxy.web.framework.base import WebApplication


class MockWebApplication(WebApplication):
    def assert_maps(self, url, method="GET", **parts):
        map_result = self.mapper.match(url, environ={"REQUEST_METHOD": method})
        for key, expected_value in parts.items():
            actual_value = map_result[key]
            assert (
                actual_value == expected_value
            ), f"Problem mapping route [{url}], part {key} expected value [{expected_value}] but obtained [{actual_value}]"


def test_add_route():
    test_webapp = MockWebApplication()
    test_webapp.add_route("/authnz/", controller="authnz", action="index", provider=None)
    test_webapp.assert_maps("/authnz/", controller="authnz", action="index")
