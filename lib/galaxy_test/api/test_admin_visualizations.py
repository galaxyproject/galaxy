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
        response = self._get("admin/visualizations", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert isinstance(data, list)

    @requires_admin
    def test_index_non_admin_rejected(self):
        response = self._get("admin/visualizations")
        assert_status_code_is(response, 403)

    @requires_admin
    def test_available_non_admin_rejected(self):
        response = self._get("admin/visualizations/available")
        assert_status_code_is(response, 403)

    @requires_admin
    def test_install_rejects_invalid_package(self):
        response = self._post(
            "admin/visualizations/api_install_test_viz/install",
            data={"package": "../not-a-package", "version": "1.2.3"},
            admin=True,
            json=True,
        )
        assert_status_code_is(response, 400)
        response = self._get("admin/visualizations/api_install_test_viz", admin=True)
        assert_status_code_is(response, 404)

    @requires_admin
    def test_show_nonexistent(self):
        response = self._get("admin/visualizations/nonexistent_viz_id_12345", admin=True)
        assert_status_code_is(response, 404)

    @requires_admin
    def test_uninstall_nonexistent(self):
        response = self._delete("admin/visualizations/nonexistent_viz_id_12345", admin=True)
        assert_status_code_is(response, 404)

    @requires_admin
    def test_toggle_nonexistent(self):
        response = self._put(
            "admin/visualizations/nonexistent_viz_id_12345/toggle",
            data={"enabled": False},
            admin=True,
            json=True,
        )
        assert_status_code_is(response, 404)

    @requires_admin
    def test_reload_registry(self):
        response = self._post("admin/visualizations/reload", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert_has_keys(data, "message")

    def test_runtime_static_file_for_unknown_plugin_is_404(self):
        response = self._get("plugins/nonexistent_viz_id_12345/static/index.js")
        assert_status_code_is(response, 404)

    @requires_admin
    def test_all_admin_endpoints_reject_non_admin(self):
        """Verify all endpoints require admin access."""
        endpoints = [
            ("GET", "admin/visualizations"),
            ("GET", "admin/visualizations/available"),
            ("POST", "admin/visualizations/reload"),
        ]
        for method, path in endpoints:
            if method == "GET":
                response = self._get(path)
            elif method == "POST":
                response = self._post(path)
            assert_status_code_is(response, 403, f"{method} {path} should require admin")
