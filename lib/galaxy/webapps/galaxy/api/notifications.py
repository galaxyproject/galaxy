"""
API operations on Notification objects.
"""

import logging

from fastapi import Path

from galaxy.managers.notification import NotificationManager
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["notifications"])


@router.cbv
class FastAPIGroupRoles:
    manager: NotificationManager = depends(NotificationManager)

    @router.get("/api/notifications", summary="Displays a collection (list) of notifications.")
    def index(self):
        return self.manager.index(limit=5)

    @router.get(
        "/api/notifications",
        summary="Displays information about a notification.",
    )
    def show(self, notification_id):
        return self.manager.show(notification_id)

    @router.put("/api/notifications", summary="Create a notificaton message")
    def create(self, message):
        return self.manager.create(message)

    @router.put("/api/notifications", summary="Updates a notificaton message")
    def update(self, notification_id, updated_message):
        return self.manager.update(notification_id, updated_message)
