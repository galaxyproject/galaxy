"""API for Admin panel extensions."""

from fastapi import (
    Body,
    Path,
)

from galaxy.managers.admin_extensions import AdminExtensionsManager
from galaxy.managers.admin_settings import AdminSettingsManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.admin_extensions import (
    AdminExtension,
    AdminExtensionFormResponse,
    SettingValue,
)
from . import (
    depends,
    DependsOnTrans,
    Router,
)

router = Router(tags=["admin_extensions"])

ExtensionIdPathParam = Path(..., title="Extension ID", description="Identifier of the admin extension.")
ItemIdPathParam = Path(..., title="Item ID", description="Identifier of the item within the extension.")


@router.get("/api/admin/extensions", require_admin=True, summary="List Admin panel extensions")
def index(manager: AdminExtensionsManager = depends(AdminExtensionsManager)) -> list[AdminExtension]:
    """Return every loaded Admin panel extension with its items."""
    return manager.extensions


@router.get(
    "/api/admin/extensions/{extension_id}/items/{item_id}/form",
    require_admin=True,
    summary="Describe a form item with its current values",
)
def show_form(
    extension_id: str = ExtensionIdPathParam,
    item_id: str = ItemIdPathParam,
    extensions: AdminExtensionsManager = depends(AdminExtensionsManager),
    settings: AdminSettingsManager = depends(AdminSettingsManager),
) -> AdminExtensionFormResponse:
    """Return a form item's inputs and current values in the shape the generic form component renders."""
    item = extensions.get_form_item(extension_id, item_id)
    return AdminExtensionFormResponse(title=item.title, message=item.description, inputs=settings.form_inputs(item))


@router.put(
    "/api/admin/extensions/{extension_id}/items/{item_id}/form",
    require_admin=True,
    summary="Save a form item's values",
)
def update_form(
    extension_id: str = ExtensionIdPathParam,
    item_id: str = ItemIdPathParam,
    payload: dict[str, SettingValue] = Body(..., description="Value per input name, as submitted by the form."),
    trans: ProvidesUserContext = DependsOnTrans,
    extensions: AdminExtensionsManager = depends(AdminExtensionsManager),
    settings: AdminSettingsManager = depends(AdminSettingsManager),
) -> AdminExtensionFormResponse:
    """Validate and save submitted values, then return the form with the values as saved."""
    item = extensions.get_form_item(extension_id, item_id)
    settings.update_form_values(item, payload, trans.user)
    return AdminExtensionFormResponse(title=item.title, message="Settings saved.", inputs=settings.form_inputs(item))
