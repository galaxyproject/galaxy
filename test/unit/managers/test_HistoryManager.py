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
from galaxy.util.bunch import Bunch

import mock
from test_ModelManager import BaseTestCase
from galaxy.managers.histories import HistoryManager
from galaxy.managers.histories import HistoryFilters


# =============================================================================
default_password = '123456'
user2_data = dict( email='user2@user2.user2', username='user2', password=default_password )
user3_data = dict( email='user3@user3.user3', username='user3', password=default_password )
user4_data = dict( email='user4@user4.user4', username='user4', password=default_password )


# =============================================================================
class HistoryManagerTestCase( BaseTestCase ):

    def set_up_managers( self ):
        super( HistoryManagerTestCase, self ).set_up_managers()
        self.history_mgr = HistoryManager( self.app )

    def test_base( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        user3 = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be able to create a new history" )
        history1 = self.history_mgr.create( self.trans, name='history1', user=user2 )
        self.assertIsInstance( history1, model.History )
        self.assertEqual( history1.name, 'history1' )
        self.assertEqual( history1.user, user2 )
        self.assertEqual( history1, self.trans.sa_session.query( model.History ).get( history1.id ) )
        self.assertEqual( history1,
            self.trans.sa_session.query( model.History ).filter( model.History.name == 'history1' ).one() )
        self.assertEqual( history1,
            self.trans.sa_session.query( model.History ).filter( model.History.user == user2 ).one() )

        self.log( "should be able to copy a history" )
        history2 = self.history_mgr.copy( self.trans, history1, user=user3 )
        self.assertIsInstance( history2, model.History )
        self.assertEqual( history2.user, user3 )
        self.assertEqual( history2, self.trans.sa_session.query( model.History ).get( history2.id ) )
        self.assertEqual( history2.name, history1.name )
        self.assertNotEqual( history2, history1 )

        self.log( "should be able to query" )
        histories = self.trans.sa_session.query( model.History ).all()
        self.assertEqual( self.history_mgr.one( self.trans, filters=( model.History.id == history1.id ) ), history1 )
        self.assertEqual( self.history_mgr.list( self.trans ), histories )
        self.assertEqual( self.history_mgr.by_id( self.trans, history1.id ), history1 )
        self.assertEqual( self.history_mgr.by_ids( self.trans, [ history2.id, history1.id ] ), [ history2, history1 ] )

        self.log( "should be able to limit and offset" )
        self.assertEqual( self.history_mgr.list( self.trans, limit=1 ), histories[0:1] )
        self.assertEqual( self.history_mgr.list( self.trans, offset=1 ), histories[1:] )
        self.assertEqual( self.history_mgr.list( self.trans, limit=1, offset=1 ), histories[1:2] )

        self.assertEqual( self.history_mgr.list( self.trans, limit=0 ), [] )
        self.assertEqual( self.history_mgr.list( self.trans, offset=3 ), [] )

        self.log( "should be able to order" )
        history3 = self.history_mgr.create( self.trans, name="history3", user=user2 )
        name_first_then_time = ( model.History.name, sqlalchemy.desc( model.History.create_time ) )
        self.assertEqual( self.history_mgr.list( self.trans, order_by=name_first_then_time ),
            [ history2, history1, history3 ] )

    def test_has_user( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        non_owner = self.user_mgr.create( self.trans, **user3_data )

        item1 = self.history_mgr.create( self.trans, user=owner )
        item2 = self.history_mgr.create( self.trans, user=owner )
        item3 = self.history_mgr.create( self.trans, user=non_owner )

        self.log( "should be able to list items by user" )
        user_histories = self.history_mgr.by_user( self.trans, owner )
        self.assertEqual( user_histories, [ item1, item2 ] )

    def test_ownable( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        non_owner = self.user_mgr.create( self.trans, **user3_data )

        item1 = self.history_mgr.create( self.trans, user=owner )

        self.log( "should be able to poll whether a given user owns an item" )
        self.assertTrue(  self.history_mgr.is_owner( self.trans, item1, owner ) )
        self.assertFalse( self.history_mgr.is_owner( self.trans, item1, non_owner ) )

        self.log( "should raise an error when checking ownership with non-owner" )
        self.assertRaises( exceptions.ItemOwnershipException,
            self.history_mgr.error_unless_owner, self.trans, item1, non_owner )
        self.assertRaises( exceptions.ItemOwnershipException,
            self.history_mgr.get_owned, self.trans, item1.id, non_owner )

        self.log( "should not raise an error when checking ownership with owner" )
        self.assertEqual( self.history_mgr.error_unless_owner( self.trans, item1, owner ), item1 )
        self.assertEqual( self.history_mgr.get_owned( self.trans, item1.id, owner ), item1 )

        self.log( "should not raise an error when checking ownership with admin" )
        self.assertTrue( self.history_mgr.is_owner( self.trans, item1, self.admin_user ) )
        self.assertEqual( self.history_mgr.error_unless_owner( self.trans, item1, self.admin_user ), item1 )
        self.assertEqual( self.history_mgr.get_owned( self.trans, item1.id, self.admin_user ), item1 )

    def test_accessible( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        item1 = self.history_mgr.create( self.trans, user=owner )

        non_owner = self.user_mgr.create( self.trans, **user3_data )

        self.log( "should be inaccessible by default except to owner" )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, item1, owner ) )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, item1, self.admin_user ) )
        self.assertFalse( self.history_mgr.is_accessible( self.trans, item1, non_owner ) )

        self.log( "should raise an error when checking accessibility with non-owner" )
        self.assertRaises( exceptions.ItemAccessibilityException,
            self.history_mgr.error_unless_accessible, self.trans, item1, non_owner )
        self.assertRaises( exceptions.ItemAccessibilityException,
            self.history_mgr.get_accessible, self.trans, item1.id, non_owner )

        self.log( "should not raise an error when checking ownership with owner" )
        self.assertEqual( self.history_mgr.error_unless_accessible( self.trans, item1, owner ), item1 )
        self.assertEqual( self.history_mgr.get_accessible( self.trans, item1.id, owner ), item1 )

        self.log( "should not raise an error when checking ownership with admin" )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, item1, self.admin_user ) )
        self.assertEqual( self.history_mgr.error_unless_accessible( self.trans, item1, self.admin_user ), item1 )
        self.assertEqual( self.history_mgr.get_accessible( self.trans, item1.id, self.admin_user ), item1 )

    def test_importable( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        self.trans.set_user( owner )
        non_owner = self.user_mgr.create( self.trans, **user3_data )

        item1 = self.history_mgr.create( self.trans, user=owner )

        self.log( "should not be importable by default" )
        self.assertFalse( item1.importable )
        self.assertIsNone( item1.slug )

        self.log( "should be able to make importable (accessible by link) to all users" )
        accessible = self.history_mgr.make_importable( self.trans, item1 )
        self.assertEqual( accessible, item1 )
        self.assertIsNotNone( accessible.slug )
        self.assertTrue( accessible.importable )

        for user in self.user_mgr.list( self.trans ):
            self.assertTrue( self.history_mgr.is_accessible( self.trans, accessible, user ) )

        self.log( "should be able to make non-importable/inaccessible again" )
        inaccessible = self.history_mgr.make_non_importable( self.trans, accessible )
        self.assertEqual( inaccessible, accessible )
        self.assertIsNotNone( inaccessible.slug )
        self.assertFalse( inaccessible.importable )

        self.assertTrue( self.history_mgr.is_accessible( self.trans, inaccessible, owner ) )
        self.assertFalse( self.history_mgr.is_accessible( self.trans, inaccessible, non_owner ) )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, inaccessible, self.admin_user ) )

    def test_published( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        self.trans.set_user( owner )
        non_owner = self.user_mgr.create( self.trans, **user3_data )

        item1 = self.history_mgr.create( self.trans, user=owner )

        self.log( "should not be published by default" )
        self.assertFalse( item1.published )
        self.assertIsNone( item1.slug )

        self.log( "should be able to publish (listed publicly) to all users" )
        published = self.history_mgr.publish( self.trans, item1 )
        self.assertEqual( published, item1 )
        self.assertTrue( published.published )
        # note: publishing sets importable to true as well
        self.assertTrue( published.importable )
        self.assertIsNotNone( published.slug )

        for user in self.user_mgr.list( self.trans ):
            self.assertTrue( self.history_mgr.is_accessible( self.trans, published, user ) )

        self.log( "should be able to make non-importable/inaccessible again" )
        unpublished = self.history_mgr.unpublish( self.trans, published )
        self.assertEqual( unpublished, published )
        self.assertFalse( unpublished.published )
        # note: unpublishing does not make non-importable, you must explicitly do that separately
        self.assertTrue( published.importable )
        self.history_mgr.make_non_importable( self.trans, unpublished )
        self.assertFalse( published.importable )
        # note: slug still remains after unpublishing
        self.assertIsNotNone( unpublished.slug )

        self.assertTrue( self.history_mgr.is_accessible( self.trans, unpublished, owner ) )
        self.assertFalse( self.history_mgr.is_accessible( self.trans, unpublished, non_owner ) )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, unpublished, self.admin_user ) )

    def test_sharable( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        self.trans.set_user( owner )
        item1 = self.history_mgr.create( self.trans, user=owner )

        non_owner = self.user_mgr.create( self.trans, **user3_data )
        #third_party = self.user_mgr.create( self.trans, **user4_data )

        self.log( "should be unshared by default" )
        self.assertEqual( self.history_mgr.get_share_assocs( self.trans, item1 ), [] )
        self.assertEqual( item1.slug, None )

        self.log( "should be able to share with specific users" )
        share_assoc = self.history_mgr.share_with( self.trans, item1, non_owner )
        self.assertIsInstance( share_assoc, model.HistoryUserShareAssociation )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, item1, non_owner ) )
        self.assertEqual(
            len( self.history_mgr.get_share_assocs( self.trans, item1 ) ), 1 )
        self.assertEqual(
            len( self.history_mgr.get_share_assocs( self.trans, item1, user=non_owner ) ), 1 )
        self.assertIsInstance( item1.slug, basestring )

        self.log( "should be able to unshare with specific users" )
        share_assoc = self.history_mgr.unshare_with( self.trans, item1, non_owner )
        self.assertIsInstance( share_assoc, model.HistoryUserShareAssociation )
        self.assertFalse( self.history_mgr.is_accessible( self.trans, item1, non_owner ) )
        self.assertEqual( self.history_mgr.get_share_assocs( self.trans, item1 ), [] )
        self.assertEqual(
            self.history_mgr.get_share_assocs( self.trans, item1, user=non_owner ), [] )

    #TODO: test slug formation

    def test_anon( self ):
        anon_user = None
        self.trans.set_user( anon_user )

        self.log( "should not allow access and owner for anon user on a history by another anon user (None)" )
        anon_history1 = self.history_mgr.create( self.trans, user=None )
        self.assertFalse( self.history_mgr.is_owner( self.trans, anon_history1, anon_user ) )
        self.assertFalse( self.history_mgr.is_accessible( self.trans, anon_history1, anon_user ) )

        self.log( "should allow access and owner for anon user on a history if it's the session's current history" )
        anon_history2 = self.history_mgr.create( self.trans, user=anon_user )
        self.trans.set_history( anon_history2 )
        self.assertTrue( self.history_mgr.is_owner( self.trans, anon_history2, anon_user ) )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, anon_history2, anon_user ) )

        self.log( "should not allow owner or access for anon user on someone elses history" )
        owner = self.user_mgr.create( self.trans, **user2_data )
        someone_elses = self.history_mgr.create( self.trans, user=owner )
        self.assertFalse( self.history_mgr.is_owner( self.trans, someone_elses, anon_user ) )
        self.assertFalse( self.history_mgr.is_accessible( self.trans, someone_elses, anon_user ) )

        self.log( "should allow access for anon user if the history is published or importable" )
        self.history_mgr.make_importable( self.trans, someone_elses )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, someone_elses, anon_user ) )
        self.history_mgr.publish( self.trans, someone_elses )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, someone_elses, anon_user ) )

    def test_delete_and_purge( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        self.trans.set_user( user2 )

        history1 = self.history_mgr.create( self.trans, name='history1', user=user2 )
        self.trans.set_history( history1 )

        self.assertFalse( history1.deleted )

        self.history_mgr.delete( self.trans, history1 )
        self.assertTrue( history1.deleted )

        self.history_mgr.undelete( self.trans, history1 )
        self.assertFalse( history1.deleted )

        history2 = self.history_mgr.create( self.trans, name='history2', user=user2 )
        self.history_mgr.purge( self.trans, history1 )
        self.assertTrue( history1.purged )

    def test_histories( self ):
        user2 = self.user_mgr.create( self.trans, **user2_data )
        self.trans.set_user( user2 )

        history1 = self.history_mgr.create( self.trans, name='history1', user=user2 )
        self.trans.set_history( history1 )
        history2 = self.history_mgr.create( self.trans, name='history2', user=user2 )

        self.log( "should be able to set or get the current history for a user" )
        self.assertEqual( self.history_mgr.get_current( self.trans ), history1 )
        self.assertEqual( self.history_mgr.set_current( self.trans, history2 ), history2 )
        self.assertEqual( self.history_mgr.get_current( self.trans ), history2 )
        self.assertEqual( self.history_mgr.set_current_by_id( self.trans, history1.id ), history1 )
        self.assertEqual( self.history_mgr.get_current( self.trans ), history1 )


    # ---- functional and orm filter splitting and resolution
    def test_parse_filters( self ):
        filter_parser = HistoryFilters( self.app )
        filters = filter_parser.parse_filters([
            ( 'name', 'eq', 'wot' ),
            ( 'deleted', 'eq', 'True' ),
            ( 'annotation', 'in', 'hrrmm' )
        ])
        self.log( 'both orm and fn filters should be parsed and returned' )
        self.assertEqual( len( filters ), 3 )

        self.log( 'values should be parsed' )
        self.assertEqual( filters[1].right.value, True )

    def test_parse_filters_invalid_filters( self ):
        filter_parser = HistoryFilters( self.app )
        self.log( 'should error on non-column attr')
        self.assertRaises( exceptions.RequestParameterInvalidException, filter_parser.parse_filters, [
            ( 'merp', 'eq', 'wot' ),
        ])
        self.log( 'should error on non-whitelisted attr')
        self.assertRaises( exceptions.RequestParameterInvalidException, filter_parser.parse_filters, [
            ( 'user_id', 'eq', 'wot' ),
        ])
        self.log( 'should error on non-whitelisted op')
        self.assertRaises( exceptions.RequestParameterInvalidException, filter_parser.parse_filters, [
            ( 'name', 'lt', 'wot' ),
        ])
        self.log( 'should error on non-listed fn op')
        self.assertRaises( exceptions.RequestParameterInvalidException, filter_parser.parse_filters, [
            ( 'annotation', 'like', 'wot' ),
        ])
        self.log( 'should error on val parsing error')
        self.assertRaises( exceptions.RequestParameterInvalidException, filter_parser.parse_filters, [
            ( 'deleted', 'eq', 'true' ),
        ])

    def test_orm_filter_parsing( self ):
        filter_parser = HistoryFilters( self.app )
        user2 = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=user2 )
        history2 = self.history_mgr.create( self.trans, name='history2', user=user2 )
        history3 = self.history_mgr.create( self.trans, name='history3', user=user2 )

        filters = filter_parser.parse_filters([
            ( 'name', 'like', 'history%' ),
        ])
        histories = self.history_mgr.list( self.trans, filters=filters )
        #for h in histories:
        #    print h.name
        self.assertEqual( histories, [ history1, history2, history3 ])

        filters = filter_parser.parse_filters([ ( 'name', 'like', '%2' ), ])
        self.assertEqual( self.history_mgr.list( self.trans, filters=filters ), [ history2 ])

        filters = filter_parser.parse_filters([ ( 'name', 'eq', 'history2' ), ])
        self.assertEqual( self.history_mgr.list( self.trans, filters=filters ), [ history2 ])

        self.history_mgr.update( self.trans, history1, dict( deleted=True ) )
        filters = filter_parser.parse_filters([ ( 'deleted', 'eq', 'True' ), ])
        self.assertEqual( self.history_mgr.list( self.trans, filters=filters ), [ history1 ])
        filters = filter_parser.parse_filters([ ( 'deleted', 'eq', 'False' ), ])
        self.assertEqual( self.history_mgr.list( self.trans, filters=filters ), [ history2, history3 ])
        self.assertEqual( self.history_mgr.list( self.trans ), [ history1, history2, history3 ])

        self.history_mgr.update( self.trans, history3, dict( deleted=True ) )
        self.history_mgr.update( self.trans, history1, dict( importable=True ) )
        self.history_mgr.update( self.trans, history2, dict( importable=True ) )
        filters = filter_parser.parse_filters([
            ( 'deleted', 'eq', 'True' ),
            ( 'importable', 'eq', 'True' ),
        ])
        self.assertEqual( self.history_mgr.list( self.trans, filters=filters ), [ history1 ])
        self.assertEqual( self.history_mgr.list( self.trans ), [ history1, history2, history3 ])

    def test_fn_filter_parsing( self ):
        filter_parser = HistoryFilters( self.app )
        user2 = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=user2 )
        history2 = self.history_mgr.create( self.trans, name='history2', user=user2 )
        history3 = self.history_mgr.create( self.trans, name='history3', user=user2 )

        filters = filter_parser.parse_filters([ ( 'annotation', 'in', 'no play' ), ])
        anno_filter = filters[0]

        history3.add_item_annotation( self.trans.sa_session, user2, history3, "All work and no play" )
        self.trans.sa_session.flush()

        self.assertTrue( anno_filter( history3 ) )
        self.assertFalse( anno_filter( history2 ) )

        self.assertEqual( self.history_mgr.list( self.trans, filters=filters ), [ history3 ])

        self.log( 'should allow combinations of orm and fn filters' )
        self.history_mgr.update( self.trans, history3, dict( importable=True ) )
        self.history_mgr.update( self.trans, history2, dict( importable=True ) )
        history1.add_item_annotation( self.trans.sa_session, user2, history1, "All work and no play" )
        self.trans.sa_session.flush()

        shining_examples = self.history_mgr.list( self.trans, filters=filter_parser.parse_filters([
            ( 'importable', 'eq', 'True' ),
            ( 'annotation', 'in', 'no play' ),
        ]))
        self.assertEqual( shining_examples, [ history3 ])

    def test_fn_filter_currying( self ):
        filter_parser = HistoryFilters( self.app )
        filter_parser.fn_filter_parsers = {
            'name_len' : { 'op': { 'lt' : lambda i, v: len( i.name ) < v }, 'val': int }
        }
        self.log( 'should be 2 filters now' )
        self.assertEqual( len( filter_parser.fn_filter_parsers ), 1 )
        filters = filter_parser.parse_filters([
            ( 'name_len', 'lt', '4' )
        ])
        self.log( 'should have parsed out a single filter' )
        self.assertEqual( len( filters ), 1 )

        filter_ = filters[0]
        fake = mock.OpenObject()
        fake.name = '123'
        self.log( '123 should return true through the filter' )
        self.assertTrue( filter_( fake ) )
        fake.name = '1234'
        self.log( '1234 should return false through the filter' )
        self.assertFalse( filter_( fake ) )

    def test_list( self ):
        """
        Test limit and offset in conjunction with both orm and fn filtering.
        """
        filter_parser = HistoryFilters( self.app )
        user2 = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=user2 )
        history2 = self.history_mgr.create( self.trans, name='history2', user=user2 )
        history3 = self.history_mgr.create( self.trans, name='history3', user=user2 )
        history4 = self.history_mgr.create( self.trans, name='history4', user=user2 )

        self.history_mgr.delete( self.trans, history1 )
        self.history_mgr.delete( self.trans, history2 )
        self.history_mgr.delete( self.trans, history3 )

        test_annotation = "testing"
        history2.add_item_annotation( self.trans.sa_session, user2, history2, test_annotation )
        self.trans.sa_session.flush()
        history3.add_item_annotation( self.trans.sa_session, user2, history3, test_annotation )
        self.trans.sa_session.flush()
        history3.add_item_annotation( self.trans.sa_session, user2, history4, test_annotation )
        self.trans.sa_session.flush()

        all_histories = [ history1, history2, history3, history4 ]
        deleted_and_annotated = [ history2, history3 ]

        self.log( "no offset, no limit should work" )
        self.assertEqual( self.history_mgr.list( self.trans, offset=None, limit=None ), all_histories )
        self.assertEqual( self.history_mgr.list( self.trans ), all_histories )
        self.log( "no offset, limit should work" )
        self.assertEqual( self.history_mgr.list( self.trans, limit=2 ), [ history1, history2 ] )
        self.log( "offset, no limit should work" )
        self.assertEqual( self.history_mgr.list( self.trans, offset=1 ), [ history2, history3, history4 ] )
        self.log( "offset, limit should work" )
        self.assertEqual( self.history_mgr.list( self.trans, offset=1, limit=1 ), [ history2 ] )

        self.log( "zero limit should return empty list" )
        self.assertEqual( self.history_mgr.list( self.trans, limit=0 ), [] )
        self.log( "past len offset should return empty list" )
        self.assertEqual( self.history_mgr.list( self.trans, offset=len( all_histories ) ), [] )
        self.log( "negative limit should return full list" )
        self.assertEqual( self.history_mgr.list( self.trans, limit=-1 ), all_histories )
        self.log( "negative offset should return full list" )
        self.assertEqual( self.history_mgr.list( self.trans, offset=-1 ), all_histories )

        filters = [ model.History.deleted == True ]
        self.log( "orm filtered, no offset, no limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters )
        self.assertEqual( found, [ history1, history2, history3 ] )
        self.log( "orm filtered, no offset, limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters, limit=2 )
        self.assertEqual( found, [ history1, history2 ] )
        self.log( "orm filtered, offset, no limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters, offset=1 )
        self.assertEqual( found, [ history2, history3 ] )
        self.log( "orm filtered, offset, limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters, offset=1, limit=1 )
        self.assertEqual( found, [ history2 ] )

        filters = filter_parser.parse_filters([ ( 'annotation', 'in', test_annotation ) ])
        self.log( "fn filtered, no offset, no limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters )
        self.assertEqual( found, [ history2, history3, history4 ] )
        self.log( "fn filtered, no offset, limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters, limit=2 )
        self.assertEqual( found, [ history2, history3 ] )
        self.log( "fn filtered, offset, no limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters, offset=1 )
        self.assertEqual( found, [ history3, history4 ] )
        self.log( "fn filtered, offset, limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters, offset=1, limit=1 )
        self.assertEqual( found, [ history3 ] )

        filters = filter_parser.parse_filters([
            ( 'deleted', 'eq', 'True' ),
            ( 'annotation', 'in', test_annotation )
        ])
        self.log( "orm and fn filtered, no offset, no limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters )
        self.assertEqual( found, [ history2, history3 ] )
        self.log( "orm and fn filtered, no offset, limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters, limit=1 )
        self.assertEqual( found, [ history2 ] )
        self.log( "orm and fn filtered, offset, no limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters, offset=1 )
        self.assertEqual( found, [ history3 ] )
        self.log( "orm and fn filtered, offset, limit should work" )
        found = self.history_mgr.list( self.trans, filters=filters, offset=1, limit=1 )
        self.assertEqual( found, [ history3 ] )

        self.log( "orm and fn filtered, zero limit should return empty list" )
        found = self.history_mgr.list( self.trans, filters=filters, limit=0 )
        self.assertEqual( found, [] )
        self.log( "orm and fn filtered, past len offset should return empty list" )
        found = self.history_mgr.list( self.trans, filters=filters, offset=len( deleted_and_annotated ) )
        self.assertEqual( found, [] )
        self.log( "orm and fn filtered, negative limit should return full list" )
        found = self.history_mgr.list( self.trans, filters=filters, limit=-1 )
        self.assertEqual( found, deleted_and_annotated )
        self.log( "orm and fn filtered, negative offset should return full list" )
        found = self.history_mgr.list( self.trans, filters=filters, offset=-1 )
        self.assertEqual( found, deleted_and_annotated )




# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
