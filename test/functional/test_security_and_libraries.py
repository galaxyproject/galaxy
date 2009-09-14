import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import *

not_logged_in_security_msg = 'You must be logged in as an administrator to access this feature.'
logged_in_security_msg = 'You must be an administrator to access this feature.'

class TestSecurityAndLibraries( TwillTestCase ):
    def test_000_admin_features_when_not_logged_in( self ):
        """Testing admin_features when not logged in"""
        self.logout()
        self.visit_url( "%s/admin" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/reload_tool?tool_id=upload1" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/roles" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/create_role" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/create_role" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/role" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/groups" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/create_group" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/users" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/library_admin/library" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/library_admin/folder?id=1&new=True" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
    def test_005_login_as_admin_user( self ):
        """Testing logging in as an admin user test@bx.psu.edu - tests initial settings for DefaultUserPermissions and DefaultHistoryPermissions"""
        self.login( email='test@bx.psu.edu' ) # test@bx.psu.edu is configured as our admin user
        self.visit_page( "admin" )
        self.check_page_for_string( 'Administration' )
        global admin_user
        admin_user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
        # Get the admin user's private role for later use
        global admin_user_private_role
        admin_user_private_role = None
        for role in admin_user.all_roles():
            if role.name == admin_user.email and role.description == 'Private Role for %s' % admin_user.email:
                admin_user_private_role = role
                break
        if not admin_user_private_role:
            raise AssertionError( "Private role not found for user '%s'" % admin_user.email )
        # Make sure DefaultUserPermissions are correct
        if len( admin_user.default_permissions ) > 1:
            raise AssertionError( '%d DefaultUserPermissions associated with user %s ( should be 1 )' \
                                  % ( len( admin_user.default_permissions ), admin_user.email ) )
        dup =  galaxy.model.DefaultUserPermissions.filter( galaxy.model.DefaultUserPermissions.table.c.user_id==admin_user.id ).first()
        if not dup.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultUserPermission.action for user "%s" is "%s", but it should be "%s"' \
                                  % ( admin_user.email, dup.action, galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        # Make sure DefaultHistoryPermissions are correct
        # Logged in as admin_user
        latest_history = galaxy.model.History.filter( and_( galaxy.model.History.table.c.deleted==False,
                                                      galaxy.model.History.table.c.user_id==admin_user.id ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        if len( latest_history.default_permissions ) > 1:
            raise AssertionError( '%d DefaultHistoryPermissions were created for history id %d when it was created ( should have been 1 )' \
                                  % ( len( latest_history.default_permissions ), latest_history.id ) )
        dhp =  galaxy.model.DefaultHistoryPermissions.filter( galaxy.model.DefaultHistoryPermissions.table.c.history_id==latest_history.id ).first()
        if not dhp.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultHistoryPermission.action for history id %d is "%s", but it should be "%s"' \
                                  % ( latest_history.id, dhp.action, galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        self.home()
        self.visit_url( "%s/admin/user?user_id=%s" % ( self.url, admin_user.id ) )
        self.check_page_for_string( admin_user.email )
        # Try deleting the admin_user's private role
        check_str = "You cannot eliminate a user's private role association."
        self.associate_roles_and_groups_with_user( str( admin_user.id ), admin_user.email,
                                                   out_role_ids=str( admin_user_private_role.id ),
                                                   check_str=check_str )
        self.logout()
    def test_010_login_as_regular_user1( self ):
        """Testing logging in as regular user test1@bx.psu.edu - tests private role creation and changing DefaultHistoryPermissions for new histories"""
        # Some of the history related tests here are similar to some tests in the
        # test_history_functions.py script, so we could potentially eliminate 1 or 2 of them.
        self.login( email='test1@bx.psu.edu' ) # test1@bx.psu.edu is not an admin user
        global regular_user1
        regular_user1 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test1@bx.psu.edu' ).first()
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        self.visit_page( "admin" )
        self.check_page_for_string( logged_in_security_msg )
        # Make sure a private role exists for regular_user1
        private_role = None
        for role in regular_user1.all_roles():
            if role.name == regular_user1.email and role.description == 'Private Role for %s' % regular_user1.email:
                private_role = role
                break
        if not private_role:
            raise AssertionError( "Private role not found for user '%s'" % regular_user1.email )
        global regular_user1_private_role
        regular_user1_private_role = private_role
        # Add a dataset to the history
        self.upload_file( '1.bed' )
        latest_dataset = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        # Make sure DatasetPermissions is correct - default is 'manage permissions'
        if len( latest_dataset.actions ) > 1:
            raise AssertionError( '%d DatasetPermissions were created for dataset id %d when it was created ( should have been 1 )' \
                                  % ( len( latest_dataset.actions ), latest_dataset.id ) )
        dp = galaxy.model.DatasetPermissions.filter( galaxy.model.DatasetPermissions.table.c.dataset_id==latest_dataset.id ).first()
        if not dp.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DatasetPermissions.action for dataset id %d is "%s", but it should be "manage permissions"' \
                                  % ( latest_dataset.id, dp.action ) )
        # Change DefaultHistoryPermissions for regular_user1
        permissions_in = []
        actions_in = []
        for key, value in galaxy.model.Dataset.permitted_actions.items():
            # NOTE: setting the 'access' permission with the private role makes this dataset private
            permissions_in.append( key )
            actions_in.append( value.action )
        # Sort actions for later comparison
        actions_in.sort()
        role_id = str( private_role.id )
        self.user_set_default_permissions( permissions_in=permissions_in, role_id=role_id )
        # Make sure the default permissions are changed for new histories
        self.new_history()
        # logged in as regular_user1
        latest_history = galaxy.model.History.filter( and_( galaxy.model.History.table.c.deleted==False,
                                                      galaxy.model.History.table.c.user_id==regular_user1.id ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        if len( latest_history.default_permissions ) != len( galaxy.model.Dataset.permitted_actions.items() ):
            raise AssertionError( '%d DefaultHistoryPermissions were created for history id %d, should have been %d' % \
                                  ( len( latest_history.default_permissions ), latest_history.id, len( galaxy.model.Dataset.permitted_actions.items() ) ) )
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
        latest_dataset = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        # Make sure DatasetPermissionss are correct
        if len( latest_dataset.actions ) != len( latest_history.default_permissions ):
            raise AssertionError( '%d DatasetPermissionss were created for dataset id %d when it was created ( should have been %d )' % \
                                  ( len( latest_dataset.actions ), latest_dataset.id, len( latest_history.default_permissions ) ) )
        dps = []
        for dp in latest_dataset.actions:
            dps.append( dp.action )
        # Sort actions for later comparison
        dps.sort()
        # Compare DatasetPermissions with permissions_in - should be the same
        if dps != actions_in:
            raise AssertionError( 'DatasetPermissionss "%s" for dataset id %d differ from changed default permissions "%s"' \
                                      % ( str( dps ), latest_dataset.id, str( actions_in ) ) )
        # Compare DefaultHistoryPermissions and DatasetPermissionss - should be the same
        if dps != dhps:
                raise AssertionError( 'DatasetPermissionss "%s" for dataset id %d differ from DefaultHistoryPermissions "%s" for history id %d' \
                                      % ( str( dps ), latest_dataset.id, str( dhps ), latest_history.id ) )
        self.logout()
    def test_015_login_as_regular_user2( self ):
        """Testing logging in as regular user test2@bx.psu.edu - tests changing DefaultHistoryPermissions for the current history"""
        self.login( email='test2@bx.psu.edu' ) # This will not be an admin user
        global regular_user2
        regular_user2 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ).first()
        assert regular_user2 is not None, 'Problem retrieving user with email "test2@bx.psu.edu" from the database'
        # Logged in as regular_user2
        latest_history = galaxy.model.History.filter( and_( galaxy.model.History.table.c.deleted==False,
                                                      galaxy.model.History.table.c.user_id==regular_user2.id ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        self.upload_file( '1.bed' )
        latest_dataset = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        permissions_in = [ 'DATASET_MANAGE_PERMISSIONS' ]
        # Make sure these are in sorted order for later comparison
        actions_in = [ 'manage permissions' ]
        permissions_out = [ 'DATASET_ACCESS' ]
        actions_out = [ 'access' ]
        regular_user2_private_role = None
        for role in regular_user2.all_roles():
            if role.name == regular_user2.email and role.description == 'Private Role for %s' % regular_user2.email:
                regular_user2_private_role = role
                break
        if not regular_user2_private_role:
            raise AssertionError( "Private role not found for user '%s'" % regular_user2.email )
        role_id = str( regular_user2_private_role.id )
        # Change DefaultHistoryPermissions for the current history
        self.history_set_default_permissions( permissions_out=permissions_out, permissions_in=permissions_in, role_id=role_id )
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
        self.logout()
    def test_020_create_new_user_account_as_admin( self ):
        """Testing creating a new user account as admin"""
        self.login( email='test@bx.psu.edu' )
        email = 'test3@bx.psu.edu'
        password = 'testuser'
        previously_created = self.create_new_account_as_admin( email=email, password=password )
        # Get the user object for later tests
        global regular_user3
        regular_user3 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test3@bx.psu.edu' ).first()
        assert regular_user3 is not None, 'Problem retrieving user with email "test3@bx.psu.edu" from the database'
        # Make sure DefaultUserPermissions were created
        if not regular_user3.default_permissions:
            raise AssertionError( 'No DefaultUserPermissions were created for user %s when the admin created the account' % email )
        # Make sure a private role was created for the user
        if not regular_user3.roles:
            raise AssertionError( 'No UserRoleAssociations were created for user %s when the admin created the account' % email )
        if not previously_created and len( regular_user3.roles ) != 1:
            raise AssertionError( '%d UserRoleAssociations were created for user %s when the admin created the account ( should have been 1 )' \
                                  % ( len( regular_user3.roles ), regular_user3.email ) )
        for ura in regular_user3.roles:
            role = galaxy.model.Role.get( ura.role_id )
            if not previously_created and role.type != 'private':
                raise AssertionError( 'Role created for user %s when the admin created the account is not private, type is' \
                                      % str( role.type ) )
        if not previously_created:
            # Make sure a history was not created ( previous test runs may have left deleted histories )
            histories = galaxy.model.History.filter( and_( galaxy.model.History.table.c.user_id==regular_user3.id,
                                                           galaxy.model.History.table.c.deleted==False ) ).all()
            if histories:
                raise AssertionError( 'Histories were incorrectly created for user %s when the admin created the account' % email )
            # Make sure the user was not associated with any groups
            if regular_user3.groups:
                raise AssertionError( 'Groups were incorrectly associated with user %s when the admin created the account' % email )
    def test_025_reset_password_as_admin( self ):
        """Testing reseting a user password as admin"""
        email = 'test3@bx.psu.edu'
        self.reset_password_as_admin( user_id=regular_user3.id, password='testreset' )
        self.logout()
    def test_030_login_after_password_reset( self ):
        """Testing logging in after an admin reset a password - tests DefaultHistoryPermissions for accounts created by an admin"""
        self.login( email='test3@bx.psu.edu', password='testreset' )
        # Make sure a History and HistoryDefaultPermissions exist for the user
        # Logged in as regular_user3
        latest_history = galaxy.model.History.filter( and_( galaxy.model.History.table.c.deleted==False,
                                                      galaxy.model.History.table.c.user_id==regular_user3.id ) ) \
            .order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        if not latest_history.user_id == regular_user3.id:
            raise AssertionError( 'A history was not created for user %s when he logged in' % email )
        if not latest_history.default_permissions:
            raise AssertionError( 'No DefaultHistoryPermissions were created for history id %d when it was created' % latest_history.id )
        if len( latest_history.default_permissions ) > 1:
            raise AssertionError( 'More than 1 DefaultHistoryPermissions were created for history id %d when it was created' % latest_history.id )
        dhp =  galaxy.model.DefaultHistoryPermissions.filter( galaxy.model.DefaultHistoryPermissions.table.c.history_id==latest_history.id ).first()
        if not dhp.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultHistoryPermission.action for history id %d is "%s", but it should be "manage permissions"' \
                                  % ( latest_history.id, dhp.action ) )
        # Upload a file to create a HistoryDatasetAssociation
        self.upload_file( '1.bed' )
        latest_dataset = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        for dp in latest_dataset.actions:
            # Should only have 1 DatasetPermissions
            if dp.action != galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
                raise AssertionError( 'The DatasetPermissions for dataset id %d is %s ( should have been %s )' \
                                      % ( latest_dataset.id,
                                          latest_dataset.actions.action, 
                                          galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        self.logout()
        # Reset the password to the default for later tests
        self.login( email='test@bx.psu.edu' )
        self.reset_password_as_admin( user_id=regular_user3.id, password='testuser' )
    def test_035_mark_user_deleted( self ):
        """Testing marking a user account as deleted"""
        self.mark_user_deleted( user_id=regular_user3.id, email=regular_user3.email )
        # Deleting a user should not delete any associations
        regular_user3.refresh()
        if not regular_user3.active_histories:
            raise AssertionError( 'HistoryDatasetAssociations for regular_user3 were incorrectly deleted when the user was marked deleted' )
    def test_040_undelete_user( self ):
        """Testing undeleting a user account"""
        self.undelete_user( user_id=regular_user3.id, email=regular_user3.email )
    def test_045_create_role( self ):
        """Testing creating new role with 3 members ( and a new group named the same ), then renaming the role"""
        name = 'Role One'
        description = "This is Role Ones description"
        user_ids=[ str( admin_user.id ), str( regular_user1.id ), str( regular_user3.id ) ]
        self.create_role( name=name, description=description, in_user_ids=user_ids, in_group_ids=[],
                          create_group_for_role='yes', private_role=admin_user.email )
        # Get the role object for later tests
        global role_one
        role_one = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
        assert role_one is not None, 'Problem retrieving role named "Role One" from the database'
        # Make sure UserRoleAssociations are correct
        if len( role_one.users ) != len( user_ids ):
            raise AssertionError( '%d UserRoleAssociations were created for role id %d when it was created ( should have been %d )' \
                                  % ( len( role_one.users ), role_one.id, len( user_ids ) ) )
        # Each of the following users should now have 2 role associations, their private role and role_one
        for user in [ admin_user, regular_user1, regular_user3 ]:
            user.refresh()
            if len( user.roles ) != 2:
                raise AssertionError( '%d UserRoleAssociations are associated with user %s ( should be 2 )' \
                                      % ( len( user.roles ), user.email ) )
        # Make sure the group was created
        self.home()
        self.visit_page( 'admin/groups' )
        self.check_page_for_string( name )
        global group_zero
        group_zero = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
        # Rename the role
        rename = "Role One's been Renamed"
        redescription="This is Role One's Re-described"
        self.rename_role( str( role_one.id ), name=rename, description=redescription )
        self.home()
        self.visit_page( 'admin/roles' )
        self.check_page_for_string( rename )
        self.check_page_for_string( redescription )
        # Reset the role back to the original name and description
        self.rename_role( str( role_one.id ), name=name, description=description )
    def test_050_create_group( self ):
        """Testing creating new group with 3 members and 1 associated role, then renaming it"""
        name = "Group One's Name"
        user_ids=[ str( admin_user.id ), str( regular_user1.id ), str( regular_user3.id ) ]
        role_ids=[ str( role_one.id ) ]
        self.create_group( name=name, in_user_ids=user_ids, in_role_ids=role_ids )
        # Get the group object for later tests
        global group_one
        group_one = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
        assert group_one is not None, 'Problem retrieving group named "Group One" from the database'
        # Make sure UserGroupAssociations are correct
        if len( group_one.users ) != len( user_ids ):
            raise AssertionError( '%d UserGroupAssociations were created for group id %d when it was created ( should have been %d )' \
                                  % ( len( group_one.users ), group_one.id, len( user_ids ) ) )
        # Each user should now have 1 group association, group_one
        for user in [ admin_user, regular_user1, regular_user3 ]:
            user.refresh()
            if len( user.groups ) != 1:
                raise AssertionError( '%d UserGroupAssociations are associated with user %s ( should be 1 )' % ( len( user.groups ), user.email ) )
        # Make sure GroupRoleAssociations are correct
        if len( group_one.roles ) != len( role_ids ):
            raise AssertionError( '%d GroupRoleAssociations were created for group id %d when it was created ( should have been %d )' \
                                  % ( len( group_one.roles ), group_one.id, len( role_ids ) ) )
        # Rename the group
        rename = "Group One's been Renamed"
        self.rename_group( str( group_one.id ), name=rename, )
        self.home()
        self.visit_page( 'admin/groups' )
        self.check_page_for_string( rename )
        # Reset the group back to the original name
        self.rename_group( str( group_one.id ), name=name )
    def test_055_add_members_and_role_to_group( self ):
        """Testing editing user membership and role associations of an existing group"""
        name = 'Group Two'
        self.create_group( name=name, in_user_ids=[], in_role_ids=[] )
        # Get the group object for later tests
        global group_two
        group_two = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
        assert group_two is not None, 'Problem retrieving group named "Group Two" from the database'
        # group_two should have no associations
        if group_two.users:
            raise AssertionError( '%d UserGroupAssociations were created for group id %d when it was created ( should have been 0 )' \
                              % ( len( group_two.users ), group_two.id ) )
        if group_two.roles:
            raise AssertionError( '%d GroupRoleAssociations were created for group id %d when it was created ( should have been 0 )' \
                              % ( len( group_two.roles ), group_two.id ) )
        group_two_id = str( group_two.id )
        user_ids = [ str( regular_user1.id )  ]
        role_ids = [ str( role_one.id ) ]
        self.associate_users_and_roles_with_group( group_two.id, group_two.name, user_ids=user_ids, role_ids=role_ids )
    def test_060_create_role_with_user_and_group_associations( self ):
        """Testing creating a role with user and group associations"""
        # NOTE: To get this to work with twill, all select lists on the ~/admin/role page must contain at least
        # 1 option value or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug in twill, we create the role, we bypass the page and visit the URL in the
        # associate_users_and_groups_with_role() method.
        name = 'Role Two'
        description = 'This is Role Two'
        user_ids=[ str( admin_user.id ) ]
        group_ids=[ str( group_two.id ) ]
        private_role=admin_user.email
        # Create the role
        self.create_role( name=name, description=description, in_user_ids=user_ids, in_group_ids=group_ids, private_role=private_role )
        # Get the role object for later tests
        global role_two
        role_two = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
        assert role_two is not None, 'Problem retrieving role named "Role Two" from the database'
        # Make sure UserRoleAssociations are correct
        if len( role_two.users ) != len( user_ids ):
            raise AssertionError( '%d UserRoleAssociations were created for role id %d when it was created with %d members' \
                                  % ( len( role_two.users ), role_two.id, len( user_ids ) ) )
        # admin_user should now have 3 role associations, private role, role_one, role_two
        admin_user.refresh()
        if len( admin_user.roles ) != 3:
            raise AssertionError( '%d UserRoleAssociations are associated with user %s ( should be 3 )' % ( len( admin_user.roles ), admin_user.email ) )
        # Make sure GroupRoleAssociations are correct
        role_two.refresh()
        if len( role_two.groups ) != len( group_ids ):
            raise AssertionError( '%d GroupRoleAssociations were created for role id %d when it was created ( should have been %d )' \
                                  % ( len( role_two.groups ), role_two.id, len( group_ids ) ) )
        # group_two should now be associated with 2 roles: role_one, role_two
        group_two.refresh()
        if len( group_two.roles ) != 2:
            raise AssertionError( '%d GroupRoleAssociations are associated with group id %d ( should be 2 )' % ( len( group_two.roles ), group_two.id ) )
    def test_065_change_user_role_associations( self ):
        """Testing changing roles associated with a user"""
        # Create a new role with no associations
        name = 'Role Three'
        description = 'This is Role Three'
        user_ids=[]
        group_ids=[]
        private_role=admin_user.email
        self.create_role( name=name, description=description, in_user_ids=user_ids, in_group_ids=group_ids, private_role=private_role )
        # Get the role object for later tests
        global role_three
        role_three = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
        assert role_three is not None, 'Problem retrieving role named "Role Three" from the database'
        # Associate the role with a user
        admin_user.refresh()
        role_ids = []
        for ura in admin_user.non_private_roles:
            role_ids.append( str( ura.role_id ) )
        role_ids.append( str( role_three.id ) )
        group_ids = []
        for uga in admin_user.groups:
            group_ids.append( str( uga.group_id ) )
        check_str = "User '%s' has been updated with %d associated roles and %d associated groups" % ( admin_user.email, len( role_ids ), len( group_ids ) )
        self.associate_roles_and_groups_with_user( str( admin_user.id ), str( admin_user.email ),
                                                   in_role_ids=role_ids, in_group_ids=group_ids, check_str=check_str )
        admin_user.refresh()
        # admin_user should now be associated with 4 roles: private, role_one, role_two, role_three
        if len( admin_user.roles ) != 4:
            raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 4 )' % ( len( admin_user.roles ), admin_user.email ) )
    def test_070_create_library( self ):
        """Testing creating a new library, then renaming it"""
        name = "Library One's Name"
        description = "This is Library One's description"
        self.create_library( name=name, description=description )
        self.visit_page( 'library_admin/browse_libraries' )
        self.check_page_for_string( name )
        self.check_page_for_string( description )
        # Get the library object for later tests
        global library_one
        library_one = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name==name,
                                                         galaxy.model.Library.table.c.description==description,
                                                         galaxy.model.Library.table.c.deleted==False ) ).first()
        assert library_one is not None, 'Problem retrieving library named "%s" from the database' % name
        # Set permissions on the library, sort for later testing
        permissions_in = [ k for k, v in galaxy.model.Library.permitted_actions.items() ]
        permissions_out = []
        # Role one members are: admin_user, regular_user1, regular_user3.  Each of these users will be permitted to
        # LIBRARY_ADD, LIBRARY_MODIFY, LIBRARY_MANAGE for library items.
        self.set_library_permissions( str( library_one.id ), library_one.name, str( role_one.id ), permissions_in, permissions_out )                                            
        # Rename the library
        rename = "Library One's been Renamed"
        redescription = "This is Library One's Re-described"
        self.rename_library( str( library_one.id ), library_one.name, name=rename, description=redescription )
        self.home()
        self.visit_page( 'library_admin/browse_libraries' )
        self.check_page_for_string( rename )
        self.check_page_for_string( redescription )
        # Reset the library back to the original name and description
        library_one.refresh()
        self.rename_library( str( library_one.id ), library_one.name, name=name, description=description )
        library_one.refresh()
        """
        def test_075_library_template_features( self ):
        Testing adding a template to a library, along with template features on the admin side
        # Make sure a form exists
        self.create_form( name='Form One', description='This is Form One' )
        current_form = galaxy.model.FormDefinitionCurrent.filter( galaxy.model.FormDefinitionCurrent.table.c.deleted==False ) \
            .order_by( desc( galaxy.model.FormDefinitionCurrent.table.c.create_time ) ).first()
        global form_one
        form_one = current_form.latest_form
        # Add a new information template to the library
        template_name = 'Library Template 1'
        self.add_library_info_template( str( library_one.id ),
                                        library_one.name,
                                        str( form_one.id ),
                                        form_one.name )
        # Make sure the template fields are displayed on the library information page
        self.home()
        self.visit_url( '%s/library_admin/library?id=%s&information=True' % ( self.url, str( library_one.id ) ) )
        num_fields = len( form_one.fields )
        for index in range( num_fields ):
            label_check_str = form_one.fields[ index ][ 'label' ]
            help_check_str = form_one.fields[ index ][ 'helptext' ]
            required_check_str = form_one.fields[ index ][ 'required' ].capitalize()
        self.check_page_for_string( label_check_str )
        self.check_page_for_string( help_check_str )
        self.check_page_for_string( required_check_str )
        # Add information to the library using the template
        for index in range( num_fields ):
            field_name = 'field_%i' % index
            contents = '%s contents' % form_one.fields[ index ][ 'label' ]
            # There are 2 forms on this page and the template is the 2nd form
            tc.fv( '2', field_name, contents )
        tc.submit( 'edit_info_button' )
        self.check_page_for_string ( 'The information has been updated.' )
        self.home()
        # TODO: add more testing for full feature coverage
        """
    def test_080_add_public_dataset_to_root_folder( self ):
        """Testing adding a public dataset to the root folder"""
        actions = [ v.action for k, v in galaxy.model.Library.permitted_actions.items() ]
        actions.sort()
        message = 'Testing adding a public dataset to the root folder'
        self.add_library_dataset( '1.bed',
                                  str( library_one.id ),
                                  str( library_one.root_folder.id ),
                                  library_one.root_folder.name,
                                  file_format='bed',
                                  dbkey='hg18',
                                  message=message.replace( ' ', '+' ),
                                  root=True )
        global ldda_one
        ldda_one = galaxy.model.LibraryDatasetDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.create_time ) ).first()
        assert ldda_one is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_one from the database'
        self.home()
        self.visit_url( '%s/library_admin/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( "1.bed" )
        self.check_page_for_string( message )
        self.check_page_for_string( admin_user.email )
        # Make sure the library permissions were inherited to the library_dataset_dataset_association
        ldda_permissions = galaxy.model.LibraryDatasetDatasetAssociationPermissions \
            .filter( galaxy.model.LibraryDatasetDatasetAssociationPermissions.table.c.library_dataset_dataset_association_id == ldda_one.id ) \
            .all()
        ldda_permissions = [ lddap_obj.action for lddap_obj in ldda_permissions ]
        ldda_permissions.sort()
        assert actions == ldda_permissions, "Permissions for ldda id %s not correctly inherited from library %s" \
                            % ( ldda_one.id, library_one.name )
        # Make sure DatasetPermissions are correct - default is 'manage permissions'
        if len( ldda_one.dataset.actions ) > 1:
            raise AssertionError( '%d DatasetPermissionss were created for dataset id %d when it was created ( should have been 1 )' \
                                  % ( len( ldda_one.dataset.actions ), ldda_one.dataset.id ) )
        dp = galaxy.model.DatasetPermissions.filter( galaxy.model.DatasetPermissions.table.c.dataset_id==ldda_one.dataset.id ).first()
        if not dp.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DatasetPermissions.action for dataset id %d is "%s", but it should be "manage permissions"' \
                                  % ( ldda_one.dataset.id, dp.action ) )
        ## TODO: temporarily eliminating templates until we have the new forms features done
        # Make sure the library template was inherited by the ldda
        """
        self.home()
        self.visit_url( "%s/library_admin/library_dataset_dataset_association?edit_info=True&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, str( library_one.id ), str( library_one.root_folder.id ), str( ldda_one.id ) ) )
        self.check_page_for_string( 'wind' )
        self.check_page_for_string( 'This is the wind component' )
        self.check_page_for_string( 'bag' )
        self.check_page_for_string( 'This is the bag component' )
        """
        # Make sure other users can access the dataset from the Libraries view
        self.logout()
        self.login( email=regular_user2.email )
        self.home()
        self.visit_url( '%s/library/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( "1.bed" )
        self.logout()
        self.login( email=admin_user.email )
        self.home()
        """
        ## TODO: temporarily eliminating templates until we have the new forms features done
        def test_085_editing_dataset_information( self ):
            Testing editing dataset template element information
            # Need the current library_item_info_element.id
            last_library_item_info_element = galaxy.model.LibraryItemInfoElement.query() \
                .order_by( desc( galaxy.model.LibraryItemInfoElement.table.c.id ) ).first()
            global ldda_one_ele_2_field_name
            ldda_one_ele_2_field_name = "info_element_%s" % str( last_library_item_info_element.id )
            ele_2_contents = 'pipe'
            global ldda_one_ele_1_field_name
            ldda_one_ele_1_field_name = "info_element_%s" % ( str( last_library_item_info_element.id - 1 ) )
            ele_1_contents = 'blown'
            self.edit_ldda_template_element_info( str( library_one.id ), str( library_one.root_folder.id ), str( ldda_one.id ),
                ldda_one.name, ldda_one_ele_1_field_name, ele_1_contents, ldda_one_ele_2_field_name, ele_2_contents )
            self.home()
        """
    def test_090_add_new_folder_to_root_folder( self ):
        """Testing adding a folder to a library root folder"""
        root_folder = library_one.root_folder
        name = "Root Folder's Folder One"
        description = "This is the root folder's Folder One"
        self.add_folder( str( library_one.id ), str( root_folder.id ), name=name, description=description )
        global folder_one
        folder_one = galaxy.model.LibraryFolder.filter( and_( galaxy.model.LibraryFolder.table.c.parent_id==root_folder.id,
                                                              galaxy.model.LibraryFolder.table.c.name==name,
                                                              galaxy.model.LibraryFolder.table.c.description==description ) ).first()
        assert folder_one is not None, 'Problem retrieving library folder named "%s" from the database' % name
        self.home()
        self.visit_url( '%s/library_admin/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( name )
        self.check_page_for_string( description )
        ## TODO: temporarily eliminating templates until we have the new forms features done
        # Make sure the library template is inherited
        """
        self.home()
        self.visit_url( '%s/library_admin/folder?id=%s&library_id=%s&information=True' % ( self.url, str( folder_one.id ), str( library_one.id ) ) )
        self.check_page_for_string( 'wind' )
        self.check_page_for_string( 'This is the wind component' )
        self.check_page_for_string( 'bag' )
        self.check_page_for_string( 'This is the bag component' )
        """
        self.home()
        """
        ## TODO: temporarily eliminating templates until we have the new forms features done
        def test_095_add_folder_template( self ):
            Testing adding a new folder template to a folder
            # Add a new information template to the folder
            template_name = 'Folder Template 1'
            ele_name_0 = 'Fu'
            ele_help_0 = 'This is the Fu component'.replace( ' ', '+' )
            ele_name_1 = 'Bar'
            ele_help_1 = 'This is the Bar component'.replace( ' ', '+' )
            self.home()
            self.add_folder_info_template( str( library_one.id ), library_one.name, str( folder_one.id ), folder_one.name,
                                           name=template_name, num_fields='2', ele_name_0=ele_name_0, ele_help_0=ele_help_0,
                                           ele_name_1=ele_name_1, ele_help_1=ele_help_1 )
            self.home()
            self.visit_url( '%s/library_admin/folder?id=%s&library_id=%s&information=True' % ( self.url, str( folder_one.id ), str( library_one.id ) ) )
            self.check_page_for_string( ele_name_0 )
            check_str = ele_help_0.replace( '+', ' ' )
            self.check_page_for_string( check_str )
            self.check_page_for_string( ele_name_1 )
            check_str = ele_help_1.replace( '+', ' ' )
            self.check_page_for_string( check_str )
            self.home()
        """
    def test_100_add_subfolder_to_folder( self ):
        """Testing adding a folder to a library folder"""
        name = "Folder One's Subfolder"
        description = "This is the Folder One's subfolder"
        self.add_folder( str( library_one.id ), str( folder_one.id ), name=name, description=description )
        global subfolder_one
        subfolder_one = galaxy.model.LibraryFolder.filter( and_( galaxy.model.LibraryFolder.table.c.parent_id==folder_one.id,
                                                                 galaxy.model.LibraryFolder.table.c.name==name,
                                                                 galaxy.model.LibraryFolder.table.c.description==description ) ).first()
        assert subfolder_one is not None, 'Problem retrieving library folder named "Folder Ones Subfolder" from the database'
        self.home()
        self.visit_url( '%s/library_admin/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( name )
        self.check_page_for_string( description )
        ## TODO: temporarily eliminating templates until we have the new forms features done
        # Make sure the parent folder's template is inherited
        self.home()
        """
        self.visit_url( '%s/library_admin/folder?id=%s&library_id=%s&information=True' % ( self.url, str( folder_one.id ), str( library_one.id ) ) )
        self.check_page_for_string( 'Fu' )
        self.check_page_for_string( 'This is the Fu component' )
        self.check_page_for_string( 'Bar' )
        self.check_page_for_string( 'This is the Bar component' )
        # Make sure the library template is not inherited
        try:
            self.check_page_for_string( 'wind' )
            raise AssertionError( 'Library template inherited by folder when it should not have been.' )
        except:
            pass
        self.home()
        """
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        def test_105_add_template_element( self ):
            Testing adding a new element to an existing library template
            library_one_template.refresh()
            element_ids = []
            for ele in library_one_template.elements:
                element_ids.append( ele.id )
            element_ids.sort()
    
            name = 'Library Template 1 renamed'
            ele_field_name_1 = "element_name_%s" % element_ids[0]
            ele_name_1 = 'wind'
            ele_field_desc_1 = "element_description_%s" % element_ids[0]
            ele_desc_1 = 'This is the wind component'
            ele_field_name_2 = "element_name_%s" % element_ids[1]
            ele_name_2 = 'bag'
            ele_field_desc_2 = "element_description_%s" % element_ids[1]
            ele_desc_2 = 'This is the bag component'
            new_ele_name = 'Fubar'
            new_ele_desc = 'This is the Fubar component'
            self.add_library_info_template_element( str( library_one.id ),
                                                    str( library_one_template.id ),
                                                    library_one_template.name,
                                                    ele_field_name_1,
                                                    ele_name_1,
                                                    ele_field_desc_1,
                                                    ele_desc_1,
                                                    ele_field_name_2,
                                                    ele_name_2,
                                                    ele_field_desc_2,
                                                    ele_desc_2,
                                                    new_ele_name=new_ele_name,
                                                    new_ele_desc=new_ele_desc )
            # Make sure the new template element shows up on the existing library info page
            self.home()
            self.visit_url( '%s/library_admin/library?id=%s&information=True' % ( self.url, str( library_one.id ) ) )
            self.check_page_for_string( library_one.name )
            self.check_page_for_string( library_one.description )
            self.check_page_for_string( 'wind' )
            self.check_page_for_string( 'hello' )
            self.check_page_for_string( 'This is the wind component' )
            self.check_page_for_string( 'bag' )
            self.check_page_for_string( 'world' )
            self.check_page_for_string( 'This is the bag component' )
            self.check_page_for_string( 'Fubar' )
            self.check_page_for_string( 'This is the Fubar component' )
            # Make sure the new template element does not show up on existing info pages for folder_one since it has its own template
            self.home()
            self.visit_url( '%s/library_admin/folder?id=%s&library_id=%s&information=True' % ( self.url, str( folder_one.id ), str( library_one.id ) ) )
            self.check_page_for_string( 'Fu' )
            self.check_page_for_string( 'This is the Fu component' )
            self.check_page_for_string( 'Bar' )
            self.check_page_for_string( 'This is the Bar component' )
            try:
                self.check_page_for_string( 'Fubar' )
                raise AssertionError( 'Changed library template inherited by folder "%s" when folder had an associated template of its own' )
            except:
                pass
            # Make sure the new template element shows up on existing info pages for ldda_one since it is contained in the root folder
            self.home()
            self.visit_url( "%s/library_admin/library_dataset_dataset_association?edit_info=True&library_id=%s&folder_id=%s&id=%s" % \
                            ( self.url, str( library_one.id ), str( folder_one.id ), str( ldda_one.id ) ) )
            # Visiting the above page will have resulted in the creation of a new LibraryItemInfoElement, so we'll retrieve it
            # for later use
            last_library_item_info_element = galaxy.model.LibraryItemInfoElement.query() \
                .order_by( desc( galaxy.model.LibraryItemInfoElement.table.c.id ) ).first()
            global ldda_one_ele_3_field_name
            ldda_one_ele_3_field_name = "info_element_%s" % str( last_library_item_info_element.id )
            self.check_page_for_string( 'wind' )
            self.check_page_for_string( 'This is the wind component' )
            self.check_page_for_string( 'bag' )
            self.check_page_for_string( 'This is the bag component' )
            self.check_page_for_string( 'Fubar' )
            self.check_page_for_string( 'This is the Fubar component' )
            self.home()
        """
    def test_110_add_2nd_new_folder_to_root_folder( self ):
        """Testing adding a 2nd folder to a library root folder"""
        root_folder = library_one.root_folder
        name = "Folder Two"
        description = "This is the root folder's Folder Two"
        self.add_folder( str( library_one.id ), str( root_folder.id ), name=name, description=description )
        global folder_two
        folder_two = galaxy.model.LibraryFolder.filter( and_( galaxy.model.LibraryFolder.table.c.parent_id==root_folder.id,
                                                              galaxy.model.LibraryFolder.table.c.name==name,
                                                              galaxy.model.LibraryFolder.table.c.description==description ) ).first()
        assert folder_two is not None, 'Problem retrieving library folder named "%s" from the database' % name
        self.home()
        self.visit_url( '%s/library_admin/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( name )
        self.check_page_for_string( description )
        ## TODO: temporarily eliminating templates until we have the new forms features done
        # Make sure the changed library template is inherited to the new folder
        """
        self.home()
        self.visit_url( '%s/library_admin/folder?id=%s&library_id=%s&information=True' % ( self.url, str( folder_two.id ), str( library_one.id ) ) )
        self.check_page_for_string( 'wind' )
        self.check_page_for_string( 'This is the wind component' )
        self.check_page_for_string( 'bag' )
        self.check_page_for_string( 'This is the bag component' )
        self.check_page_for_string( 'Fubar' )
        self.check_page_for_string( 'This is the Fubar component' )
        """
        self.home()
    def test_115_add_public_dataset_to_root_folders_2nd_subfolder( self ):
        """Testing adding a public dataset to the root folder's 2nd sub-folder"""
        actions = [ v.action for k, v in galaxy.model.Library.permitted_actions.items() ]
        actions.sort()
        message = "Testing adding a public dataset to the folder named %s" % folder_two.name
        self.add_library_dataset( '2.bed',
                                  str( library_one.id ),
                                  str( folder_two.id ),
                                  folder_two.name,
                                  file_format='bed',
                                  dbkey='hg18',
                                  message=message.replace( ' ', '+' ),
                                  root=False )
        global ldda_two
        ldda_two = galaxy.model.LibraryDatasetDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.create_time ) ).first()
        assert ldda_two is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_two from the database'
        self.home()
        self.visit_url( '%s/library_admin/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( "2.bed" )
        self.check_page_for_string( message )
        self.check_page_for_string( admin_user.email )
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        def test_120_add_template_to_root_folders_2nd_subfolder( self ):
            Testing adding a template to the root folder's 2nd sub-folder
            # Before adding the folder template, the inherited library template should be displayed
            self.home()
            self.visit_url( "%s/library_admin/library_dataset_dataset_association?edit_info=True&library_id=%s&folder_id=%s&id=%s" % \
                            ( self.url, str( library_one.id ), str( folder_two.id ), str( ldda_two.id ) ) )
            self.check_page_for_string( 'wind' )
            self.check_page_for_string( 'This is the wind component' )
            self.check_page_for_string( 'bag' )
            self.check_page_for_string( 'This is the bag component' )
            self.check_page_for_string( 'Fubar' )
            self.check_page_for_string( 'This is the Fubar component' )
            self.home()
            # Add a new folde template
            template_name = 'Folder 2 Template'
            ele_name_0 = 'kill'
            ele_help_0 = 'This is the kill component'.replace( ' ', '+' )
            ele_name_1 = 'bill'
            ele_help_1 = 'This is the bill component'.replace( ' ', '+' )
            self.home()
            self.add_folder_info_template( str( library_one.id ), library_one.name, str( folder_two.id ), folder_two.name,
                                           name=template_name, num_fields='2', ele_name_0=ele_name_0, ele_help_0=ele_help_0,
                                           ele_name_1=ele_name_1, ele_help_1=ele_help_1 )
            # Make sure the new template id displayed on the folder information page
            self.home()
            self.visit_url( '%s/library_admin/folder?id=%s&library_id=%s&information=True' % ( self.url, str( folder_two.id ), str( library_one.id ) ) )
            self.check_page_for_string( ele_name_0 )
            check_str = ele_help_0.replace( '+', ' ' )
            self.check_page_for_string( check_str )
            self.check_page_for_string( ele_name_1 )
            check_str = ele_help_1.replace( '+', ' ' )
            self.check_page_for_string( check_str )
            # The library dataset ldda_two had previously inherited the library template prior to the new folder template
            # being introduced, so the library template should still be displayed on the ldda information page
            self.home()
            self.visit_url( "%s/library_admin/library_dataset_dataset_association?edit_info=True&library_id=%s&folder_id=%s&id=%s" % \
                            ( self.url, str( library_one.id ), str( folder_two.id ), str( ldda_two.id ) ) )
            self.check_page_for_string( 'wind' )
            self.check_page_for_string( 'This is the wind component' )
            self.check_page_for_string( 'bag' )
            self.check_page_for_string( 'This is the bag component' )
            self.check_page_for_string( 'Fubar' )
            self.check_page_for_string( 'This is the Fubar component' )
            # Make sure the new folder template is not displayed
            try:
                self.check_page_for_string( 'kill' )
                raise AssertionError( 'New folder template elements incorrectly included in information page for ldda "%s"' % ldda_two.name )
            except:
                pass
            self.home()
        """
    def test_125_add_2nd_public_dataset_to_root_folders_2nd_subfolder( self ):
        """Testing adding a 2nd public dataset to the root folder's 2nd sub-folder"""
        actions = [ v.action for k, v in galaxy.model.Library.permitted_actions.items() ]
        actions.sort()
        message = "Testing adding a 2nd public dataset to the folder named %s" % folder_two.name
        self.add_library_dataset( '3.bed',
                                  str( library_one.id ),
                                  str( folder_two.id ),
                                  folder_two.name,
                                  file_format='bed',
                                  dbkey='hg18',
                                  message=message.replace( ' ', '+' ),
                                  root=False )
        global ldda_three
        ldda_three = galaxy.model.LibraryDatasetDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.create_time ) ).first()
        assert ldda_three is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_three from the database'
        self.home()
        self.visit_url( '%s/library_admin/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( "3.bed" )
        self.check_page_for_string( message )
        self.check_page_for_string( admin_user.email )
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        def test_130_editing_dataset_information_with_new_folder_template( self ):
            Testing editing dataset template element information with new inherited folder template
            # Need the current library_item_info_element.id
            last_library_item_info_element = galaxy.model.LibraryItemInfoElement.query() \
                .order_by( desc( galaxy.model.LibraryItemInfoElement.table.c.id ) ).first()
            # Make sure the changed inherited template is included in the ldda information
            ele_2_field_name = "info_element_%s" % str( last_library_item_info_element.id )
            ele_2_contents = 'II'
            ele_2_help = 'This is the bill component'
            ele_1_field_name = "info_element_%s" % ( str( last_library_item_info_element.id - 1 ) )
            ele_1_contents = 'Volume'
            ele_1_help = 'This is the kill component'
            self.edit_ldda_template_element_info( str( library_one.id ), str( folder_two.id ), str( ldda_three.id ),
                ldda_three.name, ele_1_field_name, ele_1_contents, ele_2_field_name, ele_2_contents,
                ele_1_help=ele_1_help, ele_2_help=ele_2_help )
            self.home()
        """
    def test_135_add_dataset_with_private_role_restriction_to_folder( self ):
        """Testing adding a dataset with a private role restriction to a folder"""
        # Add a dataset restricted by the following:
        # DATASET_MANAGE_PERMISSIONS = "test@bx.psu.edu" via DefaultUserPermissions
        # DATASET_ACCESS = "regular_user1" private role via this test method
        # LIBRARY_ADD = "Role One" via inheritance from parent folder
        # LIBRARY_MODIFY = "Role One" via inheritance from parent folder
        # LIBRARY_MANAGE = "Role One" via inheritance from parent folder
        # "Role One" members are: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # This means that only user test1@bx.psu.edu can see the dataset from the Libraries view
        #
        # TODO: this demonstrates a weakness in our logic:  If test@bx.psu.edu cannot
        # access the dataset from the Libraries view, then the DATASET_MANAGE_PERMISSIONS
        # setting is useless if test@bx.psu.edu is not an admin.  This should be corrected,
        # by displaying a warning message on the permissions form.
        message ='This is a test of the fourth dataset uploaded'
        ele_name_0 = 'Fu'
        ele_name_1 = 'Bar'
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        self.add_library_dataset( '4.bed',
                                  str( library_one.id ),
                                  str( folder_one.id ),
                                  folder_one.name,
                                  file_format='bed',
                                  dbkey='hg18',
                                  roles=[ str( regular_user1_private_role.id ) ],
                                  message=message.replace( ' ', '+' ),
                                  root=False,
                                  check_template_str1=ele_name_0,
                                  check_template_str2=ele_name_1 )
        """
        self.add_library_dataset( '4.bed',
                                  str( library_one.id ),
                                  str( folder_one.id ),
                                  folder_one.name,
                                  file_format='bed',
                                  dbkey='hg18',
                                  roles=[ str( regular_user1_private_role.id ) ],
                                  message=message.replace( ' ', '+' ),
                                  root=False )
        global ldda_four
        ldda_four = galaxy.model.LibraryDatasetDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.create_time ) ).first()
        assert ldda_four is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_four from the database'
        self.home()
        self.visit_url( '%s/library_admin/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( "4.bed" )
        self.check_page_for_string( message )
        self.check_page_for_string( admin_user.email )
        self.home()
    def test_140_accessing_dataset_with_private_role_restriction( self ):
        """Testing accessing a dataset with a private role restriction"""
        # admin_user should not be able to see 2.bed from the analysis view's access libraries
        self.home()
        self.visit_url( '%s/library/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can see library folder %s when it contains only datasets restricted by role %s' \
                                  % ( admin_user.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass
        try:
            self.check_page_for_string( '4.bed' )
            raise AssertionError( '%s can see dataset 4.bed in library folder %s when it was restricted by role %s' \
                                  % ( admin_user.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass
        self.logout()
        # regular_user1 should be able to see 4.bed from the analysis view's access librarys
        # since it was associated with regular_user1's private role
        self.login( email='test1@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( folder_one.name )
        self.check_page_for_string( '4.bed' )
        self.logout()
        # regular_user2 should not be able to see 1.bed from the analysis view's access librarys
        self.login( email='test2@bx.psu.edu' )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can see library folder %s when it contains only datasets restricted by role %s' \
                                  % ( regular_user2.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass
        try:
            self.check_page_for_string( '4.bed' )
            raise AssertionError( '%s can see dataset 4.bed in library folder %s when it was restricted by role %s' \
                                  % ( regular_user2.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass
        self.logout()
        # regular_user3 should not be able to see 2.bed from the analysis view's access librarys
        self.login( email='test3@bx.psu.edu' )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can see library folder %s when it contains only datasets restricted by role %s' \
                                  % ( regular_user3.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass
        try:
            self.check_page_for_string( '4.bed' )
            raise AssertionError( '%s can see dataset 4.bed in library folder %s when it was restricted by role %s' \
                                  % ( regular_user3.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        self.logout()
        self.login( email=admin_user.email )
        self.home()
    def test_145_change_dataset_access_permission( self ):
        """Testing changing the access permission on a dataset with a private role restriction"""
        # We need admin_user to be able to access 2.bed
        permissions_in = [ k for k, v in galaxy.model.Dataset.permitted_actions.items() ] + \
                         [ k for k, v in galaxy.model.Library.permitted_actions.items() ]
        permissions_out = []
        role_ids = "%s,%s" % ( str( role_one.id ), str( admin_user_private_role.id ) )
        self.set_library_dataset_permissions( str( library_one.id ), str( folder_one.id ), str( ldda_four.id ), ldda_four.name,
                                              role_ids, permissions_in, permissions_out )
        # admin_user should now be able to see 4.bed from the analysis view's access libraries
        self.home()
        self.visit_url( '%s/library/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( ldda_four.name )
        self.home()
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        def test_150_editing_restricted_datasets_information( self ):
            Testing editing a restricted library dataset's template element information
            ele_1_contents = ''
            ele_2_contents = ''
            ele_3_contents = 'Adding Fubar text'
            self.edit_ldda_template_element_info( str( library_one.id ), str( library_one.root_folder.id ), str( ldda_one.id ),
                ldda_one.name, ldda_one_ele_1_field_name, ele_1_contents, ldda_one_ele_2_field_name, ele_2_contents,
                ele_1_help='This is the wind component'.replace( ' ', '+' ),
                ele_2_help='This is the bag component'.replace( ' ', '+' ),
                ele_3_field_name=ldda_one_ele_3_field_name, ele_3_contents=ele_3_contents.replace( ' ', '+'  ) )
            # Check the updated information from the libraries view
            self.home()
            self.visit_url( '%s/library/library_dataset_dataset_association?info=True&library_id=%s&folder_id=%s&id=%s' \
                            % ( self.url, str( library_one.id ), str( library_one.root_folder.id ), str( ldda_one.id ) ) )
            self.check_page_for_string( ele_3_contents )
            try:
                self.check_page_for_string( 'blown' )
                raise AssertionError( 'Element contents were not correctly eliminated when the information was edited for ldda %s' % ldda_one.name)
            except:
                pass
            self.home()
        """
    def test_155_add_dataset_with_role_associated_with_group_and_users( self ):
        """Testing adding a dataset with a role that is associated with a group and users"""
        self.login( email='test@bx.psu.edu' )
        # Add a dataset restricted by role_two, which is currently associated as follows:
        # groups: group_two
        # users: test@bx.psu.edu, test1@bx.psu.edu via group_two
        message = 'Testing adding a dataset with a role that is associated with a group and users'
        ele_name_0 = 'Fu'
        ele_name_1 = 'Bar'
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        self.add_library_dataset( '5.bed',
                                  str( library_one.id ),
                                  str( folder_one.id ),
                                  folder_one.name,
                                  file_format='bed',
                                  dbkey='hg17',
                                  roles=[ str( role_two.id ) ],
                                  message=message.replace( ' ', '+' ),
                                  root=False,
                                  check_template_str1=ele_name_0,
                                  check_template_str2=ele_name_1 )
        """
        self.add_library_dataset( '5.bed',
                                  str( library_one.id ),
                                  str( folder_one.id ),
                                  folder_one.name,
                                  file_format='bed',
                                  dbkey='hg17',
                                  roles=[ str( role_two.id ) ],
                                  message=message.replace( ' ', '+' ),
                                  root=False )
        global ldda_five
        ldda_five = galaxy.model.LibraryDatasetDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.create_time ) ).first()
        assert ldda_five is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_five from the database'
        self.home()
        self.visit_url( '%s/library_admin/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( "5.bed" )
        self.check_page_for_string( message )
        self.check_page_for_string( admin_user.email )
        self.home()
    def test_160_accessing_dataset_with_role_associated_with_group_and_users( self ):
        """Testing accessing a dataset with a role that is associated with a group and users"""
        # admin_user should be able to see 5.bed since she is associated with role_two
        self.home()
        self.visit_url( '%s/library/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( "5.bed" )
        self.check_page_for_string( admin_user.email )
        self.logout()
        # regular_user1 should be able to see 5.bed since she is associated with group_two
        self.login( email = 'test1@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( folder_one.name )
        self.check_page_for_string( '5.bed' )
        self.check_page_for_string( admin_user.email )
        # Check the permissions on the dataset 5.bed - they are as folows:
        # DATASET_MANAGE_PERMISSIONS = test@bx.psu.edu
        # DATASET_ACCESS = Role Two
        #                  Role Two associations: test@bx.psu.edu and Group Two
        #                  Group Two members: Role One, Role Two, test1@bx.psu.edu
        #                  Role One associations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # LIBRARY_ADD = Role One
        #               Role One aassociations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # LIBRARY_MODIFY = Role One
        #                  Role One aassociations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        # LIBRARY_MANAGE = Role One
        #                  Role One aassociations: test@bx.psu.edu, test1@bx.psu.edu, test3@bx.psu.edu
        self.home()
        self.visit_url( '%s/library/library_dataset_dataset_association?edit_info=True&library_id=%s&folder_id=%s&id=%s' \
                        % ( self.url, str( library_one.id ), str( folder_one.id ), str( ldda_five.id ) ) )
        self.check_page_for_string( '5.bed' )
        self.check_page_for_string( 'This is the latest version of this library dataset' )
        # Current user test1@bx.psu.edu has Role One, which has the LIBRARY_MODIFY permission
        self.check_page_for_string( 'Edit attributes of 5.bed' )
        self.home()
        # Test importing the restricted dataset into a history, can't use the 
        # ~/library_admin/libraries form as twill barfs on it so we'll simulate the form submission
        # by going directly to the form action
        self.visit_url( '%s/library/datasets?do_action=add&ldda_ids=%d&library_id=%s' \
                        % ( self.url, ldda_five.id, str( library_one.id ) ) )
        self.check_page_for_string( '1 dataset(s) have been imported into your history' )
        self.logout()
        # regular_user2 should not be able to see 5.bed
        self.login( email = 'test2@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can see library folder %s when it contains only datasets restricted by role %s' \
                                  % ( regular_user2.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass
        try:
            self.check_page_for_string( '5.bed' )
            raise AssertionError( '%s can see dataset 5.bed in library folder %s when it was restricted by role %s' \
                                  % ( regular_user2.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass
        # regular_user3 should not be able to see folder_one ( even though it does not contain any datasets that she
        # can access ) since she has Role One, and Role One has all library permissions ( see above ).
        self.login( email = 'test3@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( folder_one.name )
        # regular_user3 should not be able to see 5.bed since users must have every role associated
        # with the dataset in order to access it, and regular_user3 isnot associated with Role Two
        try:
            self.check_page_for_string( '5.bed' )
            raise AssertionError( '%s can see dataset 5.bed in library folder %s when it was restricted by role %s' \
                                  % ( regular_user3.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass
        self.logout()
        self.login( email='test@bx.psu.edu' )
    def test_165_copy_dataset_from_history_to_subfolder( self ):
        """Testing copying a dataset from the current history to a subfolder"""
        self.new_history()
        self.upload_file( "6.bed" )
        latest_hda = galaxy.model.HistoryDatasetAssociation.query().order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        self.add_history_datasets_to_library( str( library_one.id ), str( subfolder_one.id ), subfolder_one.name, str( latest_hda.id ), root=False )
        # Test for DatasetPermissionss, the default setting is "manage permissions"
        last_dataset_created = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        dps = galaxy.model.DatasetPermissions.filter( galaxy.model.DatasetPermissions.table.c.dataset_id==last_dataset_created.id ).all()
        if not dps:
            raise AssertionError( 'No DatasetPermissionss created for dataset id: %d' % last_dataset_created.id )
        if len( dps ) > 1:
            raise AssertionError( 'More than 1 DatasetPermissionss created for dataset id: %d' % last_dataset_created.id )
        for dp in dps:
            if not dp.action == 'manage permissions':
                raise AssertionError( 'DatasetPermissions.action "%s" is not the DefaultHistoryPermission setting of "manage permissions"' \
                                      % str( dp.action ) )
        global ldda_six
        ldda_six = galaxy.model.LibraryDatasetDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.create_time ) ).first()
        assert ldda_six is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_six from the database'
        # Make sure the correct template was inherited
        ## TODO: temporarily eliminating templates until we have the new forms features done
        self.home()
        """
        self.visit_url( "%s/library_admin/library_dataset_dataset_association?edit_info=True&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, str( library_one.id ), str( subfolder_one.id ), str( ldda_six.id ) ) )
        self.check_page_for_string( 'Fu' )
        self.check_page_for_string( 'This is the Fu component' )
        self.check_page_for_string( 'Bar' )
        self.check_page_for_string( 'This is the Bar component' )
        """
    def test_170_editing_dataset_attribute_info( self ):
        """Testing editing a datasets attribute information"""
        new_ldda_name = '6.bed ( version 1 )'
        self.edit_ldda_attribute_info( str( library_one.id ), str( subfolder_one.id ), str( ldda_six.id ), ldda_six.name, new_ldda_name )
        self.home()
        ldda_six.refresh()
        self.visit_url( '%s/library_admin/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( ldda_six.name )
        self.home()
    def test_175_uploading_new_dataset_version( self ):
        """Testing uploading a new version of a dataset"""
        message = 'Testing uploading a new version of a dataset'
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        self.upload_new_dataset_version( '6.bed',
                                         str( library_one.id ),
                                         str( subfolder_one.id ),
                                         str( subfolder_one.name ),
                                         str( ldda_six.library_dataset.id ),
                                         ldda_six.name,
                                         file_format='auto',
                                         dbkey='hg18',
                                         message=message.replace( ' ', '+' ),
                                         check_template_str1='Fu',
                                         check_template_str2='Bar' )
        """
        self.upload_new_dataset_version( '6.bed',
                                         str( library_one.id ),
                                         str( subfolder_one.id ),
                                         str( subfolder_one.name ),
                                         str( ldda_six.library_dataset.id ),
                                         ldda_six.name,
                                         file_format='auto',
                                         dbkey='hg18',
                                         message=message.replace( ' ', '+' ) )
        global ldda_six_version_two
        ldda_six_version_two = galaxy.model.LibraryDatasetDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.create_time ) ).first()
        assert ldda_six_version_two is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_six_version_two from the database'
        self.home()
        self.visit_url( "%s/library_admin/library_dataset_dataset_association?info=True&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, str( library_one.id ), str( subfolder_one.id ), str( ldda_six_version_two.id ) ) )
        self.check_page_for_string( 'This is the latest version of this library dataset' )
        # Make sure the correct template was inherited
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        self.check_page_for_string( 'Fu' )
        self.check_page_for_string( 'This is the Fu component' )
        self.check_page_for_string( 'Bar' )
        self.check_page_for_string( 'This is the Bar component' )
        check_str = 'Expired versions of %s' % ldda_six_version_two.name
        self.check_page_for_string( check_str )
        self.check_page_for_string( ldda_six.name )
        """
        self.home()
        # Make sure th permissions are the same
        ldda_six.refresh()
        if len( ldda_six.actions ) != len( ldda_six_version_two.actions ):
            raise AssertionError( 'ldda "%s" actions "%s" != ldda "%s" actions "%s"' \
                % ( ldda_six.name, str( ldda_six.actions ),
                    ldda_six_version_two.name, str( ldda_six_version_two.actions ) ) )
        if len( ldda_six.library_dataset.actions ) != len( ldda_six_version_two.library_dataset.actions ):
            raise AssertionError( 'ldda.library_dataset "%s" actions "%s" != ldda.library_dataset "%s" actions "%s"' \
                % ( ldda_six.name, str( ldda_six.library_dataset.actions ), ldda_six_version_two.name, str( ldda_six_version_two.library_dataset.actions ) ) )
        if len( ldda_six.dataset.actions ) != len( ldda_six_version_two.dataset.actions ):
            raise AssertionError( 'ldda.dataset "%s" actions "%s" != ldda.dataset "%s" actions "%s"' \
                % ( ldda_six.name, str( ldda_six.dataset.actions ), ldda_six_version_two.name, str( ldda_six_version_two.dataset.actions ) ) )
        # Check the previous version
        self.visit_url( "%s/library_admin/library_dataset_dataset_association?info=True&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, str( library_one.id ), str( subfolder_one.id ), str( ldda_six.id ) ) )
        self.check_page_for_string( 'This is an expired version of this library dataset' )
        self.home()
    def test_180_uploading_new_dataset_versions( self ):
        """Testing uploading new versions of a dataset using a directory of files"""
        message = 'Testing uploading new versions of a dataset using a directory of files'
        ldda_six_version_two.refresh()
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        self.upload_new_dataset_versions( str( library_one.id ),
                                          str( subfolder_one.id ),
                                          str( subfolder_one.name ),
                                          str( ldda_six_version_two.library_dataset.id ),
                                          ldda_six_version_two.name,
                                          file_format='auto',
                                          dbkey='hg18',
                                          message=message.replace( ' ', '+' ),
                                          check_template_str1='Fu',
                                          check_template_str2='Bar' )
        """
        self.upload_new_dataset_versions( str( library_one.id ),
                                          str( subfolder_one.id ),
                                          str( subfolder_one.name ),
                                          str( ldda_six_version_two.library_dataset.id ),
                                          ldda_six_version_two.name,
                                          file_format='auto',
                                          dbkey='hg18',
                                          message=message.replace( ' ', '+' ) )
        global ldda_six_version_five
        ldda_six_version_five = galaxy.model.LibraryDatasetDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.create_time ) ).first()
        assert ldda_six_version_five is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda_six_version_five from the database'
        self.home()
        self.visit_url( "%s/library_admin/library_dataset_dataset_association?info=True&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, str( library_one.id ), str( subfolder_one.id ), str( ldda_six_version_five.id ) ) )
        self.check_page_for_string( 'This is the latest version of this library dataset' )
        # Make sure the correct template was inherited
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        self.check_page_for_string( 'Fu' )
        self.check_page_for_string( 'This is the Fu component' )
        self.check_page_for_string( 'Bar' )
        self.check_page_for_string( 'This is the Bar component' )
        """
        check_str = 'Expired versions of %s' % ldda_six_version_five.name
        self.check_page_for_string( check_str )
        self.check_page_for_string( ldda_six.name )
        self.home()
        # Make sure th permissions are the same
        ldda_six.refresh()
        if len( ldda_six.actions ) != len( ldda_six_version_five.actions ):
            raise AssertionError( 'ldda "%s" actions "%s" != ldda "%s" actions "%s"' \
                % ( ldda_six.name, str( ldda_six.actions ),
                    ldda_six_version_five.name, str( ldda_six_version_five.actions ) ) )
        if len( ldda_six.library_dataset.actions ) != len( ldda_six_version_five.library_dataset.actions ):
            raise AssertionError( 'ldda.library_dataset "%s" actions "%s" != ldda.library_dataset "%s" actions "%s"' \
                % ( ldda_six.name, str( ldda_six.library_dataset.actions ), ldda_six_version_five.name, str( ldda_six_version_five.library_dataset.actions ) ) )
        if len( ldda_six.dataset.actions ) != len( ldda_six_version_five.dataset.actions ):
            raise AssertionError( 'ldda.dataset "%s" actions "%s" != ldda.dataset "%s" actions "%s"' \
                % ( ldda_six.name, str( ldda_six.dataset.actions ), ldda_six_version_five.name, str( ldda_six_version_five.dataset.actions ) ) )
        # Check the previous version
        self.visit_url( "%s/library_admin/library_dataset_dataset_association?info=True&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, str( library_one.id ), str( subfolder_one.id ), str( ldda_six_version_two.id ) ) )
        self.check_page_for_string( 'This is an expired version of this library dataset' )
        self.home()
    def test_185_upload_directory_of_files_from_admin_view( self ):
        """Testing uploading a directory of files to a root folder from the Admin view"""
        message = 'This is a test for uploading a directory of files'
        roles_tuple = [ ( str( role_one.id ), role_one.name ) ]
        check_str = "Added 3 datasets to the library '%s' ( each is selected )." % library_one.root_folder.name
        ## TODO: temporarily eliminating templates until we have the new forms features done
        """
        self.add_dir_of_files_from_admin_view( str( library_one.id ),
                                            str( library_one.root_folder.id ),
                                            roles_tuple=roles_tuple,
                                            message=message.replace( '+', ' ' ),
                                            check_str=check_str,
                                            check_template_str1='wind',
                                            check_template_str2='bag',
                                            check_template_str3='Fubar' )
        """
        self.add_dir_of_files_from_admin_view( str( library_one.id ),
                                               str( library_one.root_folder.id ),
                                               roles_tuple=roles_tuple,
                                               message=message.replace( '+', ' ' ) )
        self.home()
        self.visit_page( 'library_admin/browse_library?id=%s' % ( str( library_one.id ) ) )
        self.check_page_for_string( admin_user.email )
        self.check_page_for_string( message )
        self.home()
    def test_190_change_permissions_on_datasets_uploaded_from_library_dir( self ):
        """Testing changing the permissions on datasets uploaded from a directory"""
        # It would be nice if twill functioned such that the above test resulted in a
        # form with the uploaded datasets selected, but it does not ( they're not checked ),
        # so we'll have to simulate this behavior ( not ideal ) for the 'edit' action.  We
        # first need to get the ldda.id for the 3 new datasets
        latest_3_lddas = galaxy.model.LibraryDatasetDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryDatasetDatasetAssociation.table.c.update_time ) ).limit( 3 )
        ldda_ids = ''
        for ldda in latest_3_lddas:
            ldda_ids += '%s,' % str( ldda.id )
        ldda_ids = ldda_ids.rstrip( ',' )
        permissions = [ 'DATASET_ACCESS', 'DATASET_MANAGE_PERMISSIONS' ]
        def build_url( permissions, role ):
            # We'll bypass the library_admin/datasets method and directly call the library_admin/dataset method, setting
            # access, manage permissions, and edit metadata permissions to role_one
            url = '/library_admin/library_dataset_dataset_association?permissions=True&id=%s&library_id=%s&folder_id=%s&update_roles_button=Save' % ( ldda_ids, str( library_one.id ), str( folder_one.id ) )
            for p in permissions:
                url += '&%s_in=%s' % ( p, str( role.id ) )
            return url
        url = build_url( permissions, role_one )
        self.home()
        self.visit_url( url )
        self.check_page_for_string( 'Permissions have been updated on 3 datasets' )
        def check_edit_page1( lddas ):
            # Make sure the permissions have been correctly updated for the 3 datasets.  Permissions should 
            # be all of the above on any of the 3 datasets that are imported into a history
            for ldda in lddas:
                # Import each library dataset into our history
                self.home()
                self.visit_url( '%s/library/datasets?do_action=add&ldda_ids=%s&library_id=%s' % ( self.url, str( ldda.id ), str( library_one.id ) ) )
                # Determine the new HistoryDatasetAssociation id created when the library dataset was imported into our history
                last_hda_created = galaxy.model.HistoryDatasetAssociation.query() \
                    .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
                self.home()
                self.visit_url( '%s/root/edit?id=%s' % ( self.url, str( last_hda_created.id ) ) )
                self.check_page_for_string( 'Edit Attributes' )
                self.check_page_for_string( last_hda_created.name )
                check_str = 'Manage dataset permissions and role associations of %s' % last_hda_created.name
                self.check_page_for_string( check_str )
                self.check_page_for_string( 'Role members can manage the roles associated with this dataset' )
                self.check_page_for_string( 'Role members can import this dataset into their history for analysis' )
        # admin_user is associated with role_one, so should have all permissions on imported datasets
        check_edit_page1( latest_3_lddas )
        self.logout()
        # regular_user1 is associated with role_one, so should have all permissions on imported datasets
        self.login( email='test1@bx.psu.edu' )
        check_edit_page1( latest_3_lddas )
        self.logout()
        # Since regular_user2 is not associated with role_one, she should not have
        # access to any of the 3 datasets, so she will not see folder_one on the libraries page
        self.login( email='test2@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse_library?id=%s' % ( self.url, str( library_one.id ) ) )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can access folder %s even though all contained datasets should be restricted from access by her' \
                                  % ( regular_user2.email, folder_one.name ) )
        except:
            pass # This is the behavior we want
        self.logout()
        # regular_user3 is associated with role_one, so should have all permissions on imported datasets
        self.login( email='test3@bx.psu.edu' )
        check_edit_page1( latest_3_lddas )
        self.logout()
        self.login( email='test@bx.psu.edu' )
        # Change the permissions and test again
        permissions = [ 'DATASET_ACCESS' ]
        url = build_url( permissions, role_one )
        self.home()
        self.visit_url( url )
        self.check_page_for_string( 'Permissions have been updated on 3 datasets' )
        def check_edit_page2( lddas ):
            # Make sure the permissions have been correctly updated for the 3 datasets.  Permissions should 
            # be all of the above on any of the 3 datasets that are imported into a history
            for ldda in lddas:
                self.home()
                self.visit_url( '%s/library/datasets?library_id=%s&do_action=add&ldda_ids=%s' % ( self.url, str( library_one.id ), str( ldda.id ) ) )
                # Determine the new HistoryDatasetAssociation id created when the library dataset was imported into our history
                last_hda_created = galaxy.model.HistoryDatasetAssociation.query() \
                    .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
                self.home()
                self.visit_url( '%s/root/edit?id=%s' % ( self.url, str( last_hda_created.id ) ) )
                self.check_page_for_string( 'Edit Attributes' )
                self.check_page_for_string( last_hda_created.name )
                self.check_page_for_string( 'View Permissions' )
                self.check_page_for_string( last_hda_created.name )
                try:
                    # This should no longer be possible
                    check_str = 'Manage dataset permissions and role associations of %s' % last_hda_created.name
                    self.check_page_for_string( check_str )
                    raise AssertionError( '%s incorrectly has DATASET_MANAGE_PERMISSIONS on datasets imported from a library' % admin_user.email )
                except:
                    pass
                try:
                    # This should no longer be possible
                    self.check_page_for_string( 'Role members can manage the roles associated with this dataset' )
                    raise AssertionError( '%s incorrectly has DATASET_MANAGE_PERMISSIONS on datasets imported from a library' % admin_user.email )
                except:
                    pass
                try:
                    # This should no longer be possible
                    self.check_page_for_string( 'Role members can import this dataset into their history for analysis' )
                    raise AssertionError( '%s incorrectly has DATASET_MANAGE_PERMISSIONS on datasets imported from a library' % admin_user.email )
                except:
                    pass
        check_edit_page2( latest_3_lddas )
        self.home()
    def test_195_upload_directory_of_files_from_libraries_view( self ):
        """Testing uploading a directory of files to a root folder from the Data Libraries view"""
        # admin_user will not have the option sto upload a directory of files from the
        # Libraries view since a sub-directory named the same as their email is not contained
        # in the configured user_library_import_dir.  However, since members of role_one have
        # the LIBRARY_ADD permission, we can test this feature as regular_user1 or regular_user3
        self.logout()
        self.login( email=regular_user1.email )
        message = 'Uploaded all files in test-data/users/test1...'
        # Since regular_user1 does not have any sub-directories contained within her configured
        # user_library_import_dir, the only option in her server_dir select list will be the
        # directory named the same as her email
        check_str_after_submit = "Added 1 datasets to the library '%s' ( each is selected )." % library_one.root_folder.name
        self.add_dir_of_files_from_libraries_view( str( library_one.id ),
                                                   str( library_one.root_folder.id ),
                                                   regular_user1.email,
                                                   check_str_after_submit=check_str_after_submit,
                                                   message=message.replace( '+', ' ' ) )
        self.home()
        self.visit_page( 'library/browse_library?id=%s' % ( str( library_one.id ) ) )
        self.check_page_for_string( regular_user1.email )
        self.check_page_for_string( message )
        self.logout()
        self.login( regular_user3.email )
        message = 'Uploaded all files in test-data/users/test3.../run1'
        # Since regular_user2 has a subdirectory contained within her configured user_library_import_dir,
        # she will have a "None" option in her server_dir select list
        check_str1 = '<option>None</option>'
        self.add_dir_of_files_from_libraries_view( str( library_one.id ),
                                                   str( library_one.root_folder.id ),
                                                   'run1',
                                                   check_str_after_submit=check_str_after_submit,
                                                   check_str1=check_str1,
                                                   message=message.replace( '+', ' ' ) )
        self.home()
        self.visit_page( 'library/browse_library?id=%s' % ( str( library_one.id ) ) )
        self.check_page_for_string( regular_user3.email )
        self.check_page_for_string( message )
        self.home()
        self.logout()
        self.login( email=admin_user.email )
    def test_200_mark_group_deleted( self ):
        """Testing marking a group as deleted"""
        self.home()
        self.visit_url( '%s/admin/groups' % self.url )
        self.check_page_for_string( group_two.name )
        self.mark_group_deleted( str( group_two.id ), group_two.name )
        group_two.refresh()
        if not group_two.deleted:
            raise AssertionError( '%s was not correctly marked as deleted.' % group_two.name )
        # Deleting a group should not delete any associations
        if not group_two.members:
            raise AssertionError( '%s incorrectly lost all members when it was marked as deleted.' % group_two.name )
        if not group_two.roles:
            raise AssertionError( '%s incorrectly lost all role associations when it was marked as deleted.' % group_two.name )
    def test_205_undelete_group( self ):
        """Testing undeleting a deleted group"""
        self.undelete_group( str( group_two.id ), group_two.name )
        group_two.refresh()
        if group_two.deleted:
            raise AssertionError( '%s was not correctly marked as not deleted.' % group_two.name )
    def test_210_mark_role_deleted( self ):
        """Testing marking a role as deleted"""
        self.home()
        self.visit_url( '%s/admin/roles' % self.url )
        self.check_page_for_string( role_two.name )
        self.mark_role_deleted( str( role_two.id ), role_two.name )
        role_two.refresh()
        if not role_two.deleted:
            raise AssertionError( '%s was not correctly marked as deleted.' % role_two.name )
        # Deleting a role should not delete any associations
        if not role_two.users:
            raise AssertionError( '%s incorrectly lost all user associations when it was marked as deleted.' % role_two.name )
        if not role_two.groups:
            raise AssertionError( '%s incorrectly lost all group associations when it was marked as deleted.' % role_two.name )
    def test_215_undelete_role( self ):
        """Testing undeleting a deleted role"""
        self.undelete_role( str( role_two.id ), role_two.name )
    def test_220_mark_dataset_deleted( self ):
        """Testing marking a library dataset as deleted"""
        self.home()
        self.delete_library_item( str( library_one.id ), str( ldda_two.library_dataset.id ), ldda_two.name, library_item_type='library_dataset' )
        self.home()
        self.visit_page( 'library_admin/browse_library?id=%s' % ( str( library_one.id ) ) )
        try:
            # 2.bed was only contained in the library in 1 place, so it should no longer display
            self.check_page_for_string( ldda_two.name )
            raise AssertionError( "Dataset '%s' is incorrectly displayed in the library after it has been deleted." % ldda_two.name )
        except:
            pass
        self.home()
    def test_225_display_deleted_dataset( self ):
        """Testing displaying deleted dataset"""
        self.home()
        self.visit_url( "%s/library_admin/browse_library?id=%s&show_deleted=True" % ( self.url, str( library_one.id ) ) )
        self.check_page_for_string( ldda_two.name )
        self.home()
    def test_230_hide_deleted_dataset( self ):
        """Testing hiding deleted dataset"""
        self.home()
        self.visit_url( "%s/library_admin/browse_library?id=%s&show_deleted=False" % ( self.url, str( library_one.id ) ) )
        try:
            self.check_page_for_string( ldda_two.name )
            raise AssertionError( "Dataset '%s' is incorrectly displayed in the library after it has been deleted." % ldda_two.name )
        except:
            pass
        self.home()
    def test_235_mark_folder_deleted( self ):
        """Testing marking a library folder as deleted"""
        self.home()
        self.delete_library_item( str( library_one.id ), str( folder_two.id ), folder_two.name, library_item_type='folder' )
        self.home()
        self.visit_page( 'library_admin/browse_library?id=%s' % ( str( library_one.id ) ) )
        try:
            self.check_page_for_string( folder_two.name )
            raise AssertionError( "Folder '%s' is incorrectly displayed in the library after it has been deleted." % folder_two.name )
        except:
            pass
        self.home()
    def test_240_mark_folder_undeleted( self ):
        """Testing marking a library folder as undeleted"""
        self.home()
        self.undelete_library_item( str( library_one.id ), str( folder_two.id ), folder_two.name, library_item_type='folder' )
        self.home()
        self.visit_page( 'library_admin/browse_library?id=%s' % ( str( library_one.id ) ) )
        self.check_page_for_string( folder_two.name )
        try:
            # 2.bed was deleted before the folder was deleted, so state should have been saved.  In order
            # fro 2.bed to be displayed, it would itself have to be marked undeleted.
            self.check_page_for_string( ldda_two.name )
            raise AssertionError( "Dataset '%s' is incorrectly displayed in the library after parent folder was undeleted." % ldda_two.name )
        except:
            pass
        self.home()
    def test_245_mark_library_deleted( self ):
        """Testing marking a library as deleted"""
        self.home()
        # First mark folder_two as deleted to further test state saving when we undelete the library
        self.delete_library_item( str( library_one.id ), str( folder_two.id ), folder_two.name, library_item_type='folder' )
        self.delete_library_item( str( library_one.id ), str( library_one.id ), library_one.name, library_item_type='library' )
        self.home()
        self.visit_page( 'library_admin/deleted_libraries' )
        self.check_page_for_string( library_one.name )
        self.home()
    def test_240_mark_library_undeleted( self ):
        """Testing marking a library as undeleted"""
        self.home()
        self.undelete_library_item( str( library_one.id ), str( library_one.id ), library_one.name, library_item_type='library' )
        self.home()
        self.visit_page( 'library_admin/browse_library?id=%s' % ( str( library_one.id ) ) )
        self.check_page_for_string( library_one.name )
        try:
            # folder_two was marked deleted before the library was deleted, so it should not be displayed
            self.check_page_for_string( folder_two.name )
            raise AssertionError( "Deleted folder '%s' is incorrectly displayed in the library after the library was undeleted." % folder_two.name )
        except:
            pass
        self.home()
    def test_250_purge_user( self ):
        """Testing purging a user account"""
        self.mark_user_deleted( user_id=regular_user3.id, email=regular_user3.email )
        regular_user3.refresh()
        self.purge_user( str( regular_user3.id ), regular_user3.email )
        regular_user3.refresh()
        if not regular_user3.purged:
            raise AssertionError( 'User %s was not marked as purged.' % regular_user3.email )
        # Make sure DefaultUserPermissions deleted EXCEPT FOR THE PRIVATE ROLE
        if len( regular_user3.default_permissions ) != 1:
            raise AssertionError( 'DefaultUserPermissions for user %s were not deleted.' % regular_user3.email )
        for dup in regular_user3.default_permissions:
            role = galaxy.model.Role.get( dup.role_id )
            if role.type != 'private':
                raise AssertionError( 'DefaultUserPermissions for user %s are not related with the private role.' % regular_user3.email )
        # Make sure History deleted
        for history in regular_user3.histories:
            history.refresh()
            if not history.deleted:
                raise AssertionError( 'User %s has active history id %d after their account was marked as purged.' % ( regular_user3.email, hda.id ) )
            # NOTE: Not all hdas / datasets will be deleted at the time a history is deleted - the cleanup_datasets.py script
            # is responsible for this.
        # Make sure UserGroupAssociations deleted
        if regular_user3.groups:
            raise AssertionError( 'User %s has active group id %d after their account was marked as purged.' % ( regular_user3.email, uga.id ) )
        # Make sure UserRoleAssociations deleted EXCEPT FOR THE PRIVATE ROLE
        if len( regular_user3.roles ) != 1:
            raise AssertionError( 'UserRoleAssociations for user %s were not deleted.' % regular_user3.email )
        for ura in regular_user3.roles:
            role = galaxy.model.Role.get( ura.role_id )
            if role.type != 'private':
                raise AssertionError( 'UserRoleAssociations for user %s are not related with the private role.' % regular_user3.email )
    def test_255_manually_unpurge_user( self ):
        """Testing manually un-purging a user account"""
        # Reset the user for later test runs.  The user's private Role and DefaultUserPermissions for that role
        # should have been preserved, so all we need to do is reset purged and deleted.
        # TODO: If we decide to implement the GUI feature for un-purging a user, replace this with a method call
        regular_user3.purged = False
        regular_user3.deleted = False
        regular_user3.flush()
    def test_260_purge_group( self ):
        """Testing purging a group"""
        group_id = str( group_two.id )
        self.mark_group_deleted( group_id, group_two.name )
        self.purge_group( group_id, group_two.name )
        # Make sure there are no UserGroupAssociations
        uga = galaxy.model.UserGroupAssociation.filter( galaxy.model.UserGroupAssociation.table.c.group_id == group_id ).all()
        if uga:
            raise AssertionError( "Purging the group did not delete the UserGroupAssociations for group_id '%s'" % group_id )
        # Make sure there are no GroupRoleAssociations
        gra = galaxy.model.GroupRoleAssociation.filter( galaxy.model.GroupRoleAssociation.table.c.group_id == group_id ).all()
        if gra:
            raise AssertionError( "Purging the group did not delete the GroupRoleAssociations for group_id '%s'" % group_id )
        # Undelete the group for later test runs
        self.undelete_group( group_id, group_two.name )
    def test_265_purge_role( self ):
        """Testing purging a role"""
        role_id = str( role_two.id )
        self.mark_role_deleted( role_id, role_two.name )
        self.purge_role( role_id, role_two.name )
        # Make sure there are no UserRoleAssociations
        uras = galaxy.model.UserRoleAssociation.filter( galaxy.model.UserRoleAssociation.table.c.role_id == role_id ).all()
        if uras:
            raise AssertionError( "Purging the role did not delete the UserRoleAssociations for role_id '%s'" % role_id )
        # Make sure there are no DefaultUserPermissions associated with the Role
        dups = galaxy.model.DefaultUserPermissions.filter( galaxy.model.DefaultUserPermissions.table.c.role_id == role_id ).all()
        if dups:
            raise AssertionError( "Purging the role did not delete the DefaultUserPermissions for role_id '%s'" % role_id )
        # Make sure there are no DefaultHistoryPermissions associated with the Role
        dhps = galaxy.model.DefaultHistoryPermissions.filter( galaxy.model.DefaultHistoryPermissions.table.c.role_id == role_id ).all()
        if dhps:
            raise AssertionError( "Purging the role did not delete the DefaultHistoryPermissions for role_id '%s'" % role_id )
        # Make sure there are no GroupRoleAssociations
        gra = galaxy.model.GroupRoleAssociation.filter( galaxy.model.GroupRoleAssociation.table.c.role_id == role_id ).all()
        if gra:
            raise AssertionError( "Purging the role did not delete the GroupRoleAssociations for role_id '%s'" % role_id )
        # Make sure there are no DatasetPermissionss
        dp = galaxy.model.DatasetPermissions.filter( galaxy.model.DatasetPermissions.table.c.role_id == role_id ).all()
        if dp:
            raise AssertionError( "Purging the role did not delete the DatasetPermissionss for role_id '%s'" % role_id )
    def test_270_manually_unpurge_role( self ):
        """Testing manually un-purging a role"""
        # Manually unpurge, then undelete the role for later test runs
        # TODO: If we decide to implement the GUI feature for un-purging a role, replace this with a method call
        role_two.purged = False
        role_two.flush()
        self.undelete_role( str( role_two.id ), role_two.name )
    def test_275_purge_library( self ):
        """Testing purging a library"""
        self.home()
        self.delete_library_item( str( library_one.id ), str( library_one.id ), library_one.name, library_item_type='library' )
        self.purge_library( str( library_one.id ), library_one.name )
        # Make sure the library was purged
        library_one.refresh()
        if not ( library_one.deleted and library_one.purged ):
            raise AssertionError( 'The library id %s named "%s" has not been marked as deleted and purged.' % ( str( library_one.id ), library_one.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                folder.refresh()
                # Make sure all of the library_folders are purged
                if not folder.purged:
                    raise AssertionError( 'The library_folder id %s named "%s" has not been marked purged.' % ( str( folder.id ), folder.name ) )
                check_folder( folder )
            # Make sure all of the LibraryDatasets and associated objects are deleted
            library_folder.refresh()
            for library_dataset in library_folder.datasets:
                library_dataset.refresh
                ldda = library_dataset.library_dataset_dataset_association
                if ldda:
                    ldda.refresh()
                    if not ldda.deleted:
                        raise AssertionError( 'The library_dataset_dataset_association id %s named "%s" has not been marked as deleted.' % \
                                              ( str( ldda.id ), ldda.name ) )
                    # Make sure all of the datasets have been deleted
                    dataset = ldda.dataset
                    dataset.refresh()
                    if not dataset.deleted:
                        raise AssertionError( 'The dataset with id "%s" has not been marked as deleted when it should have been.' % \
                                              str( ldda.dataset.id ) )
                if not library_dataset.deleted:
                    raise AssertionError( 'The library_dataset id %s named "%s" has not been marked as deleted.' % \
                                          ( str( library_dataset.id ), library_dataset.name ) )
        check_folder( library_one.root_folder )
    def test_280_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        ##################
        # Eliminate all non-private roles
        ##################
        for role in [ role_one, role_two, role_three ]:
            self.mark_role_deleted( str( role.id ), role.name )
            self.purge_role( str( role.id ), role.name )
            # Manually delete the role from the database
            role.refresh()
            role.delete()
            role.flush()
        ##################
        # Eliminate all groups
        ##################
        for group in [ group_zero, group_one, group_two ]:
            self.mark_group_deleted( str( group.id ), group.name )
            self.purge_group( str( group.id ), group.name )
            # Manually delete the group from the database
            group.refresh()
            group.delete()
            group.flush()
        ##################
        # Make sure all users are associated only with their private roles
        ##################
        for user in [ admin_user, regular_user1, regular_user2, regular_user3 ]:
            user.refresh()
            if len( user.roles) != 1:
                raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 1 )' % ( len( user.roles ), user.email ) )
        #####################
        # Reset DefaultHistoryPermissions for regular_user1
        #####################
        self.logout()
        self.login( email='test1@bx.psu.edu' )
        # Change DefaultHistoryPermissions for regular_user1 back to the default
        permissions_in = [ 'DATASET_MANAGE_PERMISSIONS' ]
        permissions_out = [ 'DATASET_ACCESS' ]
        role_id = str( regular_user1_private_role.id )
        self.user_set_default_permissions( permissions_in=permissions_in, permissions_out=permissions_out, role_id=role_id )
        self.logout()
        self.login( email='test@bx.psu.edu' )
