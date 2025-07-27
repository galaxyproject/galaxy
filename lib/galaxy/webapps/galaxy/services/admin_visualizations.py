"""
Service layer for admin visualization package management.

Provides business logic for managing visualization packages through the admin interface.
"""

import logging
from typing import (
    Dict,
    List,
    Optional,
)

from galaxy import exceptions
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.visualization_admin import VisualizationPackageManager
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

    def index(self, trans: ProvidesUserContext, include_disabled: bool = True) -> List[Dict]:
        """Return list of installed visualization packages."""
        try:
            config = self.package_manager.load_config()
            results = []

            for viz_id, info in config.items():
                is_installed = self.package_manager.is_package_installed(viz_id)

                # Parse config entry
                if isinstance(info, dict):
                    package = info.get("package", "")
                    version = info.get("version", "unknown")
                    enabled = info.get("enabled", True)
                else:
                    package = str(info)
                    version = "unknown"
                    enabled = True

                if not include_disabled and not enabled:
                    continue

                package_info = {
                    "id": viz_id,
                    "package": package,
                    "version": version,
                    "enabled": enabled,
                    "installed": is_installed,
                }

                # Add metadata if installed
                if is_installed:
                    package_path = self.package_manager.get_package_path(viz_id)
                    package_info.update(
                        {
                            "path": package_path,
                            "size": self.package_manager.get_directory_size(package_path),
                            "metadata": self.package_manager.get_package_metadata(viz_id),
                        }
                    )

                results.append(package_info)

            return results

        except Exception as e:
            log.error(f"Failed to load visualization packages: {e}")
            raise exceptions.InternalServerError(f"Failed to load visualization packages: {e}")

    def get_available_packages(self, trans: ProvidesUserContext, search: Optional[str] = None) -> List[Dict]:
        """Get available @galaxyproject visualization packages from npm registry."""
        return self.package_manager.query_npm_registry(search)

    def show(self, trans: ProvidesUserContext, viz_id: str) -> Dict:
        """Get detailed information about a specific visualization package."""
        package_info = self.package_manager.get_package_info(viz_id)

        if not package_info:
            raise exceptions.ObjectNotFound(f"Visualization package '{viz_id}' not found")

        # Build response
        result = {
            "id": viz_id,
            "package": package_info.get("package", "") if isinstance(package_info, dict) else str(package_info),
            "version": package_info.get("version", "unknown") if isinstance(package_info, dict) else "unknown",
            "enabled": package_info.get("enabled", True) if isinstance(package_info, dict) else True,
            "installed": self.package_manager.is_package_installed(viz_id),
        }

        # Add metadata if installed
        if result["installed"]:
            package_path = self.package_manager.get_package_path(viz_id)
            result.update(
                {
                    "path": package_path,
                    "size": self.package_manager.get_directory_size(package_path),
                    "metadata": self.package_manager.get_package_metadata(viz_id),
                }
            )

        return result

    def install_package(self, trans: ProvidesUserContext, viz_id: str, package: str, version: str) -> Dict:
        """Install a visualization package from npm registry."""
        # Check if package already exists
        if self.package_manager.is_package_installed(viz_id):
            raise exceptions.Conflict(f"Package '{viz_id}' is already installed")

        # Install package
        target_dir = self.package_manager.get_package_path(viz_id)
        install_result = self.package_manager.install_npm_package(package, version, target_dir)

        # Update configuration
        self.package_manager.add_package_to_config(viz_id, package, version, enabled=True)

        log.info(f"Successfully installed visualization package {viz_id} ({package}@{version})")

        return {
            "id": viz_id,
            "package": package,
            "version": version,
            "enabled": True,
            "installed": True,
            "size": install_result.get("size", 0),
            "message": "Package installed successfully",
        }

    def update_package(self, trans: ProvidesUserContext, viz_id: str, version: str) -> Dict:
        """Update an existing visualization package to a new version."""
        # Get current package info
        current_info = self.show(trans, viz_id)
        package = current_info["package"]

        # Clean up old files
        self.package_manager.cleanup_package_files(viz_id)

        # Install new version
        target_dir = self.package_manager.get_package_path(viz_id)
        install_result = self.package_manager.install_npm_package(package, version, target_dir)

        # Update configuration
        self.package_manager.add_package_to_config(viz_id, package, version, enabled=current_info["enabled"])

        log.info(f"Successfully updated visualization package {viz_id} to version {version}")

        return {
            "id": viz_id,
            "package": package,
            "version": version,
            "enabled": current_info["enabled"],
            "installed": True,
            "size": install_result.get("size", 0),
            "message": "Package updated successfully",
        }

    def uninstall_package(self, trans: ProvidesUserContext, viz_id: str) -> None:
        """Uninstall a visualization package and clean up its assets."""
        # Verify package exists
        if not self.package_manager.get_package_info(viz_id):
            raise exceptions.ObjectNotFound(f"Package '{viz_id}' not found")

        # Remove from configuration
        self.package_manager.remove_package_from_config(viz_id)

        # Clean up files
        self.package_manager.cleanup_package_files(viz_id)

        log.info(f"Successfully uninstalled visualization package {viz_id}")

    def toggle_package(self, trans: ProvidesUserContext, viz_id: str, enabled: bool) -> Dict:
        """Enable or disable a visualization package."""
        # Update enabled status
        self.package_manager.toggle_package_enabled(viz_id, enabled)

        log.info(f"Successfully {'enabled' if enabled else 'disabled'} visualization package {viz_id}")

        return {
            "id": viz_id,
            "enabled": enabled,
            "message": f"Package {'enabled' if enabled else 'disabled'} successfully",
        }

    def reload_registry(self, trans: ProvidesUserContext) -> Dict:
        """Reload the visualization registry to pick up configuration changes."""
        try:
            # Trigger reload of visualization plugins
            if hasattr(self.app, "visualizations_registry"):
                self.app.visualizations_registry.reload()

            return {"message": "Visualization registry reloaded successfully"}

        except Exception as e:
            log.error(f"Failed to reload visualization registry: {e}")
            raise exceptions.InternalServerError(f"Failed to reload registry: {e}")

    def get_usage_stats(self, trans: ProvidesUserContext, days: int = 30) -> Dict:
        """Get usage statistics for visualizations."""
        # TODO: Implement actual usage tracking
        # For now, return placeholder data
        return {"message": "Usage statistics not yet implemented", "days": days, "stats": {}}

    def stage_all_visualizations(self, trans: ProvidesUserContext) -> Dict:
        """
        Stage all visualization assets from config/plugins to static/plugins.
        This makes visualizations available to Galaxy for serving.
        """
        try:
            result = self.package_manager.stage_all_visualizations()

            log.info(f"Staged {result['staged_count']} visualizations")

            return {
                "message": f"Successfully staged {result['staged_count']} visualizations",
                "staged_count": result["staged_count"],
                "staged_visualizations": result["staged_visualizations"],
                "errors": result.get("errors", []),
            }

        except Exception as e:
            log.error(f"Failed to stage all visualizations: {e}")
            raise exceptions.InternalServerError(f"Failed to stage visualizations: {e}")

    def stage_visualization(self, trans: ProvidesUserContext, viz_id: str) -> Dict:
        """
        Stage assets for a specific visualization from config/plugins to static/plugins.
        """
        try:
            result = self.package_manager.stage_visualization(viz_id)

            log.info(f"Staged visualization {viz_id}")

            return {
                "message": f"Successfully staged visualization '{viz_id}'",
                "visualization_id": result["visualization_id"],
                "source_path": result["source_path"],
                "target_path": result["target_path"],
                "size": result["size"],
            }

        except Exception as e:
            log.error(f"Failed to stage visualization {viz_id}: {e}")
            if "not found" in str(e).lower():
                raise exceptions.ObjectNotFound(f"Visualization '{viz_id}' not found for staging")
            raise exceptions.InternalServerError(f"Failed to stage visualization: {e}")

    def clean_staged_assets(self, trans: ProvidesUserContext) -> Dict:
        """
        Clean all staged visualization assets from static/plugins.
        This removes all visualizations from Galaxy's serving directory.
        """
        try:
            result = self.package_manager.clean_staged_assets()

            log.info(f"Cleaned {result['cleaned_count']} staged assets")

            return {
                "message": f"Successfully cleaned {result['cleaned_count']} staged assets",
                "cleaned_count": result["cleaned_count"],
                "cleaned_items": result.get("cleaned_items", []),
            }

        except Exception as e:
            log.error(f"Failed to clean staged assets: {e}")
            raise exceptions.InternalServerError(f"Failed to clean staged assets: {e}")

    def get_staging_status(self, trans: ProvidesUserContext) -> Dict:
        """
        Get information about currently staged visualizations.
        """
        try:
            result = self.package_manager.get_staging_status()

            return {
                "message": "Retrieved staging status successfully",
                "staged_count": result["staged_count"],
                "staged_visualizations": result["staged_visualizations"],
                "total_size": result["total_size"],
            }

        except Exception as e:
            log.error(f"Failed to get staging status: {e}")
            raise exceptions.InternalServerError(f"Failed to get staging status: {e}")
