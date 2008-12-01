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
        self.visit_url( "%s/admin/group_members_edit" % self.url )
        self.check_page_for_string( not_logged_in_security_msg )
        self.visit_url( "%s/admin/update_group_members" % self.url )
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
    def test_03_login_as_admin_user( self ):
        """Testing logging in as an admin user - tests initial settings for DefaultUserPermissions and DefaultHistoryPermissions"""
        self.login( email='test@bx.psu.edu' ) # test@bx.psu.edu is configured as our admin user
        self.visit_page( "admin" )
        self.check_page_for_string( 'Administration' )
        global testuser1
        testuser1 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test@bx.psu.edu' ).first()
        # Make sure DefaultUserPermissions are correct
        if not testuser1.default_permissions:
            raise AssertionError( 'No DefaultUserPermissions were created for %s when their account was created' % testuser1.email )
        if len( testuser1.default_permissions ) > 1:
            raise AssertionError( 'More than 1 DefaultUserPermissions were created for %s when their account was created' % testuser1.email )
        dup =  galaxy.model.DefaultUserPermissions.filter( galaxy.model.DefaultUserPermissions.table.c.user_id==testuser1.id ).first()
        if not dup.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultUserPermission.action for user "%s" is "%s", but it should be "%s"' \
                                  % ( testuser1.email, dup.action, galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        # Make sure DefaultHistoryPermissions are correct
        latest_history = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        if not latest_history.default_permissions:
            raise AssertionError( 'No DefaultHistoryPermissions were created for history id %d when it was created' % latest_history.id )
        if len( latest_history.default_permissions ) > 1:
            raise AssertionError( 'More than 1 DefaultHistoryPermissions were created for history id %d when it was created' % latest_history.id )
        dhp =  galaxy.model.DefaultHistoryPermissions.filter( galaxy.model.DefaultHistoryPermissions.table.c.history_id==latest_history.id ).first()
        if not dhp.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultHistoryPermission.action for history id %d is "%s", but it should be "%s"' \
                                  % ( latest_history.id, dhp.action, galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        self.visit_url( "%s/admin/user?user_id=%s" % ( self.url, testuser1.id ) )
        self.check_page_for_string( testuser1.email )
        self.home()
        self.logout()
    def test_06_login_as_non_admin_user1( self ):
        """Testing logging in as non-admin user1 - tests private role creation, changing DefaultHistoryPermissions for new histories"""
        self.login( email='test2@bx.psu.edu' ) # test2@bx.psu.edu is not an admin user
        global testuser2
        testuser2 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test2@bx.psu.edu' ).first()
        self.visit_page( "admin" )
        self.check_page_for_string( logged_in_security_msg )
        # Make sure a private role exists for testuser2
        private_role = None
        for role in testuser2.all_roles():
            if role.name == testuser2.email and role.description == 'Private Role for %s' % testuser2.email:
                private_role = role
                break
        if not private_role:
            raise AssertionError( "Private role not found for user '%s'" % testuser2.email )
        # Add a dataset to the history
        self.upload_file( '1.bed' )
        latest_dataset = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        # Make sure ActionDatasetRoleAssociation is correct
        if not latest_dataset.actions:
            raise AssertionError( 'No ActionDatasetRoleAssociations were created for dataset id %d when it was created' % latest_dataset.id )
        if len( latest_dataset.actions ) > 1:
            raise AssertionError( 'More than 1 ActionDatasetRoleAssociations were created for dataset id %d when it was created' % latest_dataset.id )
        adra = galaxy.model.ActionDatasetRoleAssociation.filter( galaxy.model.ActionDatasetRoleAssociation.table.c.dataset_id==latest_dataset.id ).first()
        if not adra.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The ActionDatasetRoleAssociation.action for dataset id %d is "%s", but it should be "%s"' \
                                  % ( latest_dataset.id, adra.action, galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        # Change DefaultHistoryPermissions for testuser2
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
        if not latest_history.default_permissions:
            raise AssertionError( 'No DefaultHistoryPermissions were created for history id %d when DefaultHistoryPermissions were changed' % \
                                  latest_history.id )
        if len( latest_history.default_permissions ) != len( galaxy.model.Dataset.permitted_actions.items() ):
            raise AssertionError( '%d DefaultHistoryPermissions were created for history id %d, should have been %d' % \
                                  ( len( latest_history.default_permissions ), latest_history.id, len( galaxy.model.Dataset.permitted_actions ) ) )
        dhps = []
        for dhp in latest_history.default_permissions:
            dhps.append( dhp.action )
        # Sort actions for later comparison
        dhps.sort()
        for key, value in galaxy.model.Dataset.permitted_actions.items():
            if value.action not in dhps:
                raise AssertionError( '%s not in history id %d default_permissions after they were changed' % ( value.action, latest_history.id ) )
        # Add a dataset to the history
        self.upload_file( '1.bed' )
        latest_dataset = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        # Make sure ActionDatasetRoleAssociations are correct
        if not latest_dataset.actions:
            raise AssertionError( 'No ActionDatasetRoleAssociations were created for dataset id %d when it was created' % latest_dataset.id )
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
        # Change DefaultHistoryPermissions for testuser2 back to the default
        permissions_in = [ 'DATASET_MANAGE_PERMISSIONS' ]
        permissions_out = [ 'DATASET_ACCESS', 'DATASET_EDIT_METADATA' ]
        role_id = str( private_role.id )
        self.user_set_default_permissions( permissions_in=permissions_in, permissions_out=permissions_out, role_id=role_id )
        self.home()
        self.logout()
    def test_09_login_as_non_admin_user2( self ):
        """Testing logging in as non-admin user2 - tests changing DefaultHistoryPermissions for the current history"""
        self.login( email='test3@bx.psu.edu' ) # This will not be an admin user
        global testuser3
        testuser3 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test3@bx.psu.edu' ).first()
        latest_history = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        self.upload_file( '1.bed' )
        latest_dataset = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        permissions_in = [ 'DATASET_EDIT_METADATA', 'DATASET_MANAGE_PERMISSIONS' ]
        # Make sure these are in sorted order for later comparison
        actions_in = [ 'edit metadata', 'manage permissions' ]
        permissions_out = [ 'DATASET_ACCESS' ]
        actions_out = [ 'access' ]
        private_role = None
        for role in testuser3.all_roles():
            if role.name == testuser3.email and role.description == 'Private Role for %s' % testuser3.email:
                private_role = role
                break
        if not private_role:
            raise AssertionError( "Private role not found for user '%s'" % testuser3.email )
        role_id = str( private_role.id )
        # Change DefaultHistoryPermissions for the current history
        self.history_set_default_permissions( permissions_out=permissions_out, permissions_in=permissions_in, role_id=role_id )
        if not latest_history.default_permissions:
            raise AssertionError( 'No DefaultHistoryPermissions were created for history id %d when DefaultHistoryPermissions were changed' % \
                                  latest_history.id )
        if len( latest_history.default_permissions ) != len( actions_in ):
            raise AssertionError( '%d DefaultHistoryPermissions were created for history id %d, should have been %d' \
                                  % ( len( latest_history.default_permissions ), latest_history.id, len( permissions_in ) ) )
        # Make sure DefaultHistoryPermissions were correctly changed for the current history
        dhps = []
        for dhp in latest_history.default_permissions:
            dhps.append( dhp.action )
        # Sort actions for later comparison
        dhps.sort()
        # Compare DefaultHistoryPermissions and actions_in - should be the same
        if dhps != actions_in:
                raise AssertionError( 'DefaultHistoryPermissions "%s" for history id %d differ from actions "%s" passed for changing' \
                                      % ( str( dhps ), latest_history.id, str( actions_in ) ) )
        # Make sure ActionDatasetRoleAssociations are correct
        if not latest_dataset.actions:
            raise AssertionError( 'No ActionDatasetRoleAssociations were created for dataset id %d when it was created' % latest_dataset.id )
        if len( latest_dataset.actions ) != len( latest_history.default_permissions ):
            raise AssertionError( '%d ActionDatasetRoleAssociations were created for dataset id %d when it was created ( should have been %d )' \
                                  % ( len( latest_dataset.actions ), latest_dataset.id, len( latest_history.default_permissions ) ) )
        adras = []
        for adra in latest_dataset.actions:
            adras.append( adra.action )
        # Sort actions for later comparison
        adras.sort()
        self.home()
        self.logout()
    def test_12_create_new_user_account_as_admin( self ):
        """Testing creating a new user account as admin"""
        self.login( email='test@bx.psu.edu' )
        email = 'test4@bx.psu.edu'
        password = 'testuser'
        previously_created = self.create_new_account_as_admin( email=email, password=password )
        # Get the user object for later tests
        global testuser4
        testuser4 = galaxy.model.User.filter( galaxy.model.User.table.c.email=='test4@bx.psu.edu' ).first()
        # Make sure DefaultUserPermissions were created
        if not testuser4.default_permissions:
            raise AssertionError( 'No DefaultUserPermissions were created for user %s when the admin created the account' % email )
        # Make sure a private role was created for the user
        if not testuser4.roles:
            raise AssertionError( 'No UserRoleAssociations were created for user %s when the admin created the account' % email )
        if not previously_created and len( testuser4.roles ) != 1:
            raise AssertionError( '%d UserRoleAssociations were created for user %s when the admin created the account ( should have been <= 2 )' \
                                  % ( len( testuser4.roles ), testuser4.email ) )
        for ura in testuser4.roles:
            role = galaxy.model.Role.get( ura.role_id )
            if not previously_created and role.type != 'private':
                raise AssertionError( 'Role created for user %s when the admin created the account is not private, type is' \
                                      % str( role.type ) )
        if not previously_created:
            # Make sure a history was not created ( previous test runs may have left deleted histories )
            histories = galaxy.model.History.filter( and_( galaxy.model.History.table.c.user_id==testuser4.id,
                                                           galaxy.model.History.table.c.deleted==False ) ).all()
            if histories:
                raise AssertionError( 'Histories were incorrectly created for user %s when the admin created the account' % email )
            # Make sure the user was not associated with any groups
            if testuser4.groups:
                raise AssertionError( 'Groups were incorrectly associated with user %s when the admin created the account' % email )
    def test_15_reset_password_as_admin( self ):
        """Testing reseting a user password as admin"""
        email = 'test4@bx.psu.edu'
        self.reset_password_as_admin( user_id=testuser4.id, password='testreset' )
        self.home()
        self.logout()
    def test_18_login_after_password_reset( self ):
        """Testing logging in after an admin reset a password - tests DefaultHistoryPermissions for accounts created by an admin"""
        self.login( email='test4@bx.psu.edu', password='testreset' )
        # Make sure a History and HistoryDefaultPermissions exist for the user
        latest_history = galaxy.model.History.query().order_by( desc( galaxy.model.History.table.c.create_time ) ).first()
        if not latest_history.user_id == testuser4.id:
            raise AssertionError( 'A history was not created for user %s when he logged in' % email )
        if not latest_history.default_permissions:
            raise AssertionError( 'No DefaultHistoryPermissions were created for history id %d when it was created' % latest_history.id )
        if len( latest_history.default_permissions ) > 1:
            raise AssertionError( 'More than 1 DefaultHistoryPermissions were created for history id %d when it was created' % latest_history.id )
        dhp =  galaxy.model.DefaultHistoryPermissions.filter( galaxy.model.DefaultHistoryPermissions.table.c.history_id==latest_history.id ).first()
        if not dhp.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultHistoryPermission.action for history id %d is "%s", but it should be "%s"' \
                                  % ( latest_history.id, dhp.action, galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action ) )
        # Upload a file to create a HistoryDatasetAssociation
        self.upload_file( '1.bed' )
        self.home()
        self.logout()
    def test_21_mark_user_deleted( self ):
        """Testing marking a user account as deleted"""
        self.login( email='test@bx.psu.edu' )
        self.mark_user_deleted( user_id=testuser4.id )
    def test_24_undelete_user( self ):
        """Testing undeleting a user account"""
        self.undelete_user( user_id=testuser4.id )
    def test_27_create_role( self ):
        """Testing creating new non-private role with 3 members"""
        name = 'Role One'
        description = 'This is Role One'
        user_ids=[ str( testuser1.id ), str( testuser2.id ), str( testuser4.id ) ]
        previously_created = self.create_role( name=name, description=description, user_ids=user_ids, private_role=testuser1.email )
        # Get the role object for later tests
        global role_one
        role_one = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
        # Make sure UserRoleAssociations are correct
        if not role_one.users:
            raise AssertionError( 'No UserRoleAssociations were created for role id %d when it was created with 3 members' % role_one.id )
        if len( role_one.users ) != len( user_ids ):
            raise AssertionError( '%d UserRoleAssociations were created for role id %d when it was created ( should have been %d )' \
                                  % ( len( role_one.users ), role_one.id, len( user_ids ) ) )
        # Each user should now have 2 role associations, their private role and role_one
        for user in [ testuser1, testuser2, testuser4 ]:
            user.refresh()
            if not user.roles:
                raise AssertionError( 'No UserRoleAssociations were created for user %s when a new role was created' % user.email )
            if not previously_created and len( user.roles ) != 2:
                raise AssertionError( '%d UserRoleAssociations are associated with user %s ( should be 2 )' % ( len( user.roles ), user.email ) )
    def test_30_create_group( self ):
        """Testing creating new group with 3 members and 1 associated role"""
        name = 'Group One'
        user_ids=[ str( testuser1.id ), str( testuser2.id ), str( testuser4.id ) ]
        role_ids=[ str( role_one.id ) ]
        previously_created = self.create_group( name=name, user_ids=user_ids, role_ids=role_ids )
        # Get the group object for later tests
        global group_one
        group_one = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
        # Make sure UserGroupAssociations are correct
        if not group_one.users:
            raise AssertionError( 'No UserGroupAssociations were created for group id %d when it was created with 3 members' % group_one.id )
        if len( group_one.users ) != len( user_ids ):
            raise AssertionError( '%d UserGroupAssociations were created for group id %d when it was created ( should have been %d )' \
                                  % ( len( group_one.users ), group_one.id, len( user_ids ) ) )
        # Each user should now have 1 group association, group_one
        for user in [ testuser1, testuser2, testuser4 ]:
            user.refresh()
            if not user.groups:
                raise AssertionError( 'No UserGroupAssociations were created for user %s when a new group was created' % user.email )
            if len( user.groups ) != 1:
                raise AssertionError( '%d UserGroupAssociations are associated with user %s ( should be 1 )' % ( len( user.groups ), user.email ) )
        # Make sure GroupRoleAssociations are correct
        if not group_one.roles:
            raise AssertionError( 'No GroupRoleAssociations were created for group id %d when it was created with 3 members' % group_one.id )
        if len( group_one.roles ) != len( role_ids ):
            raise AssertionError( '%d GroupRoleAssociations were created for group id %d when it was created ( should have been %d )' \
                                  % ( len( group_one.roles ), group_one.id, len( role_ids ) ) )
    def test_33_add_group_member( self ):
        """Testing editing membership of an existing group"""
        name = 'Group Two'
        self.create_group( name=name )
        # Get the group object for later tests
        global group_two
        group_two = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
        user_ids = [ str( testuser3.id )  ]
        self.add_group_members( str( group_two.id ), user_ids )
        self.visit_url( "%s/admin/group_members_edit?group_id=%s" % ( self.url, str( group_two.id ) ) )
        self.check_page_for_string( testuser3.email )
        # Make sure UserGroupAssociations are correct
        if not group_two.users:
            raise AssertionError( 'No UserGroupAssociations were created for group id %d when %d members were added' \
                                  % ( group_two.id, len( user_ids ) ) )
        if len( group_two.users ) != len( user_ids ):
            raise AssertionError( '%d UserGroupAssociations were created for group id %d when %d members were added' \
                                  % ( len( group_two.users ), group_two.id, len( user_ids ) ) )
        # Create another group -needed for the following test
        name = 'Group Three'
        self.create_group( name=name )
        # Get the group object for later tests
        global group_three
        group_three = galaxy.model.Group.filter( galaxy.model.Group.table.c.name==name ).first()
    def test_36_associate_groups_with_role( self ):
        """Testing adding existing groups to an existing role"""
        # NOTE: To get this to work with twill, all select lists on the ~/admin/role page must contain at least
        # 1 option value or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug in twill, we create the role, associating it with at least 1 user and 1 group.  We
        # also must ensure that each of the form fields will contain at least 1 value prior to submitting the form,
        # so we had to create group_three in the previous test
        name = 'Role Two'
        description = 'This is Role Two'
        user_ids=[ str( testuser1.id ) ]
        group_ids=[ str( group_two.id ) ]
        private_role=testuser1.email
        # STEP 1: create the role
        previously_created = self.create_role( name=name, 
                                               description=description, 
                                               user_ids=user_ids, 
                                               group_ids=group_ids, 
                                               private_role=private_role )
        # Get the role object for later tests
        global role_two
        role_two = galaxy.model.Role.filter( galaxy.model.Role.table.c.name==name ).first()
        # Make sure UserRoleAssociations are correct
        if not role_two.users:
            raise AssertionError( 'No UserRoleAssociations were created for role id %d when it was created with %d members' \
                                  % ( role_two.id, len( user_ids ) ) )
        if len( role_two.users ) != len( user_ids ):
            raise AssertionError( '%d UserRoleAssociations were created for role id %d when it was created with %d members' \
                                  % ( len( role_two.users ), role_two.id, len( user_ids ) ) )
        # testuser1 should now have 3 role associations, private role, role_one, another+test_role
        for user in [ testuser1 ]:
            user.refresh()
            if not user.roles:
                raise AssertionError( 'No UserRoleAssociations were created for user %s when a new role was created' % user.email )
            if len( user.roles ) != 3:
                raise AssertionError( '%d UserRoleAssociations are associated with user %s ( should be 3 )' % ( len( user.roles ), user.email ) )
        # Make sure GroupRoleAssociations are correct
        if not role_two.groups:
            raise AssertionError( 'No GroupRoleAssociations were created for role id %d when it was created with %d groups' \
                                  % ( role_two.id, len( group_ids ) ) )
        if len( role_two.groups ) != len( group_ids ):
            raise AssertionError( '%d GroupRoleAssociations were created for role id %d when it was created ( should have been %d )' \
                                  % ( len( role_two.groups ), role_two.id, len( group_ids ) ) )
        # The group should also now be associated with 1 role
        for group in [ group_two ]:
            group.refresh()
            if not group.roles:
                raise AssertionError( 'No GroupRoleAssociations were created for group id %d when a new role was created' % group.id )
            if len( group.roles ) != 1:
                raise AssertionError( '%d GroupRoleAssociations are associated with group id %d ( should be 1 )' % ( len( group.roles ), group.id ) )
        # STEP 2: associate the role with a group not yet associated
        # TODO: Twill throws an exception on this...
        #group_names = [ group_one.name ]
        #self.associate_groups_with_role( str( role_two.id ), group_names=group_names )
        #self.visit_page( 'admin/roles' )
        #self.check_page_for_string( group_one.name )
        #
        # Manually delete the userRoleAssociation for later test runs
        for ura in testuser1.roles:
            if ura.role_id == role_two.id:
                ura.delete()
                ura.flush()
                break
    def test_39_create_library( self ):
        """Testing creating new library"""
        name = 'Library One'
        description = 'This is Library One'
        self.create_library( name=name, description=description )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( name )
        # Get the library object for later tests
        global library
        library = galaxy.model.Library.filter( and_( galaxy.model.Library.table.c.name==name,
                                                     galaxy.model.Library.table.c.description==description,
                                                     galaxy.model.Library.table.c.deleted==False ) ).first()
    def test_42_rename_library( self ):
        """Testing renaming a library"""
        self.rename_library( str( library.id ), name='Library One Renamed', description='This is Library One Re-described', root_folder='on' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "Library One Renamed" )
        # Rename it back to what it was originally
        self.rename_library( str( library.id ), name='Library One', description='This is Library One', root_folder='on' )
    def test_45_rename_root_folder( self ):
        """Testing renaming a library root folder"""
        folder = library.root_folder
        self.rename_folder( str( folder.id ), name='Library One Root Folder', description='This is Library One root folder' )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "Library One Root Folder" )
    def test_48_add_public_dataset_to_root_folder( self ):
        """Testing adding a public dataset to a library root folder"""
        folder = library.root_folder
        self.add_dataset( '1.bed', str( folder.id ), extension='bed', dbkey='hg18', roles=[] )
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "1.bed" )
        self.check_page_for_string( "bed" )
        self.check_page_for_string( "hg18" )
    def test_51_copy_dataset_from_history_to_root_folder( self ):
        """Testing copying a dataset from the current history to a library root folder"""
        folder = library.root_folder
        self.add_dataset_to_folder_from_history( str( folder.id ) )
        # Now that we have a history and a dataset, we can test for ActionDatasetRoleAssociation - we're still logged in as testuser1.
        # The default setting are "manage permissions"
        last_dataset_created = galaxy.model.Dataset.query().order_by( desc( galaxy.model.Dataset.table.c.create_time ) ).first()
        adras = galaxy.model.ActionDatasetRoleAssociation.filter( galaxy.model.ActionDatasetRoleAssociation.table.c.dataset_id==last_dataset_created.id ).all()
        if not adras:
            raise AssertionError( 'No ActionDatasetRoleAssociations created for dataset id: %d' % last_dataset_created.id )
        if len( adras ) > 1:
            raise AssertionError( 'More than 1 ActionDatasetRoleAssociations created for dataset id: %d' % last_dataset_created.id )
        for adra in adras:
            if not adra.action == 'manage permissions':
                raise AssertionError( 'ActionDatasetRoleAssociation.action "%s" is not the DefaultHistoryPermission setting, which is "manage permissions"' % \
                                      str( adra.action ) )
    def test_54_add_new_folder( self ):
        """Testing adding a folder to a library root folder"""
        root_folder = library.root_folder
        name = 'Folder One'
        description = 'This is Folder One'
        self.add_folder( str( root_folder.id ), name=name, description=description )
        global new_test_folder
        new_test_folder = galaxy.model.LibraryFolder.filter( and_( galaxy.model.LibraryFolder.table.c.parent_id==root_folder.id,
                                                                   galaxy.model.LibraryFolder.table.c.name==name,
                                                                   galaxy.model.LibraryFolder.table.c.description==description ) ).first()
        self.visit_page( 'admin/libraries' )
        self.check_page_for_string( "Folder One" )
    def test_57_add_datasets_from_library_dir( self ):
        """Testing adding several datasets from library directory to sub-folder"""
        roles_tuple = [ ( str( role_one.id ), role_one.description ) ] 
        self.add_datasets_from_library_dir( str( new_test_folder.id ), roles_tuple=roles_tuple )
    def test_60_mark_group_deleted( self ):
        """Testing marking a group as deleted"""
        self.visit_page( "admin/groups" )
        self.check_page_for_string( group_two.name )
        self.mark_group_deleted( str( group_two.id ) )
    def test_63_undelete_group( self ):
        """Testing undeleting a deleted group"""
        self.undelete_group( str( group_two.id ) )
    def test_66_mark_role_deleted( self ):
        """Testing marking a role as deleted"""
        self.visit_page( "admin/roles" )
        self.check_page_for_string( role_two.description )
        self.mark_role_deleted( str( role_two.id ) )
    def test_69_undelete_role( self ):
        """Testing undeleting a deleted role"""
        self.undelete_role( str( role_two.id ) )
    def test_72_mark_library_deleted( self ):
        """Testing marking a library as deleted"""
        self.mark_library_deleted( str( library.id ) )
        # Make sure the library was deleted
        library.refresh()
        if not library.deleted:
            raise AssertionError( 'The library id %s named "%s" has not been marked as deleted.' % ( str( library.id ), library.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                folder.refresh()
                # Make sure all of the library_folders are deleted
                if not folder.deleted:
                    raise AssertionError( 'The library_folder named "%s" has not been marked as deleted ( library.id: %s ).' % \
                                          ( folder.name, str( library.id ) ) )
                check_folder( folder )
            # Make sure all of the library_folder_dataset_associations are deleted
            for lfda in library_folder.datasets:
                lfda.refresh()
                if not lfda.deleted:
                    raise AssertionError( 'The library_folder_dataset_association id %s named "%s" has not been marked as deleted ( library.id: %s ).' % \
                                          ( str( lfda.id ), lfda.name, str( library.id ) ) )
                # Make sure none of the datasets have been deleted since that should occur only when the library is purged
                lfda.dataset.refresh()
                if lfda.dataset.deleted:
                    raise AssertionError( 'The dataset with id "%s" has been marked as deleted when it should not have been.' % lfda.dataset.id )
        check_folder( library.root_folder )
    def test_75_mark_library_undeleted( self ):
        """Testing marking a library as not deleted"""
        self.mark_library_undeleted( str( library.id ) )
        # Make sure the library is undeleted
        library.refresh()
        if library.deleted:
            raise AssertionError( 'The library id %s named "%s" has not been marked as undeleted.' % ( str( library.id ), library.name ) )
        def check_folder( library_folder ):
            for folder in library_folder.folders:
                folder.refresh()
                # Make sure all of the library_folders are undeleted
                if folder.deleted:
                    raise AssertionError( 'The library_folder id %s named "%s" has not been marked as undeleted ( library.id: %s ).' % \
                                          ( str( folder.id ), folder.name, str( library.id ) ) )
                check_folder( folder )
            # Make sure all of the library_folder_dataset_associations are undeleted
            for lfda in library_folder.datasets:
                lfda.refresh()
                if lfda.deleted:
                    raise AssertionError( 'The library_folder_dataset_association id %s named "%s" has not been marked as undeleted ( library.id: %s ).' % \
                                          ( str( lfda.id ), lfda.name, str( library.id ) ) )
                # Make sure all of the datasets have been undeleted
                if lfda.dataset.deleted:
                    raise AssertionError( 'The dataset with id "%s" has not been marked as undeleted.' % lfda.dataset.id )
        check_folder( library.root_folder )
        # Mark library as deleted again so we can test purging it
        self.mark_library_deleted( str( library.id ) )
        # Make sure the library is deleted again
        library.refresh()
        if not library.deleted:
            raise AssertionError( 'The library id %s named "%s" has not been marked as deleted after it was undeleted.' % \
                                  ( str( library.id ), library.name ) )
    def test_78_purge_user( self ):
        """Testing purging a user account"""
        self.mark_user_deleted( user_id=testuser4.id )
        self.purge_user( user_id=testuser4.id )
        testuser4.refresh()
        if not testuser4.purged:
            raise AssertionError( 'User %s was not marked as purged.' % testuser4.email )
        # Make sure DefaultUserPermissions deleted EXCEPT FOR THE PRIVATE ROLE
        if len( testuser4.default_permissions ) != 1:
            raise AssertionError( 'DefaultUserPermissions for user %s were not deleted.' % testuser4.email )
        for dup in testuser4.default_permissions:
            role = galaxy.model.Role.get( dup.role_id )
            if role.type != 'private':
                raise AssertionError( 'DefaultUserPermissions for user %s are not related with the private role.' % testuser4.email )
        # Make sure History deleted
        for history in testuser4.histories:
            if not history.deleted:
                raise AssertionError( 'User %s has active history id %d after their account was marked as purged.' % ( testuser4.email, hda.id ) )
            # Make sure DefaultHistoryPermissions deleted EXCEPT FOR THE PRIVATE ROLE
            if len( history.default_permissions ) != 1:
                raise AssertionError( 'DefaultHistoryPermissions for history id %d were not deleted.' % history.id )
            for dhp in history.default_permissions:
                role = galaxy.model.Role.get( dhp.role_id )
                if role.type != 'private':
                    raise AssertionError( 'DefaultHistoryPermissions for history id %d are not related with the private role.' % history.id )
            # Make sure HistoryDatasetAssociation deleted
            for hda in history.datasets:
                if not hda.deleted:
                    raise AssertionError( 'HistoryDatasetAssociation id %d was not deleted.' % hda.id )
                # Make sure Dataset deleted
                d = galaxy.model.Dataset.filter( galaxy.model.Dataset.table.c.id==hda.dataset_id ).first()
                if not d.deleted:
                    raise AssertionError( 'Dataset id %d was not deleted.' % d.id )
        # Make sure UserGroupAssociations deleted
        if testuser4.groups:
            raise AssertionError( 'User %s has active group id %d after their account was marked as purged.' % ( testuser4.email, uga.id ) )
        # Make sure UserRoleAssociations deleted EXCEPT FOR THE PRIVATE ROLE
        if len( testuser4.roles ) != 1:
            raise AssertionError( 'UserRoleAssociations for user %s were not deleted.' % testuser4.email )
        for ura in testuser4.roles:
            role = galaxy.model.Role.get( ura.role_id )
            if role.type != 'private':
                raise AssertionError( 'UserRoleAssociations for user %s are not related with the private role.' % testuser4.email )
    def test_81_manually_unpurge_user( self ):
        """Testing manually un-purging a user account"""
        # Reset the user for later test runs.  The user's private Role and DefaultUserPermissions for that role
        # should have been preserved, so all we need to do is reset purged and deleted.
        # TODO: If we decide to implement the GUI feature for un-purging a user, replace this with a method call
        testuser4.purged = False
        testuser4.deleted = False
        testuser4.flush()
        # Need to also manually add user as a member of group_one for later test runs
        uga = galaxy.model.UserGroupAssociation( testuser4, group_one )
        uga.flush()
    def test_84_edit_role_membership( self ):
        """Testing adding a new member to an existing role"""
        # TODO: Twill throws an exception on this...
        #self.associate_users_with_role( str( role_one.id ), user_emails=[ str( testuser4.email ) ] )
        # Due to the above bug in twill, we need to manaually re-associate the user with the role for later test runs.
        ura = galaxy.model.UserRoleAssociation( testuser4, role_one )
        ura.flush()
    def test_87_purge_group( self ):
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
    def test_90_purge_role( self ):
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
        # Manually unpurge, then undelete the role for later test runs
        role_two.perged = False
        role_two.flush()
        self.undelete_role( role_id )
        # Manually re-associate groups and users for later test runs.
        ura = galaxy.model.UserRoleAssociation( testuser1, role_two )
        ura.flush()
        uga = galaxy.model.GroupRoleAssociation( group_two, role_two )
        uga.flush()
    def test_93_purge_library( self ):
        """Testing purging a library"""
        self.purge_library( str( library.id ) )
        # Make sure the library was purged
        library.refresh()
        if not library.purged:
            raise AssertionError( 'The library id %s named "%s" has not been marked as purged.' % ( str( library.id ), library.name ) )
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
        check_folder( library.root_folder )
