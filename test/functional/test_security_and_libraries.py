import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import *

not_logged_in_security_msg = 'You must be logged in as an administrator to access this feature.'
logged_in_security_msg = 'You must be an administrator to access this feature.'

class TestSecurityAndLibraries( TwillTestCase ):
    def test_00_admin_features_when_not_logged_in( self ):
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
        self.visit_url( "%s/admin/new_role" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/role" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/groups" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/create_group" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/group_members_edit?group_id=0" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/users" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/library_browser" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/libraries" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/library" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/folder?id=1&new=True" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/dataset" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
    def test_005_login_as_admin_user( self ):
        """Testing logging in as an admin user test@bx.psu.edu - tests initial settings for DefaultUserPermissions and DefaultHistoryPermissions"""
        self.login( email='test@bx.psu.edu' ) # test@bx.psu.edu is configured as our admin user
        self.visit_page( "admin" )
        self.check_page_for_string( 'Administration' )
        global admin_user
        admin_user = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
        # Make sure DefaultUserPermissions are correct
        if len( admin_user.default_permissions ) > 1:
            raise AssertionError( '%d DefaultUserPermissions were created for %s when their account was created ( should have been 1 )' \
                                  % ( len( admin_user.default_permissions ), admin_user.email ) )
        dup =  galaxy.model.DefaultUserPermissions.filter( galaxy.model.DefaultUserPermissions.table.c.user_id==admin_user.id ).first()
        if not dup.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultUserPermission.action for user "%s" is "%s", but it should be "%s"' \
                                  % ( admin_user.email, dup.action, galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        # Make sure DefaultHistoryPermissions are correct
        latest_history = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
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
        self.logout()
    def test_010_login_as_regular_user1( self ):
        """Testing logging in as regular user test1@bx.psu.edu - tests private role creation, changing DefaultHistoryPermissions for new histories"""
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
        # Make sure ActionDatasetRoleAssociation is correct - default is 'manage permissions'
        if len( latest_dataset.actions ) > 1:
            raise AssertionError( '%d ActionDatasetRoleAssociations were created for dataset id %d when it was created ( should have been 1 )' \
                                  % ( len( latest_dataset.actions ), latest_dataset.id ) )
        adra = galaxy.model.ActionDatasetRoleAssociation.filter( galaxy.model.ActionDatasetRoleAssociation.table.c.dataset_id==latest_dataset.id ).first()
        if not adra.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The ActionDatasetRoleAssociation.action for dataset id %d is "%s", but it should be "manage permissions"' \
                                  % ( latest_dataset.id, adra.action ) )
        # Change DefaultHistoryPermissions for regular_user1
        permissions_in = []
        actions_in = []
        for key, value in galaxy.model.Dataset.permitted_actions.items():
            permissions_in.append( key )
            actions_in.append( value.action )
        # Sort actions for later comparison
        actions_in.sort()
        role_id = str( private_role.id )
        self.user_set_default_permissions( permissions_in=permissions_in, role_id=role_id )
        # Make sure the default permissions are changed for new histories
        self.new_history()
        latest_history = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        if len( latest_history.default_permissions ) != len( galaxy.model.Dataset.permitted_actions.items() ):
            raise AssertionError( '%d DefaultHistoryPermissions were created for history id %d, should have been %d' % \
                                  ( len( latest_history.default_permissions ), latest_history.id, len( galaxy.model.Dataset.permitted_actions ) ) )
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
        # Make sure ActionDatasetRoleAssociations are correct
        if len( latest_dataset.actions ) != len( latest_history.default_permissions ):
            raise AssertionError( '%d ActionDatasetRoleAssociations were created for dataset id %d when it was created ( should have been %d )' % \
                                  ( len( latest_dataset.actions ), latest_dataset.id, len( latest_history.default_permissions ) ) )
        adras = []
        for adra in latest_dataset.actions:
            adras.append( adra.action )
        # Sort actions for later comparison
        adras.sort()
        # Compare ActionDatasetRoleAssociations with permissions_in - should be the same
        if adras != actions_in:
            raise AssertionError( 'ActionDatasetRoleAssociations "%s" for dataset id %d differ from changed default permissions "%s"' \
                                      % ( str( adras ), latest_dataset.id, str( actions_in ) ) )
        # Compare DefaultHistoryPermissions and ActionDatasetRoleAssociations - should be the same
        if adras != dhps:
                raise AssertionError( 'ActionDatasetRoleAssociations "%s" for dataset id %d differ from DefaultHistoryPermissions "%s" for history id %d' \
                                      % ( str( adras ), latest_dataset.id, str( dhps ), latest_history.id ) )
        self.logout()
    def test_015_login_as_regular_user2( self ):
        """Testing logging in as regular user test2@bx.psu.edu - tests changing DefaultHistoryPermissions for the current history"""
        self.login( email='test2@bx.psu.edu' ) # This will not be an admin user
        global regular_user2
        regular_user2 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ).first()
        assert regular_user2 is not None, 'Problem retrieving user with email "test2@bx.psu.edu" from the database'
        latest_history = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        self.upload_file( '1.bed' )
        latest_dataset = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        permissions_in = [ 'DATASET_EDIT_METADATA', 'DATASET_MANAGE_PERMISSIONS' ]
        # Make sure these are in sorted order for later comparison
        actions_in = [ 'edit metadata', 'manage permissions' ]
        permissions_out = [ 'DATASET_ACCESS' ]
        actions_out = [ 'access' ]
        private_role = None
        for role in regular_user2.all_roles():
            if role.name == regular_user2.email and role.description == 'Private Role for %s' % regular_user2.email:
                private_role = role
                break
        if not private_role:
            raise AssertionError( "Private role not found for user '%s'" % regular_user2.email )
        role_id = str( private_role.id )
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
        # Make sure ActionDatasetRoleAssociations are correct
        if len( latest_dataset.actions ) != len( latest_history.default_permissions ):
            raise AssertionError( '%d ActionDatasetRoleAssociations were created for dataset id %d when it was created ( should have been %d )' \
                                  % ( len( latest_dataset.actions ), latest_dataset.id, len( latest_history.default_permissions ) ) )
        adras = []
        for adra in latest_dataset.actions:
            adras.append( adra.action )
        # Sort actions for comparison
        adras.sort()
        # Compare ActionDatasetRoleAssociations and DefaultHistoryPermissions - should be the same
        if adras != dhps:
                raise AssertionError( 'ActionDatasetRoleAssociations "%s" for dataset id %d differ from DefaultHistoryPermissions "%s"' \
                                      % ( str( adras ), latest_dataset.id, str( dhps ) ) )
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
        latest_history = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
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
        for adra in latest_dataset.actions:
            # Should only have 1 ActionDatasetRoleAssociation
            if adra.action != galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
                raise AssertionError( 'The ActionDatasetRoleAssociation for dataset id %d is %s ( should have been %s )' \
                                      % ( latest_dataset.id,
                                          latest_dataset.actions.action, 
                                          galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        self.logout()
        # Reset the password to the default for later tests
        self.login( email='test@bx.psu.edu' )
        self.reset_password_as_admin( user_id=regular_user3.id, password='testuser' )
    def test_035_mark_user_deleted( self ):
        """Testing marking a user account as deleted"""
        self.mark_user_deleted( user_id=regular_user3.id )
        # Deleting a user should not delete any associations
        regular_user3.refresh()
        if not regular_user3.active_histories:
            raise AssertionError( 'HistoryDatasetAssociations for regular_user3 were incorrectly deleted when the user was marked deleted' )
    def test_040_undelete_user( self ):
        """Testing undeleting a user account"""
        self.undelete_user( user_id=regular_user3.id )
    def test_045_create_role( self ):
        """Testing creating new role with 3 members"""
        name = 'Role One'
        description = "This is Role One's description"
        user_ids=[ str( admin_user.id ), str( regular_user1.id ), str( regular_user3.id ) ]
        previously_created = self.create_role( name=name, description=description, user_ids=user_ids, private_role=admin_user.email )
        # Get the role object for later tests
        global role_one
        role_one = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
        assert role_one is not None, 'Problem retrieving role named "Role One" from the database'
        if previously_created:
            # Since the role was created in a previous test run, we need to associate the required users with it
            role_ids = [ str( role_one.id ) ]
            for user_id in user_ids:
                self.user_roles_edit( user_id, role_ids=role_ids )
            role_one.refresh()
        # Make sure UserRoleAssociations are correct
        if len( role_one.users ) != len( user_ids ):
            raise AssertionError( '%d UserRoleAssociations were created for role id %d when it was created ( should have been %d )' \
                                  % ( len( role_one.users ), role_one.id, len( user_ids ) ) )
        # Each user should now have 2 role associations, their private role and role_one
        for user in [ admin_user, regular_user1, regular_user3 ]:
            user.refresh()
            if not previously_created and len( user.roles ) != 2:
                raise AssertionError( '%d UserRoleAssociations are associated with user %s ( should be 2 )' \
                                      % ( len( user.roles ), user.email ) )
    def test_050_create_group( self ):
        """Testing creating new group with 3 members and 1 associated role"""
        name = "Group One's Name"
        user_ids=[ str( admin_user.id ), str( regular_user1.id ), str( regular_user3.id ) ]
        role_ids=[ str( role_one.id ) ]
        previously_created = self.create_group( name=name, user_ids=user_ids, role_ids=role_ids )
        # Get the group object for later tests
        global group_one
        group_one = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
        assert group_one is not None, 'Problem retrieving group named "Group One" from the database'
        if previously_created:
            # group_one was created during a previous test run, so create associations
            self.group_members_edit( str( group_one.id ), user_ids=user_ids )
            self.group_roles_edit( str( group_one.id ), role_ids=role_ids )
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
    def test_055_add_members_and_role_to_group( self ):
        """Testing editing user membership and role associations of an existing group"""
        name = 'Group Two'
        previously_created = self.create_group( name=name, user_ids=[], role_ids=[] )
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
        # Add users to group_two based on user_ids
        self.group_members_edit( group_two_id, user_ids=user_ids )
        self.home()
        self.visit_url( "%s/admin/group_members_edit?group_id=%s" % ( self.url, group_two_id ) )
        # Make sure UserGroupAssociations are correct
        check_str = '%s currently has %d members' % ( name, len( user_ids ) )
        self.check_page_for_string( check_str )
        role_ids = [ str( role_one.id ) ]
        # Associate roles with group_two based on roles_ids
        self.group_roles_edit( group_two_id, role_ids=role_ids )
        self.home()
        self.visit_url( "%s/admin/group_roles_edit?group_id=%s" % ( self.url, group_two_id ) )
        # Make sure GroupRoleAssociation are correct
        check_str = '%s is currently associated with %d roles' % ( name, len( role_ids ) )
        self.check_page_for_string( check_str ) 
        # Create another group -needed for the following test
        name = 'Group Three'
        previously_created = self.create_group( name=name, user_ids=[], role_ids=[] )
        # Get the group object for later tests
        global group_three
        group_three = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
        assert group_three is not None, 'Problem retrieving group named "Group Three" from the database'
        group_three_id = str( group_three.id )
    def test_060_create_role_with_user_and_group_associations( self ):
        """Testing creating a role with user and group associations"""
        # NOTE: To get this to work with twill, all select lists on the ~/admin/role page must contain at least
        # 1 option value or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug in twill, we create the role, associating it with at least 1 user and 1 group.  We
        # also must ensure that each of the form fields will contain at least 1 value prior to submitting the form,
        # so we had to create group_three in the previous test
        name = 'Role Two'
        description = 'This is Role Two'
        user_ids=[ str( admin_user.id ) ]
        group_ids=[ str( group_two.id ) ]
        private_role=admin_user.email
        # STEP 1: create the role
        previously_created = self.create_role( name=name, 
                                               description=description, 
                                               user_ids=user_ids, 
                                               group_ids=group_ids, 
                                               private_role=private_role )
        # Get the role object for later tests
        global role_two
        role_two = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
        assert role_two is not None, 'Problem retrieving role named "Role Two" from the database'
        if previously_created:
            # role_two was created during a previous test run, so create associations
            user_id = user_ids[0]
            role_ids = [ str( role_two.id) ]
            self.user_roles_edit( user_id, role_ids=role_ids )
            group_id = group_ids[0]
            self.group_roles_edit( group_id, role_ids=role_ids )
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
        # STEP 2: associate the role with a group not yet associated
        # TODO: Twill throws an exception on this...
        #group_names = [ group_one.name ]
        #self.associate_groups_with_role( str( role_two.id ), group_names=group_names )
        #self.visit_page( 'admin/roles' )
        #self.check_page_for_string( group_one.name )
    def test_065_change_user_role_associations( self ):
        """Testing changing roles associated with a user"""
        # Create a new role with no associations
        name = 'Role Three'
        description = 'This is Role Three'
        user_ids=[]
        group_ids=[]
        private_role=admin_user.email
        previously_created = self.create_role( name=name, 
                                               description=description, 
                                               user_ids=user_ids, 
                                               group_ids=group_ids, 
                                               private_role=private_role )
        # Get the role object for later tests
        global role_three
        role_three = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
        assert role_three is not None, 'Problem retrieving role named "Role Three" from the database'
        # Associate the role with a user
        role_ids = [ str( role_three.id ) ]
        self.user_roles_edit( str( admin_user.id ), role_ids=role_ids )
        admin_user.refresh()
        # admin_user should now be associated with 4 roles: private, role_one, role_two, role_three
        if len( admin_user.roles) != 4:
            raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 4 )' % ( len( admin_user.roles ), admin_user.email ) )
    def test_070_create_library( self ):
        """Testing creating a new library, then renaming it and renaming the root folder"""
        name = "Library One's Name"
        description = "This is Library One's description"
        self.create_library( name=name, description=description )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( name )
        self.check_page_for_string( description )
        # Get the library object for later tests
        global library_one
        library_one = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name==name,
                                                         galaxy.model.Library.table.c.description==description,
                                                         galaxy.model.Library.table.c.deleted==False ) ).first()
        assert library_one is not None, 'Problem retrieving library named "%s" from the database' % name
        # Rename the library
        rename = "Library One's been Renamed"
        redescription="This is Library One's Re-described"
        self.rename_library( str( library_one.id ), name=rename, description=redescription, root_folder='on' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( rename )
        self.check_page_for_string( redescription )
        # Reset the library back to the original name and description
        self.rename_library( str( library_one.id ), name=name, description=description, root_folder='on' )
        # Rename the root folder
        folder = library_one.root_folder
        rename = "Library One's Root Folder"
        redescription = "This is Library One's root folder"
        self.rename_folder( str( folder.id ), name=rename, description=redescription )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( rename )
        self.check_page_for_string( redescription )
        # Reset the root folder back to the original name and description
        self.rename_folder( str( folder.id ), name=name, description=description )
    def test_075_add_new_folder_to_root_folder( self ):
        """Testing adding a folder to a library root folder"""
        self.login( email = 'test@bx.psu.edu' )
        root_folder = library_one.root_folder
        name = "Root Folder's Folder One"
        description = "This is the root folder's Folder One"
        self.add_folder( str( root_folder.id ), name=name, description=description )
        global folder_one
        folder_one = galaxy.model.LibraryFolder.filter( and_( galaxy.model.LibraryFolder.table.c.parent_id==root_folder.id,
                                                              galaxy.model.LibraryFolder.table.c.name==name,
                                                              galaxy.model.LibraryFolder.table.c.description==description ) ).first()
        assert folder_one is not None, 'Problem retrieving library folder named "Folder One" from the database'
        self.home()
        self.visit_url( '%s/admin/libraries' % self.url )
        self.check_page_for_string( name )
        self.check_page_for_string( description )
    def test_080_add_dataset_with_private_role_restriction_to_folder( self ):
        """Testing adding a dataset with a private role restriction to a folder"""
        # Add a dataset restricted by regular_user1 private role
        self.add_dataset( '1.bed', str( folder_one.id ), extension='bed', dbkey='hg18', roles=[ str( regular_user1_private_role.id ) ] )
        global lfda_three
        lfda_three = galaxy.model.LibraryFolderDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryFolderDatasetAssociation.table.c.create_time ) ).first()
        assert lfda_three is not None, 'Problem retrieving LibraryFolderDatasetAssociation lfda_three from the database'
        self.home()
        self.visit_url( '%s/admin/libraries' % self.url )
        self.check_page_for_string( "1.bed" )
        self.check_page_for_string( "hg18" )
    def test_085_accessing_dataset_with_private_role_restriction( self ):
        """Testing accessing a dataset with a private role restriction"""
        # admin_user should not be able to see 1.bed from the analysis view's access librarys
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can see library folder %s when it contains only datasets restricted by role %s' \
                                  % ( admin_user.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        try:
            self.check_page_for_string( '1.bed' )
            raise AssertionError( '%s can see dataset 1.bed in library folder %s when it was restricted by role %s' \
                                  % ( admin_user.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        self.logout()
        # regular_user1 should be able to see 1.bed from the analysis view's access librarys
        # since it was associated with regular_user1's private role
        self.login( email='test1@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        self.check_page_for_string( folder_one.name )
        self.check_page_for_string( '1.bed' )
        self.logout()
        # regular_user2 should not be able to see 1.bed from the analysis view's access librarys
        self.login( email='test2@bx.psu.edu' )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can see library folder %s when it contains only datasets restricted by role %s' \
                                  % ( regular_user2.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        try:
            self.check_page_for_string( '1.bed' )
            raise AssertionError( '%s can see dataset 1.bed in library folder %s when it was restricted by role %s' \
                                  % ( regular_user2.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        self.logout()
        # regular_user3 should not be able to see 1.bed from the analysis view's access librarys
        self.login( email='test3@bx.psu.edu' )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can see library folder %s when it contains only datasets restricted by role %s' \
                                  % ( regular_user3.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        try:
            self.check_page_for_string( '1.bed' )
            raise AssertionError( '%s can see dataset 1.bed in library folder %s when it was restricted by role %s' \
                                  % ( regular_user3.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        self.logout()
    def test_090_add_dataset_with_role_restriction_to_folder( self ):
        """Testing adding a dataset with a role restriction to a folder"""
        self.login( email='test@bx.psu.edu' )
        # Add a dataset restricted by role_two, which is currently associated as follows:
        # groups: group_two
        # users: test@bx.psu.edu, test1@bx.psu.edu via group_two
        self.add_dataset( '2.bed', str( folder_one.id ), extension='bed', dbkey='hg17', roles=[ str( role_two.id ) ] )
        global lfda_two
        lfda_two = galaxy.model.LibraryFolderDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryFolderDatasetAssociation.table.c.create_time ) ).first()
        assert lfda_two is not None, 'Problem retrieving LibraryFolderDatasetAssociation lfda_two from the database'
        self.home()
        self.visit_url( '%s/admin/libraries' % self.url )
        self.check_page_for_string( "2.bed" )
        self.check_page_for_string( "hg17" )
    def test_095_accessing_datasets_with_role_restriction( self ):
        """Testing accessing a dataset with a role restriction"""
        # admin_user should be able to see 2.bed since she is associated with role_two
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        self.check_page_for_string( "2.bed" )
        self.check_page_for_string( "hg17" )
        self.logout()
        # regular_user1 should be able to see 2.bed since she is associated with group_two
        self.login( email = 'test1@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        self.check_page_for_string( folder_one.name )
        self.check_page_for_string( '2.bed' )
        self.check_page_for_string( "hg17" )
        # Check the permissions on the dataset - should be 'access'
        self.home()
        self.visit_url( '%s/root/edit?lid=%d' % ( self.url, lfda_two.id ) )
        self.check_page_for_string( '2.bed' )
        self.check_page_for_string( 'Role members can import this dataset into their history for analysis' )
        self.home()
        # Test importing the restricted dataset into a history, can't use the 
        # ~/admin/libraries form as twill barfs on it so we'll simulate the form submission
        # by going directly to the form action
        self.visit_url( '%s/library/import_datasets?import_ids=%d' % ( self.url, lfda_two.id ) )
        self.check_page_for_string( '1 dataset(s) have been imported in to your history' )
        self.logout()
        # regular_user2 should not be able to see 2.bed
        self.login( email = 'test2@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can see library folder %s when it contains only datasets restricted by role %s' \
                                  % ( regular_user2.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        try:
            self.check_page_for_string( '2.bed' )
            raise AssertionError( '%s can see dataset 2.bed in library folder %s when it was restricted by role %s' \
                                  % ( regular_user2.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        # regular_user3 should not be able to see 2.bed
        self.login( email = 'test3@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can see library folder %s when it contains only datasets restricted by role %s' \
                                  % ( regular_user3.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        try:
            self.check_page_for_string( '2.bed' )
            raise AssertionError( '%s can see dataset 2.bed in library folder %s when it was restricted by role %s' \
                                  % ( regular_user3.email, folder_one.name, regular_user1_private_role.description ) )
        except:
            pass # This is the behavior we want
        self.logout()
    def test_100_add_public_dataset_to_root_folder( self ):
        """Testing adding a public dataset to a library root folder"""
        self.login( email='test@bx.psu.edu' )
        folder = library_one.root_folder
        self.add_dataset( '3.bed', str( folder.id ), extension='bed', dbkey='hg16', roles=[] )
        global lfda_three
        lfda_three = galaxy.model.LibraryFolderDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryFolderDatasetAssociation.table.c.create_time ) ).first()
        assert lfda_three is not None, 'Problem retrieving LibraryFolderDatasetAssociation lfda_three from the database'
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "3.bed" )
        self.check_page_for_string( "hg16" )
        self.logout()
    def test_105_access_public_library_dataset( self ):
        """Testing accessing a public library dataset"""
        # regular_user1 should not be able to see 3.bed
        self.login( email = 'test1@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        self.check_page_for_string( library_one.name )
        self.check_page_for_string( '3.bed' )
        self.check_page_for_string( "hg16" )
        self.logout()
        # regular_user2 should not be able to see 3.bed
        self.login( email = 'test2@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        self.check_page_for_string( library_one.name )
        self.check_page_for_string( '3.bed' )
        self.check_page_for_string( "hg16" )
        self.logout()
        # regular_user3 should not be able to see 3.bed
        self.login( email = 'test3@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        self.check_page_for_string( library_one.name )
        self.check_page_for_string( '3.bed' )
        self.check_page_for_string( "hg16" )
        # Test selecting "View or edit this dataset's attributes and permissions"
        self.home()
        self.visit_url( '%s/root/edit?lid=%d' % ( self.url, lfda_three.id ) )
        self.check_page_for_string( '3.bed' )
        self.check_page_for_string( 'This dataset is accessible by everyone (it is public).' )
        # Test importing a library dataset into a history
        self.home()
        self.visit_url( '%s/library/import_datasets?import_ids=%d' % ( self.url, lfda_three.id ) )
        self.check_page_for_string( '1 dataset(s) have been imported in to your history' )
        self.logout()
    def test_110_copy_dataset_from_history_to_root_folder( self ):
        """Testing copying a dataset from the current history to a library root folder"""
        self.login( email='test@bx.psu.edu' )
        folder = library_one.root_folder
        self.add_dataset_to_folder_from_history( str( folder.id ) )
        # Test for ActionDatasetRoleAssociations, the default setting is "manage permissions"
        last_dataset_created = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        adras = galaxy.model.ActionDatasetRoleAssociation.filter( galaxy.model.ActionDatasetRoleAssociation.table.c.dataset_id==last_dataset_created.id ).all()
        if not adras:
            raise AssertionError( 'No ActionDatasetRoleAssociations created for dataset id: %d' % last_dataset_created.id )
        if len( adras ) > 1:
            raise AssertionError( 'More than 1 ActionDatasetRoleAssociations created for dataset id: %d' % last_dataset_created.id )
        for adra in adras:
            if not adra.action == 'manage permissions':
                raise AssertionError( 'ActionDatasetRoleAssociation.action "%s" is not the DefaultHistoryPermission setting of "manage permissions"' % \
                                      str( adra.action ) )
    def test_115_add_datasets_from_library_dir( self ):
        """Testing adding 3 datasets from a library directory to a folder"""
        roles_tuple = [ ( str( role_one.id ), role_one.description ) ] 
        self.add_datasets_from_library_dir( str( folder_one.id ), roles_tuple=roles_tuple )
        # It would be nice if twill functioned such that the above statement resulted in a
        # form with the uploaded datasets selected, but it does not (they're not checked ),
        # so we'll have to simulate this behavior ( not ideal ) for the 'edit' action.  We
        # first need to get the lfda.id for the 3 new datasets
        latest_3_lfdas = galaxy.model.LibraryFolderDatasetAssociation.query() \
            .order_by( desc( galaxy.model.LibraryFolderDatasetAssociation.table.c.update_time ) ).limit( 3 )
        lfda_ids = ''
        for lfda in latest_3_lfdas:
            lfda_ids += '%s,' % str( lfda.id )
        lfda_ids = lfda_ids.rstrip( ',' )
        permissions = [ 'DATASET_ACCESS', 'DATASET_EDIT_METADATA', 'DATASET_MANAGE_PERMISSIONS' ]
        def build_url( permissions, role ):
            # We'll bypass the admin/datasets method and directly call the admin/dataset method, setting
            # access, manage permissions, and edit metadata permissions to role_one
            url = '/admin/dataset?id=%s&update_roles=Save' % lfda_ids
            for p in permissions:
                url += '&%s_in=%s' % ( p, str( role.id ) )
            return url
        url = build_url( permissions, role_one )
        self.home()
        self.visit_url( url )
        self.check_page_for_string( 'Permissions and roles have been updated on 3 datasets' )
        def check_edit_page1( lfdas ):
            # Make sure the permissions have been correctly updated for the 3 datasets.  Permissions should 
            # be all of the above on any of the 3 datasets that are imported into a history
            for lfda in lfdas:
                self.home()
                self.visit_url( '%s/library/import_datasets?import_ids=%s' % ( self.url, str( lfda.id ) ) )
                self.home()
                self.visit_url( '%s/root/edit?lid=%s' % ( self.url, str( lfda.id ) ) )
                self.check_page_for_string( 'Edit Attributes' )
                self.check_page_for_string( 'input type="text" name="name" value="%s"' % lfda.name )
                self.check_page_for_string( 'Manage permissions and role associations for %s' % lfda.name )
                self.check_page_for_string( 'select name="DATASET_MANAGE_PERMISSIONS_in"' )
        # admin_user is associated with role_one, so should have all permissions on imported datasets
        check_edit_page1( latest_3_lfdas )
        self.logout()
        # regular_user1 is associated with role_one, so should have all permissions on imported datasets
        self.login( email='test1@bx.psu.edu' )
        check_edit_page1( latest_3_lfdas )
        self.logout()
        # Since regular_user2 is not associated with role_one, she should not have
        # access to any of the 3 datasets, so she will not see folder_one on the libraries page
        self.login( email='test2@bx.psu.edu' )
        self.home()
        self.visit_url( '%s/library/browse?bogus_param=needed' % self.url )
        try:
            self.check_page_for_string( folder_one.name )
            raise AssertionError( '%s can access folder %s even though all contained datasets should be restricted from access by her' \
                                  % ( regular_user2.email, folder_one.name ) )
        except:
            pass # This is the behavior we want
        self.logout()
        # regular_user3 is associated with role_one, so should have all permissions on imported datasets
        self.login( email='test3@bx.psu.edu' )
        check_edit_page1( latest_3_lfdas )
        self.logout()
        self.login( email='test@bx.psu.edu' )
        # Change the permissions and test again
        permissions = [ 'DATASET_ACCESS', 'DATASET_EDIT_METADATA' ]
        url = build_url( permissions, role_one )
        self.home()
        self.visit_url( url )
        self.check_page_for_string( 'Permissions and roles have been updated on 3 datasets' )
        def check_edit_page2( lfdas ):
            # Make sure the permissions have been correctly updated for the 3 datasets.  Permissions should 
            # be all of the above on any of the 3 datasets that are imported into a history
            for lfda in lfdas:
                self.home()
                self.visit_url( '%s/library/import_datasets?import_ids=%s' % ( self.url, str( lfda.id ) ) )
                self.home()
                self.visit_url( '%s/root/edit?lid=%s' % ( self.url, str( lfda.id ) ) )
                self.check_page_for_string( 'Edit Attributes' )
                self.check_page_for_string( 'input type="text" name="name" value="%s"' % lfda.name )
                try:
                    # This should no longer be possible
                    self.check_page_for_string( 'Manage permissions and role associations for %s' % lfda.name )
                    self.check_page_for_string( 'select name="DATASET_MANAGE_PERMISSIONS_in"' )
                    raise AssertionError( '%s incorrectly has DATASET_MANAGE_PERMISSIONS on datasets imported from a library' % admin_user.email )
                except:
                    pass # This is the behavior we want
        check_edit_page2( latest_3_lfdas )
    def test_120_mark_group_deleted( self ):
        """Testing marking a group as deleted"""
        self.home()
        self.visit_url( '%s/admin/groups' % self.url )
        self.check_page_for_string( group_two.name )
        self.mark_group_deleted( str( group_two.id ) )
        group_two.refresh()
        if not group_two.deleted:
            raise AssertionError( '%s was not correctly marked as deleted.' % group_two.name )
        # Deleting a group should not delete any associations
        if not group_two.members:
            raise AssertionError( '%s incorrectly lost all members when it was marked as deleted.' % group_two.name )
        if not group_two.roles:
            raise AssertionError( '%s incorrectly lost all role associations when it was marked as deleted.' % group_two.name )
    def test_125_undelete_group( self ):
        """Testing undeleting a deleted group"""
        self.undelete_group( str( group_two.id ) )
        group_two.refresh()
        if group_two.deleted:
            raise AssertionError( '%s was not correctly marked as not deleted.' % group_two.name )
    def test_130_mark_role_deleted( self ):
        """Testing marking a role as deleted"""
        self.home()
        self.visit_url( '%s/admin/roles' % self.url )
        self.check_page_for_string( role_two.name )
        self.mark_role_deleted( str( role_two.id ) )
        role_two.refresh()
        if not role_two.deleted:
            raise AssertionError( '%s was not correctly marked as deleted.' % role_two.name )
        # Deleting a role should not delete any associations
        if not role_two.users:
            raise AssertionError( '%s incorrectly lost all user associations when it was marked as deleted.' % role_two.name )
        if not role_two.groups:
            raise AssertionError( '%s incorrectly lost all group associations when it was marked as deleted.' % role_two.name )
    def test_135_undelete_role( self ):
        """Testing undeleting a deleted role"""
        self.undelete_role( str( role_two.id ) )
    def test_140_mark_library_deleted( self ):
        """Testing marking a library as deleted"""
        self.mark_library_deleted( str( library_one.id ) )
        # Make sure the library was deleted
        library_one.refresh()
        if not library_one.deleted:
            raise AssertionError( 'The library id %s named "%s" has not been marked as deleted.' % ( str( library_one.id ), library_one.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                folder.refresh()
                # Make sure all of the library_folders are deleted
                if not folder.deleted:
                    raise AssertionError( 'The library_folder named "%s" has not been marked as deleted ( library.id: %s ).' % \
                                          ( folder.name, str( library_one.id ) ) )
                check_folder( folder )
            # Make sure all of the library_folder_dataset_associations are deleted
            for lfda in library_folder.datasets:
                lfda.refresh()
                if not lfda.deleted:
                    raise AssertionError( 'The library_folder_dataset_association id %s named "%s" has not been marked as deleted ( library.id: %s ).' % \
                                          ( str( lfda.id ), lfda.name, str( library_one.id ) ) )
                # Make sure none of the datasets have been deleted since that should occur only when the library is purged
                lfda.dataset.refresh()
                if lfda.dataset.deleted:
                    raise AssertionError( 'The dataset with id "%s" has been marked as deleted when it should not have been.' % lfda.dataset.id )
        check_folder( library_one.root_folder )
    def test_145_undelete_library( self ):
        """Testing marking a library as not deleted"""
        self.undelete_library( str( library_one.id ) )
        # Make sure the library is undeleted
        library_one.refresh()
        if library_one.deleted:
            raise AssertionError( 'The library id %s named "%s" has not been marked as undeleted.' % ( str( library_one.id ), library_one.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                folder.refresh()
                # Make sure all of the library_folders are undeleted
                if folder.deleted:
                    raise AssertionError( 'The library_folder id %s named "%s" has not been marked as undeleted ( library.id: %s ).' % \
                                          ( str( folder.id ), folder.name, str( library_one.id ) ) )
                check_folder( folder )
            # Make sure all of the library_folder_dataset_associations are undeleted
            for lfda in library_folder.datasets:
                lfda.refresh()
                if lfda.deleted:
                    raise AssertionError( 'The library_folder_dataset_association id %s named "%s" has not been marked as undeleted ( library.id: %s ).' % \
                                          ( str( lfda.id ), lfda.name, str( library_one.id ) ) )
                # Make sure all of the datasets have been undeleted
                if lfda.dataset.deleted:
                    raise AssertionError( 'The dataset with id "%s" has not been marked as undeleted.' % lfda.dataset.id )
        check_folder( library_one.root_folder )
        # Mark library as deleted again so we can test purging it
        self.mark_library_deleted( str( library_one.id ) )
        # Make sure the library is deleted again
        library_one.refresh()
        if not library_one.deleted:
            raise AssertionError( 'The library id %s named "%s" has not been marked as deleted after it was undeleted.' % \
                                  ( str( library_one.id ), library_one.name ) )
    def test_150_purge_user( self ):
        """Testing purging a user account"""
        self.mark_user_deleted( user_id=regular_user3.id )
        self.purge_user( user_id=regular_user3.id )
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
            if not history.deleted:
                raise AssertionError( 'User %s has active history id %d after their account was marked as purged.' % ( regular_user3.email, hda.id ) )
            # Make sure DefaultHistoryPermissions deleted EXCEPT FOR THE PRIVATE ROLE
            if len( history.default_permissions ) != 1:
                raise AssertionError( 'DefaultHistoryPermissions for history id %d were not deleted.' % history.id )
            for dhp in history.default_permissions:
                role = galaxy.model.Role.get( dhp.role_id )
                if role.type != 'private':
                    raise AssertionError( 'DefaultHistoryPermissions for history id %d are not related with the private role.' % history.id )
            # Make sure HistoryDatasetAssociation deleted
            for hda in history.datasets:
                hda.refresh()
                if not hda.deleted:
                    raise AssertionError( 'HistoryDatasetAssociation id %d was not deleted.' % hda.id )
                # Make sure Dataset deleted
                d = galaxy.model.Dataset.filter( galaxy.model.Dataset.table.c.id==hda.dataset_id ).first()
                d.refresh()
                if not d.deleted:
                    raise AssertionError( 'Dataset id %d was not deleted.' % d.id )
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
    def test_155_manually_unpurge_user( self ):
        """Testing manually un-purging a user account"""
        # Reset the user for later test runs.  The user's private Role and DefaultUserPermissions for that role
        # should have been preserved, so all we need to do is reset purged and deleted.
        # TODO: If we decide to implement the GUI feature for un-purging a user, replace this with a method call
        regular_user3.purged = False
        regular_user3.deleted = False
        regular_user3.flush()
    def test_160_purge_group( self ):
        """Testing purging a group"""
        group_id = str( group_two.id )
        self.mark_group_deleted( group_id )
        self.purge_group( group_id )
        # Make sure there are no UserGroupAssociations
        uga = galaxy.model.UserGroupAssociation.filter( galaxy.model.UserGroupAssociation.table.c.group_id == group_id ).all()
        if uga:
            raise AssertionError( "Purging the group did not delete the UserGroupAssociations for group_id '%s'" % group_id )
        # Make sure there are no GroupRoleAssociations
        gra = galaxy.model.GroupRoleAssociation.filter( galaxy.model.GroupRoleAssociation.table.c.group_id == group_id ).all()
        if gra:
            raise AssertionError( "Purging the group did not delete the GroupRoleAssociations for group_id '%s'" % group_id )
        # Undelete the group for later test runs
        self.undelete_group( group_id )
    def test_165_purge_role( self ):
        """Testing purging a role"""
        role_id = str( role_two.id )
        self.mark_role_deleted( role_id )
        self.purge_role( role_id )
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
        # Make sure there are no ActionDatasetRoleAssociations
        adra = galaxy.model.ActionDatasetRoleAssociation.filter( galaxy.model.ActionDatasetRoleAssociation.table.c.role_id == role_id ).all()
        if adra:
            raise AssertionError( "Purging the role did not delete the ActionDatasetRoleAssociations for role_id '%s'" % role_id )
    def test_170_manually_unpurge_role( self ):
        """Testing manually un-purging a role"""
        # Manually unpurge, then undelete the role for later test runs
        # TODO: If we decide to implement the GUI feature for un-purging a role, replace this with a method call
        role_two.purged = False
        role_two.flush()
        self.undelete_role( str( role_two.id ) )
    def test_175_purge_library( self ):
        """Testing purging a library"""
        self.purge_library( str( library_one.id ) )
        # Make sure the library was purged
        library_one.refresh()
        if not library_one.purged:
            raise AssertionError( 'The library id %s named "%s" has not been marked as purged.' % ( str( library_one.id ), library_one.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                folder.refresh()
                # Make sure all of the library_folders are purged
                if not folder.purged:
                    raise AssertionError( 'The library_folder id %s named "%s" has not been marked purged.' % ( str( folder.id ), folder.name ) )
                check_folder( folder )
            # Make sure all of the library_folder_dataset_associations are deleted ( no purged column )
            for lfda in library_folder.datasets:
                lfda.refresh()
                if not lfda.deleted:
                    raise AssertionError( 'The library_folder_dataset_association id %s named "%s" has not been marked as deleted.' % \
                                          ( str( lfda.id ), lfda.name ) )
                # Make sure all of the datasets have been deleted
                dataset = lfda.dataset
                dataset.refresh()
                if not dataset.deleted:
                    raise AssertionError( 'The dataset with id "%s" has not been marked as deleted when it should have been.' % \
                                          str( lfda.dataset.id ) )
        check_folder( library_one.root_folder )
    def test_180_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        ##################
        # Reset admin_user
        ##################
        # Eliminate all role associations except private
        self.remove_user_from_role( str( admin_user.id ), str( role_one.id ) )
        self.remove_user_from_role( str( admin_user.id ), str( role_three.id ) )
        admin_user.refresh()
        if len( admin_user.roles) != 1:
            raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 1 )' % ( len( admin_user.roles ), admin_user.email ) )
        # Eliminate all group associations
        self.remove_user_from_group( str( admin_user.id ), str( group_one.id ) )
        admin_user.refresh()
        if admin_user.groups:
            raise AssertionError( '%d UserGroupAssociations are associated with %s ( should be 0 )' % ( len( admin_user.groups ), admin_user.email ) )
        #####################
        # Reset regular_user1
        #####################
        self.logout()
        self.login( email='test1@bx.psu.edu' )
        # Change DefaultHistoryPermissions for regular_user1 back to the default
        permissions_in = [ 'DATASET_MANAGE_PERMISSIONS' ]
        permissions_out = [ 'DATASET_ACCESS', 'DATASET_EDIT_METADATA' ]
        role_id = str( regular_user1_private_role.id )
        self.user_set_default_permissions( permissions_in=permissions_in, permissions_out=permissions_out, role_id=role_id )
        self.logout()
        self.login( email='test@bx.psu.edu' )
        # Eliminate all role associations except private
        self.remove_user_from_role( str( regular_user1.id ), str( role_one.id ) )
        regular_user1.refresh()
        if len( regular_user1.roles) != 1:
            raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 1 )' % ( len( regular_user1.roles ), regular_user1.email ) )
        # Eliminate all group associations
        self.remove_user_from_group( str( regular_user1.id ), str( group_one.id ) )
        regular_user1.refresh()
        if regular_user1.groups:
            raise AssertionError( '%d UserGroupAssociations are associated with %s ( should be 0 )' % ( len( regular_user1.groups ), regular_user1.email ) )
        #################
        # Reset group_one
        #################
        # Eliminate all role associations
        self.remove_role_from_group( str( role_one.id ), str( group_one.id ) )
        group_one.refresh()
        if group_one.roles:
            raise AssertionError( '%d GroupRoleAssociations are associated with group %s ( should be 0 )' % ( len( group_one.roles ), group_one.name ) )
