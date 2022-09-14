import json
from datetime import (
    datetime,
    timedelta,
)
from unittest import TestCase

from galaxy import model
from galaxy.app_unittest_utils import galaxy_mock
from galaxy.managers.users import UserManager
from galaxy.security.passwords import check_password
from galaxy.webapps.galaxy.controllers.user import User

admin_email = "admin@admin.admin"
admin_users = admin_email
default_password = "123456"
changed_password = "654321"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)


class LoginControllerTestCase(TestCase):
    def setUp(self):
        admin_users_list = [u for u in admin_users.split(",") if u]
        self.trans = galaxy_mock.MockTrans(admin_users=admin_users, admin_users_list=admin_users_list)
        self.app = self.trans.app

        self.user_manager = self.app[UserManager]

        self.admin_user = self.user_manager.create(email=admin_email, username="admin", password=default_password)
        self.trans.set_user(self.admin_user)
        self.trans.set_history(None)

    def test_login(self):
        user2 = self.user_manager.create(**user2_data)
        self.app.security.encode_id(user2.id)
        self.assertIsInstance(user2, model.User)
        self.assertIsNotNone(user2.id)
        self.assertEqual(user2.email, user2_data["email"])
        self.assertTrue(check_password(default_password, user2.password))

        controller = User(self.app)
        response = json.loads(controller.login(self.trans))
        self.assertEqual(response["err_msg"], "Please specify a username and password.")
        response = json.loads(
            controller.login(self.trans, payload={"login": user2.email, "password": changed_password})
        )
        self.assertEqual(response["err_msg"], "Invalid password.")
        response = json.loads(
            controller.login(self.trans, payload={"login": user2.username, "password": changed_password})
        )
        self.assertEqual(response["err_msg"], "Invalid password.")
        user2.deleted = True
        response = json.loads(
            controller.login(self.trans, payload={"login": user2.username, "password": default_password})
        )
        self.assertEqual(
            response["err_msg"],
            "This account has been marked deleted, contact your local Galaxy administrator to restore the account. Contact: admin@email.to.",
        )
        user2.deleted = False
        user2.external = True
        response = json.loads(
            controller.login(self.trans, payload={"login": user2.username, "password": default_password})
        )
        self.assertEqual(
            response["err_msg"],
            "This account was created for use with an external authentication method, contact your local Galaxy administrator to activate it. Contact: admin@email.to.",
        )
        user2.external = False
        self.trans.app.config.password_expiration_period = timedelta(days=1)
        user2.last_password_change = datetime.today() - timedelta(days=1)
        response = json.loads(
            controller.login(self.trans, payload={"login": user2.username, "password": default_password})
        )
        self.assertEqual(response["message"], "Your password has expired. Please reset or change it to access Galaxy.")
        self.assertEqual(response["expired_user"], self.trans.security.encode_id(user2.id))
        self.trans.app.config.password_expiration_period = timedelta(days=10)
        response = json.loads(
            controller.login(self.trans, payload={"login": user2.username, "password": default_password})
        )
        self.assertEqual(response["message"], "Your password will expire in 11 day(s).")
        self.trans.app.config.password_expiration_period = timedelta(days=100)
        response = json.loads(
            controller.login(self.trans, payload={"login": user2.username, "password": default_password})
        )
        self.assertEqual(response["message"], "Success.")
