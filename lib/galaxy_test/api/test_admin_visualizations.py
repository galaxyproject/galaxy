"""API tests for admin visualization management endpoints."""

from unittest.mock import patch

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
    def test_available(self):
        response = self._get("admin/visualizations/available", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert isinstance(data, list)

    @requires_admin
    def test_available_non_admin_rejected(self):
        response = self._get("admin/visualizations/available")
        assert_status_code_is(response, 403)

    @requires_admin
    @patch("galaxy.managers.visualization_admin.VisualizationPackageManager.install_npm_package")
    def test_install(self, mock_install):
        viz_id = "api_install_test_viz"
        mock_install.return_value = {
            "package": "@galaxyproject/api-install-test-viz",
            "version": "1.2.3",
            "size": 123,
        }
        response = self._post(
            f"admin/visualizations/{viz_id}/install",
            data={"package": "@galaxyproject/api-install-test-viz", "version": "1.2.3"},
            admin=True,
            json=True,
        )
        assert_status_code_is(response, 201)
        data = response.json()
        assert_has_keys(data, "id", "package", "version", "installed", "message")

    @requires_admin
    @patch("galaxy.managers.visualization_admin.VisualizationPackageManager.get_package_versions")
    def test_package_versions(self, mock_versions):
        mock_versions.return_value = ["2.0.0", "1.0.0"]
        response = self._get("admin/visualizations/versions/@galaxyproject/circster", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert_has_keys(data, "package", "versions")
        assert data["versions"] == ["2.0.0", "1.0.0"]

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

    @requires_admin
    def test_usage_stats(self):
        response = self._get("admin/visualizations/usage_stats", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert_has_keys(data, "message", "days", "stats")

    @requires_admin
    def test_staging_status(self):
        response = self._get("admin/visualizations/staging_status", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert_has_keys(data, "staged_count", "staged_visualizations", "total_size")

    @requires_admin
    def test_stage_all(self):
        response = self._post("admin/visualizations/stage", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert_has_keys(data, "message", "staged_count", "staged_visualizations")

    @requires_admin
    def test_clean_staged(self):
        response = self._delete("admin/visualizations/staged", admin=True)
        assert_status_code_is(response, 200)
        data = response.json()
        assert_has_keys(data, "message", "cleaned_count")

    @requires_admin
    def test_stage_nonexistent(self):
        response = self._post("admin/visualizations/nonexistent_viz_id_12345/stage", admin=True)
        assert_status_code_is(response, 404)

    @requires_admin
    def test_all_admin_endpoints_reject_non_admin(self):
        """Verify all endpoints require admin access."""
        endpoints = [
            ("GET", "admin/visualizations"),
            ("GET", "admin/visualizations/available"),
            ("GET", "admin/visualizations/usage_stats"),
            ("GET", "admin/visualizations/staging_status"),
            ("POST", "admin/visualizations/reload"),
            ("POST", "admin/visualizations/stage"),
            ("DELETE", "admin/visualizations/staged"),
        ]
        for method, path in endpoints:
            if method == "GET":
                response = self._get(path)
            elif method == "POST":
                response = self._post(path)
            elif method == "DELETE":
                response = self._delete(path)
            assert_status_code_is(response, 403, f"{method} {path} should require admin")
