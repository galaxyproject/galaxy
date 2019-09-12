#!/usr/bin/env python
"""
"""
import unittest

from galaxy import model
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.histories import HistoryManager
from .base import BaseTestCase, CreatesCollectionsMixin

# =============================================================================
default_password = '123456'
user2_data = dict(email='user2@user2.user2', username='user2', password=default_password)
user3_data = dict(email='user3@user3.user3', username='user3', password=default_password)


# =============================================================================
class DatasetCollectionManagerTestCase(BaseTestCase, CreatesCollectionsMixin):

    def set_up_managers(self):
        super(DatasetCollectionManagerTestCase, self).set_up_managers()
        self.dataset_manager = DatasetManager(self.app)
        self.hda_manager = HDAManager(self.app)
        self.history_manager = HistoryManager(self.app)
        self.collection_manager = DatasetCollectionManager(self.app)

    def test_create_simple_list(self):
        owner = self.user_manager.create(**user2_data)

        history = self.history_manager.create(name='history1', user=owner)

        hda1 = self.hda_manager.create(name='one',
            history=history, dataset=self.dataset_manager.create())
        hda2 = self.hda_manager.create(name='two',
            history=history, dataset=self.dataset_manager.create())
        hda3 = self.hda_manager.create(name='three',
            history=history, dataset=self.dataset_manager.create())

        self.log("should be able to create a new Collection via ids")
        element_identifiers = self.build_element_identifiers([hda1, hda2, hda3])
        hdca = self.collection_manager.create(self.trans, history, 'test collection', 'list',
                                           element_identifiers=element_identifiers)
        self.assertIsInstance(hdca, model.HistoryDatasetCollectionAssociation)
        self.assertEqual(hdca.name, 'test collection')
        self.assertEqual(hdca.hid, 4)
        self.assertFalse(hdca.deleted)
        self.assertTrue(hdca.visible)

        self.log("should contain an underlying, well-formed DatasetCollection")
        self.assertIsInstance(hdca.collection, model.DatasetCollection)
        collection = hdca.collection
        self.assertEqual(collection.collection_type, 'list')
        self.assertEqual(collection.state, 'ok')
        self.assertEqual(len(collection.dataset_instances), 3)
        self.assertEqual(len(collection.elements), 3)

        self.log("and that collection should have three well-formed Elements")
        self.assertIsInstance(collection.elements[0], model.DatasetCollectionElement)
        self.assertEqual(collection.elements[0].element_identifier, 'one')
        self.assertEqual(collection.elements[0].element_index, 0)
        self.assertEqual(collection.elements[0].element_type, 'hda')
        self.assertEqual(collection.elements[0].element_object, hda1)

        self.assertIsInstance(collection.elements[1], model.DatasetCollectionElement)
        self.assertEqual(collection.elements[1].element_identifier, 'two')
        self.assertEqual(collection.elements[1].element_index, 1)
        self.assertEqual(collection.elements[1].element_type, 'hda')
        self.assertEqual(collection.elements[1].element_object, hda2)

        self.assertIsInstance(collection.elements[2], model.DatasetCollectionElement)
        self.assertEqual(collection.elements[2].element_identifier, 'three')
        self.assertEqual(collection.elements[2].element_index, 2)
        self.assertEqual(collection.elements[2].element_type, 'hda')
        self.assertEqual(collection.elements[2].element_object, hda3)

        self.log("should be able to create a new Collection via objects")
        elements = dict(one=hda1, two=hda2, three=hda3)
        hdca2 = self.collection_manager.create(self.trans, history, 'test collection 2', 'list', elements=elements)
        self.assertIsInstance(hdca2, model.HistoryDatasetCollectionAssociation)

    def test_update_from_dict(self):
        owner = self.user_manager.create(**user2_data)

        history = self.history_manager.create(name='history1', user=owner)

        hda1 = self.hda_manager.create(name='one',
            history=history, dataset=self.dataset_manager.create())
        hda2 = self.hda_manager.create(name='two',
            history=history, dataset=self.dataset_manager.create())
        hda3 = self.hda_manager.create(name='three',
            history=history, dataset=self.dataset_manager.create())

        elements = dict(one=hda1, two=hda2, three=hda3)
        hdca = self.collection_manager.create(self.trans, history, 'test collection', 'list', elements=elements)

        self.log("should be set from a dictionary")
        self.collection_manager._set_from_dict(self.trans, hdca, {
            'deleted': True,
            'visible': False,
            'name': 'New Name',
            # TODO: doesn't work
            # 'tags'      : [ 'one', 'two', 'three' ]
            # 'annotations'      : [?]
        })
        self.assertEqual(hdca.name, 'New Name')
        self.assertTrue(hdca.deleted)
        self.assertFalse(hdca.visible)
        # self.assertEqual( hdca.tags, [ 'one', 'two', 'three' ] )
        # self.assertEqual( hdca.annotations, [ 'one', 'two', 'three' ] )

    # def test_validation( self ):
    #    self.log( "should be able to change the name" )
    #    self.log( "should be able to set deleted" )
    #    self.log( "should be able to set visible" )
    #    self.log( "should be able to set tags" )


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
