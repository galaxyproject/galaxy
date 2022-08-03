from typing import (
    List,
    Optional,
)

from sqlalchemy import false

from galaxy import model
from galaxy.exceptions import ObjectNotFound
from galaxy.managers.context import ProvidesAppContext
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.structured_app import MinimalManagerApp


class NotificationManager:
    """Interface/service object shared by controllers for interacting with notifications."""

    def __init__(self, app: MinimalManagerApp, sa_session: galaxy_scoped_session):
        self._app = app
        self.sa_session = sa_session

    def index(self, limit: int = 10, offset: int = 0, user: Optional[model.User] = None):
        """
        Displays a collection (list) of notifications.
        """
        rval = []
        for notification in (
            self.sa_session.query(model.Notification)
            .filter(model.Notification.deleted == false())
            .limit(limit)
            .offset(offset)
        ):
            rval.append(notification)
        return rval

    def create(self, trans: ProvidesAppContext, payload: str):
        """
        Creates a new notification.
        """
        notification = model.Notification(message_text=payload)
        self.sa_session.add(notification)
        self.sa_session.flush()
        return notification

    def show(self, trans, notification_id):
        """
        Displays information about a notification.
        """
        notification = self.sa_session.query(model.Notification).get(notification_id)
        if notification is None:
            raise ObjectNotFound(f"Notification with id {notification_id} was not found.")
        return notification

    def update(self, notification_id, updated_message: str):
        """
        Modifies a notification.
        """
        notification = self.sa_session.query(model.Notification).get(notification_id)
        if notification is None:
            raise ObjectNotFound(f"Notification with id {notification_id} was not found.")
        notification.message_text = updated_message
        self.sa_session.add(notification)
        self.sa_session.flush()

    def associate_user_notification(self, users: List[model.User], notification: model.Notification):
        for user in users:
            assoc = model.UserNotificationAssociation(user, notification)
            assoc.user_id = user.id
            assoc.notification_id = notification.id
            self.sa_session.add(assoc)
        self.sa_session.flush()
