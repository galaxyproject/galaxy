from typing import (
    List,
    Optional,
)
from xmlrpc.client import boolean

from sqlalchemy import false

from galaxy import model
from galaxy.exceptions import ObjectNotFound
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.fields import DecodedDatabaseIdField


class NotificationManager:
    """Interface/service object shared by controllers for interacting with notifications."""

    def __init__(self, sa_session: galaxy_scoped_session):
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

    def create(self, message_text: str):
        """
        Creates a new notification.
        """
        notification = model.Notification(message_text=message_text)
        self.sa_session.add(notification)
        self.sa_session.flush()
        return notification

    def show(self, notification_id):
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
        return notification

    def update_status(self, user_id, notification_id, status_seen: boolean):
        """
        Modifies a notification status.
        """
        user = self.sa_session.query(model.User).get(user_id)
        notification = self.sa_session.query(model.Notification).get(notification_id)
        if notification is None:
            raise ObjectNotFound(f"Notification with id {notification_id} was not found.")
        notification.status_seen = status_seen
        self.sa_session.add(notification)
        self.sa_session.flush()
        return notification

    def associate_user_notification(self, user_ids: List[DecodedDatabaseIdField], notification: model.Notification):
        assoc_ids = []
        for user_id in user_ids:
            user = self.sa_session.query(model.User).get(user_id)
            assoc = model.UserNotificationAssociation(user, notification)
            assoc.user_id = user.id
            assoc.notification_id = notification.id
            assoc_ids.append(assoc.id)
            self.sa_session.add(assoc)
        self.sa_session.flush()
        return assoc_ids