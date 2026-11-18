"""API tests for admin visualization management endpoints."""

from galaxy_test.base.api_asserts import (
    assert_has_keys,
    assert_status_code_is,
)
from galaxy_test.base.decorators import requires_admin
from ._framework import ApiTestCase


class TestAdminVisualizationsApi(ApiTestCase):
    @requires_admin
    def test_index(self):
        response = self._get("admin/plugins", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert isinstance(data, list)

    @requires_admin
    def test_index_non_admin_rejected(self):
        response = self._get("admin/plugins")
        assert_status_code_is(response, 403)

    @requires_admin
    def test_available_non_admin_rejected(self):
        response = self._get("admin/plugins/available")
        assert_status_code_is(response, 403)

    @requires_admin
    def test_install_rejects_invalid_package(self):
        response = self._post(
            "admin/plugins",
            data={"package": "../not-a-package", "version": "1.2.3"},
            admin=True,
            json=True,
        )
        assert_status_code_is(response, 400)
        response = self._get("admin/plugins/api_install_test_viz", admin=True)
        assert_status_code_is(response, 404)

    @requires_admin
    def test_install_takes_the_id_from_the_package(self):
        response = self._post(
            "admin/plugins",
            data={"package": "@galaxyproject/api.install.test", "version": "1.2.3"},
            admin=True,
            json=True,
        )
        # a dotted name can't be a visualization id, so this is refused before npm is ever run
        assert_status_code_is(response, 400)
        response = self._get("admin/plugins", admin=True)
        assert all(viz["package"] != "@galaxyproject/api.install.test" for viz in response.json())

    @requires_admin
    def test_show_nonexistent(self):
        response = self._get("admin/plugins/nonexistent_viz_id_12345", admin=True)
        assert_status_code_is(response, 404)

    @requires_admin
    def test_uninstall_nonexistent(self):
        response = self._delete("admin/plugins/nonexistent_viz_id_12345", admin=True)
        assert_status_code_is(response, 404)

    @requires_admin
    def test_toggle_nonexistent(self):
        response = self._put(
            "admin/plugins/nonexistent_viz_id_12345/toggle",
            data={"enabled": False},
            admin=True,
            json=True,
        )
        assert_status_code_is(response, 404)

    @requires_admin
    def test_reload_registry(self):
        response = self._post("admin/plugins/reload", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert_has_keys(data, "message")

    def test_runtime_static_file_for_unknown_plugin_is_404(self):
        response = self._get("plugins/nonexistent_viz_id_12345/static/index.js")
        assert_status_code_is(response, 404)

    @requires_admin
    def test_all_admin_endpoints_reject_non_admin(self):
        """Every admin visualization route, the ones that change things included, requires an admin."""
        body = {"package": "@galaxyproject/circster", "version": "1.0.0", "enabled": False}
        requests = {
            "GET admin/plugins": lambda: self._get("admin/plugins"),
            "GET available": lambda: self._get("admin/plugins/available"),
            "GET versions": lambda: self._get("admin/plugins/versions/@galaxyproject/circster"),
            "POST reload": lambda: self._post("admin/plugins/reload"),
            "GET show": lambda: self._get("admin/plugins/circster"),
            "POST install": lambda: self._post("admin/plugins", data=body, json=True),
            "PUT update": lambda: self._put("admin/plugins/circster/update", data=body, json=True),
            "DELETE uninstall": lambda: self._delete("admin/plugins/circster"),
            "PUT toggle": lambda: self._put("admin/plugins/circster/toggle", data=body, json=True),
        }
        for name, request in requests.items():
            assert_status_code_is(request(), 403, f"{name} should require admin")
