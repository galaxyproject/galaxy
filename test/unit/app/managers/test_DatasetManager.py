"""
"""

from unittest import mock

import sqlalchemy
from sqlalchemy import select

from galaxy import (
    exceptions,
    model,
)
from galaxy.app_unittest_utils.galaxy_mock import mock_url_builder
from galaxy.managers.base import SkipAttribute
from galaxy.managers.datasets import (
    DatasetManager,
    DatasetSerializer,
)
from galaxy.managers.roles import RoleManager
from .base import BaseTestCase

# =============================================================================
default_password = "123456"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)
user3_data = dict(email="user3@user3.user3", username="user3", password=default_password)


# =============================================================================
class TestDatasetManager(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.dataset_manager = DatasetManager(self.app)

    def create_dataset_with_permissions(self, manage_roles=None, access_roles=None) -> model.Dataset:
        dataset = self.dataset_manager.create(flush=False)
        self.dataset_manager.permissions.set(dataset, manage_roles, access_roles)
        return dataset

    def test_create(self):
        self.log("should be able to create a new Dataset")
        dataset1 = self.dataset_manager.create()
        assert isinstance(dataset1, model.Dataset)
        assert dataset1 == self.trans.sa_session.get(model.Dataset, dataset1.id)

    def test_base(self):
        dataset1 = self.dataset_manager.create()
        dataset2 = self.dataset_manager.create()

        self.log("should be able to query")
        datasets = self.trans.sa_session.scalars(select(model.Dataset)).all()
        assert self.dataset_manager.list() == datasets
        assert self.dataset_manager.one(filters=(model.Dataset.id == dataset1.id)) == dataset1
        assert self.dataset_manager.by_id(dataset1.id) == dataset1
        assert self.dataset_manager.by_ids([dataset2.id, dataset1.id]) == [dataset2, dataset1]

        self.log("should be able to limit and offset")
        assert self.dataset_manager.list(limit=1) == datasets[0:1]
        assert self.dataset_manager.list(offset=1) == datasets[1:]
        assert self.dataset_manager.list(limit=1, offset=1) == datasets[1:2]

        assert self.dataset_manager.list(limit=0) == []
        assert self.dataset_manager.list(offset=3) == []

        self.log("should be able to order")
        assert self.dataset_manager.list(order_by=sqlalchemy.desc(model.Dataset.create_time)) == [dataset2, dataset1]

    def test_delete(self):
        item1 = self.dataset_manager.create()

        self.log("should be able to delete and undelete a dataset")
        assert not item1.deleted
        assert self.dataset_manager.delete(item1) == item1
        assert item1.deleted
        assert self.dataset_manager.undelete(item1) == item1
        assert not item1.deleted

    def test_purge_allowed(self):
        self.trans.app.config.allow_user_dataset_purge = True
        item1 = self.dataset_manager.create()

        self.log("should purge a dataset if config does allow")
        assert not item1.purged
        assert self.dataset_manager.purge(item1) == item1
        assert item1.purged

        self.log("should delete a dataset when purging")
        assert item1.deleted

    def test_purge_not_allowed(self):
        self.trans.app.config.allow_user_dataset_purge = False
        item1 = self.dataset_manager.create()

        self.log("should raise an error when purging a dataset if config does not allow")
        assert not item1.purged
        with self.assertRaises(exceptions.ConfigDoesNotAllowException):
            self.dataset_manager.purge(item1)
        assert not item1.purged

    def test_create_with_no_permissions(self):
        self.log("should be able to create a new Dataset without any permissions")
        dataset = self.dataset_manager.create()

        permissions = self.dataset_manager.permissions.get(dataset)
        assert isinstance(permissions, tuple)
        assert len(permissions) == 2
        manage_permissions, access_permissions = permissions
        assert manage_permissions == []
        assert access_permissions == []

        user3 = self.user_manager.create(**user3_data)
        self.log("a dataset without permissions shouldn't be manageable to just anyone")
        assert not self.dataset_manager.permissions.manage.is_permitted(dataset, user3)
        self.log("a dataset without permissions should be accessible")
        assert self.dataset_manager.permissions.access.is_permitted(dataset, user3)

        self.log("a dataset without permissions should be manageable by an admin")
        assert self.dataset_manager.permissions.manage.is_permitted(dataset, self.admin_user)
        self.log("a dataset without permissions should be accessible by an admin")
        assert self.dataset_manager.permissions.access.is_permitted(dataset, self.admin_user)

        self.log("a dataset without permissions shouldn't be manageable by an anonymous user")
        assert not self.dataset_manager.permissions.manage.is_permitted(dataset, None)
        self.log("a dataset without permissions should be accessible by an anonymous user")
        assert self.dataset_manager.permissions.access.is_permitted(dataset, None)

    def test_create_public_dataset(self):
        self.log(
            "should be able to create a new Dataset and give it some permissions that actually, you know, "
            "might work if there's any justice in this universe"
        )
        owner = self.user_manager.create(**user2_data)
        owner_private_role = self.user_manager.private_role(owner)
        dataset = self.create_dataset_with_permissions(manage_roles=[owner_private_role])

        permissions = self.dataset_manager.permissions.get(dataset)
        assert isinstance(permissions, tuple)
        assert len(permissions) == 2
        manage_permissions, access_permissions = permissions
        assert isinstance(manage_permissions, list)
        assert isinstance(manage_permissions[0], model.DatasetPermissions)
        assert access_permissions == []

        user3 = self.user_manager.create(**user3_data)
        self.log("a public dataset should be manageable to it's owner")
        assert self.dataset_manager.permissions.manage.is_permitted(dataset, owner)
        self.log("a public dataset shouldn't be manageable to just anyone")
        assert not self.dataset_manager.permissions.manage.is_permitted(dataset, user3)
        self.log("a public dataset should be accessible")
        assert self.dataset_manager.permissions.access.is_permitted(dataset, user3)

        self.log("a public dataset should be manageable by an admin")
        assert self.dataset_manager.permissions.manage.is_permitted(dataset, self.admin_user)
        self.log("a public dataset should be accessible by an admin")
        assert self.dataset_manager.permissions.access.is_permitted(dataset, self.admin_user)

        self.log("a public dataset shouldn't be manageable by an anonymous user")
        assert not self.dataset_manager.permissions.manage.is_permitted(dataset, None)
        self.log("a public dataset should be accessible by an anonymous user")
        assert self.dataset_manager.permissions.access.is_permitted(dataset, None)

    def test_create_private_dataset(self):
        self.log("should be able to create a new Dataset and give it private permissions")
        owner = self.user_manager.create(**user2_data)
        owner_private_role = self.user_manager.private_role(owner)
        dataset = self.create_dataset_with_permissions(
            manage_roles=[owner_private_role], access_roles=[owner_private_role]
        )

        permissions = self.dataset_manager.permissions.get(dataset)
        assert isinstance(permissions, tuple)
        assert len(permissions) == 2
        manage_permissions, access_permissions = permissions
        assert isinstance(manage_permissions, list)
        assert isinstance(manage_permissions[0], model.DatasetPermissions)
        assert isinstance(access_permissions, list)
        assert isinstance(access_permissions[0], model.DatasetPermissions)

        self.log("a private dataset should be manageable by it's owner")
        assert self.dataset_manager.permissions.manage.is_permitted(dataset, owner)
        self.log("a private dataset should be accessible to it's owner")
        assert self.dataset_manager.permissions.access.is_permitted(dataset, owner)

        user3 = self.user_manager.create(**user3_data)
        self.log("a private dataset shouldn't be manageable to just anyone")
        assert not self.dataset_manager.permissions.manage.is_permitted(dataset, user3)
        self.log("a private dataset shouldn't be accessible to just anyone")
        assert not self.dataset_manager.permissions.access.is_permitted(dataset, user3)

        self.log("a private dataset should be manageable by an admin")
        assert self.dataset_manager.permissions.manage.is_permitted(dataset, self.admin_user)
        self.log("a private dataset should be accessible by an admin")
        assert self.dataset_manager.permissions.access.is_permitted(dataset, self.admin_user)

        self.log("a private dataset shouldn't be manageable by an anonymous user")
        assert not self.dataset_manager.permissions.manage.is_permitted(dataset, None)
        self.log("a private dataset shouldn't be accessible by an anonymous user")
        assert not self.dataset_manager.permissions.access.is_permitted(dataset, None)


@mock.patch("galaxy.managers.datasets.DatasetSerializer.url_for", mock_url_builder)
class TestDatasetSerializer(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.dataset_manager = DatasetManager(self.app)
        self.dataset_serializer = DatasetSerializer(self.app, self.user_manager)
        self.role_manager = RoleManager(self.app)

    def test_views(self):
        dataset = self.dataset_manager.create()

        self.log("should have a summary view")
        summary_view = self.dataset_serializer.serialize_to_view(dataset, view="summary")
        self.assertKeys(summary_view, self.dataset_serializer.views["summary"])

        self.log("should have the summary view as default view")
        self.dataset_serializer.serialize_to_view(dataset, default_view="summary")
        self.assertKeys(summary_view, self.dataset_serializer.views["summary"])

        self.log("should have a serializer for all serializable keys")
        for key in self.dataset_serializer.serializable_keyset:
            instantiated_attribute = getattr(dataset, key, None)
            assert key in self.dataset_serializer.serializers or isinstance(
                instantiated_attribute, self.TYPES_NEEDING_NO_SERIALIZERS
            ), f"No serializer for: {key} ({instantiated_attribute})"

    def test_views_and_keys(self):
        dataset = self.dataset_manager.create()

        self.log("should be able to use keys with views")
        serialized = self.dataset_serializer.serialize_to_view(
            dataset,
            # file_name is exposed using app.config.expose_dataset_path = True
            view="summary",
            keys=["file_name"],
        )
        self.assertKeys(serialized, self.dataset_serializer.views["summary"] + ["file_name"])

        self.log("should be able to use keys on their own")
        serialized = self.dataset_serializer.serialize_to_view(dataset, keys=["purgable", "file_size"])
        self.assertKeys(serialized, ["purgable", "file_size"])

    def test_serialize_permissions(self):
        dataset = self.dataset_manager.create()
        who_manages = self.user_manager.create(**user2_data)
        self.dataset_manager.permissions.manage.grant(dataset, who_manages)

        self.log("serialized permissions should be returned for the user who can manage and be well formed")
        permissions = self.dataset_serializer.serialize_permissions(dataset, "perms", user=who_manages)
        assert isinstance(permissions, dict)
        self.assertKeys(permissions, ["manage", "access"])
        assert isinstance(permissions["manage"], list)
        assert isinstance(permissions["access"], list)

        manage_perms = permissions["manage"]
        assert len(manage_perms) == 1
        role_id = manage_perms[0]
        self.assertEncodedId(role_id)
        role_id = self.app.security.decode_id(role_id)
        role = self.role_manager.get(self.trans, role_id)
        assert who_manages in [user_role.user for user_role in role.users]

        self.log("permissions should be not returned for non-managing users")
        not_my_supervisor = self.user_manager.create(**user3_data)
        with self.assertRaises(SkipAttribute):
            self.dataset_serializer.serialize_permissions(dataset, "perms", user=not_my_supervisor)

        self.log("permissions should not be returned for anon users")
        with self.assertRaises(SkipAttribute):
            self.dataset_serializer.serialize_permissions(dataset, "perms", user=None)

        self.log("permissions should be returned for admin users")
        permissions = self.dataset_serializer.serialize_permissions(dataset, "perms", user=self.admin_user)
        assert isinstance(permissions, dict)
        self.assertKeys(permissions, ["manage", "access"])

    def test_serializers(self):
        # self.user_manager.create( **user2_data )
        dataset = self.dataset_manager.create(state=model.Dataset.states.NEW)
        all_keys = list(self.dataset_serializer.serializable_keyset)
        serialized = self.dataset_serializer.serialize(dataset, all_keys)

        self.log("everything serialized should be of the proper type")
        self.assertEncodedId(serialized["id"])
        self.assertDate(serialized["create_time"])
        self.assertDate(serialized["update_time"])

        self.assertUUID(serialized["uuid"])
        assert isinstance(serialized["state"], str)
        assert isinstance(serialized["deleted"], bool)
        assert isinstance(serialized["purged"], bool)
        assert isinstance(serialized["purgable"], bool)

        # # TODO: no great way to do these with mocked dataset
        # assert isinstance(serialized["file_size"], int)
        # assert isinstance(serialized["total_size"], int)

        self.log("serialized should jsonify well")
        self.assertIsJsonifyable(serialized)


# =============================================================================
# NOTE: that we test the DatasetAssociation* classes in either test_HDAManager or test_LDAManager
# (as part of those subclasses):
#   DatasetAssociationManager,
#   DatasetAssociationSerializer,
#   DatasetAssociationDeserializer,
#   DatasetAssociationFilterParser
