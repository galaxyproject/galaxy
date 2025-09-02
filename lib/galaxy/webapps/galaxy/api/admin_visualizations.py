"""
Admin API for visualization package management.

Provides endpoints for Galaxy administrators to manage visualization packages
dynamically without requiring client rebuilds.
"""

import logging
from typing import (
    Optional,
)

from fastapi import (
    Body,
    Path,
    Query,
    status,
)
from typing_extensions import Annotated

from galaxy.managers.context import ProvidesUserContext
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.admin_visualizations import AdminVisualizationsService

log = logging.getLogger(__name__)

router = Router(tags=["admin_visualizations"])

VisualizationIdPathParam = Annotated[
    str,
    Path(..., title="Visualization ID", description="The identifier of the visualization package."),
]


@router.cbv
class FastAPIAdminVisualizations:
    service: AdminVisualizationsService = depends(AdminVisualizationsService)

    @router.get(
        "/api/admin/visualizations",
        summary="List all installed visualization packages.",
        require_admin=True,
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        include_disabled: bool = Query(
            default=True,
            title="Include disabled",
            description="Whether to include disabled visualizations in the result.",
        ),
    ):
        """Return a list of all installed visualization packages with their status."""
        return self.service.index(trans, include_disabled=include_disabled)

    @router.get(
        "/api/admin/visualizations/available",
        summary="List available visualization packages from npm registry.",
        require_admin=True,
    )
    def available(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        search: Optional[str] = Query(
            default=None, title="Search term", description="Filter available packages by name or description."
        ),
    ):
        """Return a list of available @galaxyproject visualization packages from npm registry."""
        return self.service.get_available_packages(trans, search=search)

    @router.get(
        "/api/admin/visualizations/{viz_id}",
        summary="Get details for a specific visualization package.",
        require_admin=True,
    )
    def show(
        self,
        viz_id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Return detailed information about a specific visualization package."""
        return self.service.show(trans, viz_id)

    @router.post(
        "/api/admin/visualizations/{viz_id}/install",
        summary="Install a visualization package.",
        require_admin=True,
        status_code=status.HTTP_201_CREATED,
    )
    def install(
        self,
        viz_id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        package: str = Body(..., description="The npm package name"),
        version: str = Body(..., description="The package version to install"),
    ):
        """Install a visualization package from npm registry."""
        return self.service.install_package(trans, viz_id, package, version)

    @router.put(
        "/api/admin/visualizations/{viz_id}/update",
        summary="Update a visualization package to a new version.",
        require_admin=True,
    )
    def update(
        self,
        viz_id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        version: str = Body(..., description="The new version to update to"),
    ):
        """Update an installed visualization package to a new version."""
        return self.service.update_package(trans, viz_id, version)

    @router.delete(
        "/api/admin/visualizations/{viz_id}",
        summary="Uninstall a visualization package.",
        require_admin=True,
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def uninstall(
        self,
        viz_id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Uninstall a visualization package and clean up its assets."""
        self.service.uninstall_package(trans, viz_id)

    @router.put(
        "/api/admin/visualizations/{viz_id}/toggle",
        summary="Enable or disable a visualization package.",
        require_admin=True,
    )
    def toggle(
        self,
        viz_id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        enabled: bool = Body(..., description="Whether to enable or disable the visualization"),
    ):
        """Enable or disable a visualization package without uninstalling it."""
        return self.service.toggle_package(trans, viz_id, enabled)

    @router.post(
        "/api/admin/visualizations/reload",
        summary="Reload the visualization registry.",
        require_admin=True,
    )
    def reload(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Reload the visualization registry to pick up configuration changes."""
        return self.service.reload_registry(trans)

    @router.get(
        "/api/admin/visualizations/usage_stats",
        summary="Get usage statistics for visualizations.",
        require_admin=True,
    )
    def usage_stats(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        days: int = Query(default=30, title="Days", description="Number of days to look back for usage statistics"),
    ):
        """Return usage statistics for installed visualizations."""
        return self.service.get_usage_stats(trans, days=days)

    @router.post(
        "/api/admin/visualizations/stage",
        summary="Stage all visualization assets.",
        require_admin=True,
    )
    def stage_all(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Stage all visualization assets from config/plugins to static/plugins for Galaxy to serve."""
        return self.service.stage_all_visualizations(trans)

    @router.post(
        "/api/admin/visualizations/{viz_id}/stage",
        summary="Stage assets for a specific visualization.",
        require_admin=True,
    )
    def stage_visualization(
        self,
        viz_id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Stage assets for a specific visualization from config/plugins to static/plugins."""
        return self.service.stage_visualization(trans, viz_id)

    @router.delete(
        "/api/admin/visualizations/staged",
        summary="Clean all staged visualization assets.",
        require_admin=True,
    )
    def clean_staged(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Clean all staged visualization assets from static/plugins."""
        return self.service.clean_staged_assets(trans)

    @router.get(
        "/api/admin/visualizations/staging_status",
        summary="Get staging status information.",
        require_admin=True,
    )
    def staging_status(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        """Get information about currently staged visualizations."""
        return self.service.get_staging_status(trans)
