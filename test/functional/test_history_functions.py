import urllib
import galaxy.model
from galaxy.model.orm import *
from galaxy.model.mapping import context as sa_session
from base.twilltestcase import *

class TestHistory( TwillTestCase ):

    def test_000_history_behavior_between_logout_login( self ):
        """Testing history behavior between logout and login"""
        self.logout()
        self.history_options()
        # Create a new, empty history named anonymous
        name = 'anonymous'
        self.new_history( name=name )
        global anonymous_history
        anonymous_history = sa_session.query( galaxy.model.History ) \
                                      .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                     galaxy.model.History.table.c.name==name ) ) \
                                      .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                      .first()
        assert anonymous_history is not None, "Problem retrieving anonymous_history from database"
        # Upload a dataset to anonymous_history so it will be set as the current history after login
        self.upload_file( '1.bed', dbkey='hg18' )
        self.login( email='test1@bx.psu.edu', username='regular-user1' )
        global regular_user1
        regular_user1 = sa_session.query( galaxy.model.User ) \
                                  .filter( galaxy.model.User.table.c.email=='test1@bx.psu.edu' ) \
                                  .first()
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        # Current history should be anonymous_history
        self.check_history_for_string( name )
        self.logout()
        # Login as the same user again to ensure anonymous_history is still the current history
        self.login( email=regular_user1.email )
        self.check_history_for_string( name )
        self.logout()
        self.login( email='test2@bx.psu.edu', username='regular-user2' )
        global regular_user2
        regular_user2 = sa_session.query( galaxy.model.User ) \
                                  .filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ) \
                                  .first()
        assert regular_user2 is not None, 'Problem retrieving user with email "test2@bx.psu.edu" from the database'
        self.logout()
        self.login( email='test3@bx.psu.edu', username='regular-user3' )
        global regular_user3
        regular_user3 = sa_session.query( galaxy.model.User ) \
                                  .filter( galaxy.model.User.table.c.email=='test3@bx.psu.edu' ) \
                                  .first()
        assert regular_user3 is not None, 'Problem retrieving user with email "test3@bx.psu.edu" from the database'
        self.logout()
        self.login( email='test@bx.psu.edu', username='admin-user' )
        global admin_user
        admin_user = sa_session.query( galaxy.model.User ) \
                               .filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ) \
                               .one()
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
        # Get the admin_user private role for later use
        global admin_user_private_role
        admin_user_private_role = None
        for role in admin_user.all_roles():
            if role.name == admin_user.email and role.description == 'Private Role for %s' % admin_user.email:
                admin_user_private_role = role
                break
        if not admin_user_private_role:
            raise AssertionError( "Private role not found for user '%s'" % admin_user.email )
        historyA = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert historyA is not None, "Problem retrieving historyA from database"
        assert not historyA.deleted, "After login, historyA is deleted"
        # Make sure the last used history is set for the next session after login
        self.logout()
        self.login( email=admin_user.email )
        historyB = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert historyB is not None, "Problem retrieving historyB from database"
        assert historyA.id == historyB.id, "After the same user logged out and back in, their last used history was not associated with their new session"
    def test_005_deleting_histories( self ):
        """Testing deleting histories"""
        # Logged in as admin_user
        historyB = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert historyB is not None, "Problem retrieving historyB from database"
        self.delete_history( self.security.encode_id( historyB.id ) )
        sa_session.refresh( historyB )
        if not historyB.deleted:
            raise AssertionError, "Problem deleting history id %d" % historyB.id
        # Since we deleted the current history, make sure the history frame was refreshed
        self.check_history_for_string( 'Your history is empty.' )
        # We'll now test deleting a list of histories
        # After deleting the current history, a new one should have been created
        global history1
        history1 = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert history1 is not None, "Problem retrieving history1 from database"
        self.upload_file( '1.bed', dbkey='hg18' )
        self.new_history( name=urllib.quote( 'history2' ) )
        global history2
        history2 = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert history2 is not None, "Problem retrieving history2 from database"
        self.upload_file( '2.bed', dbkey='hg18' )
        ids = '%s,%s' % ( self.security.encode_id( history1.id ), self.security.encode_id( history2.id ) )
        self.delete_history( ids )
        # Since we deleted the current history, make sure the history frame was refreshed
        self.check_history_for_string( 'Your history is empty.' )
        try:
            self.view_stored_active_histories( strings_displayed=[ history1.name ] )
            raise AssertionError, "History %s is displayed in the active history list after it was deleted" % history1.name
        except:
            pass
        self.view_stored_deleted_histories( strings_displayed=[ history1.name ] )
        try:
            self.view_stored_active_histories( strings_displayed=[ history2.name ] )
            raise AssertionError, "History %s is displayed in the active history list after it was deleted" % history2.name
        except:
            pass
        self.view_stored_deleted_histories( strings_displayed=[ history2.name ] )
        sa_session.refresh( history1 )
        if not history1.deleted:
            raise AssertionError, "Problem deleting history id %d" % history1.id
        if not history1.default_permissions:
            raise AssertionError, "Default permissions were incorrectly deleted from the db for history id %d when it was deleted" % history1.id
        sa_session.refresh( history2 )
        if not history2.deleted:
            raise AssertionError, "Problem deleting history id %d" % history2.id
        if not history2.default_permissions:
            raise AssertionError, "Default permissions were incorrectly deleted from the db for history id %d when it was deleted" % history2.id
        # Current history is empty
        self.history_options( user=True )
    def test_010_history_rename( self ):
        """Testing renaming a history"""
        # Logged in as admin_user
        global history3
        history3 = sa_session.query( galaxy.model.History ) \
                             .filter( galaxy.model.History.table.c.deleted==False ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert history3 is not None, "Problem retrieving history3 from database"
        if history3.deleted:
            raise AssertionError, "History id %d deleted when it should not be" % latest_history.id
        self.rename_history( self.security.encode_id( history3.id ), history3.name, new_name=urllib.quote( 'history 3' ) )
        sa_session.refresh( history3 )
    def test_015_history_list( self ):
        """Testing viewing previously stored active histories"""
        # Logged in as admin_user
        self.view_stored_active_histories()
    def test_020_share_current_history( self ):
        """Testing sharing the current history which contains only public datasets"""
        # Logged in as admin_user
        # Test sharing an empty history - current history is history3
        self.share_current_history( regular_user1.email,
                                    strings_displayed=[ history3.name ],
                                    strings_displayed_after_submit=[ 'You cannot share an empty history.' ] )
        # Make history3 sharable by adding a dataset
        self.upload_file( '1.bed', dbkey='hg18' )
        # Current history is no longer empty
        self.history_options( user=True, active_datasets=True, activatable_datasets=True )
        # Test sharing history3 with yourself
        self.share_current_history( admin_user.email,
                                    strings_displayed=[ history3.name ],
                                    strings_displayed_after_submit=[ 'You cannot send histories to yourself.' ] )
        # Share history3 with 1 valid user
        self.share_current_history( regular_user1.email,
                                    strings_displayed=[ history3.name ] )
        # Check out list of histories to make sure history3 was shared
        self.view_stored_active_histories( strings_displayed=[ 'operation=share' ] )
        # Make history3 accessible via link.
        self.make_accessible_via_link( self.security.encode_id( history3.id ),
                                     strings_displayed=[ 'Make History Accessible via Link' ],
                                     strings_displayed_after_submit=[ 'Anyone can view and import this history' ] )
        # Make sure history3 is now accessible.
        sa_session.refresh( history3 )
        if not history3.importable:
            raise AssertionError, "History 3 is not marked as importable after make_accessible_via_link"
        # Try importing history3
        #Importing your own history was enabled in 5248:dc9efb540f61.
        #self.import_history_via_url( self.security.encode_id( history3.id ),
        #                             admin_user.email,
        #                             strings_displayed_after_submit=[ 'You cannot import your own history.' ] )
        # Disable access via link for history3.
        self.disable_access_via_link( self.security.encode_id( history3.id ),
                                     strings_displayed=[ 'Anyone can view and import this history' ],
                                     strings_displayed_after_submit=[ 'Make History Accessible via Link' ] )
        # Try importing history3 after disabling access via link. To do this, need to login as regular user 2, who cannot access
        # history via sharing or via link.
        self.logout()
        self.login( email=regular_user2.email )
        self.import_history_via_url( self.security.encode_id( history3.id ),
                                     admin_user.email,
                                     strings_displayed_after_submit=[ 'History is not accessible to the current user' ] )
        self.logout()
        self.login( email=admin_user.email )
        # Test sharing history3 with an invalid user
        self.share_current_history( 'jack@jill.com',
                                    strings_displayed_after_submit=[ 'jack@jill.com is not a valid Galaxy user.' ] )
    def test_025_delete_shared_current_history( self ):
        """Testing deleting the current history after it was shared"""
        # Logged in as admin_user
        self.delete_current_history( strings_displayed=[ "History (%s) has been shared with others, unshare it before deleting it." % history3.name ] )
    def test_030_clone_shared_history( self ):
        """Testing cloning a shared history"""
        # logged in as admin user
        self.logout()
        self.login( email=regular_user1.email )
        # Shared history3 affects history options
        self.history_options( user=True, histories_shared_by_others=True )
        # Shared history3 should be in regular_user1's list of shared histories
        self.view_shared_histories( strings_displayed=[ history3.name, admin_user.email ] )
        self.clone_history( self.security.encode_id( history3.id ),
                            'activatable',
                            strings_displayed_after_submit=[ 'is now included in your previously stored histories.' ] )
        global history3_clone1
        history3_clone1 = sa_session.query( galaxy.model.History ) \
                                    .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                   galaxy.model.History.table.c.user_id==regular_user1.id ) ) \
                                    .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                    .first()
        assert history3_clone1 is not None, "Problem retrieving history3_clone1 from database"
        # Check list of histories to make sure shared history3 was cloned
        strings_displayed=[ "Clone of '%s' shared by '%s'" % ( history3.name, admin_user.email ) ]
        self.view_stored_active_histories( strings_displayed=strings_displayed )
    def test_035_clone_current_history( self ):
        """Testing cloning the current history"""
        # logged in as regular_user1
        self.logout()
        self.login( email=admin_user.email )
        # Current history should be history3, add more datasets to history3, then delete them so we can
        # test cloning activatable datasets as well as only the active datasets
        self.upload_file( '2.bed', dbkey='hg18' )
        hda_2_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history3.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='2.bed' ) ) \
                              .first()
        assert hda_2_bed is not None, "Problem retrieving hda_2_bed from database"
        self.delete_history_item( str( hda_2_bed.id ) )
        self.upload_file( '3.bed', dbkey='hg18' )
        hda_3_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history3.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='3.bed' ) ) \
                              .first()
        assert hda_3_bed is not None, "Problem retrieving hda_3_bed from database"
        self.delete_history_item( str( hda_3_bed.id ) )
        # Test cloning activatable datasets
        self.clone_history( self.security.encode_id( history3.id ),
                            'activatable',
                            strings_displayed_after_submit=['is now included in your previously stored histories.' ] )
        global history3_clone2
        history3_clone2 = sa_session.query( galaxy.model.History ) \
                                    .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                   galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                                    .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                    .first()
        assert history3_clone2 is not None, "Problem retrieving history3_clone2 from database"
        # Check list of histories to make sure shared history3 was cloned
        self.view_stored_active_histories( strings_displayed=[ "Clone of '%s'" % history3.name ] )
        # Switch to the cloned history to make sure activatable datasets were cloned
        self.switch_history( id=self.security.encode_id( history3_clone2.id ), name=history3_clone2.name )
        hda_2_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history3_clone2.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='2.bed' ) ) \
                              .first()
        assert hda_2_bed is not None, "Problem retrieving hda_2_bed from database"
        hda_3_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history3_clone2.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='3.bed' ) ) \
                              .first()
        assert hda_3_bed is not None, "Problem retrieving hda_3_bed from database"
        # Make sure the deleted datasets are included in the cloned history
        check_str = 'This dataset has been deleted. Click undelete id=%d' % hda_2_bed.id
        self.check_history_for_string( check_str, show_deleted=True )
        check_str = 'This dataset has been deleted. Click undelete id=%d' % hda_3_bed.id
        self.check_history_for_string( check_str, show_deleted=True )
        # Test cloning only active datasets
        self.clone_history( self.security.encode_id( history3.id ),
                            'active',
                            strings_displayed_after_submit=[ 'is now included in your previously stored histories.' ] )
        global history3_clone3
        history3_clone3 = sa_session.query( galaxy.model.History ) \
                                    .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                   galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                                    .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                    .first()
        assert history3_clone3 is not None, "Problem retrieving history3_clone3 from database"
        # Check list of histories to make sure shared history3 was cloned
        self.view_stored_active_histories( strings_displayed = ["Clone of '%s'" % history3.name ] )
        # Switch to the cloned history to make sure activatable datasets were cloned
        self.switch_history( id=self.security.encode_id( history3_clone3.id ) )
        # Make sure the deleted datasets are NOT included in the cloned history
        try:
            self.check_history_for_string( 'This dataset has been deleted.', show_deleted=True )
            raise AssertionError, "Deleted datasets incorrectly included in cloned history history3_clone3"
        except:
            pass
    def test_040_sharing_mulitple_histories_with_multiple_users( self ):
        """Testing sharing multiple histories containing only public datasets with multiple users"""
        # Logged in as admin_user
        self.new_history()
        global history4
        history4 = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert history4 is not None, "Problem retrieving history4 from database"
        self.rename_history( self.security.encode_id( history4.id ), history4.name, new_name=urllib.quote( 'history 4' ) )
        sa_session.refresh( history4 )
        # Galaxy's new history sharing code does not yet support sharing multiple histories; when support for sharing multiple histories is added, 
        # this test will be uncommented and updated.
        """
        self.upload_file( '2.bed', dbkey='hg18' )
        ids = '%s,%s' % ( self.security.encode_id( history3.id ), self.security.encode_id( history4.id ) )
        emails = '%s,%s' % ( regular_user2.email, regular_user3.email )
        self.share_histories_with_users( ids,
                                         emails,
                                         strings_displayed=[ 'Share 2 histories', history4.name ] )
        self.logout()
        self.login( email=regular_user2.email )
        # Shared history3 should be in regular_user2's list of shared histories
        self.view_shared_histories( strings_displayed=[ history3.name, admin_user.email ] )
        self.logout()
        self.login( email=regular_user3.email )
        # Shared history3 should be in regular_user3's list of shared histories
        self.view_shared_histories( cstrings_displayed=[ history3.name, admin_user.email ] )
        """
    def test_045_change_permissions_on_current_history( self ):
        """Testing changing permissions on the current history"""
        # Logged in as regular_user3
        self.logout()
        self.login( email=admin_user.email )
        # Current history is history4
        self.new_history()
        global history5
        history5 = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert history5 is not None, "Problem retrieving history5 from database"
        self.rename_history( self.security.encode_id( history5.id ), history5.name, new_name=urllib.quote( 'history 5' ) )
        # Current history is history5
        sa_session.refresh( history5 )
        # Due to the limitations of twill ( not functional with the permissions forms ), we're forced
        # to do this manually.  At this point, we just want to restrict the access permission on history5
        # to the admin_user
        global access_action
        access_action = galaxy.model.Dataset.permitted_actions.DATASET_ACCESS.action
        dhp = galaxy.model.DefaultHistoryPermissions( history5, access_action, admin_user_private_role )
        sa_session.add( dhp )
        sa_session.flush()
        sa_session.refresh( history5 )
        global history5_default_permissions
        history5_default_permissions = [ dhp.action for dhp in history5.default_permissions ]
        # Sort for later comparison
        history5_default_permissions.sort()
        self.upload_file( '1.bed', dbkey='hg18' )
        history5_dataset1 = None
        for hda in history5.datasets:
            if hda.name == '1.bed':
                history5_dataset1 = hda.dataset
                break
        assert history5_dataset1 is not None, "Problem retrieving history5_dataset1 from the database"
        # The permissions on the dataset should be restricted from sharing with anyone due to the 
        # inherited history permissions
        dataset_permissions = [ a.action for a in history5_dataset1.actions ]
        dataset_permissions.sort()
        if dataset_permissions != history5_default_permissions:
            err_msg = "Dataset permissions for history5_dataset1 (%s) were not correctly inherited from history permissions (%s)" \
                % ( str( dataset_permissions ), str( history5_default_permissions ) )
            raise AssertionError, err_msg
        # Make sure when we logout and login, the history default permissions are preserved
        self.logout()
        self.login( email=admin_user.email )
        sa_session.refresh( history5 )
        current_history_permissions = [ dhp.action for dhp in history5.default_permissions ]
        current_history_permissions.sort()
        if current_history_permissions != history5_default_permissions:
            raise AssertionError, "With logout and login, the history default permissions are not preserved"
    def test_050_sharing_restricted_history_by_making_datasets_public( self ):
        """Testing sharing a restricted history by making the datasets public"""
        # Logged in as admin_user
        action_strings_displayed = [ 'The following datasets can be shared with %s by updating their permissions' % regular_user1.email ]
        # Current history is history5
        self.share_current_history( regular_user1.email,
                                    action='public',
                                    action_strings_displayed=action_strings_displayed )
        self.logout()
        self.login( email=regular_user1.email )
        # Shared history5 should be in regular_user1's list of shared histories
        self.view_shared_histories( strings_displayed=[ history5.name, admin_user.email ] )
        # Clone restricted history5
        self.clone_history( self.security.encode_id( history5.id ),
                            'activatable',
                            strings_displayed_after_submit=[ 'is now included in your previously stored histories.' ] )
        global history5_clone1
        history5_clone1 = sa_session.query( galaxy.model.History ) \
                                    .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                   galaxy.model.History.table.c.user_id==regular_user1.id ) ) \
                                    .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                    .first()
        assert history5_clone1 is not None, "Problem retrieving history5_clone1 from database"
        # Check list of histories to make sure shared history5 was cloned
        self.view_stored_active_histories( strings_displayed=[ "Clone of '%s'" % history5.name ] )
        # Make sure the dataset is accessible
        self.switch_history( id=self.security.encode_id( history5_clone1.id ), name=history5_clone1.name )
        self.check_history_for_string( 'chr1' )
        self.logout()
        self.login( email=admin_user.email )
    def test_055_sharing_restricted_history_by_making_new_sharing_role( self ):
        """Testing sharing a restricted history by associating a new sharing role with protected datasets"""
        # At this point, history5 should have 1 item, 1.bed, which is public.  We'll add another
        # item which will be private to admin_user due to the permissions on history5
        self.upload_file( '2.bed', dbkey='hg18' )
        strings_displayed_after_submit = [ 'The following datasets can be shared with %s with no changes' % regular_user2.email,
                                         'The following datasets can be shared with %s by updating their permissions' % regular_user2.email ]
        self.share_current_history( regular_user2.email,
                                    strings_displayed_after_submit=strings_displayed_after_submit,
                                    action='private' )        
        # We should now have a new sharing role
        global sharing_role
        role_name = 'Sharing role for: %s, %s' % ( admin_user.email, regular_user2.email )
        sharing_role = sa_session.query( galaxy.model.Role ).filter( galaxy.model.Role.table.c.name==role_name ).first()
        if not sharing_role:
            # May have created a sharing role in a previous functional test suite from the opposite direction.
            role_name = 'Sharing role for: %s, %s' % ( regular_user2.email, admin_user.email )
            sharing_role = sa_session.query( galaxy.model.Role ) \
                                     .filter( and_( galaxy.model.Role.table.c.type==role_type,
                                                    galaxy.model.Role.table.c.name==role_name ) ) \
                                     .first()
        if not sharing_role:
            raise AssertionError( "Privately sharing a dataset did not properly create a sharing role" )
        # The DATASET_ACCESS permission on 2.bed was originally associated with admin_user's private role.  
        # Since we created a new sharing role for 2.bed, the original permission should have been eliminated,
        # replaced with the sharing role.
        history5_dataset2 = None
        for hda in history5.datasets:
            if hda.name == '2.bed':
                history5_dataset2 = hda.dataset
                break
        assert history5_dataset2 is not None, "Problem retrieving history5_dataset2 from the database"
        for dp in history5_dataset2.actions:
            if dp.action == 'access':
                assert dp.role == sharing_role, "Associating new sharing role with history5_dataset2 did not correctly eliminate original DATASET ACCESS permissions"
        self.logout()
        self.login( email=regular_user2.email )
        # Shared history5 should be in regular_user2's list of shared histories
        self.view_shared_histories( strings_displayed=[ history5.name, admin_user.email ] )
        # Clone restricted history5
        self.clone_history( self.security.encode_id( history5.id ),
                            'activatable',
                            strings_displayed_after_submit=[ 'is now included in your previously stored histories.' ] )
        global history5_clone2
        history5_clone2 = sa_session.query( galaxy.model.History ) \
                                    .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                   galaxy.model.History.table.c.user_id==regular_user2.id ) ) \
                                    .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                    .first()
        assert history5_clone2 is not None, "Problem retrieving history5_clone2 from database"
        # Check list of histories to make sure shared history3 was cloned
        self.view_stored_active_histories( strings_displayed=[ "Clone of '%s'" % history5.name ] )
        # Make sure the dataset is accessible
        self.switch_history( id=self.security.encode_id( history5_clone2.id ), name=history5_clone2.name )
       # Make sure both datasets are in the history
        self.check_history_for_string( '1.bed' )
        self.check_history_for_string( '2.bed' )
        # Get both new hdas from the db that were created for the shared history
        hda_1_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_clone2.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='1.bed' ) ) \
                              .first()
        assert hda_1_bed is not None, "Problem retrieving hda_1_bed from database"
        hda_2_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_clone2.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='2.bed' ) ) \
                              .first()
        assert hda_2_bed is not None, "Problem retrieving hda_2_bed from database"
        # Make sure 1.bed is accessible since it is public
        self.display_history_item( str( hda_1_bed.id ), strings_displayed=[ 'chr1' ] )
        # Make sure 2.bed is accessible since it is associated with a sharing role
        self.display_history_item( str( hda_2_bed.id ), strings_displayed=[ 'chr1' ] )
        # Delete the clone so the next test will be valid
        self.delete_history( id=self.security.encode_id( history5_clone2.id ) )
    def test_060_sharing_restricted_history_with_multiple_users_by_changing_no_permissions( self ):
        """Testing sharing a restricted history with multiple users, making no permission changes"""
        # Logged in as regular_user2
        self.logout()
        self.login( email=admin_user.email )
        # History5 can be shared with any user, since it contains a public dataset ( 1.bed ).  However, only
        # regular_user2 should be able to access history5's 2.bed dataset since it is associated with a
        # sharing role, and regular_user3 should be able to access history5's 1.bed, but not 2.bed even
        # though they can see it in their shared history.
        # We first need to unshare history5 from regular_user2 so that we can re-share it.
        self.unshare_history( self.security.encode_id( history5.id ),
                              self.security.encode_id( regular_user2.id ),
                              strings_displayed=[ regular_user1.email, regular_user2.email ] )
        # Make sure the history was unshared correctly
        self.logout()
        self.login( email=regular_user2.email )
        self.visit_page( "root/history_options" )
        try:
            self.check_page_for_string( 'List</a> histories shared with you by others' )
            raise AssertionError, "history5 still shared with regular_user2 after unsharing it with that user."
        except:
            pass
        self.logout()
        self.login( admin_user.email )
        email = '%s,%s' % ( regular_user2.email, regular_user3.email )
        strings_displayed_after_submit = [ 'The following datasets can be shared with %s with no changes' % email,
                                         'The following datasets can be shared with %s by updating their permissions' % email ]
        # history5 will be shared with regular_user1, regular_user2 and regular_user3
        self.share_current_history( email,
                                    strings_displayed_after_submit=strings_displayed_after_submit,
                                    action='share_anyway' )
        # Check security on clone of history5 for regular_user2
        self.logout()
        self.login( email=regular_user2.email )
        # Shared history5 should be in regular_user2's list of shared histories
        self.view_shared_histories( strings_displayed=[ history5.name, admin_user.email ] )
        # Clone restricted history5
        self.clone_history( self.security.encode_id( history5.id ),
                            'activatable',
                            strings_displayed_after_submit=[ 'is now included in your previously stored histories.' ] )
        global history5_clone3
        history5_clone3 = sa_session.query( galaxy.model.History ) \
                                    .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                   galaxy.model.History.table.c.user_id==regular_user2.id ) ) \
                                    .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                    .first()
        assert history5_clone3 is not None, "Problem retrieving history5_clone3 from database"
        # Check list of histories to make sure shared history3 was cloned
        self.view_stored_active_histories( strings_displayed=[ "Clone of '%s'" % history5.name ] )
        # Make sure the dataset is accessible
        self.switch_history( id=self.security.encode_id( history5_clone3.id ), name=history5_clone3.name )
       # Make sure both datasets are in the history
        self.check_history_for_string( '1.bed' )
        self.check_history_for_string( '2.bed' )
        # Get both new hdas from the db that were created for the shared history
        hda_1_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_clone3.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='1.bed' ) ) \
                              .first()
        assert hda_1_bed is not None, "Problem retrieving hda_1_bed from database"
        hda_2_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_clone3.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='2.bed' ) ) \
                              .first()
        assert hda_2_bed is not None, "Problem retrieving hda_2_bed from database"
        # Make sure 1.bed is accessible since it is public
        self.display_history_item( str( hda_1_bed.id ), strings_displayed=[ 'chr1' ] )
        # Make sure 2.bed is accessible since it is associated with a sharing role
        self.display_history_item( str( hda_2_bed.id ), strings_displayed=[ 'chr1' ] )
        # Delete the clone so the next test will be valid
        self.delete_history( id=self.security.encode_id( history5_clone3.id ) )
        # Check security on clone of history5 for regular_user3
        self.logout()
        self.login( email=regular_user3.email )
        # Shared history5 should be in regular_user2's list of shared histories
        self.view_shared_histories( strings_displayed=[ history5.name, admin_user.email ] )
        # Clone restricted history5
        self.clone_history( self.security.encode_id( history5.id ),
                            'activatable',
                            strings_displayed_after_submit=[ 'is now included in your previously stored histories.' ] )
        global history5_clone4
        history5_clone4 = sa_session.query( galaxy.model.History ) \
                                    .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                   galaxy.model.History.table.c.user_id==regular_user3.id ) ) \
                                    .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                    .first()
        assert history5_clone4 is not None, "Problem retrieving history5_clone4 from database"
        # Check list of histories to make sure shared history3 was cloned
        self.view_stored_active_histories( strings_displayed=[ "Clone of '%s'" % history5.name ] )
        # Make sure the dataset is accessible
        self.switch_history( id=self.security.encode_id( history5_clone4.id ), name=history5_clone4.name )
       # Make sure both datasets are in the history
        self.check_history_for_string( '1.bed' )
        self.check_history_for_string( '2.bed' )
        # Get both new hdas from the db that were created for the shared history
        hda_1_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_clone4.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='1.bed' ) ) \
                              .first()
        assert hda_1_bed is not None, "Problem retrieving hda_1_bed from database"
        hda_2_bed = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                              .filter( and_( galaxy.model.HistoryDatasetAssociation.table.c.history_id==history5_clone4.id,
                                             galaxy.model.HistoryDatasetAssociation.table.c.name=='2.bed' ) ) \
                              .first()
        assert hda_2_bed is not None, "Problem retrieving hda_2_bed from database"
        # Make sure 1.bed is accessible since it is public
        self.display_history_item( str( hda_1_bed.id ), strings_displayed=[ 'chr1' ] )
        # Make sure 2.bed is not accessible since it is protected
        try:
            self.display_history_item( str( hda_2_bed.id ), strings_displayed=[ 'chr1' ] )
            raise AssertionError, "History item 2.bed is accessible by user %s when is should not be" % regular_user3.email
        except:
            pass
        self.check_history_for_string( 'You do not have permission to view this dataset' )
        # Admin users can view all datasets ( using the history/view feature ), so make sure 2.bed is accessible to the admin
        self.logout()
        self.login( email=admin_user.email )
        self.view_history( str( hda_2_bed.history_id ), strings_displayed=[ '<td>NM_005997_cds_0_0_chr1_147962193_r</td>' ] )
        self.logout()
        self.login( email=regular_user3.email )
        # Delete the clone so the next test will be valid
        self.delete_history( id=self.security.encode_id( history5_clone4.id ) )
    def test_065_sharing_private_history_by_choosing_to_not_share( self ):
        """Testing sharing a restricted history with multiple users by choosing not to share"""
        # Logged in as regular_user3
        self.logout()
        self.login( email=admin_user.email )
        # Unshare history5 from regular_user2
        self.unshare_history( self.security.encode_id( history5.id ),
                              self.security.encode_id( regular_user2.id ),
                              strings_displayed=[ regular_user1.email, regular_user2.email ] )
        # Unshare history5 from regular_user3
        self.unshare_history( self.security.encode_id( history5.id ),
                              self.security.encode_id( regular_user3.id ),
                              strings_displayed=[ regular_user1.email, regular_user3.email ] )
        # Make sure the history was unshared correctly
        self.logout()
        self.login( email=regular_user2.email )
        self.visit_page( "root/history_options" )
        try:
            self.check_page_for_string( 'List</a> histories shared with you by others' )
            raise AssertionError, "history5 still shared with regular_user2 after unshaing it with that user."
        except:
            pass
        self.logout()
        self.login( email=regular_user3.email )
        self.visit_page( "root/history_options" )
        try:
            self.check_page_for_string( 'List</a> histories shared with you by others' )
            raise AssertionError, "history5 still shared with regular_user3 after unshaing it with that user."
        except:
            pass
        self.logout()
        self.login( email=admin_user.email )
    def test_070_history_show_and_hide_deleted_datasets( self ):
        """Testing displaying deleted history items"""
        # Logged in as admin_user
        self.new_history( name=urllib.quote( 'show hide deleted datasets' ) )
        latest_history = sa_session.query( galaxy.model.History ) \
                                   .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                  galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                                   .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                   .first()
        assert latest_history is not None, "Problem retrieving latest_history from database"
        self.upload_file('1.bed', dbkey='hg18')
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        self.home()
        self.delete_history_item( str( latest_hda.id ) )
        self.check_history_for_string( 'Your history is empty' )
        self.home()
        self.visit_url( "%s/history/?show_deleted=True" % self.url )
        self.check_page_for_string( 'This dataset has been deleted.' )
        self.check_page_for_string( '1.bed' )
        self.home()
        self.visit_url( "%s/history/?show_deleted=False" % self.url )
        self.check_page_for_string( 'Your history is empty' )
        self.delete_history( self.security.encode_id( latest_history.id ) )
    def test_075_deleting_and_undeleting_history_items( self ):
        """Testing deleting and un-deleting history items"""
        # logged in as admin_user
        # Deleting the current history in the last method created a new history
        latest_history = sa_session.query( galaxy.model.History ) \
                                   .filter( and_( galaxy.model.History.table.c.deleted==False,
                                                  galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                                   .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                                   .first()
        assert latest_history is not None, "Problem retrieving latest_history from database"
        self.rename_history( self.security.encode_id( latest_history.id ), latest_history.name, new_name=urllib.quote( 'delete undelete history items' ) )
        # Add a new history item
        self.upload_file( '1.bed', dbkey='hg15' )
        latest_hda = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                               .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                               .first()
        self.home()
        self.visit_url( "%s/history/?show_deleted=False" % self.url )
        self.check_page_for_string( '1.bed' )
        self.check_page_for_string( 'hg15' )
        self.assertEqual ( len( self.get_history_as_data_list() ), 1 )
        # Delete the history item
        self.delete_history_item( str( latest_hda.id ), strings_displayed=[ "Your history is empty" ] )
        self.assertEqual ( len( self.get_history_as_data_list() ), 0 )
        # Try deleting an invalid hid
        try:
            self.delete_history_item( 'XXX' )
            raise AssertionError, "Inproperly able to delete hda_id 'XXX' which is not an integer"
        except:
            pass
        # Undelete the history item
        self.undelete_history_item( str( latest_hda.id ) )
        self.home()
        self.visit_url( "%s/history/?show_deleted=False" % self.url )
        self.check_page_for_string( '1.bed' )
        self.check_page_for_string( 'hg15' )
        self.delete_history( self.security.encode_id( latest_history.id ) )
    def test_080_copying_history_items_between_histories( self ):
        """Testing copying history items between histories"""
        # logged in as admin_user
        self.new_history( name=urllib.quote( 'copy history items' ) )
        history6 = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert history6 is not None, "Problem retrieving history6 from database"
        self.upload_file( '1.bed', dbkey='hg18' )
        hda1 = sa_session.query( galaxy.model.HistoryDatasetAssociation ) \
                         .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ) \
                         .first()
        assert hda1 is not None, "Problem retrieving hda1 from database"
        # We'll just test copying 1 hda
        source_dataset_ids=self.security.encode_id( hda1.id )
        # The valid list of target histories is only the user's active histories
        all_target_history_ids = [ self.security.encode_id( hda.id ) for hda in admin_user.active_histories ]
        # Since history1 and history2 have been deleted, they should not be displayed in the list of target histories
        # on the copy_view.mako form
        deleted_history_ids = [ self.security.encode_id( history1.id ), self.security.encode_id( history2.id ) ]
        # Test copying to the current history
        target_history_id = self.security.encode_id( history6.id )
        self.copy_history_item( source_dataset_id=source_dataset_ids,
                                target_history_id=target_history_id,
                                all_target_history_ids=all_target_history_ids,
                                deleted_history_ids=deleted_history_ids )
        sa_session.refresh( history6 )
        if len( history6.datasets ) != 2:
            raise AssertionError, "Copying hda1 to the current history failed, history 6 has %d datasets, but should have 2" % len( history6.datasets )
        # Test copying 1 hda to another history
        self.new_history( name=urllib.quote( 'copy history items - 2' ) )
        history7 = sa_session.query( galaxy.model.History ) \
                             .filter( and_( galaxy.model.History.table.c.deleted==False,
                                            galaxy.model.History.table.c.user_id==admin_user.id ) ) \
                             .order_by( desc( galaxy.model.History.table.c.create_time ) ) \
                             .first()
        assert history7 is not None, "Problem retrieving history7 from database"
        # Switch back to our history from which we want to copy
        self.switch_history( id=self.security.encode_id( history6.id ), name=history6.name )
        target_history_id = self.security.encode_id( history7.id )
        all_target_history_ids = [ self.security.encode_id( hda.id ) for hda in admin_user.active_histories ]
        # Test copying to the a history that is not the current history
        target_history_ids=[ self.security.encode_id( history7.id ) ]
        self.copy_history_item( source_dataset_id=source_dataset_ids,
                                target_history_id=target_history_id,
                                all_target_history_ids=all_target_history_ids,
                                deleted_history_ids=deleted_history_ids )
        # Switch to the history to which we copied
        self.switch_history( id=self.security.encode_id( history7.id ), name=history7.name )
        self.check_history_for_string( hda1.name )
        self.delete_history( self.security.encode_id( history6.id ) )
        self.delete_history( self.security.encode_id( history7.id ) )
    def test_085_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to to be valid"""
        # logged in as admin_user
        # Clean up admin_user
        # Unshare history3 - shared with regular_user1, regular_user2, regular_user3
        self.unshare_history( self.security.encode_id( history3.id ),
                              self.security.encode_id( regular_user1.id ) )
        self.unshare_history( self.security.encode_id( history3.id ),
                              self.security.encode_id( regular_user2.id ) )
        self.unshare_history( self.security.encode_id( history3.id ),
                              self.security.encode_id( regular_user3.id ) )
        # Unshare history4 - shared with regular_user2, regular_user3
        self.unshare_history( self.security.encode_id( history4.id ),
                              self.security.encode_id( regular_user2.id ) )
        self.unshare_history( self.security.encode_id( history4.id ),
                              self.security.encode_id( regular_user3.id ) )
        # Unshare history5 - shared with regular_user1
        self.unshare_history( self.security.encode_id( history5.id ),
                              self.security.encode_id( regular_user1.id ) )
        # Delete histories
        self.delete_history( id=self.security.encode_id( history3.id ) )
        self.delete_history( id=self.security.encode_id( history3_clone2.id ) )
        self.delete_history( id=self.security.encode_id( history3_clone3.id ) )
        self.delete_history( id=self.security.encode_id( history4.id ) )
        self.delete_history( id=self.security.encode_id( history5.id ) )
        # Eliminate Sharing role for: test@bx.psu.edu, test2@bx.psu.edu
        self.mark_role_deleted( self.security.encode_id( sharing_role.id ), sharing_role.name )
        self.purge_role( self.security.encode_id( sharing_role.id ), sharing_role.name )
        # Manually delete the sharing role from the database
        sa_session.refresh( sharing_role )
        sa_session.delete( sharing_role )
        sa_session.flush()
        # Clean up regular_user_1
        self.logout()
        self.login( email=regular_user1.email )
        self.delete_history( id=self.security.encode_id( history3_clone1.id ) )
        self.delete_history( id=self.security.encode_id( history5_clone1.id ) )
