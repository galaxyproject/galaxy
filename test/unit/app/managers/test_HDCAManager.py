from unittest import mock

from galaxy.app_unittest_utils.galaxy_mock import mock_url_builder
from galaxy.managers import (
    collections,
    hdas,
    hdcas,
)
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.histories import HistoryManager
from .base import (
    BaseTestCase,
    CreatesCollectionsMixin,
)

# =============================================================================
default_password = "123456"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)
user3_data = dict(email="user3@user3.user3", username="user3", password=default_password)


# =============================================================================
class HDCATestCase(BaseTestCase, CreatesCollectionsMixin):
    def set_up_managers(self):
        super().set_up_managers()
        self.hdca_manager = self.app[hdcas.HDCAManager]
        self.hda_manager = self.app[hdas.HDAManager]
        self.history_manager = self.app[HistoryManager]
        self.dataset_manager = self.app[DatasetManager]
        self.collection_manager = self.app[collections.DatasetCollectionManager]

    def _create_history(self, user_data=None, **kwargs):
        user_data = user_data or user2_data
        owner = self.user_manager.create(**user_data)
        self.trans.set_user(owner)
        return self.history_manager.create(user=owner, **kwargs)

    def _create_hda(self, history, dataset=None, **kwargs):
        if not dataset:
            dataset = self.hda_manager.dataset_manager.create()
        hda = self.hda_manager.create(history=history, dataset=dataset, **kwargs)
        return hda

    def _create_list_hdca(self, hdas, history=None, name="test collection", **kwargs):
        if not history:
            history = history or self._create_history()
        for i, hda in enumerate(hdas):
            if not isinstance(hdas, self.hda_manager.model_class):
                hdas[i] = self._create_hda(history, **hda)
        hdca = self.collection_manager.create(
            self.trans, history, name, "list", element_identifiers=self.build_element_identifiers(hdas)
        )
        return hdca


@mock.patch("galaxy.managers.base.ModelSerializer.url_for", mock_url_builder)
class TestHDCASerializer(HDCATestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.hdca_serializer = hdcas.HDCASerializer(self.app)

    def test_views(self):
        serializer = self.hdca_serializer
        item = self._create_list_hdca([dict(name=(f"hda-{i}"), hid=i) for i in range(5)])

        self.log("should have a summary view")
        summary_view = serializer.serialize_to_view(item, view="summary")
        self.assertKeys(summary_view, serializer.views["summary"])

        self.log("should have the summary view as default view")
        default_view = serializer.serialize_to_view(item, default_view="summary")
        self.assertKeys(default_view, serializer.views["summary"])

        self.log("should have a detailed view")
        detailed_view = serializer.serialize_to_view(item, view="detailed")
        self.assertKeys(detailed_view, serializer.views["detailed"])

        self.log("should have a serializer for all serializable keys")
        for key in serializer.serializable_keyset:
            instantiated_attribute = getattr(item, key, None)
            assert key in serializer.serializers or isinstance(
                instantiated_attribute, self.TYPES_NEEDING_NO_SERIALIZERS
            ), f"No serializer for: {key} ({instantiated_attribute})"

    def test_views_and_keys(self):
        serializer = self.hdca_serializer
        item = self._create_list_hdca([dict(name=(f"hda-{i}"), hid=i) for i in range(5)])
        summary_plus_key = ["elements"]
        only_keys = ["id", "populated_state_message"]

        self.log("should be able to use keys with views")
        serialized = serializer.serialize_to_view(item, view="summary", keys=summary_plus_key)
        self.assertKeys(serialized, serializer.views["summary"] + summary_plus_key)

        self.log("should be able to use keys on their own")
        serialized = serializer.serialize_to_view(item, keys=only_keys)
        self.assertKeys(serialized, only_keys)
