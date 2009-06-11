import urllib
import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import *

class TestHistory( TwillTestCase ):

    def test_000_history_options_when_not_logged_in( self ):
        """Testing history options when not logged in"""
        self.logout()
        check_str = 'logged in</a> to store or switch histories.'
        self.history_options( check_str=check_str )
         # Make sure we have created the following accounts
        self.login( email='test1@bx.psu.edu' )
        global regular_user1
        regular_user1 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test1@bx.psu.edu' ).first()
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        self.logout()
        self.login( email='test2@bx.psu.edu' )
        global regular_user2
        regular_user2 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ).first()
        assert regular_user2 is not None, 'Problem retrieving user with email "test2@bx.psu.edu" from the database'
        self.logout()
        self.login( email='test3@bx.psu.edu' )
        global regular_user3
        regular_user3 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test3@bx.psu.edu' ).first()
        assert regular_user3 is not None, 'Problem retrieving user with email "test3@bx.psu.edu" from the database'
    def test_005_deleting_histories( self ):
        """Testing deleting histories"""
        self.logout()
        self.login( email='test@bx.psu.edu' )
        global admin_user
        admin_user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
        # Get the admin_user private role
        global admin_user_private_role
        admin_user_private_role = None
        for role in admin_user.all_roles():
            if role.name == admin_user.email and role.description == 'Private Role for %s' % admin_user.email:
                admin_user_private_role = role
                break
        if not admin_user_private_role:
            raise AssertionError( "Private role not found for user '%s'" % admin_user.email )
        latest_history = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert latest_history is not None, "Problem retrieving latest history from database"
        assert not latest_history.deleted, "After login, associated history is deleted"
        self.delete_history( str( latest_history.id ) )
        latest_history.refresh()
        if not latest_history.deleted:
            raise AssertionError, "Problem deleting history id %d" % latest_history.id
        # Since we deleted the current history, make sure the history frame was refreshed
        self.check_history_for_string( 'Your history is empty.' )
        # We'll now test deleting a list of histories
        # After deleting the current history, a new one should have been created
        global history1
        history1 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history1 is not None, "Problem retrieving history1 from database"
        self.upload_file( '1.bed', dbkey='hg18' )
        self.new_history( name=urllib.quote( 'history2' ) )
        global history2
        history2 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history2 is not None, "Problem retrieving history2 from database"
        self.upload_file( '2.bed', dbkey='hg18' )
        ids = '%s,%s' % ( str( history1.id ), str( history2.id ) )
        self.delete_history( ids )
        # Since we deleted the current history, make sure the history frame was refreshed
        self.check_history_for_string( 'Your history is empty.' )
        try:
            self.view_stored_active_histories( check_str=history1.name )
            raise AssertionError, "History %s is displayed in the active history list after it was deleted" % history1.name
        except:
            pass
        self.view_stored_deleted_histories( check_str=history1.name )
        try:
            self.view_stored_active_histories( check_str=history2.name )
            raise AssertionError, "History %s is displayed in the active history list after it was deleted" % history2.name
        except:
            pass
        self.view_stored_deleted_histories( check_str=history2.name )
        history1.refresh()
        if not history1.deleted:
            raise AssertionError, "Problem deleting history id %d" % history1.id
        if not history1.default_permissions:
            raise AssertionError, "Default permissions were incorrectly deleted from the db for history id %d when it was deleted" % history1.id
        history2.refresh()
        if not history2.deleted:
            raise AssertionError, "Problem deleting history id %d" % history2.id
        if not history2.default_permissions:
            raise AssertionError, "Default permissions were incorrectly deleted from the db for history id %d when it was deleted" % history2.id
    def test_010_history_options_when_logged_in( self ):
        """Testing history options when logged in"""
        self.history_options()
    def test_015_history_rename( self ):
        """Testing renaming a history"""
        global history3
        history3 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history3 is not None, "Problem retrieving history3 from database"
        if history3.deleted:
            raise AssertionError, "History id %d deleted when it should not be" % latest_history.id
        self.rename_history( str( history3.id ), history3.name, new_name=urllib.quote( 'history 3' ) )
    def test_020_history_list( self ):
        """Testing viewing previously stored histories"""
        self.view_stored_active_histories()
    def test_025_history_share( self ):
        """Testing sharing histories containing only public datasets"""
        history3.refresh()
        self.upload_file( '1.bed', dbkey='hg18' )
        # Test sharing a history with yourself
        check_str = "You can't send histories to yourself."
        self.share_history( str( history3.id ), 'test@bx.psu.edu', check_str )
        # Share a history with 1 valid user
        check_str = 'Histories (%s) have been shared with: %s' % ( history3.name, regular_user1.email )
        self.share_history( str( history3.id ), regular_user1.email, check_str )
        # We need to keep track of all shared histories so they can later be deleted
        global history3_copy1
        history3_copy1 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history3_copy1 is not None, "Problem retrieving history3_copy1 from database"
        self.logout()
        self.login( email=regular_user1.email )
        check_str = '%s from %s' % ( history3.name, admin_user.email )
        self.view_stored_active_histories( check_str=check_str )
        # Need to delete history3_copy1
        self.delete_history( id=str( history3_copy1.id ) )
        self.logout()
        self.login( email=admin_user.email )
        # Test sharing a history with an invalid user
        email = 'jack@jill.com'
        check_str = '%s is not a valid Galaxy user.' % email
        self.share_history( str( history3.id ), email, check_str )
        # Test sharing multiple histories with multiple users
        self.new_history()
        global history4
        history4 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history4 is not None, "Problem retrieving history4 from database"
        self.rename_history( str( history4.id ), history4.name, new_name=urllib.quote( 'history 4' ) )
        history4.refresh()
        self.upload_file( '2.bed', dbkey='hg18' )
        id = '%s,%s' % ( str( history3.id ), str( history4.id ) )
        name = '%s,%s' % ( history3.name, history4.name )
        email = '%s,%s' % ( regular_user2.email, regular_user3.email )
        check_str = 'Histories (%s) have been shared with: %s' % ( name, email )
        self.share_history( id, email, check_str )
        # We need to keep track of all shared histories so they can later be deleted
        history3_copy_name = "%s from %s" % ( history3.name, admin_user.email )
        history3_to_use_for_regular_user2 = galaxy.model.History \
            .filter( and_( galaxy.model.History.table.c.name==history3_copy_name,
                           galaxy.model.History.table.c.user_id==regular_user2.id,
                           galaxy.model.History.table.c.deleted==False ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
            .first()
        assert history3_to_use_for_regular_user2 is not None, "Problem retrieving history3_to_use_for_regular_user2 from database" 
        history3_to_use_for_regular_user3 = galaxy.model.History \
            .filter( and_( galaxy.model.History.table.c.name==history3_copy_name,
                           galaxy.model.History.table.c.user_id==regular_user3.id,
                           galaxy.model.History.table.c.deleted==False ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
            .first()
        assert history3_to_use_for_regular_user3 is not None, "Problem retrieving history3_to_use_for_regular_user3 from database"           
        history4_copy_name = "%s from %s" % ( history4.name, admin_user.email )
        history4_to_use_for_regular_user2 = galaxy.model.History \
            .filter( and_( galaxy.model.History.table.c.name==history4_copy_name,
                           galaxy.model.History.table.c.user_id==regular_user2.id,
                           galaxy.model.History.table.c.deleted==False ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
            .first()
        assert history4_to_use_for_regular_user2 is not None, "Problem retrieving history4_to_use_for_regular_user2 from database" 
        history4_to_use_for_regular_user3 = galaxy.model.History \
            .filter( and_( galaxy.model.History.table.c.name==history4_copy_name,
                           galaxy.model.History.table.c.user_id==regular_user3.id,
                           galaxy.model.History.table.c.deleted==False ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
            .first()
        assert history4_to_use_for_regular_user3 is not None, "Problem retrieving history4_to_use_for_regular_user3 from database" 
        self.logout()
        self.login( email=regular_user2.email )
        check_str = '%s from %s' % ( history3.name, admin_user.email )
        self.view_stored_active_histories( check_str=check_str )
        check_str = '%s from %s' % ( history4.name, admin_user.email )
        self.view_stored_active_histories( check_str=check_str )
        # Need to delete the copied histories, so later test runs are valid
        self.delete_history( id=str( history3_to_use_for_regular_user2.id ) )
        self.delete_history( id=str( history4_to_use_for_regular_user2.id ) )
        self.logout()
        self.login( email=regular_user3.email )
        check_str = '%s from %s' % ( history3.name, admin_user.email )
        self.view_stored_active_histories( check_str=check_str )
        check_str = '%s from %s' % ( history4.name, admin_user.email )
        self.view_stored_active_histories( check_str=check_str )
        # Need to delete the copied histories, so later test runs are valid
        self.delete_history( id=str( history3_to_use_for_regular_user3.id ) )
        self.delete_history( id=str( history4_to_use_for_regular_user3.id ) )
        self.logout()
        self.login( email=admin_user.email )
    def test_030_change_permissions_on_current_history( self ):
        """Testing changing permissions on the current history"""
        global history5
        history5 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history5 is not None, "Problem retrieving history5 from database"
        self.rename_history( str( history5.id ), history5.name, new_name=urllib.quote( 'history5' ) )
        history5.refresh()
        # Due to the limitations of twill ( not functional with the permissions forms ), we're forced
        # to do this manually.  At this point, we just want to restrict the access permission on history5
        # to the admin_user
        global access_action
        access_action = galaxy.model.Dataset.permitted_actions.DATASET_ACCESS.action
        dhp = galaxy.model.DefaultHistoryPermissions( history5, access_action, admin_user_private_role )
        dhp.flush()
        self.upload_file( '1.bed', dbkey='hg18' )
        history5_dataset1 = None
        for hda in history5.datasets:
            if hda.name == '1.bed':
                history5_dataset1 = hda.dataset
        assert history5_dataset1 is not None, "Problem retrieving history5_dataset1 from the database"
        # The permissions on the dataset should be restricted from sharing with anyone due to the 
        # inherited history permissions
        restricted = False
        for action in history5_dataset1.actions:
            if action.action == access_action:
                restricted = True
                break
        if not restricted:
            raise AssertionError, "The 'access' permission is not set for history5_dataset1.actions"
    def test_035_sharing_history_by_making_datasets_public( self ):
        """Testing sharing a restricted history by making the datasets public"""
        # We're still logged in as admin_user.email
        check_str = 'The following datasets can be shared with %s by updating their permissions' % regular_user1.email
        action_check_str = 'Histories (%s) have been shared with: %s' % ( history5.name, regular_user1.email )
        self.share_history( str( history5.id ), regular_user1.email, check_str, action='public', action_check_str=action_check_str )
        history5_copy1 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history5_copy1 is not None, "Problem retrieving history5_copy1 from database"
        self.logout()
        self.login( email=regular_user1.email )
        self.visit_url( "%s/history/list" % self.url )
        self.check_page_for_string( history5_copy1.name )
        # Need to delete history5_copy1 on the history list page for regular_user1
        self.delete_history( id=str( history5_copy1.id ) )
        self.logout()
        self.login( email=admin_user.email )
    def test_040_sharing_history_by_making_new_sharing_role( self ):
        """Testing sharing a restricted history by associating a new sharing role with protected datasets"""
        self.switch_history( id=str( history5.id ), name=history5.name )
        # At this point, history5 should have 1 item, 1.bed, which is public.  We'll add another
        # item which will be private to admin_user due to the permissions on history5
        self.upload_file( '2.bed', dbkey='hg18' )
        check_str = 'The following datasets can be shared with %s with no changes' % regular_user1.email
        check_str2 = 'The following datasets can be shared with %s by updating their permissions' % regular_user1.email
        action_check_str = 'Histories (%s) have been shared with: %s' % ( history5.name, regular_user1.email )
        self.share_history( str( history5.id ),
                            regular_user1.email,
                            check_str,
                            check_str2=check_str2,
                            action='private',
                            action_check_str=action_check_str )
        history5_copy2 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history5_copy2 is not None, "Problem retrieving history5_copy2 from database"
        # We should now have a new sharing role
        global sharing_role
        role_name = 'Sharing role for: %s, %s' % ( admin_user.email, regular_user1.email )
        sharing_role = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==role_name ).first()
        if not sharing_role:
            # May have created a sharing role in a previous functional test suite from the opposite direction.
            role_name = 'Sharing role for: %s, %s' % ( regular_user1.email, admin_user.email )
            sharing_role = galaxy.model.Role.filter( and_( galaxy.model.Role.table.c.type==role_type,
                                                           galaxy.model.Role.table.c.name==role_name ) ).first()
        if not sharing_role:
            raise AssertionError( "Privately sharing a dataset did not properly create a sharing role" )
        self.logout()
        self.login( email=regular_user1.email )
        self.visit_url( "%s/history/list" % self.url )
        self.check_page_for_string( history5_copy2.name )
        self.switch_history( id=str( history5_copy2.id ), name=history5_copy2.name )
       # Make sure both datasets are in the history
        self.check_history_for_string( '1.bed' )
        self.check_history_for_string( '2.bed' )
        # Get both new hdas from the db that were created for the shared history
        hda_1_bed = galaxy.model.HistoryDatasetAssociation \
            .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_copy2.id,
                           galaxy.model.HistoryDatasetAssociation.table.c.name=='1.bed' ) ) \
            .first()
        assert hda_1_bed is not None, "Problem retrieving hda_1_bed from database"
        hda_2_bed = galaxy.model.HistoryDatasetAssociation \
            .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_copy2.id,
                           galaxy.model.HistoryDatasetAssociation.table.c.name=='2.bed' ) ) \
            .first()
        assert hda_2_bed is not None, "Problem retrieving hda_2_bed from database"
        # Make sure 1.bed is accessible since it is public
        self.display_history_item( str( hda_1_bed.id ), check_str='chr1' )
        # Make sure 2.bed is accessible since it is associated with a sharing role
        self.display_history_item( str( hda_2_bed.id ), check_str='chr1' )
        # Need to delete history5_copy2 on the history list page for regular_user1
        self.delete_history( id=str( history5_copy2.id ) )
    def test_045_sharing_private_history_with_multiple_users_by_changing_no_permissions( self ):
        """Testing sharing a restricted history with multiple users, making no permission changes"""
        self.logout()
        self.login( email=admin_user.email )
        # History5 can be shared with any user, since it contains a public dataset.  However, only
        # regular_user1 should be able to access history5's 2.bed dataset since it is associated with a
        # sharing role, and regular_user2 should be able to access history5's 1.bed, but not 2.bed even
        # though they can see it in their shared history.
        self.switch_history( id=str( history5.id ), name=history5.name )
        email = '%s,%s' % ( regular_user1.email, regular_user2.email )
        check_str = 'The following datasets can be shared with %s with no changes' % email
        check_str2 = 'The following datasets can be shared with %s by updating their permissions' % email
        action_check_str = 'Histories (%s) have been shared with: %s' % ( history5.name, regular_user1.email )
        self.share_history( str( history5.id ),
                            email,
                            check_str,
                            check_str2=check_str2,
                            action='share',
                            action_check_str=action_check_str )
        # We need to keep track of all shared histories so they can later be deleted
        history5_copy_name = "%s from %s" % ( history5.name, admin_user.email )
        history5_to_use_for_regular_user1 = galaxy.model.History \
            .filter( and_( galaxy.model.History.table.c.name==history5_copy_name,
                           galaxy.model.History.table.c.user_id==regular_user1.id,
                           galaxy.model.History.table.c.deleted==False ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
            .first()
        assert history5_to_use_for_regular_user1 is not None, "Problem retrieving history5_to_use_for_regular_user1 from database" 
        history5_to_use_for_regular_user2 = galaxy.model.History \
            .filter( and_( galaxy.model.History.table.c.name==history5_copy_name,
                           galaxy.model.History.table.c.user_id==regular_user2.id,
                           galaxy.model.History.table.c.deleted==False ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
            .first()
        assert history5_to_use_for_regular_user2 is not None, "Problem retrieving history5_to_use_for_regular_user2 from database" 
        self.logout()
        self.login( email=regular_user1.email )
        check_str = '%s from %s' % ( history5.name, admin_user.email )
        self.view_stored_active_histories( check_str=check_str )
        self.switch_history( id=str( history5_to_use_for_regular_user1.id ), name=history5_to_use_for_regular_user1.name )
        self.check_history_for_string( '1.bed' )
        self.check_history_for_string( '2.bed' )
        # Need to delete the copied histories, so later test runs are valid
        self.delete_history( id=str( history5_to_use_for_regular_user1.id ) )
        self.logout()
        # Make sure test2@bx.psu.edu received a copy of history5, with only 1.bed accessible
        self.login( email=regular_user2.email )
        self.view_stored_active_histories( check_str=check_str )
        self.switch_history( id=str( history5_to_use_for_regular_user2.id ), name=history5_to_use_for_regular_user2.name )
        self.check_history_for_string( '1.bed' )
        self.check_history_for_string( '2.bed' )
        # Get both new hdas from the db that were created for the shared history
        hda_1_bed = galaxy.model.HistoryDatasetAssociation \
            .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_to_use_for_regular_user1.id,
                           galaxy.model.HistoryDatasetAssociation.table.c.name=='1.bed' ) ) \
            .first()
        assert hda_1_bed is not None, "Problem retrieving hda_1_bed from database"
        hda_2_bed = galaxy.model.HistoryDatasetAssociation \
            .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_to_use_for_regular_user1.id,
                           galaxy.model.HistoryDatasetAssociation.table.c.name=='2.bed' ) ) \
            .first()
        assert hda_2_bed is not None, "Problem retrieving hda_2_bed from database"
        # Make sure 1.bed is accessible since it is public
        self.display_history_item( str( hda_1_bed.id ), check_str='chr1' )
        # Make sure 2.bed is not accessible since it is protected
        try:
            self.display_history_item( str( hda_2_bed.id ), check_str='chr1' )
            raise AssertionError, "History item 2.bed is accessible by user %s when is should not be" % regular_user2.email
        except:
            pass
        self.check_history_for_string( 'You do not have permission to view this dataset' )
        # Need to delete the copied histories, so later test runs are valid
        self.delete_history( id=str( history5_to_use_for_regular_user2.id ) )
    def test_050_sharing_private_history_by_choosing_to_not_share( self ):
        """Testing sharing a restricted history with multiple users by choosing not to share"""
        self.logout()
        self.login( email=admin_user.email )
        self.switch_history( id=str( history5.id ), name=history5.name )
        email = '%s,%s' % ( regular_user1.email, regular_user2.email )
        check_str = 'The following datasets can be shared with %s with no changes' % email
        check_str2 = 'The following datasets can be shared with %s by updating their permissions' % email
        action_check_str = 'History Options'
        self.share_history( str( history5.id ),
                            email,
                            check_str,
                            check_str2=check_str2,
                            action='no_share' )
    def test_055_history_show_and_hide_deleted_datasets( self ):
        """Testing displaying deleted history items"""
        self.new_history( name=urllib.quote( 'show hide deleted datasets' ) )
        self.upload_file('1.bed', dbkey='hg18')
        latest_hda = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        self.home()
        self.visit_url( "%s/root/delete?show_deleted_on_refresh=False&id=%s" % ( self.url, str( latest_hda.id ) ) )
        self.check_history_for_string( 'Your history is empty' )
        self.home()
        self.visit_url( "%s/history/?show_deleted=True" % self.url )
        self.check_page_for_string( 'This dataset has been deleted.' )
        self.check_page_for_string( '1.bed' )
        self.home()
        self.visit_url( "%s/history/?show_deleted=False" % self.url )
        self.check_page_for_string( 'Your history is empty' )
    def test_060_deleting_and_undeleting_history_items( self ):
        """Testing deleting and un-deleting history items"""
        self.new_history( name=urllib.quote( 'delete undelete history items' ) )
        # Add a new history item
        self.upload_file( '1.bed', dbkey='hg15' )
        self.home()
        self.visit_url( "%s/history/?show_deleted=False" % self.url )
        self.check_page_for_string( '1.bed' )
        self.check_page_for_string( 'hg15' )
        self.assertEqual ( len( self.get_history() ), 1 )
        # Delete the history item
        self.delete_history_item( 1, check_str="Your history is empty" )
        self.assertEqual ( len( self.get_history() ), 0 )
        # Try deleting an invalid hid
        try:
            self.delete_history_item( 'XXX' )
            raise AssertionError, "Inproperly able to delete hid 'XXX' which is not an integer"
        except:
            pass
        # Undelete the history item
        self.undelete_history_item( 1, show_deleted=True )
        self.home()
        self.visit_url( "%s/history/?show_deleted=False" % self.url )
        self.check_page_for_string( '1.bed' )
        self.check_page_for_string( 'hg15' )
    def test_065_copying_history_items_between_histories( self ):
        """Testing copying history items between histories"""
        self.new_history( name=urllib.quote( 'copy history items' ) )
        global history6
        history6 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history6 is not None, "Problem retrieving history6 from database"
        self.upload_file( '1.bed', dbkey='hg18' )
        hda1 = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        assert hda1 is not None, "Problem retrieving hda1 from database"
        # We'll just test copying 1 hda
        source_dataset_ids=str( hda1.id )
        # The valid list of target histories is only the user's active histories
        all_target_history_ids = [ str( hda.id ) for hda in admin_user.active_histories ]
        # Since history1 and history2 have been deleted, they should not be displayed in the list of target histories
        # on the copy_view.mako form
        deleted_history_ids = [ str( history1.id ), str( history2.id ) ]
        # Test copying to the current history
        target_history_ids=[ str( history6.id ) ]
        self.copy_history_item( source_dataset_ids=source_dataset_ids,
                                target_history_ids=target_history_ids,
                                all_target_history_ids=all_target_history_ids,
                                deleted_history_ids=deleted_history_ids )
        history6.refresh()
        if len( history6.datasets ) != 2:
            raise AssertionError, "Copying hda1 to the current history failed"
        # Test copying 1 hda to another history
        self.new_history( name=urllib.quote( 'copy history items - 2' ) )
        global history7
        history7 = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        assert history7 is not None, "Problem retrieving history7 from database"
        # Switch back to our history from which we want to copy
        self.switch_history( id=str( history6.id ), name=history6.name )
        target_history_ids=[ str( history7.id ) ]
        all_target_history_ids = [ str( hda.id ) for hda in admin_user.active_histories ]
        # Test copying to the a history that is not the current history
        target_history_ids=[ str( history7.id ) ]
        self.copy_history_item( source_dataset_ids=source_dataset_ids,
                                target_history_ids=target_history_ids,
                                all_target_history_ids=all_target_history_ids,
                                deleted_history_ids=deleted_history_ids )
        # Switch to the history to which we copied
        self.switch_history( id=str( history7.id ), name=history7.name )
        self.check_history_for_string( hda1.name )
    def test_070_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        self.delete_history( id=str( history3.id ) )
        self.delete_history( id=str( history4.id ) )
        self.delete_history( id=str( history5.id ) )
        self.delete_history( id=str( history6.id ) )
        self.delete_history( id=str( history7.id ) )
