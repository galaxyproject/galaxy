# -*- coding: utf-8 -*-
"""
"""
import datetime
import random
import unittest

from sqlalchemy import column, desc, false, true
from sqlalchemy.sql import text

from galaxy.managers import collections, hdas, history_contents
from galaxy.managers.histories import HistoryManager

from .base import BaseTestCase
from .base import CreatesCollectionsMixin

default_password = '123456'
user2_data = dict( email='user2@user2.user2', username='user2', password=default_password )
user3_data = dict( email='user3@user3.user3', username='user3', password=default_password )
user4_data = dict( email='user4@user4.user4', username='user4', password=default_password )


# =============================================================================
class HistoryAsContainerBaseTestCase( BaseTestCase, CreatesCollectionsMixin ):

    def set_up_managers( self ):
        super( HistoryAsContainerBaseTestCase, self ).set_up_managers()
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


# =============================================================================
class HistoryAsContainerTestCase( HistoryAsContainerBaseTestCase ):

    def test_contents( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )

        self.log( "calling contents on an empty history should return an empty list" )
        self.assertEqual( [], list( self.contents_manager.contents( history ) ) )

        self.log( "calling contents on an history with hdas should return those in order of their hids" )
        hdas = [ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 3 ) ]
        random.shuffle( hdas )
        ordered_hda_contents = list( self.contents_manager.contents( history ) )
        self.assertEqual( [hda.hid for hda in ordered_hda_contents], [ 1, 2, 3 ] )

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
        hdas = [ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 3 ) ]
        self.add_list_collection_to_history( history, hdas )
        self.assertEqual( list( self.contents_manager.contained( history ) ), hdas )

    def test_subcontainers( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )

        self.log( "calling subcontainers on an empty history should return an empty list" )
        self.assertEqual( [], list( self.contents_manager.subcontainers( history ) ) )

        self.log( "calling subcontainers on an history with both hdas and collections should return only collections" )
        hdas = [ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 3 ) ]
        hdca = self.add_list_collection_to_history( history, hdas )
        subcontainers = list( self.contents_manager.subcontainers( history ) )
        self.assertEqual( subcontainers, [ hdca ] )

    def test_limit_and_offset( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )
        contents = []
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 3 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[:3] ) )
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 4, 6 ) ])
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
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 3 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[:3] ) )
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 4, 6 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[4:6] ) )

        self.log( "should allow filter on deleted" )
        self.hda_manager.delete( contents[1] )
        self.hda_manager.delete( contents[4] )
        contents[6].deleted = True
        deleted = [ contents[1], contents[4], contents[6] ]
        self.app.model.context.flush()

        # TODO: cross db compat?
        filters = [ text( 'deleted = 1' ) ]
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

        self.log( "should allow filter on visible" )
        contents[2].visible = False
        contents[5].visible = False
        contents[6].visible = False
        invisible = [ contents[2], contents[5], contents[6] ]
        # for content in invisible:
        #     print content.id, content.__class__.__name__, content
        self.app.model.context.flush()

        filters = [ text( 'visible = 0' ) ]
        self.assertEqual( self.contents_manager.contents( history, filters=filters ), invisible )
        self.assertEqual( self.contents_manager.contents( history,
            filters=[ HDA.visible == false() ] ), invisible )
        filter_limited_contents = self.contents_manager.contents( history,
            filters=[ HDA.visible == false() ], limit=2, offset=1 )
        self.assertEqual( filter_limited_contents, invisible[1:] )

        self.log( "should allow filtering more than one attribute" )
        deleted_and_invisible = [ contents[6] ]

        filters = [ text( 'deleted = 1' ), text( 'visible = 0' ) ]
        self.assertEqual( self.contents_manager.contents( history, filters=filters ), deleted_and_invisible )
        self.assertEqual( self.contents_manager.contents( history,
            filters=[ HDA.deleted == true(), HDA.visible == false() ] ), deleted_and_invisible )
        offset_too_far = self.contents_manager.contents( history,
            filters=[ HDA.deleted == true(), HDA.visible == false() ], limit=2, offset=1 )
        self.assertEqual( offset_too_far, [] )

        self.log( "should allow filtering more than one attribute" )
        deleted_and_invisible = [ contents[6] ]
        # note the two syntaxes both work
        self.assertEqual( self.contents_manager.contents( history,
            filters=[ text( 'deleted = 1' ), text( 'visible = 0' ) ] ), deleted_and_invisible )
        self.assertEqual( self.contents_manager.contents( history,
            filters=[ HDA.deleted == true(), HDA.visible == false() ] ), deleted_and_invisible )
        offset_too_far = self.contents_manager.contents( history,
            filters=[ HDA.deleted == true(), HDA.visible == false() ], limit=2, offset=1 )
        self.assertEqual( offset_too_far, [] )

        self.log( "should allow filtering using like" )
        # find 'hda-4'
        self.assertEqual( [ contents[4] ],
            self.contents_manager.contents( history, filters=[ HDA.name.like( '%-4' ) ] ) )
        # the collections added above have the default name 'test collection'
        self.assertEqual( self.contents_manager.subcontainers( history ),
            self.contents_manager.contents( history, filters=[ HDA.name.like( '%collect%' ) ] ) )

    def test_order_by( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )
        contents = []
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 3 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[:3] ) )
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 4, 6 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[4:6] ) )

        self.log( "should default to hid order_by" )
        self.assertEqual( self.contents_manager.contents( history ), contents )

        self.log( "should allow asc, desc order_by" )
        self.assertEqual( self.contents_manager.contents( history, order_by=desc( 'hid' ) ), contents[::-1] )

        def get_create_time( item ):
            create_time = getattr( item, 'create_time', None )
            if not create_time:
                create_time = item.collection.create_time
            return create_time

        self.log( "should allow create_time order_by" )
        newest_first = sorted( contents, key=get_create_time, reverse=True )
        results = self.contents_manager.contents( history, order_by=desc( 'create_time' ) )
        self.assertEqual( newest_first, results )

        self.log( "should allow update_time order_by" )
        # change the oldest created to update the update_time
        contents[0].name = 'zany and/or wacky'
        self.app.model.context.flush()
        results = self.contents_manager.contents( history, order_by=desc( 'update_time' ) )
        self.assertEqual( contents[0], results[0] )

    def test_update_time_filter( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )
        contents = []
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 3 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[:3] ) )
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 4, 6 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[4:6] ) )

        self.log( "should allow filtering by update_time" )
        # in the case of collections we have to change the collection.collection (ugh) to change the update_time
        contents[3].collection.populated_state = 'big ball of mud'
        self.app.model.context.flush()
        update_time = contents[3].collection.update_time

        def get_update_time( item ):
            update_time = getattr( item, 'update_time', None )
            if not update_time:
                update_time = item.collection.update_time
            return update_time

        results = self.contents_manager.contents( history, filters=[ column( 'update_time' ) >= update_time ] )
        self.assertEqual( results, [ contents[3] ] )

    def test_filtered_counting( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )
        contents = []
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 3 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[:3] ) )
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 4, 6 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[4:6] ) )

        self.log( "should show correct count with filters" )
        self.hda_manager.delete( contents[1] )
        self.hda_manager.delete( contents[4] )
        contents[6].deleted = True
        self.app.model.context.flush()

        contents[2].visible = False
        contents[5].visible = False
        contents[6].visible = False
        self.app.model.context.flush()

        HDA = self.hda_manager.model_class
        self.assertEqual( self.contents_manager.contents_count( history, filters=[ HDA.deleted == true() ] ), 3 )
        filters = [ text( 'visible = 0' ) ]
        self.assertEqual( self.contents_manager.contents_count( history, filters=filters ), 3 )

        filters = [ text( 'deleted = 1' ), text( 'visible = 0' ) ]
        self.assertEqual( self.contents_manager.contents_count( history, filters=filters ), 1 )

    def test_type_id( self ):
        user2 = self.user_manager.create( **user2_data )
        history = self.history_manager.create( name='history', user=user2 )
        contents = []
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 3 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[:3] ) )
        contents.extend([ self.add_hda_to_history( history, name=( 'hda-' + str( x ) ) ) for x in range( 4, 6 ) ])
        contents.append( self.add_list_collection_to_history( history, contents[4:6] ) )

        self.log( "should be able to use eq and in with hybrid type_id" )
        filters = [ column( 'type_id' ) == u'dataset-2' ]
        self.assertEqual( self.contents_manager.contents( history, filters=filters ), [ contents[1] ])
        filters = [ column( 'type_id' ).in_([ u'dataset-1', u'dataset-3' ]) ]
        self.assertEqual( self.contents_manager.contents( history, filters=filters ), [ contents[0], contents[2] ])
        filters = [ column( 'type_id' ) == u'dataset_collection-1' ]
        self.assertEqual( self.contents_manager.contents( history, filters=filters ), [ contents[3] ])
        filters = [ column( 'type_id' ).in_([ u'dataset-2', u'dataset_collection-2' ]) ]
        self.assertEqual( self.contents_manager.contents( history, filters=filters ), [ contents[1], contents[6] ])


class HistoryContentsFilterParserTestCase( HistoryAsContainerBaseTestCase ):

    def set_up_managers( self ):
        super( HistoryContentsFilterParserTestCase, self ).set_up_managers()
        self.filter_parser = history_contents.HistoryContentsFilters( self.app )

    def test_date_parser( self ):
        # -- seconds and milliseconds from epoch
        self.log( 'should be able to parse epoch seconds' )
        self.assertEqual( self.filter_parser.parse_date( '1234567890' ),
            datetime.datetime.fromtimestamp( 1234567890 ).isoformat( sep=' ' ) )

        self.log( 'should be able to parse floating point epoch seconds.milliseconds' )
        self.assertEqual( self.filter_parser.parse_date( '1234567890.123' ),
            datetime.datetime.fromtimestamp( 1234567890.123 ).isoformat( sep=' ' ) )

        self.log( 'should error if bad epoch is used' )
        self.assertRaises( ValueError, self.filter_parser.parse_date, '0x000234' )

        # -- datetime strings
        self.log( 'should allow date alone' )
        self.assertEqual( self.filter_parser.parse_date( '2009-02-13' ), '2009-02-13' )

        self.log( 'should allow date and time' )
        self.assertEqual( self.filter_parser.parse_date( '2009-02-13 18:13:00' ), '2009-02-13 18:13:00' )
        self.assertEqual( self.filter_parser.parse_date( '2009-02-13T18:13:00' ), '2009-02-13 18:13:00' )
        self.assertEqual( self.filter_parser.parse_date( '2009-02-13T18:13:00Z' ), '2009-02-13 18:13:00' )

        self.log( 'should allow date and time with milliseconds' )
        self.assertEqual( self.filter_parser.parse_date( '2009-02-13 18:13:00.123' ), '2009-02-13 18:13:00.123' )
        self.assertEqual( self.filter_parser.parse_date( '2009-02-13T18:13:00.123' ), '2009-02-13 18:13:00.123' )
        self.assertEqual( self.filter_parser.parse_date( '2009-02-13T18:13:00.123Z' ), '2009-02-13 18:13:00.123' )

        self.log( 'should error if timezone is added' )
        self.assertRaises( ValueError, self.filter_parser.parse_date, '2009-02-13T18:13:00.123+0700' )

        self.log( 'should error if locale is used' )
        self.assertRaises( ValueError, self.filter_parser.parse_date, 'Fri Feb 13 18:31:30 2009' )

        self.log( 'should error if wrong milliseconds format is used' )
        self.assertRaises( ValueError, self.filter_parser.parse_date, '2009-02-13 18:13:00.' )
        self.assertRaises( ValueError, self.filter_parser.parse_date, '2009-02-13 18:13:00.1234567' )


if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
