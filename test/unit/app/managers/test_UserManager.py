"""
User Manager testing.

Executable directly using: python -m test.unit.managers.test_UserManager
"""

from datetime import datetime
from unittest.mock import patch

from sqlalchemy import (
    desc,
    select,
)

from galaxy import (
    exceptions,
    model,
)
from galaxy.managers import (
    base as base_manager,
    histories,
    users,
)
from galaxy.security.passwords import check_password
from .base import BaseTestCase

# =============================================================================
default_password = "123456"
changed_password = "654321"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)
user3_data = dict(email="user3@user3.user3", username="user3", password=default_password)
user4_data = dict(email="user4@user4.user4", username="user4", password=default_password)
uppercase_email_user = dict(email="USER5@USER5.USER5", username="USER5", password=default_password)
lowercase_email_user = dict(email="user5@user5.user5", username="user5", password=default_password)


# =============================================================================
class TestUserManager(BaseTestCase):
    def test_framework(self):
        self.log("(for testing) should have admin_user, and admin_user is current")
        assert self.trans.user == self.admin_user

    def test_base(self):
        self.log("should be able to create a user")
        user2 = self.user_manager.create(**user2_data)
        assert isinstance(user2, model.User)
        assert user2.id is not None
        assert user2.email == user2_data["email"]
        assert check_password(default_password, user2.password)

        user3 = self.user_manager.create(**user3_data)

        self.log("should be able to query")
        users = self.trans.sa_session.scalars(select(model.User)).all()
        assert self.user_manager.list() == users

        assert self.user_manager.by_id(user2.id) == user2
        assert self.user_manager.by_ids([user3.id, user2.id]) == [user3, user2]

        self.log("should be able to limit and offset")
        assert self.user_manager.list(limit=1) == users[0:1]
        assert self.user_manager.list(offset=1) == users[1:]
        assert self.user_manager.list(limit=1, offset=1) == users[1:2]

        assert self.user_manager.list(limit=0) == []
        assert self.user_manager.list(offset=3) == []

        self.log("should be able to order")
        assert self.user_manager.list(order_by=(desc(model.User.create_time))) == [user3, user2, self.admin_user]

    def test_invalid_create(self):
        self.user_manager.create(**user2_data)

        self.log("emails must be unique")
        with self.assertRaises(exceptions.Conflict):
            self.user_manager.create(
                **dict(email="user2@user2.user2", username="user2a", password=default_password),
            )
        self.log("usernames must be unique")
        with self.assertRaises(exceptions.Conflict):
            self.user_manager.create(
                **dict(email="user2a@user2.user2", username="user2", password=default_password),
            )

    def test_trimming(self):
        self.log("emails must be trimmed")
        user2b, message = self.user_manager.register(
            self.trans,
            email=" user2b@user2.user2 ",
            username="user2b",
            password=default_password,
            confirm=default_password,
        )
        assert message is None
        assert user2b.email == "user2b@user2.user2"
        self.log("usernames must be trimmed")
        user2c, message = self.user_manager.register(
            self.trans,
            email="user2c@user2.user2",
            username=" user2c ",
            password=default_password,
            confirm=default_password,
        )
        assert message is None
        assert user2c.username == "user2c"

    def test_email_queries(self):
        user2 = self.user_manager.create(**user2_data)

        self.log("should be able to query by email")
        assert self.user_manager.by_email(user2_data["email"]) == user2

    def test_admin(self):
        user2 = self.user_manager.create(**user2_data)

        self.log("should be able to test whether admin")
        assert self.user_manager.is_admin(self.admin_user)
        assert not self.user_manager.is_admin(user2)
        assert self.user_manager.admins() == [self.admin_user]
        with self.assertRaises(exceptions.AdminRequiredException):
            self.user_manager.error_unless_admin(user2)
        assert self.user_manager.error_unless_admin(self.admin_user) == self.admin_user

    def test_anonymous(self):
        anon = None
        user2 = self.user_manager.create(**user2_data)

        self.log("should be able to tell if a user is anonymous")
        with self.assertRaises(exceptions.AuthenticationFailed):
            self.user_manager.error_if_anonymous(anon)
        assert self.user_manager.error_if_anonymous(user2) == user2

    def test_current(self):
        user2 = self.user_manager.create(**user2_data)

        self.log("should be able to tell if a user is the current (trans) user")
        assert self.user_manager.current_user(self.trans) == self.admin_user
        assert self.user_manager.current_user(self.trans) != user2

    def test_change_password(self):
        self.log("should be able to change password")
        user2 = self.user_manager.create(**user2_data)
        encoded_id = self.app.security.encode_id(user2.id)
        assert isinstance(user2, model.User)
        assert user2.id is not None
        assert user2.email == user2_data["email"]
        assert check_password(default_password, user2.password)
        user, message = self.user_manager.change_password(self.trans)
        assert message == "Please provide a token or a user and password."
        user, message = self.user_manager.change_password(self.trans, id=encoded_id, current=changed_password)
        assert message == "Invalid current password."
        user, message = self.user_manager.change_password(
            self.trans, id=encoded_id, current=default_password, password=changed_password, confirm=default_password
        )
        assert message == "Passwords do not match."
        user, message = self.user_manager.change_password(
            self.trans, id=encoded_id, current=default_password, password=default_password, confirm=changed_password
        )
        assert message == "Passwords do not match."
        user, message = self.user_manager.change_password(
            self.trans, id=encoded_id, current=default_password, password=changed_password, confirm=changed_password
        )
        assert not check_password(default_password, user2.password)
        assert check_password(changed_password, user2.password)
        reset_user, prt = self.user_manager.get_reset_token(self.trans, user2.email)
        user, message = self.user_manager.change_password(
            self.trans, token=prt.token, password=default_password, confirm=default_password
        )
        assert check_password(default_password, user2.password)
        assert not check_password(changed_password, user2.password)
        prt.expiration_time = datetime.utcnow()
        user, message = self.user_manager.change_password(
            self.trans, token=prt.token, password=default_password, confirm=default_password
        )
        assert message == "Invalid or expired password reset token, please request a new one."

    def test_login(self):
        self.log("should be able to validate user credentials")
        user2 = self.user_manager.create(**user2_data)
        self.app.security.encode_id(user2.id)
        assert isinstance(user2, model.User)
        assert user2.id is not None
        assert user2.email == user2_data["email"]
        assert check_password(default_password, user2.password)

    def test_empty_password(self):
        self.log("should be able to create a user with no password")
        user = self.user_manager.create(email="user@nopassword.com", username="nopassword")
        assert user.id is not None
        assert user.password is not None
        # should not be able to login with a null or empty password
        assert not check_password("", user.password)
        assert not check_password(None, user.password)

    def test_activation_email(self):
        self.log("should produce the activation email")
        self.user_manager.create(email="user@nopassword.com", username="nopassword")

        def validate_send_email(frm, to, subject, body, config, html=None):
            assert frm == "email_from"
            assert to == "user@nopassword.com"
            assert subject == "Galaxy Account Activation"
            assert "custom_activation_email_message" in body
            assert "Hello nopassword" in body
            assert (
                "{'activation_token': 'activation_token', 'email': Markup('user@nopassword.com'), 'qualified': True}"
                in body
            )

        with patch("galaxy.util.send_mail", side_effect=validate_send_email) as mock_send_mail:
            with patch("galaxy.util.hash_util.new_secure_hash_v2", return_value="activation_token") as mock_hash_util:
                result = self.user_manager.send_activation_email(self.trans, "user@nopassword.com", "nopassword")
                mock_send_mail.assert_called_once()
                mock_hash_util.assert_called_once()
        assert result is True

    def test_reset_email(self):
        self.log("should produce the password reset email")
        self.user_manager.create(email="user@nopassword.com", username="nopassword")

        def validate_send_email(frm, to, subject, body, config, html=None):
            assert frm == "email_from"
            assert to == "user@nopassword.com"
            assert subject == "Galaxy Password Reset"
            assert "reset your Galaxy password" in body
            assert "{'token': 'reset_token'}" in body

        with patch("galaxy.util.send_mail", side_effect=validate_send_email) as mock_send_mail:
            with patch("galaxy.model.unique_id", return_value="reset_token") as mock_unique_id:
                result = self.user_manager.send_reset_email(self.trans, dict(email="user@nopassword.com"))
                mock_send_mail.assert_called_once()
                mock_unique_id.assert_called_once()
        assert result is None

    def test_reset_email_user_deleted(self):
        self.trans.app.config.allow_user_deletion = True
        self.log("should not produce the password reset email if user is deleted")
        user_email = "user@nopassword.com"
        user = self.user_manager.create(email=user_email, username="nopassword")
        self.user_manager.delete(user)
        assert user.deleted is True
        message = self.user_manager.send_reset_email(self.trans, {"email": user_email})
        assert message is None

    def test_get_user_by_identity(self):
        # return None if username/email not found
        assert self.user_manager.get_user_by_identity("xyz") is None
        uppercase_user = self.user_manager.create(**uppercase_email_user)
        assert uppercase_user.email == uppercase_email_user["email"]
        assert uppercase_user.username == uppercase_email_user["username"]
        assert self.user_manager.get_user_by_identity(uppercase_user.email) == uppercase_user
        assert self.user_manager.get_user_by_identity(uppercase_user.username) == uppercase_user
        # Create another user with the same email just differently capitalized.
        # This is not normally allowed now, since registration goes through user_manager.register(),
        # which checks for that, but was possible in earlier releases of Galaxy
        lowercase_user = self.user_manager.create(**lowercase_email_user)
        assert lowercase_user.email == lowercase_email_user["email"]
        assert lowercase_user.username == lowercase_email_user["username"]
        assert self.user_manager.get_user_by_identity(lowercase_user.email) == lowercase_user
        assert self.user_manager.get_user_by_identity(lowercase_user.username) == lowercase_user
        # assert uppercase user can still be retrieved
        assert self.user_manager.get_user_by_identity(uppercase_user.email) == uppercase_user
        assert self.user_manager.get_user_by_identity(uppercase_user.username) == uppercase_user
        # username matches need to be exact
        assert self.user_manager.get_user_by_identity(uppercase_user.username.capitalize()) is None
        # email matches can ignore capitalization
        ignore_email_capitalization_user = self.user_manager.create(
            email="user123@nopassword.com", username="someusername123"
        )
        assert (
            self.user_manager.get_user_by_identity(ignore_email_capitalization_user.email.capitalize())
            == ignore_email_capitalization_user
        )


# =============================================================================
class TestUserSerializer(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.user_serializer = users.UserSerializer(self.app)

    def test_views(self):
        user = self.user_manager.create(**user2_data)

        self.log("should have a summary view")
        summary_view = self.user_serializer.serialize_to_view(user, view="summary")
        self.assertKeys(summary_view, self.user_serializer.views["summary"])

        self.log("should have the summary view as default view")
        default_view = self.user_serializer.serialize_to_view(user, default_view="summary")
        self.assertKeys(default_view, self.user_serializer.views["summary"])

        self.log("should have a serializer for all serializable keys")
        for key in self.user_serializer.serializable_keyset:
            instantiated_attribute = getattr(user, key, None)
            assert key in self.user_serializer.serializers or isinstance(
                instantiated_attribute, self.TYPES_NEEDING_NO_SERIALIZERS
            ), f"No serializer for: {key} ({instantiated_attribute})"

    def test_views_and_keys(self):
        user = self.user_manager.create(**user2_data)

        self.log("should be able to use keys with views")
        serialized = self.user_serializer.serialize_to_view(user, view="summary", keys=["create_time"])
        self.assertKeys(serialized, self.user_serializer.views["summary"] + ["create_time"])

        self.log("should be able to use keys on their own")
        serialized = self.user_serializer.serialize_to_view(user, keys=["tags_used", "is_admin"])
        self.assertKeys(serialized, ["tags_used", "is_admin"])

    def test_serializers(self):
        user = self.user_manager.create(**user2_data)
        all_keys = list(self.user_serializer.serializable_keyset)
        serialized = self.user_serializer.serialize(user, all_keys, trans=self.trans)
        # pprint.pprint( serialized )

        self.log("everything serialized should be of the proper type")
        self.assertEncodedId(serialized["id"])
        self.assertDate(serialized["create_time"])
        self.assertDate(serialized["update_time"])
        assert isinstance(serialized["deleted"], bool)
        assert isinstance(serialized["purged"], bool)

        # assert isinstance(serialized['active'], bool)
        assert isinstance(serialized["is_admin"], bool)
        assert isinstance(serialized["total_disk_usage"], float)
        assert isinstance(serialized["nice_total_disk_usage"], str)
        assert isinstance(serialized["quota_percent"], (type(None), float))
        assert isinstance(serialized["tags_used"], list)

        self.log("serialized should jsonify well")
        self.assertIsJsonifyable(serialized)


class TestCurrentUserSerializer(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.history_manager = self.app[histories.HistoryManager]
        self.user_serializer = users.CurrentUserSerializer(self.app)

    def test_anonymous(self):
        anonym = None
        # need a history here for total_disk_usage
        self.trans.set_history(self.history_manager.create())

        self.log("should be able to serialize anonymous user")
        serialized = self.user_serializer.serialize_to_view(anonym, view="detailed", trans=self.trans)
        self.assertKeys(serialized, ["id", "total_disk_usage", "nice_total_disk_usage", "quota_percent"])

        self.log("anonymous's id should be None")
        assert serialized["id"] is None
        self.log("everything serialized should be of the proper type")
        assert isinstance(serialized["total_disk_usage"], float)
        assert isinstance(serialized["nice_total_disk_usage"], str)
        assert isinstance(serialized["quota_percent"], (type(None), float))

        self.log("serialized should jsonify well")
        self.assertIsJsonifyable(serialized)


# =============================================================================
class TestUserDeserializer(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.deserializer = users.UserDeserializer(self.app)

    def _assertRaises_and_return_raised(self, exception_class, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except exception_class as exception:
            return exception
        raise AssertionError(f"{exception_class.__name__} not raised")

    def test_username_validation(self):
        user = self.user_manager.create(**user2_data)

        # self.log( "usernames can be unicode" ) #TODO: nope they can't
        # self.deserializer.deserialize( user, { 'username': 'Σίσυφος' }, trans=self.trans )

        self.log("usernames must be long enough and with no non-hyphen punctuation")
        exception = self._assertRaises_and_return_raised(
            base_manager.ModelDeserializingError,
            self.deserializer.deserialize,
            user,
            {"username": ""},
            trans=self.trans,
        )
        assert "Public name cannot be empty" in str(exception)
        with self.assertRaises(base_manager.ModelDeserializingError):
            self.deserializer.deserialize(
                user,
                {"username": "f,d,r,"},
                trans=self.trans,
            )

        self.log("usernames must be unique")
        self.user_manager.create(**user3_data)
        with self.assertRaises(base_manager.ModelDeserializingError):
            self.deserializer.deserialize(
                user,
                {"username": "user3"},
                trans=self.trans,
            )

        self.log("username should be updatable")
        new_name = "double-plus-good"
        self.deserializer.deserialize(user, {"username": new_name}, trans=self.trans)
        assert self.user_manager.by_id(user.id).username == new_name


# =============================================================================
class TestAdminUserFilterParser(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.filter_parser = users.AdminUserFilterParser(self.app)

    def test_parsable(self):
        self.log("the following filters should be parsable")
        self.assertORMFilter(self.filter_parser.parse_filter("email", "eq", "wot"))
        self.assertORMFilter(self.filter_parser.parse_filter("email", "contains", "wot"))
        self.assertORMFilter(self.filter_parser.parse_filter("email", "like", "wot"))
        self.assertORMFilter(self.filter_parser.parse_filter("username", "eq", "wot"))
        self.assertORMFilter(self.filter_parser.parse_filter("username", "contains", "wot"))
        self.assertORMFilter(self.filter_parser.parse_filter("username", "like", "wot"))
        self.assertORMFilter(self.filter_parser.parse_filter("active", "eq", True))
        self.assertORMFilter(self.filter_parser.parse_filter("disk_usage", "le", 500000.00))
        self.assertORMFilter(self.filter_parser.parse_filter("disk_usage", "ge", 500000.00))
