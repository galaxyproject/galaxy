from unittest import mock

import sqlalchemy
from sqlalchemy import select

from galaxy import (
    exceptions,
    model,
)
from galaxy.app_unittest_utils.galaxy_mock import mock_url_builder
from galaxy.managers import hdas
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.histories import HistoryManager
from .base import BaseTestCase

# =============================================================================
default_password = "123456"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)
user3_data = dict(email="user3@user3.user3", username="user3", password=default_password)


# =============================================================================
class HDATestCase(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.hda_manager = self.app[hdas.HDAManager]
        self.history_manager = self.app[HistoryManager]
        self.dataset_manager = self.app[DatasetManager]

    def _create_vanilla_hda(self, user_data=None):
        user_data = user_data or user2_data
        owner = self.user_manager.create(**user_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        return self.hda_manager.create(history=history1, dataset=dataset1)


# =============================================================================
class TestHDAManager(HDATestCase):
    def test_base(self):
        hda_model = model.HistoryDatasetAssociation
        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        hda1 = self.hda_manager.create(history=history1, hid=1)
        hda2 = self.hda_manager.create(history=history1, hid=2)
        hda3 = self.hda_manager.create(history=history1, hid=3)

        self.log("should be able to query")
        hdas = self.trans.sa_session.scalars(select(hda_model)).all()
        assert self.hda_manager.list() == hdas
        assert self.hda_manager.one(filters=(hda_model.id == hda1.id)) == hda1
        assert self.hda_manager.by_id(hda1.id) == hda1
        assert self.hda_manager.by_ids([hda2.id, hda1.id]) == [hda2, hda1]

        self.log("should be able to limit and offset")
        assert self.hda_manager.list(limit=1) == hdas[0:1]
        assert self.hda_manager.list(offset=1) == hdas[1:]
        assert self.hda_manager.list(limit=1, offset=1) == hdas[1:2]

        assert self.hda_manager.list(limit=0) == []
        assert self.hda_manager.list(offset=3) == []

        self.log("should be able to order")
        assert self.hda_manager.list(order_by=sqlalchemy.desc(hda_model.create_time)) == [hda3, hda2, hda1]

    def test_create(self):
        owner = self.user_manager.create(**user2_data)

        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()

        self.log("should be able to create a new HDA with a specified history and dataset")
        hda1 = self.hda_manager.create(history=history1, dataset=dataset1)
        assert isinstance(hda1, model.HistoryDatasetAssociation)
        assert hda1 == self.trans.sa_session.get(model.HistoryDatasetAssociation, hda1.id)
        assert hda1.history == history1
        assert hda1.dataset == dataset1
        assert hda1.hid == 1

        self.log("should be able to create a new HDA with only a specified history and no dataset")
        hda2 = self.hda_manager.create(history=history1)
        assert isinstance(hda2, model.HistoryDatasetAssociation)
        assert isinstance(hda2.dataset, model.Dataset)
        assert hda2.history == history1
        assert hda2.hid == 2

        self.log("should be able to create a new HDA with no history and no dataset")
        hda3 = self.hda_manager.create(hid=None)
        assert isinstance(hda3, model.HistoryDatasetAssociation)
        assert isinstance(hda3.dataset, model.Dataset), "dataset will be auto created"
        assert hda3.history is None, "history will be None"
        assert hda3.hid is None, "should allow setting hid to None (or any other value)"

    def test_hda_annotation(self):
        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        hda1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should be able to set annotation on an hda")
        annotation = "an annotation or анотація"
        self.hda_manager.annotate(hda1, annotation, user=owner)
        assert self.hda_manager.annotation(hda1) == annotation

    def test_copy_from_hda(self):
        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        hda1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should be able to copy an HDA")
        hda2 = self.hda_manager.copy(hda1, history=history1)
        assert isinstance(hda2, model.HistoryDatasetAssociation)
        assert hda2 == self.trans.sa_session.get(model.HistoryDatasetAssociation, hda2.id)
        assert hda2.name == hda1.name
        assert hda2.history == hda1.history
        assert hda2.dataset == hda1.dataset
        assert hda2 != hda1

        self.log("tags should be copied between HDAs")
        tagged = self.hda_manager.create(history=history1, dataset=self.dataset_manager.create())
        tags_to_set = ["tag-one", "tag-two"]
        self.app.tag_handler.add_tags_from_list(owner, tagged, tags_to_set)
        hda2 = self.hda_manager.copy(tagged, history=history1)
        assert tagged.make_tag_string_list() == hda2.make_tag_string_list()

        self.log("annotations should be copied between HDAs")
        annotated = self.hda_manager.create(history=history1, dataset=self.dataset_manager.create())
        annotation = "( ͡° ͜ʖ ͡°)"
        self.hda_manager.annotate(annotated, annotation, user=owner)

        hda3 = self.hda_manager.copy(annotated, history=history1)
        hda3_annotation = self.hda_manager.annotation(hda3)
        assert annotation == hda3_annotation

    def test_delete(self):
        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should be able to delete and undelete an hda")
        assert not item1.deleted
        assert self.hda_manager.delete(item1) == item1
        assert item1.deleted
        assert self.hda_manager.undelete(item1) == item1
        assert not item1.deleted

    def test_purge_allowed(self):
        self.trans.app.config.allow_user_dataset_purge = True

        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should purge an hda if config does allow")
        assert not item1.purged
        self.hda_manager.purge(item1)
        assert item1.deleted
        assert item1.purged

    def test_purge_not_allowed(self):
        self.trans.app.config.allow_user_dataset_purge = False

        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should raise an error when purging an hda if config does not allow")
        assert not item1.purged
        with self.assertRaises(exceptions.ConfigDoesNotAllowException):
            self.hda_manager.purge(item1)
        assert not item1.deleted
        assert not item1.purged

    def test_ownable(self):
        owner = self.user_manager.create(**user2_data)
        non_owner = self.user_manager.create(**user3_data)

        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should be able to poll whether a given user owns an item")
        assert self.hda_manager.is_owner(item1, owner)
        assert not self.hda_manager.is_owner(item1, non_owner)

        self.log("should raise an error when checking ownership with non-owner")
        with self.assertRaises(exceptions.ItemOwnershipException):
            self.hda_manager.error_unless_owner(item1, non_owner)

        self.log("should raise an error when checking ownership with anonymous")
        with self.assertRaises(exceptions.ItemOwnershipException):
            self.hda_manager.error_unless_owner(item1, None)

        self.log("should not raise an error when checking ownership with owner")
        assert self.hda_manager.error_unless_owner(item1, owner) == item1

        self.log("should not raise an error when checking ownership with admin")
        assert self.hda_manager.error_unless_owner(item1, self.admin_user) == item1

    def test_accessible(self):
        owner = self.user_manager.create(**user2_data)
        non_owner = self.user_manager.create(**user3_data)

        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("(by default, dataset permissions are lax) should be accessible to all")

        for user in self.user_manager.list():
            assert self.hda_manager.is_accessible(item1, user)

        self.log("after setting a dataset to private (one user) permissions, access should be allowed for that user")
        # for this test, set restrictive access permissions
        self.dataset_manager.permissions.set_private_to_one_user(dataset1, owner)
        accessible = self.hda_manager.get_accessible(item1.id, owner, current_history=self.trans.history)
        assert accessible == item1

        self.log(
            "after setting a dataset to private (one user) permissions, access should be not allowed for other users"
        )
        with self.assertRaises(exceptions.ItemAccessibilityException):
            self.hda_manager.get_accessible(
                item1.id,
                non_owner,
                current_history=self.trans.history,
            )

        self.log(
            "a copy of a restricted dataset in another users history should be inaccessible even to "
            "the histories owner"
        )
        history2 = self.history_manager.create(name="history2", user=non_owner)
        self.trans.set_history(history2)
        item2 = self.hda_manager.copy(item1, history=history2)
        assert isinstance(item2, model.HistoryDatasetAssociation)
        with self.assertRaises(exceptions.ItemAccessibilityException):
            self.hda_manager.get_accessible(
                item2.id,
                non_owner,
                current_history=self.trans.history,
            )

        self.log("a restricted dataset cannot be accessed by anonymous users")
        anon_user = None
        self.trans.set_user(anon_user)
        history3 = self.history_manager.create(name="anon_history", user=anon_user)
        self.trans.set_history(history3)
        with self.assertRaises(exceptions.ItemAccessibilityException):
            self.hda_manager.get_accessible(
                item1.id,
                anon_user,
                current_history=self.trans.history,
            )

    def test_anon_ownership(self):
        anon_user = None
        self.trans.set_user(anon_user)

        history1 = self.history_manager.create(name="anon_history", user=anon_user)
        self.trans.set_history(history1)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should not raise an error when checking ownership on anonymous' own dataset")
        # need to pass the current history for comparison
        assert self.hda_manager.is_owner(item1, anon_user, current_history=self.trans.history)
        item = self.hda_manager.error_unless_owner(item1, anon_user, current_history=self.trans.history)
        assert item == item1
        item = self.hda_manager.get_owned(item1.id, anon_user, current_history=self.trans.history)
        assert item == item1

        self.log("should raise an error when checking ownership on anonymous' dataset with other user")
        non_owner = self.user_manager.create(**user3_data)
        assert not self.hda_manager.is_owner(item1, non_owner)
        with self.assertRaises(exceptions.ItemOwnershipException):
            self.hda_manager.error_unless_owner(item1, non_owner)
        with self.assertRaises(exceptions.ItemOwnershipException):
            self.hda_manager.get_owned(item1.id, non_owner)

    def test_anon_accessibility(self):
        anon_user = None
        self.trans.set_user(anon_user)

        history1 = self.history_manager.create(name="anon_history", user=anon_user)
        self.trans.set_history(history1)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        # datasets are public by default
        assert self.hda_manager.is_accessible(item1, anon_user)
        # for this test, set restrictive access permissions
        dataset_owner = self.user_manager.create(**user3_data)
        self.dataset_manager.permissions.set_private_to_one_user(dataset1, dataset_owner)

        self.log(
            "anonymous users should not be able to access datasets within their own histories if "
            "permissions do not allow"
        )
        assert not self.hda_manager.is_accessible(item1, anon_user)
        with self.assertRaises(exceptions.ItemAccessibilityException):
            self.hda_manager.error_unless_accessible(item1, anon_user)

        self.log(
            "those users with access permissions should still be allowed access to datasets "
            "within anon users' histories"
        )
        assert self.hda_manager.is_accessible(item1, dataset_owner)

    def test_error_if_uploading(self):
        hda = self._create_vanilla_hda()

        hda.state = model.Dataset.states.OK
        self.log("should not raise an error when calling error_if_uploading and in a non-uploading state")
        assert self.hda_manager.error_if_uploading(hda) == hda

        hda.state = model.Dataset.states.UPLOAD
        self.log("should raise an error when calling error_if_uploading and in the uploading state")
        with self.assertRaises(exceptions.Conflict):
            self.hda_manager.error_if_uploading(hda)

    def test_data_conversion_status(self):
        hda = self._create_vanilla_hda()

        self.log("data conversion status should reflect state")
        assert self.hda_manager.data_conversion_status(None) == hda.conversion_messages.NO_DATA
        hda.state = model.Dataset.states.ERROR
        assert self.hda_manager.data_conversion_status(hda) == hda.conversion_messages.ERROR
        hda.state = model.Dataset.states.QUEUED
        assert self.hda_manager.data_conversion_status(hda) == hda.conversion_messages.PENDING
        hda.state = model.Dataset.states.OK
        assert self.hda_manager.data_conversion_status(hda) is None

    # def test_text_data( self ):


@mock.patch("galaxy.managers.hdas.HDASerializer.url_for", mock_url_builder)
class TestHDASerializer(HDATestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.hda_serializer = hdas.HDASerializer(self.app)

    def test_views(self):
        hda = self._create_vanilla_hda()

        self.log("should have a summary view")
        summary_view = self.hda_serializer.serialize_to_view(hda, view="summary")
        self.assertKeys(summary_view, self.hda_serializer.views["summary"])

        self.log("should have the summary view as default view")
        default_view = self.hda_serializer.serialize_to_view(hda, default_view="summary")
        self.assertKeys(default_view, self.hda_serializer.views["summary"])

        # self.log("should have a detailed view")
        # detailed_view = self.hda_serializer.serialize_to_view(hda, view="detailed")
        # self.assertKeys(detailed_view, self.hda_serializer.views["detailed"])

        # self.log("should have a extended view")
        # extended_view = self.hda_serializer.serialize_to_view(hda, view="extended")
        # self.assertKeys(extended_view, self.hda_serializer.views["extended"])

        self.log("should have a inaccessible view")
        inaccessible_view = self.hda_serializer.serialize_to_view(hda, view="inaccessible")
        self.assertKeys(inaccessible_view, self.hda_serializer.views["inaccessible"])

        # skip metadata for this test
        def is_metadata(key):
            return key == "metadata" or key.startswith("metadata_")

        self.log("should have a serializer for all serializable keys")
        for key in self.hda_serializer.serializable_keyset:
            instantiated_attribute = getattr(hda, key, None)
            assert (
                key in self.hda_serializer.serializers
                or isinstance(instantiated_attribute, self.TYPES_NEEDING_NO_SERIALIZERS)
                or is_metadata(key)
            ), f"No serializer for: {key} ({instantiated_attribute})"

    def test_views_and_keys(self):
        hda = self._create_vanilla_hda()

        self.log("should be able to use keys with views")
        serialized = self.hda_serializer.serialize_to_view(hda, view="summary", keys=["uuid"])
        self.assertKeys(serialized, self.hda_serializer.views["summary"] + ["uuid"])

        self.log("should be able to use keys on their own")
        serialized = self.hda_serializer.serialize_to_view(hda, keys=["file_path"])
        self.assertKeys(serialized, ["file_path"])

    def test_serializers(self):
        hda = self._create_vanilla_hda()
        all_keys = list(self.hda_serializer.serializable_keyset)
        serialized = self.hda_serializer.serialize(hda, all_keys, user=hda.history.user)

        self.log("everything serialized should be of the proper type")
        # base
        self.assertEncodedId(serialized["id"])
        self.assertDate(serialized["create_time"])
        self.assertDate(serialized["update_time"])

        # dataset association
        assert isinstance(serialized["dataset"], dict)
        self.assertEncodedId(serialized["dataset_id"])
        self.assertUUID(serialized["uuid"])
        assert isinstance(serialized["file_name"], str)
        assert isinstance(serialized["extra_files_path"], str)
        assert isinstance(serialized["size"], int)
        assert isinstance(serialized["file_size"], int)
        assert isinstance(serialized["nice_size"], str)
        # TODO: these should be tested w/copy
        assert isinstance(serialized["copied_from_history_dataset_association_id"], int)
        self.assertNullableEncodedId(serialized["copied_from_library_dataset_dataset_association_id"])
        self.assertNullableBasestring(serialized["info"])
        self.assertNullableBasestring(serialized["blurb"])
        self.assertNullableBasestring(serialized["peek"])
        assert isinstance(serialized["meta_files"], list)
        self.assertNullableEncodedId(serialized["parent_id"])
        assert serialized["designation"] is None
        assert isinstance(serialized["genome_build"], str)
        assert isinstance(serialized["data_type"], str)

        # hda
        self.assertEncodedId(serialized["history_id"])
        assert serialized["type_id"] == "dataset-" + serialized["id"]

        assert isinstance(serialized["resubmitted"], bool)
        assert isinstance(serialized["display_apps"], list)
        assert isinstance(serialized["display_types"], list)

        # remapped
        self.assertNullableBasestring(serialized["misc_info"])
        self.assertNullableBasestring(serialized["misc_blurb"])
        self.assertNullableBasestring(serialized["file_ext"])
        self.assertNullableBasestring(serialized["file_path"])

        # identities
        assert serialized["model_class"] == "HistoryDatasetAssociation"
        assert serialized["history_content_type"] == "dataset"
        assert serialized["hda_ldda"] == "hda"
        assert serialized["accessible"] is True
        assert serialized["api_type"] == "file"
        assert serialized["type"] == "file"

        assert isinstance(serialized["url"], str)
        assert isinstance(serialized["urls"], dict)
        assert isinstance(serialized["download_url"], str)

        self.log("serialized should jsonify well")
        self.assertIsJsonifyable(serialized)

    def test_file_name_serializers(self):
        hda = self._create_vanilla_hda()
        owner = hda.user
        keys = ["file_name"]

        self.log("file_name should be included if app configured to do so")
        # this is on by default in galaxy_mock
        assert self.app.config.expose_dataset_path
        # ... so non-admin user CAN get file_name
        serialized = self.hda_serializer.serialize(hda, keys, user=None)
        assert "file_name" in serialized
        serialized = self.hda_serializer.serialize(hda, keys, user=owner)
        assert "file_name" in serialized

        self.log("file_name should be skipped for non-admin when not exposed by config")
        self.app.config.expose_dataset_path = False
        serialized = self.hda_serializer.serialize(hda, keys, user=None)
        assert "file_name" not in serialized
        serialized = self.hda_serializer.serialize(hda, keys, user=owner)
        assert "file_name" not in serialized

        self.log("file_name should be sent for admin in either case")
        serialized = self.hda_serializer.serialize(hda, keys, user=self.admin_user)
        assert "file_name" in serialized
        self.app.config.expose_dataset_path = True
        serialized = self.hda_serializer.serialize(hda, keys, user=self.admin_user)
        assert "file_name" in serialized

    def test_serializing_inaccessible(self):
        owner = self.user_manager.create(**user2_data)
        non_owner = self.user_manager.create(**user3_data)

        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        keys_in_inaccessible_view = self.hda_serializer._view_to_keys("inaccessible")

        self.log("file_name should be included if app configured to do so")
        self.dataset_manager.permissions.set_private_to_one_user(dataset1, owner)
        # request random crap
        serialized = self.hda_serializer.serialize_to_view(item1, view="detailed", keys=["file_path"], user=non_owner)
        assert sorted(keys_in_inaccessible_view) == sorted(serialized.keys())

    # TODO: test extra_files_path as well


# =============================================================================
class TestHDADeserializer(HDATestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.hda_deserializer = hdas.HDADeserializer(self.app)

    def test_deserialize_delete(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing deleted from non-bool")
        assert not hda.deleted
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.hda_deserializer.deserialize(hda, {"deleted": None})
        assert not hda.deleted
        self.log("should be able to deserialize deleted from True")
        self.hda_deserializer.deserialize(hda, {"deleted": True})
        assert hda.deleted
        self.log("should be able to reverse by deserializing deleted from False")
        self.hda_deserializer.deserialize(hda, {"deleted": False})
        assert not hda.deleted

    def test_deserialize_purge(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing purged from non-bool")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.hda_deserializer.deserialize(hda, {"purged": None})
        assert not hda.purged
        self.log("should be able to deserialize purged from True")
        self.hda_deserializer.deserialize(hda, {"purged": True})
        assert hda.purged
        # TODO: should this raise an error?
        self.log("should NOT be able to deserialize purged from False (will remain True)")
        self.hda_deserializer.deserialize(hda, {"purged": False})
        assert hda.purged

    def test_deserialize_visible(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing from non-bool")
        assert hda.visible
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.hda_deserializer.deserialize(hda, {"visible": "None"})
        assert hda.visible
        self.log("should be able to deserialize from False")
        self.hda_deserializer.deserialize(hda, {"visible": False})
        assert not hda.visible
        self.log("should be able to reverse by deserializing from True")
        self.hda_deserializer.deserialize(hda, {"visible": True})
        assert hda.visible

    def test_deserialize_genome_build(self):
        hda = self._create_vanilla_hda()

        assert isinstance(hda.dbkey, str)
        self.log('should deserialize to "?" from None')
        self.hda_deserializer.deserialize(hda, {"genome_build": None})
        assert hda.dbkey == "?"
        self.log("should raise when deserializing from non-string")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.hda_deserializer.deserialize(hda, {"genome_build": 12})
        self.log("should be able to deserialize from unicode")
        date_palm = "نخيل التمر"
        self.hda_deserializer.deserialize(hda, {"genome_build": date_palm})
        assert hda.dbkey == date_palm
        self.log("should be deserializable from empty string")
        self.hda_deserializer.deserialize(hda, {"genome_build": ""})
        assert hda.dbkey == ""

    def test_deserialize_name(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing from non-string")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.hda_deserializer.deserialize(hda, {"name": True})
        self.log("should raise when deserializing from None")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.hda_deserializer.deserialize(hda, {"name": None})
        # self.log( 'should deserialize to empty string from None' )
        # self.hda_deserializer.deserialize( hda, { 'name': None } )
        # assert hda.name == ""
        self.log("should be able to deserialize from unicode")
        olive = "ελιά"
        self.hda_deserializer.deserialize(hda, {"name": olive})
        assert hda.name == olive
        self.log("should be deserializable from empty string")
        self.hda_deserializer.deserialize(hda, {"name": ""})
        assert hda.name == ""

    def test_deserialize_info(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing from non-string")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.hda_deserializer.deserialize(hda, {"info": True})
        self.log("should raise when deserializing from None")
        with self.assertRaises(exceptions.RequestParameterInvalidException):
            self.hda_deserializer.deserialize(hda, {"info": None})
        self.log("should be able to deserialize from unicode")
        rice = "飯"
        self.hda_deserializer.deserialize(hda, {"info": rice})
        assert hda.info == rice
        self.log("should be deserializable from empty string")
        self.hda_deserializer.deserialize(hda, {"info": ""})
        assert hda.info == ""


# =============================================================================
class TestHDAFilterParser(HDATestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.filter_parser = hdas.HDAFilterParser(self.app)

    def test_parsable(self):
        self.log("the following filters should be parsable")
        # base
        self.assertORMFilter(self.filter_parser.parse_filter("id", "in", [1, 2]))
        encoded_id_string = ",".join(self.app.security.encode_id(id_) for id_ in [1, 2])
        self.assertORMFilter(self.filter_parser.parse_filter("encoded_id", "in", encoded_id_string))
        self.assertORMFilter(self.filter_parser.parse_filter("create_time", "le", "2015-03-15"))
        self.assertORMFilter(self.filter_parser.parse_filter("create_time", "ge", "2015-03-15"))
        self.assertORMFilter(self.filter_parser.parse_filter("update_time", "le", "2015-03-15"))
        self.assertORMFilter(self.filter_parser.parse_filter("update_time", "ge", "2015-03-15"))
        # purgable
        self.assertORMFilter(self.filter_parser.parse_filter("deleted", "eq", True))
        self.assertORMFilter(self.filter_parser.parse_filter("purged", "eq", True))
        # dataset asociation
        self.assertORMFilter(self.filter_parser.parse_filter("name", "eq", "wot"))
        self.assertORMFilter(self.filter_parser.parse_filter("name", "contains", "wot"))
        self.assertORMFilter(self.filter_parser.parse_filter("name", "like", "wot"))
        self.assertORMFilter(self.filter_parser.parse_filter("state", "eq", "ok"))
        self.assertORMFilter(self.filter_parser.parse_filter("state", "in", ["queued", "running"]))
        self.assertORMFilter(self.filter_parser.parse_filter("visible", "eq", True))
        # taggable
        self.assertORMFunctionFilter(self.filter_parser.parse_filter("tag", "eq", "wot"))
        self.assertORMFunctionFilter(self.filter_parser.parse_filter("tag", "has", "wot"))
        # genomebuild
        self.assertFnFilter(self.filter_parser.parse_filter("genome_build", "eq", "wot"))
        self.assertFnFilter(self.filter_parser.parse_filter("genome_build", "contains", "wot"))
        # data_type
        self.assertFnFilter(self.filter_parser.parse_filter("data_type", "eq", "wot"))
        self.assertFnFilter(self.filter_parser.parse_filter("data_type", "isinstance", "wot"))
        # annotatable
        self.assertFnFilter(self.filter_parser.parse_filter("annotation", "has", "wot"))


#     def test_genome_build_filters( self ):
#         pass

#     def test_data_type_filters( self ):
#         pass
