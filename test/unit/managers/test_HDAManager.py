# -*- coding: utf-8 -*-
import sys
import os
import pprint
import unittest

__GALAXY_ROOT__ = os.getcwd() + '/../../../'
sys.path.insert( 1, __GALAXY_ROOT__ + 'lib' )

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
from galaxy.managers import hdas


# =============================================================================
default_password = '123456'
user2_data = dict( email='user2@user2.user2', username='user2', password=default_password )
user3_data = dict( email='user3@user3.user3', username='user3', password=default_password )

class HDATestCase( BaseTestCase ):

    def set_up_managers( self ):
        super( HDATestCase, self ).set_up_managers()
        self.hda_mgr = hdas.HDAManager( self.app )
        self.history_mgr = HistoryManager( self.app )
        self.dataset_mgr = DatasetManager( self.app )

    def _create_vanilla_hda( self, user_data=None ):
        user_data = user_data or user2_data
        owner = self.user_mgr.create( self.trans, **user_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )
        return self.hda_mgr.create( self.trans, history=history1, dataset=dataset1 )


# =============================================================================
class HDAManagerTestCase( HDATestCase ):

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
        hda2 = self.hda_mgr.copy( self.trans, hda1, history=history1 )
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

    def test_error_if_uploading( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )
        hda = self.hda_mgr.create( self.trans, history=history1, dataset=dataset1 )

        hda.state = model.Dataset.states.OK
        self.log( "should not raise an error when calling error_if_uploading and in a non-uploading state" )
        self.assertEqual( self.hda_mgr.error_if_uploading( self.trans, hda ), hda )

        hda.state = model.Dataset.states.UPLOAD
        self.log( "should raise an error when calling error_if_uploading and in the uploading state" )
        self.assertRaises( exceptions.Conflict,
            self.hda_mgr.error_if_uploading, self.trans, hda )

    def test_data_conversion_status( self ):
        owner = self.user_mgr.create( self.trans, **user2_data )
        history1 = self.history_mgr.create( self.trans, name='history1', user=owner )
        dataset1 = self.dataset_mgr.create( self.trans )
        hda = self.hda_mgr.create( self.trans, history=history1, dataset=dataset1 )

        self.log( "data conversion status should reflect state" )
        self.assertEqual( self.hda_mgr.data_conversion_status( self.trans, None ),
            hda.conversion_messages.NO_DATA )
        hda.state = model.Dataset.states.ERROR
        self.assertEqual( self.hda_mgr.data_conversion_status( self.trans, hda ),
            hda.conversion_messages.ERROR )
        hda.state = model.Dataset.states.QUEUED
        self.assertEqual( self.hda_mgr.data_conversion_status( self.trans, hda ),
            hda.conversion_messages.PENDING )
        hda.state = model.Dataset.states.OK
        self.assertEqual( self.hda_mgr.data_conversion_status( self.trans, hda ), None )

    # def test_text_data( self ):


# =============================================================================
# web.url_for doesn't work well in the framework
testable_url_for = lambda *a, **k: '(fake url): %s, %s' % ( a, k )
hdas.HDASerializer.url_for = staticmethod( testable_url_for )

class HDASerializerTestCase( HDATestCase ):

    def set_up_managers( self ):
        super( HDASerializerTestCase, self ).set_up_managers()
        self.hda_serializer = hdas.HDASerializer( self.app )

    def test_views( self ):
        hda = self._create_vanilla_hda()

        self.log( 'should have a summary view' )
        summary_view = self.hda_serializer.serialize_to_view( self.trans, hda, view='summary' )
        self.assertKeys( summary_view, self.hda_serializer.views[ 'summary' ] )

        self.log( 'should have the summary view as default view' )
        default_view = self.hda_serializer.serialize_to_view( self.trans, hda, default_view='summary' )
        self.assertKeys( summary_view, self.hda_serializer.views[ 'summary' ] )

        # self.log( 'should have a detailed view' )
        # detailed_view = self.hda_serializer.serialize_to_view( self.trans, hda, view='detailed' )
        # self.assertKeys( detailed_view, self.hda_serializer.views[ 'detailed' ] )

        # self.log( 'should have a extended view' )
        # extended_view = self.hda_serializer.serialize_to_view( self.trans, hda, view='extended' )
        # self.assertKeys( extended_view, self.hda_serializer.views[ 'extended' ] )

        self.log( 'should have a inaccessible view' )
        inaccessible_view = self.hda_serializer.serialize_to_view( self.trans, hda, view='inaccessible' )
        self.assertKeys( inaccessible_view, self.hda_serializer.views[ 'inaccessible' ] )

        # skip metadata for this test
        def is_metadata( key ):
            return ( key == 'metadata'
                  or key.startswith( 'metadata_' ) )

        self.log( 'should have a serializer for all serializable keys' )
        for key in self.hda_serializer.serializable_keyset:
            instantiated_attribute = getattr( hda, key, None )
            if not ( ( key in self.hda_serializer.serializers )
                  or ( isinstance( instantiated_attribute, self.TYPES_NEEDING_NO_SERIALIZERS ) )
                  or ( is_metadata( key ) ) ):
                self.fail( 'no serializer for: %s (%s)' % ( key, instantiated_attribute ) )
        else:
            self.assertTrue( True, 'all serializable keys have a serializer' )

    def test_views_and_keys( self ):
        hda = self._create_vanilla_hda()

        self.log( 'should be able to use keys with views' )
        serialized = self.hda_serializer.serialize_to_view( self.trans, hda,
            view='summary', keys=[ 'uuid' ] )
        self.assertKeys( serialized,
            self.hda_serializer.views[ 'summary' ] + [ 'uuid' ] )

        self.log( 'should be able to use keys on their own' )
        serialized = self.hda_serializer.serialize_to_view( self.trans, hda,
            keys=[ 'file_path', 'visualizations' ] )
        self.assertKeys( serialized, [ 'file_path', 'visualizations' ] )

    def test_serializers( self ):
        hda = self._create_vanilla_hda()
        all_keys = list( self.hda_serializer.serializable_keyset )
        serialized = self.hda_serializer.serialize( self.trans, hda, all_keys )

        self.log( 'everything serialized should be of the proper type' )
        # base
        self.assertEncodedId( serialized[ 'id' ] )
        self.assertDate( serialized[ 'create_time' ] )
        self.assertDate( serialized[ 'update_time' ] )

        # dataset association
        self.assertIsInstance( serialized[ 'dataset' ], dict )
        self.assertEncodedId( serialized[ 'dataset_id' ] )
        self.assertUUID( serialized[ 'uuid' ] )
        self.assertIsInstance( serialized[ 'file_name' ], basestring )
        self.assertIsInstance( serialized[ 'extra_files_path' ], basestring )
        self.assertIsInstance( serialized[ 'permissions' ], dict )
        self.assertIsInstance( serialized[ 'size' ], int )
        self.assertIsInstance( serialized[ 'file_size' ], int )
        self.assertIsInstance( serialized[ 'nice_size' ], basestring )
        # TODO: these should be tested w/copy
        self.assertNullableEncodedId( serialized[ 'copied_from_history_dataset_association_id'] )
        self.assertNullableEncodedId( serialized[ 'copied_from_library_dataset_dataset_association_id'] )
        self.assertNullableBasestring( serialized[ 'info' ] )
        self.assertNullableBasestring( serialized[ 'blurb' ] )
        self.assertNullableBasestring( serialized[ 'peek' ] )
        self.assertIsInstance( serialized[ 'meta_files' ], list )
        self.assertNullableEncodedId( serialized[ 'parent_id'] )
        self.assertEqual( serialized[ 'designation' ], None )
        self.assertIsInstance( serialized[ 'genome_build' ], basestring )
        self.assertIsInstance( serialized[ 'data_type' ], basestring )

        # hda
        self.assertEncodedId( serialized[ 'history_id' ] )
        self.assertEqual( serialized[ 'type_id' ], 'dataset-' + serialized[ 'id' ] )

        self.assertIsInstance( serialized[ 'resubmitted' ], bool )
        self.assertIsInstance( serialized[ 'display_apps' ], list )
        self.assertIsInstance( serialized[ 'display_types' ], list )
        self.assertIsInstance( serialized[ 'visualizations' ], list )

        # remapped
        self.assertNullableBasestring( serialized[ 'misc_info' ] )
        self.assertNullableBasestring( serialized[ 'misc_blurb' ] )
        self.assertNullableBasestring( serialized[ 'file_ext' ] )
        self.assertNullableBasestring( serialized[ 'file_path' ] )

        # identities
        self.assertEqual( serialized[ 'model_class' ], 'HistoryDatasetAssociation' )
        self.assertEqual( serialized[ 'history_content_type' ], 'dataset' )
        self.assertEqual( serialized[ 'hda_ldda' ], 'hda' )
        self.assertEqual( serialized[ 'accessible' ], True )
        self.assertEqual( serialized[ 'api_type' ], 'file' )
        self.assertEqual( serialized[ 'type' ], 'file' )

        self.assertIsInstance( serialized[ 'url' ], basestring )
        self.assertIsInstance( serialized[ 'urls' ], dict )
        self.assertIsInstance( serialized[ 'download_url' ], basestring )

        self.log( 'serialized should jsonify well' )
        self.assertIsJsonifyable( serialized )


# =============================================================================
class HDADeserializerTestCase( HDATestCase ):

    def set_up_managers( self ):
        super( HDADeserializerTestCase, self ).set_up_managers()
        self.hda_deserializer = hdas.HDADeserializer( self.app )

    def test_deserialize_delete( self ):
        hda = self._create_vanilla_hda()

        self.log( 'should raise when deserializing deleted from non-bool' )
        self.assertFalse( hda.deleted )
        self.assertRaises( exceptions.RequestParameterInvalidException,
            self.hda_deserializer.deserialize, self.trans, hda, data={ 'deleted': None } )
        self.assertFalse( hda.deleted )
        self.log( 'should be able to deserialize deleted from True' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'deleted': True } )
        self.assertTrue( hda.deleted )
        self.log( 'should be able to reverse by deserializing deleted from False' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'deleted': False } )
        self.assertFalse( hda.deleted )

    def test_deserialize_purge( self ):
        hda = self._create_vanilla_hda()

        self.log( 'should raise when deserializing purged from non-bool' )
        self.assertRaises( exceptions.RequestParameterInvalidException,
            self.hda_deserializer.deserialize, self.trans, hda, data={ 'purged': None } )
        self.assertFalse( hda.purged )
        self.log( 'should be able to deserialize purged from True' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'purged': True } )
        self.assertTrue( hda.purged )
        # TODO: should this raise an error?
        self.log( 'should NOT be able to deserialize purged from False (will remain True)' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'purged': False } )
        self.assertTrue( hda.purged )

    def test_deserialize_visible( self ):
        hda = self._create_vanilla_hda()

        self.log( 'should raise when deserializing from non-bool' )
        self.assertTrue( hda.visible )
        self.assertRaises( exceptions.RequestParameterInvalidException,
            self.hda_deserializer.deserialize, self.trans, hda, data={ 'visible': 'None' } )
        self.assertTrue( hda.visible )
        self.log( 'should be able to deserialize from False' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'visible': False } )
        self.assertFalse( hda.visible )
        self.log( 'should be able to reverse by deserializing from True' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'visible': True } )
        self.assertTrue( hda.visible )

    def test_deserialize_genome_build( self ):
        hda = self._create_vanilla_hda()

        self.assertIsInstance( hda.dbkey, basestring )
        self.log( 'should deserialize to "?" from None' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'genome_build': None } )
        self.assertEqual( hda.dbkey, '?' )
        self.log( 'should raise when deserializing from non-string' )
        self.assertRaises( exceptions.RequestParameterInvalidException,
            self.hda_deserializer.deserialize, self.trans, hda, data={ 'genome_build': 12 } )
        self.log( 'should be able to deserialize from unicode' )
        date_palm = u'نخيل التمر'
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'genome_build': date_palm } )
        self.assertEqual( hda.dbkey, date_palm )
        self.log( 'should be deserializable from empty string' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'genome_build': '' } )
        self.assertEqual( hda.dbkey, '' )

    def test_deserialize_name( self ):
        hda = self._create_vanilla_hda()

        self.log( 'should raise when deserializing from non-string' )
        self.assertRaises( exceptions.RequestParameterInvalidException,
            self.hda_deserializer.deserialize, self.trans, hda, data={ 'name': True } )
        self.log( 'should raise when deserializing from None' )
        self.assertRaises( exceptions.RequestParameterInvalidException,
            self.hda_deserializer.deserialize, self.trans, hda, data={ 'name': None } )
        # self.log( 'should deserialize to empty string from None' )
        # self.hda_deserializer.deserialize( self.trans, hda, data={ 'name': None } )
        # self.assertEqual( hda.name, '' )
        self.log( 'should be able to deserialize from unicode' )
        olive = u'ελιά'
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'name': olive } )
        self.assertEqual( hda.name, olive )
        self.log( 'should be deserializable from empty string' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'name': '' } )
        self.assertEqual( hda.name, '' )

    def test_deserialize_info( self ):
        hda = self._create_vanilla_hda()

        self.log( 'should raise when deserializing from non-string' )
        self.assertRaises( exceptions.RequestParameterInvalidException,
            self.hda_deserializer.deserialize, self.trans, hda, data={ 'info': True } )
        self.log( 'should raise when deserializing from None' )
        self.assertRaises( exceptions.RequestParameterInvalidException,
            self.hda_deserializer.deserialize, self.trans, hda, data={ 'info': None } )
        self.log( 'should be able to deserialize from unicode' )
        rice = u'飯'
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'info': rice } )
        self.assertEqual( hda.info, rice )
        self.log( 'should be deserializable from empty string' )
        self.hda_deserializer.deserialize( self.trans, hda, data={ 'info': '' } )
        self.assertEqual( hda.info, '' )


# =============================================================================
class HDAFilterParserTestCase( HDATestCase ):

    def set_up_managers( self ):
        super( HDAFilterParserTestCase, self ).set_up_managers()
        self.filter_parser = hdas.HDAFilterParser( self.app )

    def test_parsable( self ):
        self.log( 'the following filters should be parsable' )
        # base
        self.assertORMFilter( self.filter_parser.parse_filter( 'id', 'in', [ 1, 2 ] ) )
        encoded_id_string = ','.join([ self.app.security.encode_id( id_ ) for id_ in [ 1, 2 ] ] )
        self.assertORMFilter( self.filter_parser.parse_filter( 'encoded_id', 'in', encoded_id_string ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'create_time', 'le', '2015-03-15' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'create_time', 'ge', '2015-03-15' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'update_time', 'le', '2015-03-15' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'update_time', 'ge', '2015-03-15' ) )
        # purgable
        self.assertORMFilter( self.filter_parser.parse_filter( 'deleted', 'eq', True ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'purged', 'eq', True ) )
        # dataset asociation
        self.assertORMFilter( self.filter_parser.parse_filter( 'name', 'eq', 'wot' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'name', 'contains', 'wot' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'name', 'like', 'wot' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'state', 'eq', 'ok' ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'state', 'in', [ 'queued', 'running' ] ) )
        self.assertORMFilter( self.filter_parser.parse_filter( 'visible', 'eq', True ) )
        self.assertFnFilter( self.filter_parser.parse_filter( 'genome_build', 'eq', 'wot' ) )
        self.assertFnFilter( self.filter_parser.parse_filter( 'genome_build', 'contains', 'wot' ) )
        self.assertFnFilter( self.filter_parser.parse_filter( 'data_type', 'eq', 'wot' ) )
        self.assertFnFilter( self.filter_parser.parse_filter( 'data_type', 'isinstance', 'wot' ) )
        # taggable
        self.assertFnFilter( self.filter_parser.parse_filter( 'tag', 'eq', 'wot' ) )
        self.assertFnFilter( self.filter_parser.parse_filter( 'tag', 'has', 'wot' ) )
        # annotatable
        self.assertFnFilter( self.filter_parser.parse_filter( 'annotation', 'has', 'wot' ) )


    def test_genome_build_filters( self ):
        pass

    def test_data_type_filters( self ):
        pass


# =============================================================================
if __name__ == '__main__':
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
