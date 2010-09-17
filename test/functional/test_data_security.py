from base.twilltestcase import *
from base.test_db_util import *

class TestDataSecurity( TwillTestCase ):
    def test_000_initiate_users( self ):
        """Ensuring all required user accounts exist"""
        self.logout()
        self.login( email='test1@bx.psu.edu', username='regular-user1' )
        global regular_user1
        regular_user1 = get_user( 'test1@bx.psu.edu' )
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        global regular_user1_private_role
        regular_user1_private_role = get_private_role( regular_user1 )
        self.logout()
        self.login( email='test2@bx.psu.edu', username='regular-user2' )
        global regular_user2
        regular_user2 = get_user( 'test2@bx.psu.edu' )
        assert regular_user2 is not None, 'Problem retrieving user with email "test2@bx.psu.edu" from the database'
        global regular_user2_private_role
        regular_user2_private_role = get_private_role( regular_user2 )
        self.logout()
        self.login( email='test3@bx.psu.edu', username='regular-user3' )
        global regular_user3
        regular_user3 = get_user( 'test3@bx.psu.edu' )
        assert regular_user3 is not None, 'Problem retrieving user with email "test3@bx.psu.edu" from the database'
        global regular_user3_private_role
        regular_user3_private_role = get_private_role( regular_user3 )
        self.logout()
        self.login( email='test@bx.psu.edu', username='admin-user' )
        global admin_user
        admin_user = get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
        global admin_user_private_role
        admin_user_private_role = get_private_role( admin_user )
    def test_005_default_permissions( self ):
        """Testing initial settings for DefaultUserPermissions and DefaultHistoryPermissions"""
        # Logged in as admin_user
        # Make sure DefaultUserPermissions are correct
        dups = get_default_user_permissions_by_user( admin_user )
        if len( dups ) > 1:
            raise AssertionError( '%d DefaultUserPermissions associated with user %s ( should be 1 )' \
                                  % ( len( admin_user.default_permissions ), admin_user.email ) )
        dup = dups[0]
        if not dup.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultUserPermission.action for user "%s" is "%s", but it should be "%s"' \
                                  % ( admin_user.email, dup.action, galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        # Make sure DefaultHistoryPermissions are correct
        latest_history = get_latest_history_for_user( admin_user )
        dhps = get_default_history_permissions_by_history( latest_history )
        if len( dhps ) > 1:
            raise AssertionError( '%d DefaultHistoryPermissions were created for history id %d when it was created ( should have been 1 )' \
                                  % ( len( latest_history.default_permissions ), latest_history.id ) )
        dhp = dhps[0]
        if not dhp.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultHistoryPermission.action for history id %d is "%s", but it should be "%s"' \
                                  % ( latest_history.id, dhp.action, galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        self.manage_roles_and_groups_for_user( self.security.encode_id( admin_user.id ),
                                               strings_displayed=[ admin_user.email ] )
        # Try deleting the admin_user's private role
        self.manage_roles_and_groups_for_user( self.security.encode_id( admin_user.id ),
                                               out_role_ids=str( admin_user_private_role.id ),
                                               strings_displayed = [ "You cannot eliminate a user's private role association." ] )
    def test_010_private_role_creation_and_default_history_permissions( self ):
        """Testing private role creation and changing DefaultHistoryPermissions for new histories"""
        # Logged in as admin_user
        self.logout()
        # Some of the history related tests here are similar to some tests in the
        # test_history_functions.py script, so we could potentially eliminate 1 or 2 of them.
        self.login( email='test1@bx.psu.edu' )
        global regular_user1
        regular_user1 = get_user( 'test1@bx.psu.edu' )
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        # Add a dataset to the history
        self.upload_file( '1.bed' )
        latest_dataset = get_latest_dataset()
        # Make sure DatasetPermissions are correct - default is 'manage permissions'
        dps = get_dataset_permissions_by_dataset( latest_dataset )
        if len( dps ) > 1:
            raise AssertionError( '%d DatasetPermissions were created for dataset id %d when it was created ( should have been 1 )' \
                                  % ( len( dps ), latest_dataset.id ) )
        dp = dps[0]
        if not dp.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DatasetPermissions.action for dataset id %d is "%s", but it should be "manage permissions"' \
                                  % ( latest_dataset.id, dp.action ) )
        # Change DefaultHistoryPermissions for regular_user1
        permissions_in = []
        actions_in = []
        for key, value in galaxy.model.Dataset.permitted_actions.items():
            # Setting the 'access' permission with the private role makes this dataset private
            permissions_in.append( key )
            actions_in.append( value.action )
        # Sort actions for later comparison
        actions_in.sort()
        self.user_set_default_permissions( permissions_in=permissions_in, role_id=str( regular_user1_private_role.id ) )
        # Make sure the default permissions are changed for new histories
        self.new_history()
        # logged in as regular_user1
        latest_history = get_latest_history_for_user( regular_user1 )
        if len( latest_history.default_permissions ) != len( actions_in ):
            raise AssertionError( '%d DefaultHistoryPermissions were created for history id %d, should have been %d' % \
                                  ( len( latest_history.default_permissions ), latest_history.id, len( actions_in ) ) )
        dhps = []
        for dhp in latest_history.default_permissions:
            dhps.append( dhp.action )
        # Sort permissions for later comparison
        dhps.sort()
        for key, value in galaxy.model.Dataset.permitted_actions.items():
            if value.action not in dhps:
                raise AssertionError( '%s not in history id %d default_permissions after they were changed' % ( value.action, latest_history.id ) )
        # Add a dataset to the history
        self.upload_file( '1.bed' )
        latest_dataset = get_latest_dataset()
        # Make sure DatasetPermissions are correct
        if len( latest_dataset.actions ) != len( latest_history.default_permissions ):
            raise AssertionError( '%d DatasetPermissions were created for dataset id %d when it was created ( should have been %d )' % \
                                  ( len( latest_dataset.actions ), latest_dataset.id, len( latest_history.default_permissions ) ) )
        dps = []
        for dp in latest_dataset.actions:
            dps.append( dp.action )
        # Sort actions for later comparison
        dps.sort()
        # Compare DatasetPermissions with permissions_in - should be the same
        if dps != actions_in:
            raise AssertionError( 'DatasetPermissions "%s" for dataset id %d differ from changed default permissions "%s"' \
                % ( str( dps ), latest_dataset.id, str( actions_in ) ) )
        # Compare DefaultHistoryPermissions and DatasetPermissions - should be the same
        if dps != dhps:
                raise AssertionError( 'DatasetPermissions "%s" for dataset id %d differ from DefaultHistoryPermissions "%s" for history id %d' \
                                      % ( str( dps ), latest_dataset.id, str( dhps ), latest_history.id ) )
    def test_015_change_default_permissions_for_current_history( self ):
        """Testing changing DefaultHistoryPermissions for the current history"""
        # logged in a regular_user1
        self.logout()
        self.login( email=regular_user2.email )
        latest_history = get_latest_history_for_user( regular_user2 )
        self.upload_file( '1.bed' )
        latest_dataset = get_latest_dataset()
        permissions_in = [ 'DATASET_MANAGE_PERMISSIONS' ]
        # Make sure these are in sorted order for later comparison
        actions_in = [ 'manage permissions' ]
        permissions_out = [ 'DATASET_ACCESS' ]
        actions_out = [ 'access' ]
        # Change DefaultHistoryPermissions for the current history
        self.history_set_default_permissions( permissions_out=permissions_out, permissions_in=permissions_in, role_id=str( regular_user2_private_role.id ) )
        if len( latest_history.default_permissions ) != len( actions_in ):
            raise AssertionError( '%d DefaultHistoryPermissions were created for history id %d, should have been %d' \
                                  % ( len( latest_history.default_permissions ), latest_history.id, len( permissions_in ) ) )
        # Make sure DefaultHistoryPermissions were correctly changed for the current history
        dhps = []
        for dhp in latest_history.default_permissions:
            dhps.append( dhp.action )
        # Sort permissions for later comparison
        dhps.sort()
        # Compare DefaultHistoryPermissions and actions_in - should be the same
        if dhps != actions_in:
            raise AssertionError( 'DefaultHistoryPermissions "%s" for history id %d differ from actions "%s" passed for changing' \
                                      % ( str( dhps ), latest_history.id, str( actions_in ) ) )
        # Make sure DatasetPermissionss are correct
        if len( latest_dataset.actions ) != len( latest_history.default_permissions ):
            raise AssertionError( '%d DatasetPermissionss were created for dataset id %d when it was created ( should have been %d )' \
                                  % ( len( latest_dataset.actions ), latest_dataset.id, len( latest_history.default_permissions ) ) )
        dps = []
        for dp in latest_dataset.actions:
            dps.append( dp.action )
        # Sort actions for comparison
        dps.sort()
        # Compare DatasetPermissionss and DefaultHistoryPermissions - should be the same
        if dps != dhps:
            raise AssertionError( 'DatasetPermissionss "%s" for dataset id %d differ from DefaultHistoryPermissions "%s"' \
                                      % ( str( dps ), latest_dataset.id, str( dhps ) ) )
    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as regular_user2
        self.logout()
        self.login( email=admin_user.email )
        ##################
        # Make sure all users are associated only with their private roles
        ##################
        for user in [ admin_user, regular_user1, regular_user2, regular_user3 ]:
            refresh( user )
            if len( user.roles) != 1:
                raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 1 )' % ( len( user.roles ), user.email ) )
        #####################
        # Reset DefaultHistoryPermissions for regular_user1
        #####################
        self.logout()
        self.login( email=regular_user1.email )
        # Change DefaultHistoryPermissions for regular_user1 back to the default
        permissions_in = [ 'DATASET_MANAGE_PERMISSIONS' ]
        permissions_out = [ 'DATASET_ACCESS' ]
        self.user_set_default_permissions( permissions_in=permissions_in,
                                           permissions_out=permissions_out,
                                           role_id=str( regular_user1_private_role.id ) )
        self.logout()
        self.login( email=admin_user.email )
