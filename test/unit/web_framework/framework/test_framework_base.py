from galaxy.web.framework.base import WebApplication


class TestWebapp(WebApplication):
    def assert_maps(self, url, method="GET", **parts):
        map_result = self.mapper.match(url, environ={"REQUEST_METHOD": method})
        for key, expected_value in parts.items():
            actual_value = map_result[key]
            if actual_value != expected_value:
                message = "Problem mapping route [%s], part %s expected value [%s] but obtained [%s]"
                raise AssertionError(message % (url, key, expected_value, actual_value))


def test_add_route():
    test_webapp = TestWebapp()
    test_webapp.add_route("/authnz/", controller="authnz", action="index", provider=None)
    test_webapp.assert_maps("/authnz/", controller="authnz", action="index")
