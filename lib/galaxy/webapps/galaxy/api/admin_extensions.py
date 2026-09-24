"""API for Admin panel extensions."""

from galaxy.managers.admin_extensions import AdminExtensionsManager
from galaxy.schema.admin_extensions import AdminExtension
from . import (
    depends,
    Router,
)

router = Router(tags=["admin_extensions"])


@router.get("/api/admin/extensions", require_admin=True, summary="List Admin panel extensions")
def index(manager: AdminExtensionsManager = depends(AdminExtensionsManager)) -> list[AdminExtension]:
    """Return every loaded Admin panel extension with its items."""
    return manager.extensions
