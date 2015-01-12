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

        query = self.history_mgr._query_by_user( self.trans, owner )
        self.assertEqual( query.all(), user_histories )

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

        self.log( "should be able to share with specific users" )
        share_assoc = self.history_mgr.share_with( self.trans, item1, non_owner )
        self.assertIsInstance( share_assoc, model.HistoryUserShareAssociation )
        self.assertTrue( self.history_mgr.is_accessible( self.trans, item1, non_owner ) )
        self.assertEqual(
            len( self.history_mgr.get_share_assocs( self.trans, item1 ) ), 1 )
        self.assertEqual(
            len( self.history_mgr.get_share_assocs( self.trans, item1, user=non_owner ) ), 1 )

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


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
