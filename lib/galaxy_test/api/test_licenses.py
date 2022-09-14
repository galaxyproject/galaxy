from ._framework import ApiTestCase


class LicensesApiTestCase(ApiTestCase):
    def test_index(self):
        response = self._get("licenses")
        self._assert_status_code_is(response, 200)

    def test_get_license(self):
        licenseId = "Apache-2.0"
        response = self._get(f"licenses/{licenseId}")
        self._assert_status_code_is(response, 200)
        self._assert_matches_license_id(licenseId, response.json())

    def test_404_on_unknown_license(self):
        licenseId = "unknown"
        response = self._get(f"licenses/{licenseId}")
        self._assert_status_code_is(response, 404)

    def _assert_matches_license_id(self, license_id, json_response):
        self._assert_has_key(json_response, "licenseId")
        assert json_response["licenseId"] == license_id
