"""
Admin API for visualization package management.

Provides endpoints for Galaxy administrators to manage visualization packages
dynamically without requiring client rebuilds.
"""

import logging
from typing import (
    Annotated,
)

from fastapi import (
    Path,
    Query,
    status,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.visualization_admin import (
    AvailableVisualizationListResponse,
    InstalledVisualizationListResponse,
    InstalledVisualizationResponse,
    InstallVisualizationRequest,
    MessageResponse,
    PackageVersionsResponse,
    ToggleVisualizationRequest,
    ToggleVisualizationResponse,
    UpdateVisualizationRequest,
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
        search: str | None = Query(
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
    ) -> None:
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
