"""Service layer for admin visualization package management."""

from __future__ import annotations

import logging

from galaxy import exceptions
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.visualization_admin import VisualizationPackageManager
from galaxy.schema.visualization_admin import (
    AvailableVisualizationListResponse,
    AvailableVisualizationResponse,
    InstalledVisualizationListResponse,
    InstalledVisualizationResponse,
    MessageResponse,
    PackageVersionsResponse,
    ToggleVisualizationResponse,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.structured_app import StructuredApp
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class AdminVisualizationsService(ServiceBase):
    """Service for managing visualization packages through admin interface."""

    def __init__(
        self,
        security: IdEncodingHelper,
        app: StructuredApp,
        package_manager: VisualizationPackageManager,
    ):
        super().__init__(security)
        self.app = app
        self.package_manager = package_manager

    def index(self, trans: ProvidesUserContext, include_disabled: bool = True) -> InstalledVisualizationListResponse:
        """Return list of installed visualization packages."""
        config = self.package_manager.load_config()
        results = []

        for viz_id, info in config.items():
            is_installed = self.package_manager.is_package_installed(viz_id)
            package = info.get("package", "")
            version = info.get("version", "unknown")
            enabled = info.get("enabled", True)

            if not include_disabled and not enabled:
                continue

            item = InstalledVisualizationResponse(
                id=viz_id,
                package=package,
                version=version,
                enabled=enabled,
                installed=is_installed,
            )

            if is_installed:
                package_path = self.package_manager.get_package_path(viz_id)
                item.path = package_path
                item.size = self.package_manager.get_directory_size(package_path)
                item.metadata = self.package_manager.get_package_metadata(viz_id)

            results.append(item)

        return InstalledVisualizationListResponse(root=results)

    def get_available_packages(
        self, trans: ProvidesUserContext, search: str | None = None
    ) -> AvailableVisualizationListResponse:
        """Get available @galaxyproject visualization packages from npm registry."""
        raw = self.package_manager.query_npm_registry(search)
        return AvailableVisualizationListResponse(root=[AvailableVisualizationResponse(**pkg) for pkg in raw])

    def get_package_versions(self, trans: ProvidesUserContext, package_name: str) -> PackageVersionsResponse:
        versions = self.package_manager.get_package_versions(package_name)
        return PackageVersionsResponse(package=package_name, versions=versions)

    def show(self, trans: ProvidesUserContext, viz_id: str) -> InstalledVisualizationResponse:
        self.package_manager.validate_viz_id(viz_id)
        package_info = self.package_manager.get_package_info(viz_id)

        if not package_info:
            raise exceptions.ObjectNotFound(f"Visualization package '{viz_id}' not found")

        is_installed = self.package_manager.is_package_installed(viz_id)
        result = InstalledVisualizationResponse(
            id=viz_id,
            package=package_info.get("package", ""),
            version=package_info.get("version", "unknown"),
            enabled=package_info.get("enabled", True),
            installed=is_installed,
        )

        if is_installed:
            package_path = self.package_manager.get_package_path(viz_id)
            result.path = package_path
            result.size = self.package_manager.get_directory_size(package_path)
            result.metadata = self.package_manager.get_package_metadata(viz_id)

        return result

    def install_package(
        self, trans: ProvidesUserContext, viz_id: str, package: str, version: str
    ) -> InstalledVisualizationResponse:
        install_result = self.package_manager.install_package(viz_id, package, version)
        self._reload_registry()
        return InstalledVisualizationResponse(
            id=viz_id,
            package=package,
            version=version,
            enabled=True,
            installed=True,
            size=install_result.get("size", 0),
            message="Package installed successfully",
        )

    def update_package(self, trans: ProvidesUserContext, viz_id: str, version: str) -> InstalledVisualizationResponse:
        update_result = self.package_manager.update_package(viz_id, version)
        self._reload_registry()
        return InstalledVisualizationResponse(
            id=viz_id,
            package=update_result["package"],
            version=version,
            enabled=update_result["enabled"],
            installed=True,
            size=update_result.get("size", 0),
            message="Package updated successfully",
        )

    def uninstall_package(self, trans: ProvidesUserContext, viz_id: str) -> None:
        self.package_manager.uninstall_package(viz_id)
        self._reload_registry()

    def toggle_package(self, trans: ProvidesUserContext, viz_id: str, enabled: bool) -> ToggleVisualizationResponse:
        self.package_manager.validate_viz_id(viz_id)
        self.package_manager.toggle_package_enabled(viz_id, enabled)
        self._reload_registry()

        log.info(f"Successfully {'enabled' if enabled else 'disabled'} visualization package {viz_id}")

        return ToggleVisualizationResponse(
            id=viz_id,
            enabled=enabled,
            message=f"Package {'enabled' if enabled else 'disabled'} successfully",
        )

    def reload_registry(self, trans: ProvidesUserContext) -> MessageResponse:
        """Reload the visualization registry in this process and every other Galaxy process."""
        self._reload_registry()
        return MessageResponse(message="Visualization registry reloaded successfully")

    def _reload_registry(self) -> None:
        # Package changes have to reach the registry in every process, not just this one
        self.app.visualizations_registry.reload()
        self.app.queue_worker.send_control_task("reload_visualizations", noop_self=True)
