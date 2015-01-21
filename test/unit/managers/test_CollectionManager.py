#!/usr/bin/env python
"""
"""
import sys
import os
import pprint
import unittest

__GALAXY_ROOT__ = os.getcwd() + '/../../../'
sys.path.append( __GALAXY_ROOT__ + 'lib' )

from galaxy import eggs
eggs.require( 'SQLAlchemy >= 0.4' )
import sqlalchemy

from galaxy import model
from galaxy import exceptions

import mock
from test_ModelManager import BaseTestCase
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.histories import HistoryManager
from galaxy.managers.hdas import HDAManager

from galaxy.managers.collections import DatasetCollectionManager


# =============================================================================
default_password = '123456'
user2_data = dict( email='user2@user2.user2', username='user2', password=default_password )
user3_data = dict( email='user3@user3.user3', username='user3', password=default_password )


# =============================================================================
class DatasetCollectionManagerTestCase( BaseTestCase ):

    def set_up_managers( self ):
        super( DatasetCollectionManagerTestCase, self ).set_up_managers()
        self.dataset_mgr = DatasetManager( self.app )
        self.hda_mgr = HDAManager( self.app )
        self.history_mgr = HistoryManager( self.app )
        self.collection_mgr = DatasetCollectionManager( self.app )

    def build_element_identifiers( self, elements ):
        identifier_list = []
        for element in elements:
            src = 'hda'
            #if isinstance( element, model.DatasetCollection ):
            #    src = 'collection'#?
            #elif isinstance( element, model.LibraryDatasetDatasetAssociation ):
            #    src = 'ldda'#?
            encoded_id = self.trans.security.encode_id( element.id )
            identifier_list.append( dict( src=src, name=element.name, id=encoded_id ) )
        return identifier_list

    def test_create_simple_list( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )

        history = self.history_mgr.create( self.trans, name='history1', user=owner )

        hda1 = self.hda_mgr.create( self.trans, name='one',
            history=history, dataset=self.dataset_mgr.create( self.trans ) )
        hda2 = self.hda_mgr.create( self.trans, name='two',
            history=history, dataset=self.dataset_mgr.create( self.trans ) )
        hda3 = self.hda_mgr.create( self.trans, name='three',
            history=history, dataset=self.dataset_mgr.create( self.trans ) )

        self.log( "should be able to create a new Collection via ids" )
        element_identifiers = self.build_element_identifiers( [ hda1, hda2, hda3 ] )
        hdca = self.collection_mgr.create( self.trans, history, 'test collection', 'list',
                                           element_identifiers=element_identifiers )
        self.assertIsInstance( hdca, model.HistoryDatasetCollectionAssociation )
        self.assertEqual( hdca.name, 'test collection' )
        self.assertEqual( hdca.hid, 4 )
        self.assertFalse( hdca.deleted )
        self.assertTrue( hdca.visible )

        #print 'hdca dir:'
        #for k in dir( hdca ):
        #    print k, getattr( hdca, k, '(?)' )

        self.log( "should contain an underlying, well-formed DatasetCollection" )
        self.assertIsInstance( hdca.collection, model.DatasetCollection )
        collection = hdca.collection
        self.assertEqual( collection.collection_type, 'list' )
        self.assertEqual( collection.state, 'ok' )
        self.assertEqual( len( collection.dataset_instances ), 3 )
        self.assertEqual( len( collection.elements ), 3 )

        #print 'hdca.collection dir:'
        #for k in dir( hdca.collection ):
        #    print k, getattr( hdca.collection, k, '(?)' )

        #elements = collection.elements
        #print 'hdca.collection element dir:'
        #for k in dir( elements[0] ):
        #    print k, getattr( elements[0], k, '(?)' )

        self.log( "and that collection should have three well-formed Elements" )
        self.assertIsInstance( collection.elements[0], model.DatasetCollectionElement )
        self.assertEqual( collection.elements[0].element_identifier, 'one' )
        self.assertEqual( collection.elements[0].element_index, 0 )
        self.assertEqual( collection.elements[0].element_type, 'hda' )
        self.assertEqual( collection.elements[0].element_object, hda1 )

        self.assertIsInstance( collection.elements[1], model.DatasetCollectionElement )
        self.assertEqual( collection.elements[1].element_identifier, 'two' )
        self.assertEqual( collection.elements[1].element_index, 1 )
        self.assertEqual( collection.elements[1].element_type, 'hda' )
        self.assertEqual( collection.elements[1].element_object, hda2 )

        self.assertIsInstance( collection.elements[2], model.DatasetCollectionElement )
        self.assertEqual( collection.elements[2].element_identifier, 'three' )
        self.assertEqual( collection.elements[2].element_index, 2 )
        self.assertEqual( collection.elements[2].element_type, 'hda' )
        self.assertEqual( collection.elements[2].element_object, hda3 )

        self.log( "should be able to create a new Collection via objects" )
        elements = dict( one=hda1, two=hda2, three=hda3 )
        hdca2 = self.collection_mgr.create( self.trans, history, 'test collection 2', 'list', elements=elements )
        self.assertIsInstance( hdca2, model.HistoryDatasetCollectionAssociation )

    def test_update_from_dict( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )

        history = self.history_mgr.create( self.trans, name='history1', user=owner )

        hda1 = self.hda_mgr.create( self.trans, name='one',
            history=history, dataset=self.dataset_mgr.create( self.trans ) )
        hda2 = self.hda_mgr.create( self.trans, name='two',
            history=history, dataset=self.dataset_mgr.create( self.trans ) )
        hda3 = self.hda_mgr.create( self.trans, name='three',
            history=history, dataset=self.dataset_mgr.create( self.trans ) )

        elements = dict( one=hda1, two=hda2, three=hda3 )
        hdca = self.collection_mgr.create( self.trans, history, 'test collection', 'list', elements=elements )

        self.log( "should be set from a dictionary" )
        self.collection_mgr._set_from_dict( self.trans, hdca, {
            'deleted'   : True,
            'visible'   : False,
            'name'      : 'New Name',
            #TODO: doesn't work
            #'tags'      : [ 'one', 'two', 'three' ]
            #'annotations'      : [?]
        })
        self.assertEqual( hdca.name, 'New Name' )
        self.assertTrue( hdca.deleted )
        self.assertFalse( hdca.visible )
        #self.assertEqual( hdca.tags, [ 'one', 'two', 'three' ] )
        #self.assertEqual( hdca.annotations, [ 'one', 'two', 'three' ] )

    #def test_validation( self ):
    #    self.log( "should be able to change the name" )
    #    self.log( "should be able to set deleted" )
    #    self.log( "should be able to set visible" )
    #    self.log( "should be able to set tags" )


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
