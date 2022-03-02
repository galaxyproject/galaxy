import unittest
from unittest import mock

import sqlalchemy

from galaxy import (
    exceptions,
    model,
)
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
class HDAManagerTestCase(HDATestCase):
    def test_base(self):
        hda_model = model.HistoryDatasetAssociation
        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        hda1 = self.hda_manager.create(history=history1, hid=1)
        hda2 = self.hda_manager.create(history=history1, hid=2)
        hda3 = self.hda_manager.create(history=history1, hid=3)

        self.log("should be able to query")
        hdas = self.trans.sa_session.query(hda_model).all()
        self.assertEqual(self.hda_manager.list(), hdas)
        self.assertEqual(self.hda_manager.one(filters=(hda_model.id == hda1.id)), hda1)
        self.assertEqual(self.hda_manager.by_id(hda1.id), hda1)
        self.assertEqual(self.hda_manager.by_ids([hda2.id, hda1.id]), [hda2, hda1])

        self.log("should be able to limit and offset")
        self.assertEqual(self.hda_manager.list(limit=1), hdas[0:1])
        self.assertEqual(self.hda_manager.list(offset=1), hdas[1:])
        self.assertEqual(self.hda_manager.list(limit=1, offset=1), hdas[1:2])

        self.assertEqual(self.hda_manager.list(limit=0), [])
        self.assertEqual(self.hda_manager.list(offset=3), [])

        self.log("should be able to order")
        self.assertEqual(self.hda_manager.list(order_by=sqlalchemy.desc(hda_model.create_time)), [hda3, hda2, hda1])

    def test_create(self):
        owner = self.user_manager.create(**user2_data)

        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()

        self.log("should be able to create a new HDA with a specified history and dataset")
        hda1 = self.hda_manager.create(history=history1, dataset=dataset1)
        self.assertIsInstance(hda1, model.HistoryDatasetAssociation)
        self.assertEqual(hda1, self.trans.sa_session.query(model.HistoryDatasetAssociation).get(hda1.id))
        self.assertEqual(hda1.history, history1)
        self.assertEqual(hda1.dataset, dataset1)
        self.assertEqual(hda1.hid, 1)

        self.log("should be able to create a new HDA with only a specified history and no dataset")
        hda2 = self.hda_manager.create(history=history1)
        self.assertIsInstance(hda2, model.HistoryDatasetAssociation)
        self.assertIsInstance(hda2.dataset, model.Dataset)
        self.assertEqual(hda2.history, history1)
        self.assertEqual(hda2.hid, 2)

        self.log("should be able to create a new HDA with no history and no dataset")
        hda3 = self.hda_manager.create(hid=None)
        self.assertIsInstance(hda3, model.HistoryDatasetAssociation)
        self.assertIsInstance(hda3.dataset, model.Dataset, msg="dataset will be auto created")
        self.assertIsNone(hda3.history, msg="history will be None")
        self.assertEqual(hda3.hid, None, msg="should allow setting hid to None (or any other value)")

    def test_hda_tags(self):
        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        hda1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should be able to set tags on an hda")
        tags_to_set = ["tag-one", "tag-two"]
        self.hda_manager.set_tags(hda1, tags_to_set, user=owner)
        tag_str_array = self.hda_manager.get_tags(hda1)
        self.assertEqual(sorted(tags_to_set), sorted(tag_str_array))

    def test_hda_annotation(self):
        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        hda1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should be able to set annotation on an hda")
        annotation = "an annotation or анотація"
        self.hda_manager.annotate(hda1, annotation, user=owner)
        self.assertEqual(self.hda_manager.annotation(hda1), annotation)

    def test_copy_from_hda(self):
        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        hda1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should be able to copy an HDA")
        hda2 = self.hda_manager.copy(hda1, history=history1)
        self.assertIsInstance(hda2, model.HistoryDatasetAssociation)
        self.assertEqual(hda2, self.trans.sa_session.query(model.HistoryDatasetAssociation).get(hda2.id))
        self.assertEqual(hda2.name, hda1.name)
        self.assertEqual(hda2.history, hda1.history)
        self.assertEqual(hda2.dataset, hda1.dataset)
        self.assertNotEqual(hda2, hda1)

        self.log("tags should be copied between HDAs")
        tagged = self.hda_manager.create(history=history1, dataset=self.dataset_manager.create())
        tags_to_set = ["tag-one", "tag-two"]
        self.hda_manager.set_tags(tagged, tags_to_set, user=owner)

        hda2 = self.hda_manager.copy(tagged, history=history1)
        tag_str_array = self.hda_manager.get_tags(hda2)
        self.assertEqual(sorted(tags_to_set), sorted(tag_str_array))

        self.log("annotations should be copied between HDAs")
        annotated = self.hda_manager.create(history=history1, dataset=self.dataset_manager.create())
        annotation = "( ͡° ͜ʖ ͡°)"
        self.hda_manager.annotate(annotated, annotation, user=owner)

        hda3 = self.hda_manager.copy(annotated, history=history1)
        hda3_annotation = self.hda_manager.annotation(hda3)
        self.assertEqual(annotation, hda3_annotation)

    # def test_copy_from_ldda( self ):
    #    owner = self.user_manager.create( self.trans, **user2_data )
    #    history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
    #
    #    self.log( "should be able to copy an HDA" )
    #    hda2 = self.hda_manager.copy_ldda( history1, hda1 )

    def test_delete(self):
        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should be able to delete and undelete an hda")
        self.assertFalse(item1.deleted)
        self.assertEqual(self.hda_manager.delete(item1), item1)
        self.assertTrue(item1.deleted)
        self.assertEqual(self.hda_manager.undelete(item1), item1)
        self.assertFalse(item1.deleted)

    def test_purge_allowed(self):
        self.trans.app.config.allow_user_dataset_purge = True

        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should purge an hda if config does allow")
        self.assertFalse(item1.purged)
        self.hda_manager.purge(item1)
        self.assertTrue(item1.deleted)
        self.assertTrue(item1.purged)

    def test_purge_not_allowed(self):
        self.trans.app.config.allow_user_dataset_purge = False

        owner = self.user_manager.create(**user2_data)
        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history=history1, dataset=dataset1)

        self.log("should raise an error when purging an hda if config does not allow")
        self.assertFalse(item1.purged)
        self.assertRaises(exceptions.ConfigDoesNotAllowException, self.hda_manager.purge, item1)
        self.assertFalse(item1.deleted)
        self.assertFalse(item1.purged)

    def test_ownable(self):
        owner = self.user_manager.create(**user2_data)
        non_owner = self.user_manager.create(**user3_data)

        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history1, dataset1)

        self.log("should be able to poll whether a given user owns an item")
        self.assertTrue(self.hda_manager.is_owner(item1, owner))
        self.assertFalse(self.hda_manager.is_owner(item1, non_owner))

        self.log("should raise an error when checking ownership with non-owner")
        self.assertRaises(exceptions.ItemOwnershipException, self.hda_manager.error_unless_owner, item1, non_owner)

        self.log("should raise an error when checking ownership with anonymous")
        self.assertRaises(exceptions.ItemOwnershipException, self.hda_manager.error_unless_owner, item1, None)

        self.log("should not raise an error when checking ownership with owner")
        self.assertEqual(self.hda_manager.error_unless_owner(item1, owner), item1)

        self.log("should not raise an error when checking ownership with admin")
        self.assertEqual(self.hda_manager.error_unless_owner(item1, self.admin_user), item1)

    def test_accessible(self):
        owner = self.user_manager.create(**user2_data)
        non_owner = self.user_manager.create(**user3_data)

        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history1, dataset1)

        self.log("(by default, dataset permissions are lax) should be accessible to all")

        for user in self.user_manager.list():
            self.assertTrue(self.hda_manager.is_accessible(item1, user))

        self.log("after setting a dataset to private (one user) permissions, access should be allowed for that user")
        # for this test, set restrictive access permissions
        self.dataset_manager.permissions.set_private_to_one_user(dataset1, owner)
        accessible = self.hda_manager.get_accessible(item1.id, owner, current_history=self.trans.history)
        self.assertEqual(accessible, item1)

        self.log(
            "after setting a dataset to private (one user) permissions, "
            + "access should be not allowed for other users"
        )
        self.assertRaises(
            exceptions.ItemAccessibilityException,
            self.hda_manager.get_accessible,
            item1.id,
            non_owner,
            current_history=self.trans.history,
        )

        self.log(
            "a copy of a restricted dataset in another users history should be inaccessible even to "
            + "the histories owner"
        )
        history2 = self.history_manager.create(name="history2", user=non_owner)
        self.trans.set_history(history2)
        item2 = self.hda_manager.copy(item1, history=history2)
        self.assertIsInstance(item2, model.HistoryDatasetAssociation)
        self.assertRaises(
            exceptions.ItemAccessibilityException,
            self.hda_manager.get_accessible,
            item2.id,
            non_owner,
            current_history=self.trans.history,
        )

        self.log("a restricted dataset cannot be accessed by anonymous users")
        anon_user = None
        self.trans.set_user(anon_user)
        history3 = self.history_manager.create(name="anon_history", user=anon_user)
        self.trans.set_history(history3)
        self.assertRaises(
            exceptions.ItemAccessibilityException,
            self.hda_manager.get_accessible,
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
        item1 = self.hda_manager.create(history1, dataset1)

        self.log("should not raise an error when checking ownership on anonymous' own dataset")
        # need to pass the current history for comparison
        self.assertTrue(self.hda_manager.is_owner(item1, anon_user, current_history=self.trans.history))
        item = self.hda_manager.error_unless_owner(item1, anon_user, current_history=self.trans.history)
        self.assertEqual(item, item1)
        item = self.hda_manager.get_owned(item1.id, anon_user, current_history=self.trans.history)
        self.assertEqual(item, item1)

        self.log("should raise an error when checking ownership on anonymous' dataset with other user")
        non_owner = self.user_manager.create(**user3_data)
        self.assertFalse(self.hda_manager.is_owner(item1, non_owner))
        self.assertRaises(exceptions.ItemOwnershipException, self.hda_manager.error_unless_owner, item1, non_owner)
        self.assertRaises(exceptions.ItemOwnershipException, self.hda_manager.get_owned, item1.id, non_owner)

    def test_anon_accessibility(self):
        anon_user = None
        self.trans.set_user(anon_user)

        history1 = self.history_manager.create(name="anon_history", user=anon_user)
        self.trans.set_history(history1)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history1, dataset1)

        # datasets are public by default
        self.assertTrue(self.hda_manager.is_accessible(item1, anon_user))
        # for this test, set restrictive access permissions
        dataset_owner = self.user_manager.create(**user3_data)
        self.dataset_manager.permissions.set_private_to_one_user(dataset1, dataset_owner)

        self.log(
            "anonymous users should not be able to access datasets within their own histories if "
            + "permissions do not allow"
        )
        self.assertFalse(self.hda_manager.is_accessible(item1, anon_user))
        self.assertRaises(
            exceptions.ItemAccessibilityException, self.hda_manager.error_unless_accessible, item1, anon_user
        )

        self.log(
            "those users with access permissions should still be allowed access to datasets "
            + "within anon users' histories"
        )
        self.assertTrue(self.hda_manager.is_accessible(item1, dataset_owner))

    def test_error_if_uploading(self):
        hda = self._create_vanilla_hda()

        hda.state = model.Dataset.states.OK
        self.log("should not raise an error when calling error_if_uploading and in a non-uploading state")
        self.assertEqual(self.hda_manager.error_if_uploading(hda), hda)

        hda.state = model.Dataset.states.UPLOAD
        self.log("should raise an error when calling error_if_uploading and in the uploading state")
        self.assertRaises(exceptions.Conflict, self.hda_manager.error_if_uploading, hda)

    def test_data_conversion_status(self):
        hda = self._create_vanilla_hda()

        self.log("data conversion status should reflect state")
        self.assertEqual(self.hda_manager.data_conversion_status(None), hda.conversion_messages.NO_DATA)
        hda.state = model.Dataset.states.ERROR
        self.assertEqual(self.hda_manager.data_conversion_status(hda), hda.conversion_messages.ERROR)
        hda.state = model.Dataset.states.QUEUED
        self.assertEqual(self.hda_manager.data_conversion_status(hda), hda.conversion_messages.PENDING)
        hda.state = model.Dataset.states.OK
        self.assertEqual(self.hda_manager.data_conversion_status(hda), None)

    # def test_text_data( self ):


# =============================================================================
# web.url_for doesn't work well in the framework
def testable_url_for(*a, **k):
    return f"(fake url): {a}, {k}"


@mock.patch("galaxy.managers.hdas.HDASerializer.url_for", testable_url_for)
class HDASerializerTestCase(HDATestCase):
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

        # self.log( 'should have a detailed view' )
        # detailed_view = self.hda_serializer.serialize_to_view( hda, view='detailed' )
        # self.assertKeys( detailed_view, self.hda_serializer.views[ 'detailed' ] )

        # self.log( 'should have a extended view' )
        # extended_view = self.hda_serializer.serialize_to_view( hda, view='extended' )
        # self.assertKeys( extended_view, self.hda_serializer.views[ 'extended' ] )

        self.log("should have a inaccessible view")
        inaccessible_view = self.hda_serializer.serialize_to_view(hda, view="inaccessible")
        self.assertKeys(inaccessible_view, self.hda_serializer.views["inaccessible"])

        # skip metadata for this test
        def is_metadata(key):
            return key == "metadata" or key.startswith("metadata_")

        self.log("should have a serializer for all serializable keys")
        for key in self.hda_serializer.serializable_keyset:
            instantiated_attribute = getattr(hda, key, None)
            if not (
                (key in self.hda_serializer.serializers)
                or (isinstance(instantiated_attribute, self.TYPES_NEEDING_NO_SERIALIZERS))
                or (is_metadata(key))
            ):
                self.fail(f"no serializer for: {key} ({instantiated_attribute})")
        else:
            self.assertTrue(True, "all serializable keys have a serializer")

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
        self.assertIsInstance(serialized["dataset"], dict)
        self.assertEncodedId(serialized["dataset_id"])
        self.assertUUID(serialized["uuid"])
        self.assertIsInstance(serialized["file_name"], str)
        self.assertIsInstance(serialized["extra_files_path"], str)
        self.assertIsInstance(serialized["size"], int)
        self.assertIsInstance(serialized["file_size"], int)
        self.assertIsInstance(serialized["nice_size"], str)
        # TODO: these should be tested w/copy
        self.assertNullableEncodedId(serialized["copied_from_history_dataset_association_id"])
        self.assertNullableEncodedId(serialized["copied_from_library_dataset_dataset_association_id"])
        self.assertNullableBasestring(serialized["info"])
        self.assertNullableBasestring(serialized["blurb"])
        self.assertNullableBasestring(serialized["peek"])
        self.assertIsInstance(serialized["meta_files"], list)
        self.assertNullableEncodedId(serialized["parent_id"])
        self.assertEqual(serialized["designation"], None)
        self.assertIsInstance(serialized["genome_build"], str)
        self.assertIsInstance(serialized["data_type"], str)

        # hda
        self.assertEncodedId(serialized["history_id"])
        self.assertEqual(serialized["type_id"], "dataset-" + serialized["id"])

        self.assertIsInstance(serialized["resubmitted"], bool)
        self.assertIsInstance(serialized["display_apps"], list)
        self.assertIsInstance(serialized["display_types"], list)

        # remapped
        self.assertNullableBasestring(serialized["misc_info"])
        self.assertNullableBasestring(serialized["misc_blurb"])
        self.assertNullableBasestring(serialized["file_ext"])
        self.assertNullableBasestring(serialized["file_path"])

        # identities
        self.assertEqual(serialized["model_class"], "HistoryDatasetAssociation")
        self.assertEqual(serialized["history_content_type"], "dataset")
        self.assertEqual(serialized["hda_ldda"], "hda")
        self.assertEqual(serialized["accessible"], True)
        self.assertEqual(serialized["api_type"], "file")
        self.assertEqual(serialized["type"], "file")

        self.assertIsInstance(serialized["url"], str)
        self.assertIsInstance(serialized["urls"], dict)
        self.assertIsInstance(serialized["download_url"], str)

        self.log("serialized should jsonify well")
        self.assertIsJsonifyable(serialized)

    def test_file_name_serializers(self):
        hda = self._create_vanilla_hda()
        owner = hda.history.user
        keys = ["file_name"]

        self.log("file_name should be included if app configured to do so")
        # this is on by default in galaxy_mock
        self.assertTrue(self.app.config.expose_dataset_path)
        # ... so non-admin user CAN get file_name
        serialized = self.hda_serializer.serialize(hda, keys, user=None)
        self.assertTrue("file_name" in serialized)
        serialized = self.hda_serializer.serialize(hda, keys, user=owner)
        self.assertTrue("file_name" in serialized)

        self.log("file_name should be skipped for non-admin when not exposed by config")
        self.app.config.expose_dataset_path = False
        serialized = self.hda_serializer.serialize(hda, keys, user=None)
        self.assertFalse("file_name" in serialized)
        serialized = self.hda_serializer.serialize(hda, keys, user=owner)
        self.assertFalse("file_name" in serialized)

        self.log("file_name should be sent for admin in either case")
        serialized = self.hda_serializer.serialize(hda, keys, user=self.admin_user)
        self.assertTrue("file_name" in serialized)
        self.app.config.expose_dataset_path = True
        serialized = self.hda_serializer.serialize(hda, keys, user=self.admin_user)
        self.assertTrue("file_name" in serialized)

    def test_serializing_inaccessible(self):
        owner = self.user_manager.create(**user2_data)
        non_owner = self.user_manager.create(**user3_data)

        history1 = self.history_manager.create(name="history1", user=owner)
        dataset1 = self.dataset_manager.create()
        item1 = self.hda_manager.create(history1, dataset1)

        keys_in_inaccessible_view = self.hda_serializer._view_to_keys("inaccessible")

        self.log("file_name should be included if app configured to do so")
        self.dataset_manager.permissions.set_private_to_one_user(dataset1, owner)
        # request random crap
        serialized = self.hda_serializer.serialize_to_view(item1, view="detailed", keys=["file_path"], user=non_owner)
        self.assertEqual(sorted(keys_in_inaccessible_view), sorted(serialized.keys()))

    # TODO: test extra_files_path as well


# =============================================================================
class HDADeserializerTestCase(HDATestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.hda_deserializer = hdas.HDADeserializer(self.app)

    def test_deserialize_delete(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing deleted from non-bool")
        self.assertFalse(hda.deleted)
        self.assertRaises(
            exceptions.RequestParameterInvalidException, self.hda_deserializer.deserialize, hda, {"deleted": None}
        )
        self.assertFalse(hda.deleted)
        self.log("should be able to deserialize deleted from True")
        self.hda_deserializer.deserialize(hda, {"deleted": True})
        self.assertTrue(hda.deleted)
        self.log("should be able to reverse by deserializing deleted from False")
        self.hda_deserializer.deserialize(hda, {"deleted": False})
        self.assertFalse(hda.deleted)

    def test_deserialize_purge(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing purged from non-bool")
        self.assertRaises(
            exceptions.RequestParameterInvalidException, self.hda_deserializer.deserialize, hda, {"purged": None}
        )
        self.assertFalse(hda.purged)
        self.log("should be able to deserialize purged from True")
        self.hda_deserializer.deserialize(hda, {"purged": True})
        self.assertTrue(hda.purged)
        # TODO: should this raise an error?
        self.log("should NOT be able to deserialize purged from False (will remain True)")
        self.hda_deserializer.deserialize(hda, {"purged": False})
        self.assertTrue(hda.purged)

    def test_deserialize_visible(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing from non-bool")
        self.assertTrue(hda.visible)
        self.assertRaises(
            exceptions.RequestParameterInvalidException, self.hda_deserializer.deserialize, hda, {"visible": "None"}
        )
        self.assertTrue(hda.visible)
        self.log("should be able to deserialize from False")
        self.hda_deserializer.deserialize(hda, {"visible": False})
        self.assertFalse(hda.visible)
        self.log("should be able to reverse by deserializing from True")
        self.hda_deserializer.deserialize(hda, {"visible": True})
        self.assertTrue(hda.visible)

    def test_deserialize_genome_build(self):
        hda = self._create_vanilla_hda()

        self.assertIsInstance(hda.dbkey, str)
        self.log('should deserialize to "?" from None')
        self.hda_deserializer.deserialize(hda, {"genome_build": None})
        self.assertEqual(hda.dbkey, "?")
        self.log("should raise when deserializing from non-string")
        self.assertRaises(
            exceptions.RequestParameterInvalidException, self.hda_deserializer.deserialize, hda, {"genome_build": 12}
        )
        self.log("should be able to deserialize from unicode")
        date_palm = "نخيل التمر"
        self.hda_deserializer.deserialize(hda, {"genome_build": date_palm})
        self.assertEqual(hda.dbkey, date_palm)
        self.log("should be deserializable from empty string")
        self.hda_deserializer.deserialize(hda, {"genome_build": ""})
        self.assertEqual(hda.dbkey, "")

    def test_deserialize_name(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing from non-string")
        self.assertRaises(
            exceptions.RequestParameterInvalidException, self.hda_deserializer.deserialize, hda, {"name": True}
        )
        self.log("should raise when deserializing from None")
        self.assertRaises(
            exceptions.RequestParameterInvalidException, self.hda_deserializer.deserialize, hda, {"name": None}
        )
        # self.log( 'should deserialize to empty string from None' )
        # self.hda_deserializer.deserialize( hda, { 'name': None } )
        # self.assertEqual( hda.name, '' )
        self.log("should be able to deserialize from unicode")
        olive = "ελιά"
        self.hda_deserializer.deserialize(hda, {"name": olive})
        self.assertEqual(hda.name, olive)
        self.log("should be deserializable from empty string")
        self.hda_deserializer.deserialize(hda, {"name": ""})
        self.assertEqual(hda.name, "")

    def test_deserialize_info(self):
        hda = self._create_vanilla_hda()

        self.log("should raise when deserializing from non-string")
        self.assertRaises(
            exceptions.RequestParameterInvalidException, self.hda_deserializer.deserialize, hda, {"info": True}
        )
        self.log("should raise when deserializing from None")
        self.assertRaises(
            exceptions.RequestParameterInvalidException, self.hda_deserializer.deserialize, hda, {"info": None}
        )
        self.log("should be able to deserialize from unicode")
        rice = "飯"
        self.hda_deserializer.deserialize(hda, {"info": rice})
        self.assertEqual(hda.info, rice)
        self.log("should be deserializable from empty string")
        self.hda_deserializer.deserialize(hda, {"info": ""})
        self.assertEqual(hda.info, "")


# =============================================================================
class HDAFilterParserTestCase(HDATestCase):
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


# =============================================================================
if __name__ == "__main__":
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
