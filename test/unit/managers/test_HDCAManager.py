# -*- coding: utf-8 -*-
import unittest

from galaxy.managers import (
    collections,
    hdas,
    hdcas
)
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.histories import HistoryManager
from .base import (
    BaseTestCase,
    CreatesCollectionsMixin
)

# =============================================================================
default_password = '123456'
user2_data = dict(email='user2@user2.user2', username='user2', password=default_password)
user3_data = dict(email='user3@user3.user3', username='user3', password=default_password)


# =============================================================================
class HDCATestCase(BaseTestCase, CreatesCollectionsMixin):

    def set_up_managers(self):
        super(HDCATestCase, self).set_up_managers()
        self.hdca_manager = hdcas.HDCAManager(self.app)
        self.hda_manager = hdas.HDAManager(self.app)
        self.history_manager = HistoryManager(self.app)
        self.dataset_manager = DatasetManager(self.app)
        self.collection_manager = collections.DatasetCollectionManager(self.app)

    def _create_history(self, user_data=None, **kwargs):
        user_data = user_data or user2_data
        owner = self.user_manager.create(**user_data)
        return self.history_manager.create(user=owner, **kwargs)

    def _create_hda(self, history, dataset=None, **kwargs):
        if not dataset:
            dataset = self.hda_manager.dataset_manager.create()
        hda = self.hda_manager.create(history=history, dataset=dataset, **kwargs)
        return hda

    def _create_list_hdca(self, hdas, history=None, name='test collection', **kwargs):
        if not history:
            history = history or self._create_history()
        for i, hda in enumerate(hdas):
            if not isinstance(hdas, self.hda_manager.model_class):
                hdas[i] = self._create_hda(history, **hda)
        hdca = self.collection_manager.create(self.trans, history, name, 'list',
            element_identifiers=self.build_element_identifiers(hdas))
        return hdca


# =============================================================================
# web.url_for doesn't work well in the framework
def testable_url_for(*a, **k):
    return '(fake url): %s, %s' % (a, k)


hdcas.HDCASerializer.url_for = staticmethod(testable_url_for)


class HDCASerializerTestCase(HDCATestCase):

    def set_up_managers(self):
        super(HDCASerializerTestCase, self).set_up_managers()
        self.hdca_serializer = hdcas.HDCASerializer(self.app)

    def test_views(self):
        serializer = self.hdca_serializer
        item = self._create_list_hdca([
            dict(name=("hda-{0}".format(i)), hid=i) for i in range(5)
        ])

        self.log('should have a summary view')
        summary_view = serializer.serialize_to_view(item, view='summary')
        self.assertKeys(summary_view, serializer.views['summary'])

        self.log('should have the summary view as default view')
        default_view = serializer.serialize_to_view(item, default_view='summary')
        self.assertKeys(default_view, serializer.views['summary'])

        self.log('should have a detailed view')
        detailed_view = serializer.serialize_to_view(item, view='detailed')
        self.assertKeys(detailed_view, serializer.views['detailed'])

        self.log('should have a serializer for all serializable keys')
        for key in serializer.serializable_keyset:
            instantiated_attribute = getattr(item, key, None)
            if not ((key in serializer.serializers) or
                   (isinstance(instantiated_attribute, self.TYPES_NEEDING_NO_SERIALIZERS))):
                self.fail('no serializer for: %s (%s)' % (key, instantiated_attribute))
        else:
            self.assertTrue(True, 'all serializable keys have a serializer')

    def test_views_and_keys(self):
        serializer = self.hdca_serializer
        item = self._create_list_hdca([
            dict(name=("hda-{0}".format(i)), hid=i) for i in range(5)
        ])
        summary_plus_key = ['elements']
        only_keys = ['id', 'populated_state_message']

        self.log('should be able to use keys with views')
        serialized = serializer.serialize_to_view(item, view='summary', keys=summary_plus_key)
        self.assertKeys(serialized, serializer.views['summary'] + summary_plus_key)

        self.log('should be able to use keys on their own')
        serialized = serializer.serialize_to_view(item, keys=only_keys)
        self.assertKeys(serialized, only_keys)


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
