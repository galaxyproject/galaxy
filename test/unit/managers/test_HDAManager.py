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
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.hdas import HDAManager


# =============================================================================
default_password = '123456'
user2_data = dict( email='user2@user2.user2', username='user2', password=default_password )
user3_data = dict( email='user3@user3.user3', username='user3', password=default_password )


# =============================================================================
class HDAManagerTestCase( BaseTestCase ):

    def set_up_managers( self ):
        super( HDAManagerTestCase, self ).set_up_managers()
        self.history_mgr = HistoryManager( self.app )
        self.dataset_mgr = DatasetManager( self.app )
        self.hda_mgr = HDAManager( self.app )

    def test_base( self ):
        hda_model = model.HistoryDatasetAssociation
        owner = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        hda1 = self.hda_mgr.create( self.trans, history=history1, hid=1 )
        hda2 = self.hda_mgr.create( self.trans, history=history1, hid=2 )
        hda3 = self.hda_mgr.create( self.trans, history=history1, hid=3 )

        self.log( "should be able to query" )
        hdas = self.trans.sa_session.query( hda_model ).all()
        self.assertEqual( self.hda_mgr.list( self.trans ), hdas )
        self.assertEqual( self.hda_mgr.one( self.trans, filters=( hda_model.id == hda1.id ) ), hda1 )
        self.assertEqual( self.hda_mgr.by_id( self.trans, hda1.id ), hda1 )
        self.assertEqual( self.hda_mgr.by_ids( self.trans, [ hda2.id, hda1.id ] ), [ hda2, hda1 ] )

        self.log( "should be able to limit and offset" )
        self.assertEqual( self.hda_mgr.list( self.trans, limit=1 ), hdas[0:1] )
        self.assertEqual( self.hda_mgr.list( self.trans, offset=1 ), hdas[1:] )
        self.assertEqual( self.hda_mgr.list( self.trans, limit=1, offset=1 ), hdas[1:2] )

        self.assertEqual( self.hda_mgr.list( self.trans, limit=0 ), [] )
        self.assertEqual( self.hda_mgr.list( self.trans, offset=3 ), [] )

        self.log( "should be able to order" )
        self.assertEqual( self.hda_mgr.list( self.trans, order_by=sqlalchemy.desc( hda_model.create_time ) ),
            [ hda3, hda2, hda1 ] )

    def test_create( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        non_owner = self.user_mgr.create( self.trans, **user3_data )

        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )

        self.log( "should be able to create a new HDA with a specified history and dataset" )
        hda1 = self.hda_mgr.create( self.trans, history=history1, dataset=dataset1 )
        self.assertIsInstance( hda1, model.HistoryDatasetAssociation )
        self.assertEqual( hda1, self.trans.sa_session.query( model.HistoryDatasetAssociation ).get( hda1.id ) )
        self.assertEqual( hda1.history, history1 )
        self.assertEqual( hda1.dataset, dataset1 )
        self.assertEqual( hda1.hid, 1 )

        self.log( "should be able to create a new HDA with only a specified history and no dataset" )
        hda2 = self.hda_mgr.create( self.trans, history=history1 )
        self.assertIsInstance( hda2, model.HistoryDatasetAssociation )
        self.assertIsInstance( hda2.dataset, model.Dataset )
        self.assertEqual( hda2.history, history1 )
        self.assertEqual( hda2.hid, 2 )

        self.log( "should be able to create a new HDA with no history and no dataset" )
        hda3 = self.hda_mgr.create( self.trans, hid=None )
        self.assertIsInstance( hda3, model.HistoryDatasetAssociation )
        self.assertIsInstance( hda3.dataset, model.Dataset, msg="dataset will be auto created" )
        self.assertIsNone( hda3.history, msg="history will be None" )
        self.assertEqual( hda3.hid, None, msg="should allow setting hid to None (or any other value)" )

    def test_copy_from_hda( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )
        hda1 = self.hda_mgr.create( self.trans, history=history1, dataset=dataset1 )

        self.log( "should be able to copy an HDA" )
        hda2 = self.hda_mgr.copy_hda( self.trans, hda1, history=history1 )
        self.assertIsInstance( hda2, model.HistoryDatasetAssociation )
        self.assertEqual( hda2, self.trans.sa_session.query( model.HistoryDatasetAssociation ).get( hda2.id ) )
        self.assertEqual( hda2.name, hda1.name )
        self.assertEqual( hda2.history, hda1.history )
        self.assertEqual( hda2.dataset, hda1.dataset )
        self.assertNotEqual( hda2, hda1 )

    #def test_copy_from_ldda( self ):
    #    owner = self.user_mgr.create( self.trans, **user2_data )
    #    history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
    #
    #    self.log( "should be able to copy an HDA" )
    #    hda2 = self.hda_mgr.copy_ldda( self.trans, history1, hda1 )

    def test_delete( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )
        item1 = self.hda_mgr.create( self.trans, history=history1, dataset=dataset1 )

        self.log( "should be able to delete and undelete an hda" )
        self.assertFalse( item1.deleted )
        self.assertEqual( self.hda_mgr.delete( self.trans, item1 ), item1 )
        self.assertTrue( item1.deleted )
        self.assertEqual( self.hda_mgr.undelete( self.trans, item1 ), item1 )
        self.assertFalse( item1.deleted )

    def test_purge_allowed( self ):
        self.trans.app.config.allow_user_dataset_purge = True

        owner = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )
        item1 = self.hda_mgr.create( self.trans, history=history1, dataset=dataset1 )

        self.log( "should purge an hda if config does allow" )
        self.assertFalse( item1.purged )
        self.assertEqual( self.hda_mgr.purge( self.trans, item1 ), item1 )
        self.assertTrue( item1.purged )

    def test_purge_not_allowed( self ):
        self.trans.app.config.allow_user_dataset_purge = False

        owner = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )
        item1 = self.hda_mgr.create( self.trans, history=history1, dataset=dataset1 )

        self.log( "should raise an error when purging an hda if config does not allow" )
        self.assertFalse( item1.purged )
        self.assertRaises( exceptions.ConfigDoesNotAllowException, self.hda_mgr.purge, self.trans, item1 )
        self.assertFalse( item1.purged )

    def test_ownable( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        non_owner = self.user_mgr.create( self.trans, **user3_data )

        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )
        item1 = self.hda_mgr.create( self.trans, history1, dataset1 )

        self.log( "should be able to poll whether a given user owns an item" )
        self.assertTrue(  self.hda_mgr.is_owner( self.trans, item1, owner ) )
        self.assertFalse( self.hda_mgr.is_owner( self.trans, item1, non_owner ) )

        self.log( "should raise an error when checking ownership with non-owner" )
        self.assertRaises( exceptions.ItemOwnershipException,
            self.hda_mgr.error_unless_owner, self.trans, item1, non_owner )

        self.log( "should raise an error when checking ownership with anonymous" )
        self.assertRaises( exceptions.ItemOwnershipException,
            self.hda_mgr.error_unless_owner, self.trans, item1, None )

        self.log( "should not raise an error when checking ownership with owner" )
        self.assertEqual( self.hda_mgr.error_unless_owner( self.trans, item1, owner ), item1 )

        self.log( "should not raise an error when checking ownership with admin" )
        self.assertEqual( self.hda_mgr.error_unless_owner( self.trans, item1, self.admin_user ), item1 )

    def test_accessible( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        non_owner = self.user_mgr.create( self.trans, **user3_data )

        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )
        item1 = self.hda_mgr.create( self.trans, history1, dataset1 )

        self.log( "(by default, dataset permissions are lax) should be accessible to all" )
        for user in self.user_mgr.list( self.trans ):
            self.assertTrue( self.hda_mgr.is_accessible( self.trans, item1, user ) )

        #TODO: set perms on underlying dataset and then test accessible

    def test_anon( self ):
        anon_user = None
        self.trans.set_user( anon_user )

        history1 = self.history_mgr.create( self.trans, name='anon_history', user=anon_user )
        self.trans.set_history( history1 )
        dataset1 = self.dataset_mgr.create( self.trans )
        item1 = self.hda_mgr.create( self.trans, history1, dataset1 )

        self.log( "should not raise an error when checking ownership/access on anonymous' own dataset" )
        self.assertTrue( self.hda_mgr.is_accessible( self.trans, item1, anon_user ) )
        self.assertEqual( self.hda_mgr.error_unless_owner( self.trans, item1, anon_user ), item1 )

        self.log( "should raise an error when checking ownership on anonymous' dataset with other user" )
        non_owner = self.user_mgr.create( self.trans, **user3_data )
        self.assertRaises( exceptions.ItemOwnershipException,
            self.hda_mgr.error_unless_owner, self.trans, item1, non_owner )


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
