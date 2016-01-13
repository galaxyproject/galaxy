# -*- coding: utf-8 -*-
"""
"""
import os
import imp
import unittest
import random

test_utils = imp.load_source( 'test_utils',
    os.path.join( os.path.dirname( __file__), '../unittest_utils/utility.py' ) )

from galaxy import eggs
eggs.require( 'SQLAlchemy >= 0.4' )
from sqlalchemy import true
from sqlalchemy.sql import text

from base import BaseTestCase
from base import CreatesCollectionsMixin

from galaxy.managers.histories import HistoryManager
from galaxy.managers import hdas
from galaxy.managers import collections
from galaxy.managers import history_contents

default_password = '123456'
user2_data = dict( email='user2@user2.user2', username='user2', password=default_password )
user3_data = dict( email='user3@user3.user3', username='user3', password=default_password )
user4_data = dict( email='user4@user4.user4', username='user4', password=default_password )


# =============================================================================
class HistoryAsContainerTestCase( BaseTestCase, CreatesCollectionsMixin ):

    def set_up_managers( self ):
        super( HistoryAsContainerTestCase, self ).set_up_managers()
        self.history_manager = HistoryManager( self.app )
        self.hda_manager = hdas.HDAManager( self.app )
        self.collection_manager = collections.DatasetCollectionManager( self.app )
        self.contents_manager = history_contents.HistoryContentsManager( self.app )

    def add_hda_to_history( self, history, **kwargs ):
        dataset = self.hda_manager.dataset_manager.create()
        hda = self.hda_manager.create( history=history, dataset=dataset, **kwargs )
        return hda

    def add_list_collection_to_history( self, history, hdas, name='test collection', **kwargs ):
        hdca = self.collection_manager.create( self.trans, history, name, 'list',
            element_identifiers=self.build_element_identifiers( hdas ) )
        return hdca

    def test_contents( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )

        self.log( "calling contents on an empty history should return an empty list" )
        self.assertEqual( [], list( self.contents_manager.contents( history ) ) )

        self.log( "calling contents on an history with hdas should return those in order of their hids" )
        hdas = [ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in xrange( 3 ) ]
        random.shuffle( hdas )
        ordered_hda_contents = list( self.contents_manager.contents( history ) )
        self.assertEqual( map( lambda hda: hda.hid, ordered_hda_contents ), [ 1, 2, 3 ] )

        self.log( "calling contents on an history with both hdas and collections should return both" )
        hdca = self.add_list_collection_to_history( history, hdas )
        all_contents = list( self.contents_manager.contents( history ) )
        self.assertEqual( all_contents, list( ordered_hda_contents ) + [ hdca ] )

    def test_contained( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )

        self.log( "calling contained on an empty history should return an empty list" )
        self.assertEqual( [], list( self.contents_manager.contained( history ) ) )

        self.log( "calling contained on an history with both hdas and collections should return only hdas" )
        hdas = [ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in xrange( 3 ) ]
        self.add_list_collection_to_history( history, hdas )
        self.assertEqual( list( self.contents_manager.contained( history ) ), hdas )

    def test_subcontainers( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )

        self.log( "calling subcontainers on an empty history should return an empty list" )
        self.assertEqual( [], list( self.contents_manager.subcontainers( history ) ) )

        self.log( "calling subcontainers on an history with both hdas and collections should return only collections" )
        hdas = [ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in xrange( 3 ) ]
        hdca = self.add_list_collection_to_history( history, hdas )
        subcontainers = list( self.contents_manager.subcontainers( history ) )
        self.assertEqual( subcontainers, [ hdca ] )

    def test_limit_and_offset( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )
        contents = []
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in xrange( 3 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[:3] ) )
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in xrange( 4, 6 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[4:6] ) )

        # _subquery = self.contents_manager._contents_common_query( self.contents_manager.subcontainer_class, history.id )
        # _subquery = self.contents_manager._contents_common_query( self.contents_manager.contained_class, history.id )
        # print _subquery
        # for row in _subquery.all():
        #     print row

        self.log( "should be able to limit and offset" )
        results = self.contents_manager.contents( history )
        # print [ r.id for r in results ]
        # print '--'
        # print [ c.id for c in contents ]
        self.assertEqual( results, contents )

        self.assertEqual( self.contents_manager.contents( history, limit=4 ), contents[0:4] )
        self.assertEqual( self.contents_manager.contents( history, offset=3 ), contents[3:] )
        self.assertEqual( self.contents_manager.contents( history, limit=4, offset=4 ), contents[4:8] )

        self.assertEqual( self.contents_manager.contents( history, limit=0 ), [] )
        self.assertEqual( self.contents_manager.contents( history, offset=len( contents ) ), [] )

    def test_orm_filtering( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )
        contents = []
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in xrange( 3 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[:3] ) )
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in xrange( 4, 6 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[4:6] ) )

        self.log( "should be filter on deleted" )
        self.hda_manager.delete( contents[1] )
        self.hda_manager.delete( contents[4] )
        contents[6].deleted = True
        deleted = [ contents[1], contents[4], contents[6] ]
        self.app.model.context.flush()
        # weird filter language at this low level
        filters = [ text( 'anon_1.deleted = 1' ) ]
        # for content in self.contents_manager.contents( history, filters=filters ):
        #     print content.hid, content.history_content_type, content.id, content.name
        self.assertEqual( self.contents_manager.contents( history, filters=filters ), deleted )
        # even stranger that sqlalx can use the first model in the union (HDA) for columns across the union
        HDA = self.hda_manager.model_class
        self.assertEqual( self.contents_manager.contents( history,
            filters=[ HDA.deleted == true() ] ), deleted )
        filter_limited_contents = self.contents_manager.contents( history,
            filters=[ HDA.deleted == true() ], limit=2, offset=1 )
        self.assertEqual( filter_limited_contents, deleted[1:] )


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
