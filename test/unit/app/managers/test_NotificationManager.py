import random

import pytest

from galaxy.managers.notification import NotificationManager
from galaxy.model import User
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.model.unittest_utils import GalaxyDataTestApp


@pytest.fixture
def sa_session():
    return GalaxyDataTestApp().model.session


@pytest.fixture
def notification_manager(sa_session: galaxy_scoped_session):
    notification_manager = NotificationManager(sa_session)
    return notification_manager


def test_update_notification(notification_manager: NotificationManager):
    notification = notification_manager.create(content="New notification")
    updated_content = "Updated notification"
    notification_manager.update(notification.id, updated_content)
    assert notification.content == updated_content


def create_user(sa_session: galaxy_scoped_session):
    random_number = random.randint(0, 1000)
    user = User(
        email=f"test{random_number}@test.com",
        password="abcde",
        username=f"notification_user{random_number}",
    )
    sa_session.add(user)
    sa_session.flush()
    assert user.id is not None
    return user


def test_create_notification(notification_manager: NotificationManager, sa_session: galaxy_scoped_session):
    notification = notification_manager.create(content="New notification")
    assert notification.id
    assert notification.content == "New notification"


def test_associate_user_notification(notification_manager: NotificationManager, sa_session: galaxy_scoped_session):
    user = create_user(sa_session)
    notification = notification_manager.create(content="New notification")
    notification_manager.associate_user_notification([user.id], notification)
    assert len(user.all_notifications) == 1
    assert len(notification.user_notification_associations) == 1
    for association in notification.user_notification_associations:
        assert association.user_id == user.id
        assert association.notification_id == notification.id
