"""
Admin API for visualization package management.

Provides endpoints for Galaxy administrators to manage visualization packages
dynamically without requiring client rebuilds.
"""

import logging
from typing import (
    Annotated,
    Optional,
)

from fastapi import (
    Path,
    Query,
    status,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.visualization_admin import (
    AvailableVisualizationListResponse,
    CleanStagingResultResponse,
    InstalledVisualizationListResponse,
    InstalledVisualizationResponse,
    InstallVisualizationRequest,
    MessageResponse,
    PackageVersionsResponse,
    StagingResultResponse,
    StagingStatusResponse,
    ToggleVisualizationRequest,
    ToggleVisualizationResponse,
    UpdateVisualizationRequest,
    UsageStatsResponse,
    VisualizationStagingResultResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.admin_visualizations import (
    AdminVisualizationsService,
)

log = logging.getLogger(__name__)

router = Router(tags=["admin_visualizations"])

VisualizationIdPathParam = Annotated[
    str,
    Path(
        ...,
        title="Visualization ID",
        description="The identifier of the visualization package.",
    ),
]


@router.cbv
class FastAPIAdminVisualizations:
    service: AdminVisualizationsService = depends(AdminVisualizationsService)

    # --- Static-segment routes (must be declared before {viz_id} routes) ---

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
    ) -> InstalledVisualizationListResponse:
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
            default=None,
            title="Search term",
            description="Filter available packages by name or description.",
        ),
    ) -> AvailableVisualizationListResponse:
        """Return a list of available @galaxyproject visualization packages from npm registry."""
        return self.service.get_available_packages(trans, search=search)

    @router.get(
        "/api/admin/visualizations/versions/{package_name:path}",
        summary="Get available versions for an npm package.",
        require_admin=True,
    )
    def package_versions(
        self,
        package_name: str = Path(
            ...,
            title="Package Name",
            description="The npm package name (e.g., @galaxyproject/circster).",
        ),
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> PackageVersionsResponse:
        """Return available versions for a specific npm package."""
        return self.service.get_package_versions(trans, package_name)

    @router.get(
        "/api/admin/visualizations/usage_stats",
        summary="Get usage statistics for visualizations.",
        require_admin=True,
    )
    def usage_stats(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        days: int = Query(
            default=30,
            title="Days",
            description="Number of days to look back for usage statistics",
        ),
    ) -> UsageStatsResponse:
        """Return usage statistics for installed visualizations."""
        return self.service.get_usage_stats(trans, days=days)

    @router.get(
        "/api/admin/visualizations/staging_status",
        summary="Get staging status information.",
        require_admin=True,
    )
    def staging_status(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> StagingStatusResponse:
        """Get information about currently staged visualizations."""
        return self.service.get_staging_status(trans)

    @router.post(
        "/api/admin/visualizations/reload",
        summary="Reload the visualization registry.",
        require_admin=True,
    )
    def reload(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> MessageResponse:
        """Reload the visualization registry to pick up configuration changes."""
        return self.service.reload_registry(trans)

    @router.post(
        "/api/admin/visualizations/stage",
        summary="Stage all visualization assets.",
        require_admin=True,
    )
    def stage_all(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> StagingResultResponse:
        """Stage all visualization assets into Galaxy's static serving directory."""
        return self.service.stage_all_visualizations(trans)

    @router.delete(
        "/api/admin/visualizations/staged",
        summary="Clean all staged visualization assets.",
        require_admin=True,
    )
    def clean_staged(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> CleanStagingResultResponse:
        """Clean all staged visualization assets from static/plugins."""
        return self.service.clean_staged_assets(trans)

    # --- Dynamic {viz_id} routes ---

    @router.get(
        "/api/admin/visualizations/{viz_id}",
        summary="Get details for a specific visualization package.",
        require_admin=True,
    )
    def show(
        self,
        viz_id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InstalledVisualizationResponse:
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
        request: InstallVisualizationRequest,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InstalledVisualizationResponse:
        """Install a visualization package from npm registry."""
        return self.service.install_package(trans, viz_id, request.package, request.version)

    @router.put(
        "/api/admin/visualizations/{viz_id}/update",
        summary="Update a visualization package to a new version.",
        require_admin=True,
    )
    def update(
        self,
        viz_id: VisualizationIdPathParam,
        request: UpdateVisualizationRequest,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> InstalledVisualizationResponse:
        """Update an installed visualization package to a new version."""
        return self.service.update_package(trans, viz_id, request.version)

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
        request: ToggleVisualizationRequest,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> ToggleVisualizationResponse:
        """Enable or disable a visualization package without uninstalling it."""
        return self.service.toggle_package(trans, viz_id, request.enabled)

    @router.post(
        "/api/admin/visualizations/{viz_id}/stage",
        summary="Stage assets for a specific visualization.",
        require_admin=True,
    )
    def stage_visualization(
        self,
        viz_id: VisualizationIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> VisualizationStagingResultResponse:
        """Stage assets for a specific visualization into Galaxy's static serving directory."""
        return self.service.stage_visualization(trans, viz_id)
