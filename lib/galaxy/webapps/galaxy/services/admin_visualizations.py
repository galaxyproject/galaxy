"""Service layer for admin visualization package management."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile

from galaxy import exceptions
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.visualization_admin import VisualizationPackageManager
from galaxy.schema.visualization_admin import (
    AvailableVisualizationListResponse,
    AvailableVisualizationResponse,
    CleanStagingResultResponse,
    InstalledVisualizationListResponse,
    InstalledVisualizationResponse,
    MessageResponse,
    PackageVersionsResponse,
    StagedVisualizationInfo,
    StagingResultResponse,
    StagingStatusResponse,
    ToggleVisualizationResponse,
    UsageStatsResponse,
    VisualizationStagingResultResponse,
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
        try:
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

        except Exception as e:
            log.error(f"Failed to load visualization packages: {e}")
            raise exceptions.InternalServerError(f"Failed to load visualization packages: {e}")

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
        self.package_manager.validate_viz_id(viz_id)
        if self.package_manager.get_package_info(viz_id) or self.package_manager.is_package_installed(viz_id):
            raise exceptions.Conflict(f"Package '{viz_id}' is already installed")

        target_dir = self.package_manager.get_package_path(viz_id)
        install_result = self.package_manager.install_npm_package(package, version, target_dir)

        self.package_manager.add_package_to_config(viz_id, package, version, enabled=True)

        log.info(f"Successfully installed visualization package {viz_id} ({package}@{version})")

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
        """Safe update: install new version to temp, swap on success, keep old on failure."""
        self.package_manager.validate_viz_id(viz_id)
        current_info = self.show(trans, viz_id)
        package = current_info.package
        target_dir = self.package_manager.get_package_path(viz_id)

        with tempfile.TemporaryDirectory() as staging_dir:
            new_pkg_dir = os.path.join(staging_dir, viz_id)
            try:
                install_result = self.package_manager.install_npm_package(package, version, new_pkg_dir)
            except Exception:
                log.warning(f"Failed to install {package}@{version}, keeping existing version")
                raise

            backup_dir = os.path.join(staging_dir, f"{viz_id}_backup")
            if os.path.exists(target_dir):
                shutil.move(target_dir, backup_dir)

            try:
                shutil.move(new_pkg_dir, target_dir)
            except Exception:
                if os.path.exists(backup_dir):
                    shutil.move(backup_dir, target_dir)
                raise

        self.package_manager.add_package_to_config(viz_id, package, version, enabled=current_info.enabled)

        log.info(f"Successfully updated visualization package {viz_id} to version {version}")

        return InstalledVisualizationResponse(
            id=viz_id,
            package=package,
            version=version,
            enabled=current_info.enabled,
            installed=True,
            size=install_result.get("size", 0),
            message="Package updated successfully",
        )

    def uninstall_package(self, trans: ProvidesUserContext, viz_id: str) -> None:
        self.package_manager.validate_viz_id(viz_id)
        if not self.package_manager.get_package_info(viz_id):
            raise exceptions.ObjectNotFound(f"Package '{viz_id}' not found")

        self.package_manager.remove_package_from_config(viz_id)
        self.package_manager.cleanup_package_files(viz_id)

        log.info(f"Successfully uninstalled visualization package {viz_id}")

    def toggle_package(self, trans: ProvidesUserContext, viz_id: str, enabled: bool) -> ToggleVisualizationResponse:
        self.package_manager.validate_viz_id(viz_id)
        self.package_manager.toggle_package_enabled(viz_id, enabled)

        log.info(f"Successfully {'enabled' if enabled else 'disabled'} visualization package {viz_id}")

        return ToggleVisualizationResponse(
            id=viz_id,
            enabled=enabled,
            message=f"Package {'enabled' if enabled else 'disabled'} successfully",
        )

    def reload_registry(self, trans: ProvidesUserContext) -> MessageResponse:
        """Reload the visualization registry to pick up configuration changes."""
        try:
            if hasattr(self.app, "visualizations_registry"):
                self.app.visualizations_registry.reload()

            return MessageResponse(message="Visualization registry reloaded successfully")

        except Exception as e:
            log.error(f"Failed to reload visualization registry: {e}")
            raise exceptions.InternalServerError(f"Failed to reload registry: {e}")

    def get_usage_stats(self, trans: ProvidesUserContext, days: int = 30) -> UsageStatsResponse:
        """Get usage statistics for visualizations."""
        return UsageStatsResponse(
            message="Usage statistics not yet implemented",
            days=days,
            stats={},
        )

    def stage_all_visualizations(self, trans: ProvidesUserContext) -> StagingResultResponse:
        """Stage all visualization assets from managed and legacy sources to static/plugins."""
        try:
            result = self.package_manager.stage_all_visualizations()

            log.info(f"Staged {result['staged_count']} visualizations")

            return StagingResultResponse(
                message=f"Successfully staged {result['staged_count']} visualizations",
                staged_count=result["staged_count"],
                staged_visualizations=result["staged_visualizations"],
                errors=result.get("errors", []),
            )

        except Exception as e:
            log.error(f"Failed to stage all visualizations: {e}")
            raise exceptions.InternalServerError(f"Failed to stage visualizations: {e}")

    def stage_visualization(self, trans: ProvidesUserContext, viz_id: str) -> VisualizationStagingResultResponse:
        self.package_manager.validate_viz_id(viz_id)
        try:
            result = self.package_manager.stage_visualization(viz_id)

            log.info(f"Staged visualization {viz_id}")

            return VisualizationStagingResultResponse(
                message=f"Successfully staged visualization '{viz_id}'",
                visualization_id=result["visualization_id"],
                source_path=result["source_path"],
                target_path=result["target_path"],
                size=result["size"],
            )

        except exceptions.ObjectNotFound:
            raise
        except Exception as e:
            log.error(f"Failed to stage visualization {viz_id}: {e}")
            raise exceptions.InternalServerError(f"Failed to stage visualization: {e}")

    def clean_staged_assets(self, trans: ProvidesUserContext) -> CleanStagingResultResponse:
        """Clean all staged visualization assets from static/plugins."""
        try:
            result = self.package_manager.clean_staged_assets()

            log.info(f"Cleaned {result['cleaned_count']} staged assets")

            return CleanStagingResultResponse(
                message=f"Successfully cleaned {result['cleaned_count']} staged assets",
                cleaned_count=result["cleaned_count"],
                cleaned_items=result.get("cleaned_items", []),
            )

        except Exception as e:
            log.error(f"Failed to clean staged assets: {e}")
            raise exceptions.InternalServerError(f"Failed to clean staged assets: {e}")

    def get_staging_status(self, trans: ProvidesUserContext) -> StagingStatusResponse:
        """Get information about currently staged visualizations."""
        try:
            result = self.package_manager.get_staging_status()

            return StagingStatusResponse(
                message="Retrieved staging status successfully",
                staged_count=result["staged_count"],
                staged_visualizations=[StagedVisualizationInfo(**viz) for viz in result["staged_visualizations"]],
                total_size=result["total_size"],
            )

        except Exception as e:
            log.error(f"Failed to get staging status: {e}")
            raise exceptions.InternalServerError(f"Failed to get staging status: {e}")
