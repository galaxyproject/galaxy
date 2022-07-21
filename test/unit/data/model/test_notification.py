import random

import pytest

from galaxy.managers.notification import NotificationManager
from galaxy.model import User
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.model.unittest_utils import GalaxyDataTestApp


@pytest.fixture
def sa_session():
    random.seed(43)
    app = GalaxyDataTestApp()
    return app.model.session


def create_notification_mananger(sa_session: galaxy_scoped_session):
    notificationManager = NotificationManager(sa_session)
    return notificationManager


def test_update_notification(sa_session: galaxy_scoped_session):
    notificationManager = create_notification_mananger(sa_session)
    notification = notificationManager.create(message="New notification")
    updated_message = "Updated notification"
    notificationManager.update(notification, updated_message)
    assert notification.message_text == updated_message


def create_user(sa_session: galaxy_scoped_session):
    random_number = random.randint(0, 1000)
    user = User(
        email="test" + str(random_number) + "@test.com",
        password="abcde",
        username="notification_user" + str(random_number),
    )
    sa_session.add(user)
    sa_session.flush()
    assert user.id is not None
    return user


def create_user_notification_association(sa_session: galaxy_scoped_session, users, notification):
    notificationManager = create_notification_mananger(sa_session)
    notificationManager.associate_user_notification(users, notification)


def test_create_notification(sa_session: galaxy_scoped_session):
    notificationManager = create_notification_mananger(sa_session)
    notification = notificationManager.create(message="New notification")
    user = create_user(sa_session)
    create_user_notification_association(sa_session, [user], notification)
    assert user.all_notifications is not None
    # test backref from Notifcation to UserNotificationAssociation
    assert notification.user_notification_associations is not None
