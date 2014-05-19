from base.twilltestcase import TwillTestCase
from functional import database_contexts
import galaxy.model
from base.test_db_util import (
    get_user,
    get_private_role,
    get_all_histories_for_user,
    get_latest_history_for_user,
    get_default_history_permissions_by_history,
    get_latest_dataset,
    refresh,
    flush,
    get_group_by_name,
    get_role_by_name,
    get_user_group_associations_by_group,
    get_default_history_permissions_by_role,
    get_default_user_permissions_by_role,
    get_user_role_associations_by_role,
    get_group_role_associations_by_group,
    get_dataset_permissions_by_role,
    get_group_role_associations_by_role,
)


# Globals setup by these tests.
regular_user1 = regular_user2 = regular_user3 = admin_user = None
role_one = role_two = role_three = None
group_zero = group_one = group_two = None


class TestDataSecurity( TwillTestCase ):
    def test_000_initiate_users( self ):
        """Ensuring all required user accounts exist"""
        self.logout()
        self.login( email='test1@bx.psu.edu', username='regular-user1' )
        global regular_user1
        regular_user1 = get_user( 'test1@bx.psu.edu' )
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        self.logout()
        self.login( email='test2@bx.psu.edu', username='regular-user2' )
        global regular_user2
        regular_user2 = get_user( 'test2@bx.psu.edu' )
        assert regular_user2 is not None, 'Problem retrieving user with email "test2@bx.psu.edu" from the database'
        self.logout()
        self.login( email='test@bx.psu.edu', username='admin-user' )
        global admin_user
        admin_user = get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'

    def test_005_create_new_user_account_as_admin( self ):
        """Testing creating a new user account as admin"""
        # Logged in as admin_user
        email = 'test3@bx.psu.edu'
        password = 'testuser'
        # Test setting the user name to one that is already taken.  Note that the account must not exist in order
        # for this test to work as desired, so the email we're passing is important...
        previously_created, username_taken, invalid_username = self.create_new_account_as_admin( email='diff@you.com',
                                                                                                 password=password,
                                                                                                 username='admin-user',
                                                                                                 redirect='' )
        if not username_taken:
            error_msg = "The public name (%s) is already being used by another user, but no error was displayed" % 'admin-user'
            raise AssertionError( error_msg )

        # Test setting the user name to an invalid one.  Note that the account must not exist in order
        # for this test to work as desired, so the email we're passing is important...
        previously_created, username_taken, invalid_username = self.create_new_account_as_admin( email='diff@you.com',
                                                                                                 password=password,
                                                                                                 username='h',
                                                                                                 redirect='' )
        if not invalid_username:
            raise AssertionError( "The public name (%s) is is invalid, but no error was displayed" % 'diff@you.com' )
        previously_created, username_taken, invalid_username = self.create_new_account_as_admin( email=email,
                                                                                                 password=password,
                                                                                                 username='regular-user3',
                                                                                                 redirect='' )
        # Get the user object for later tests
        global regular_user3
        regular_user3 = get_user( email )
        assert regular_user3 is not None, 'Problem retrieving user with email "%s" from the database' % email
        global regular_user3_private_role
        regular_user3_private_role = get_private_role( regular_user3 )
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
            role = database_contexts.galaxy_context.query( galaxy.model.Role ).get( ura.role_id )
            if not previously_created and role.type != 'private':
                raise AssertionError( 'Role created for user %s when the admin created the account is not private, type is' \
                                      % str( role.type ) )
        if not previously_created:
            # Make sure a history was not created ( previous test runs may have left deleted histories )
            histories = get_all_histories_for_user( regular_user3 )
            if histories:
                raise AssertionError( 'Histories were incorrectly created for user %s when the admin created the account' % email )
            # Make sure the user was not associated with any groups
            if regular_user3.groups:
                raise AssertionError( 'Groups were incorrectly associated with user %s when the admin created the account' % email )

    def test_010_reset_password_as_admin( self ):
        """Testing reseting a user password as admin"""
        self.reset_password_as_admin( user_id=self.security.encode_id( regular_user3.id ), password='testreset' )

    def test_015_login_after_password_reset( self ):
        """Testing logging in after an admin reset a password - tests DefaultHistoryPermissions for accounts created by an admin"""
        # logged in as admin_user
        self.logout()
        self.login( email=regular_user3.email, password='testreset' )
        # Make sure a History and HistoryDefaultPermissions exist for the user
        latest_history = get_latest_history_for_user( regular_user3 )
        if not latest_history.user_id == regular_user3.id:
            raise AssertionError( 'A history was not created for user %s when he logged in' % regular_user3.email )
        if not latest_history.default_permissions:
            raise AssertionError( 'No DefaultHistoryPermissions were created for history id %d when it was created' % latest_history.id )
        dhps = get_default_history_permissions_by_history( latest_history )
        if len( dhps ) > 1:
            raise AssertionError( 'More than 1 DefaultHistoryPermissions were created for history id %d when it was created' % latest_history.id )
        dhp = dhps[0]
        if not dhp.action == galaxy.model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
            raise AssertionError( 'The DefaultHistoryPermission.action for history id %d is "%s", but it should be "manage permissions"' \
                                  % ( latest_history.id, dhp.action ) )
        # Upload a file to create a HistoryDatasetAssociation
        self.upload_file( '1.bed' )
        latest_dataset = get_latest_dataset()
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
        self.reset_password_as_admin( user_id=self.security.encode_id( regular_user3.id ), password='testuser' )

    def test_020_mark_user_deleted( self ):
        """Testing marking a user account as deleted"""
        # Logged in as admin_user
        self.mark_user_deleted( user_id=self.security.encode_id( regular_user3.id ), email=regular_user3.email )
        if not regular_user3.active_histories:
            raise AssertionError( 'HistoryDatasetAssociations for regular_user3 were incorrectly deleted when the user was marked deleted' )

    def test_025_undelete_user( self ):
        """Testing undeleting a user account"""
        # Logged in as admin_user
        self.undelete_user( user_id=self.security.encode_id( regular_user3.id ), email=regular_user3.email )

    def test_030_create_role( self ):
        """Testing creating new role with 3 members ( and a new group named the same ), then renaming the role"""
        # Logged in as admin_user
        name = 'Role One'
        description = "This is Role Ones description"
        in_user_ids = [ str( admin_user.id ), str( regular_user1.id ), str( regular_user3.id ) ]
        in_group_ids = []
        # Add 1 to the number of associated groups since we are creating a new one with the same name as the role
        num_gras = len( in_group_ids ) + 1
        self.create_role( name=name,
                          description=description,
                          in_user_ids=in_user_ids,
                          in_group_ids=in_group_ids,
                          create_group_for_role='yes',
                          private_role=admin_user.email,
                          strings_displayed=[ "Role '%s' has been created with %d associated users and %d associated groups." % ( name, len( in_user_ids ), num_gras ),
                                              "One of the groups associated with this role is the newly created group with the same name." ] )
        # Get the role object for later tests
        global role_one
        role_one = database_contexts.galaxy_context.query( galaxy.model.Role ).filter( galaxy.model.Role.table.c.name == name ).first()
        assert role_one is not None, 'Problem retrieving role named "Role One" from the database'
        # Make sure UserRoleAssociations are correct
        if len( role_one.users ) != len( in_user_ids ):
            raise AssertionError( '%d UserRoleAssociations were created for role id %d when it was created ( should have been %d )' \
                                  % ( len( role_one.users ), role_one.id, len( in_user_ids ) ) )
        # Each of the following users should now have 2 role associations, their private role and role_one
        for user in [ admin_user, regular_user1, regular_user3 ]:
            refresh( user )
            if len( user.roles ) != 2:
                raise AssertionError( '%d UserRoleAssociations are associated with user %s ( should be 2 )' \
                                      % ( len( user.roles ), user.email ) )
        # Make sure the group was created
        self.visit_url( '%s/admin/groups' % self.url )
        self.check_page_for_string( name )
        global group_zero
        group_zero = get_group_by_name( name )
        # Rename the role
        rename = "Role One's been Renamed"
        new_description = "This is Role One's Re-described"
        self.rename_role( self.security.encode_id( role_one.id ), name=rename, description=new_description )
        self.visit_url( '%s/admin/roles' % self.url )
        self.check_page_for_string( rename )
        self.check_page_for_string( new_description )
        # Reset the role back to the original name and description
        self.rename_role( self.security.encode_id( role_one.id ), name=name, description=description )

    def test_035_create_group( self ):
        """Testing creating new group with 3 members and 2 associated roles, then renaming it"""
        # Logged in as admin_user
        name = "Group One's Name"
        in_user_ids = [ str( admin_user.id ), str( regular_user1.id ), str( regular_user3.id ) ]
        in_role_ids = [ str( role_one.id ) ]
        # The number of GroupRoleAssociations should be 2, role_one and the newly created role named 'Group One's Name'
        num_gras = len( in_role_ids ) + 1
        self.create_group( name=name,
                           in_user_ids=in_user_ids,
                           in_role_ids=in_role_ids,
                           create_role_for_group=True,
                           strings_displayed=[ "Group '%s' has been created with %d associated users and %d associated roles." % ( name, len( in_user_ids ), num_gras ),
                                               "One of the roles associated with this group is the newly created role with the same name." ] )
        # Get the group object for later tests
        global group_one
        group_one = get_group_by_name( name )
        assert group_one is not None, 'Problem retrieving group named "Group One" from the database'
        # Make sure UserGroupAssociations are correct
        if len( group_one.users ) != len( in_user_ids ):
            raise AssertionError( '%d UserGroupAssociations were created for group id %d when it was created ( should have been %d )' \
                                  % ( len( group_one.users ), group_one.id, len( in_user_ids ) ) )
        # Each user should now have 1 group association, group_one
        for user in [ admin_user, regular_user1, regular_user3 ]:
            refresh( user )
            if len( user.groups ) != 1:
                raise AssertionError( '%d UserGroupAssociations are associated with user %s ( should be 1 )' % ( len( user.groups ), user.email ) )
        # Make sure GroupRoleAssociations are correct
        if len( group_one.roles ) != num_gras:
            raise AssertionError( '%d GroupRoleAssociations were created for group id %d when it was created ( should have been %d )' \
                                  % ( len( group_one.roles ), group_one.id, num_gras ) )
        # Rename the group
        rename = "Group One's been Renamed"
        self.rename_group( self.security.encode_id( group_one.id ), name=rename, )
        self.visit_url( '%s/admin/groups' % self.url )
        self.check_page_for_string( rename )
        # Reset the group back to the original name
        self.rename_group( self.security.encode_id( group_one.id ), name=name )

    def test_040_add_members_and_role_to_group( self ):
        """Testing editing user membership and role associations of an existing group"""
        # Logged in as admin_user
        name = 'Group Two'
        self.create_group( name=name, in_user_ids=[], in_role_ids=[] )
        # Get the group object for later tests
        global group_two
        group_two = get_group_by_name( name )
        assert group_two is not None, 'Problem retrieving group named "Group Two" from the database'
        # group_two should have no associations
        if group_two.users:
            raise AssertionError( '%d UserGroupAssociations were created for group id %d when it was created ( should have been 0 )' \
                              % ( len( group_two.users ), group_two.id ) )
        if group_two.roles:
            raise AssertionError( '%d GroupRoleAssociations were created for group id %d when it was created ( should have been 0 )' \
                              % ( len( group_two.roles ), group_two.id ) )
        user_ids = [ str( regular_user1.id )  ]
        role_ids = [ str( role_one.id ) ]
        self.associate_users_and_roles_with_group( self.security.encode_id( group_two.id ),
                                                   group_two.name,
                                                   user_ids=user_ids,
                                                   role_ids=role_ids )

    def test_045_create_role_with_user_and_group_associations( self ):
        """Testing creating a role with user and group associations"""
        # Logged in as admin_user
        # NOTE: To get this to work with twill, all select lists on the ~/admin/role page must contain at least
        # 1 option value or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug in twill, we create the role, we bypass the page and visit the URL in the
        # associate_users_and_groups_with_role() method.
        name = 'Role Two'
        description = 'This is Role Two'
        user_ids = [ str( admin_user.id ) ]
        group_ids = [ str( group_two.id ) ]
        private_role = admin_user.email
        # Create the role
        self.create_role( name=name,
                          description=description,
                          in_user_ids=user_ids,
                          in_group_ids=group_ids,
                          private_role=private_role )
        # Get the role object for later tests
        global role_two
        role_two = get_role_by_name( name )
        assert role_two is not None, 'Problem retrieving role named "Role Two" from the database'
        # Make sure UserRoleAssociations are correct
        if len( role_two.users ) != len( user_ids ):
            raise AssertionError( '%d UserRoleAssociations were created for role id %d when it was created with %d members' \
                                  % ( len( role_two.users ), role_two.id, len( user_ids ) ) )
        # admin_user should now have 3 role associations, private role, role_one, role_two
        refresh( admin_user )
        if len( admin_user.roles ) != 3:
            raise AssertionError( '%d UserRoleAssociations are associated with user %s ( should be 3 )' % ( len( admin_user.roles ), admin_user.email ) )
        # Make sure GroupRoleAssociations are correct
        refresh( role_two )
        if len( role_two.groups ) != len( group_ids ):
            raise AssertionError( '%d GroupRoleAssociations were created for role id %d when it was created ( should have been %d )' \
                                  % ( len( role_two.groups ), role_two.id, len( group_ids ) ) )
        # group_two should now be associated with 2 roles: role_one, role_two
        refresh( group_two )
        if len( group_two.roles ) != 2:
            raise AssertionError( '%d GroupRoleAssociations are associated with group id %d ( should be 2 )' % ( len( group_two.roles ), group_two.id ) )

    def test_050_change_user_role_associations( self ):
        """Testing changing roles associated with a user"""
        # Logged in as admin_user
        # Create a new role with no associations
        name = 'Role Three'
        description = 'This is Role Three'
        user_ids = []
        group_ids = []
        private_role = admin_user.email
        self.create_role( name=name,
                          description=description,
                          in_user_ids=user_ids,
                          in_group_ids=group_ids,
                          private_role=private_role )
        # Get the role object for later tests
        global role_three
        role_three = get_role_by_name( name )
        assert role_three is not None, 'Problem retrieving role named "Role Three" from the database'
        # Associate the role with a user
        refresh( admin_user )
        role_ids = []
        for ura in admin_user.non_private_roles:
            role_ids.append( str( ura.role_id ) )
        role_ids.append( str( role_three.id ) )
        group_ids = []
        for uga in admin_user.groups:
            group_ids.append( str( uga.group_id ) )
        strings_displayed = [ "User '%s' has been updated with %d associated roles and %d associated groups" % \
                            ( admin_user.email, len( role_ids ), len( group_ids ) ) ]
        self.manage_roles_and_groups_for_user( self.security.encode_id( admin_user.id ),
                                               in_role_ids=role_ids,
                                               in_group_ids=group_ids,
                                               strings_displayed=strings_displayed )
        refresh( admin_user )
        # admin_user should now be associated with 4 roles: private, role_one, role_two, role_three
        if len( admin_user.roles ) != 4:
            raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 4 )' % \
                                  ( len( admin_user.roles ), admin_user.email ) )

    def test_055_mark_group_deleted( self ):
        """Testing marking a group as deleted"""
        # Logged in as admin_user
        self.browse_groups( strings_displayed=[ group_two.name ] )
        self.mark_group_deleted( self.security.encode_id( group_two.id ), group_two.name )
        refresh( group_two )
        if not group_two.deleted:
            raise AssertionError( '%s was not correctly marked as deleted.' % group_two.name )
        # Deleting a group should not delete any associations
        if not group_two.members:
            raise AssertionError( '%s incorrectly lost all members when it was marked as deleted.' % group_two.name )
        if not group_two.roles:
            raise AssertionError( '%s incorrectly lost all role associations when it was marked as deleted.' % group_two.name )

    def test_060_undelete_group( self ):
        """Testing undeleting a deleted group"""
        # Logged in as admin_user
        self.undelete_group( self.security.encode_id( group_two.id ), group_two.name )
        refresh( group_two )
        if group_two.deleted:
            raise AssertionError( '%s was not correctly marked as not deleted.' % group_two.name )

    def test_065_mark_role_deleted( self ):
        """Testing marking a role as deleted"""
        # Logged in as admin_user
        self.browse_roles( strings_displayed=[ role_two.name ] )
        self.mark_role_deleted( self.security.encode_id( role_two.id ), role_two.name )
        refresh( role_two )
        if not role_two.deleted:
            raise AssertionError( '%s was not correctly marked as deleted.' % role_two.name )
        # Deleting a role should not delete any associations
        if not role_two.users:
            raise AssertionError( '%s incorrectly lost all user associations when it was marked as deleted.' % role_two.name )
        if not role_two.groups:
            raise AssertionError( '%s incorrectly lost all group associations when it was marked as deleted.' % role_two.name )

    def test_070_undelete_role( self ):
        """Testing undeleting a deleted role"""
        # Logged in as admin_user
        self.undelete_role( self.security.encode_id( role_two.id ), role_two.name )

    def test_075_purge_user( self ):
        """Testing purging a user account"""
        # Logged in as admin_user
        self.mark_user_deleted( user_id=self.security.encode_id( regular_user3.id ), email=regular_user3.email )
        refresh( regular_user3 )
        self.purge_user( self.security.encode_id( regular_user3.id ), regular_user3.email )
        refresh( regular_user3 )
        if not regular_user3.purged:
            raise AssertionError( 'User %s was not marked as purged.' % regular_user3.email )
        # Make sure DefaultUserPermissions deleted EXCEPT FOR THE PRIVATE ROLE
        if len( regular_user3.default_permissions ) != 1:
            raise AssertionError( 'DefaultUserPermissions for user %s were not deleted.' % regular_user3.email )
        for dup in regular_user3.default_permissions:
            role = database_contexts.galaxy_context.query( galaxy.model.Role ).get( dup.role_id )
            if role.type != 'private':
                raise AssertionError( 'DefaultUserPermissions for user %s are not related with the private role.' % regular_user3.email )
        # Make sure History deleted
        for history in regular_user3.histories:
            refresh( history )
            if not history.deleted:
                raise AssertionError( 'User %s has active history id %d after their account was marked as purged.' % ( regular_user3.email, history.id ) )
            # NOTE: Not all hdas / datasets will be deleted at the time a history is deleted - the cleanup_datasets.py script
            # is responsible for this.
        # Make sure UserGroupAssociations deleted
        if regular_user3.groups:
            raise AssertionError( 'User %s has active group after their account was marked as purged.' % ( regular_user3.email ) )
        # Make sure UserRoleAssociations deleted EXCEPT FOR THE PRIVATE ROLE
        if len( regular_user3.roles ) != 1:
            raise AssertionError( 'UserRoleAssociations for user %s were not deleted.' % regular_user3.email )
        for ura in regular_user3.roles:
            role = database_contexts.galaxy_context.query( galaxy.model.Role ).get( ura.role_id )
            if role.type != 'private':
                raise AssertionError( 'UserRoleAssociations for user %s are not related with the private role.' % regular_user3.email )

    def test_080_manually_unpurge_user( self ):
        """Testing manually un-purging a user account"""
        # Logged in as admin_user
        # Reset the user for later test runs.  The user's private Role and DefaultUserPermissions for that role
        # should have been preserved, so all we need to do is reset purged and deleted.
        # TODO: If we decide to implement the GUI feature for un-purging a user, replace this with a method call
        regular_user3.purged = False
        regular_user3.deleted = False
        flush( regular_user3 )

    def test_085_purge_group( self ):
        """Testing purging a group"""
        # Logged in as admin_user
        self.mark_group_deleted( self.security.encode_id( group_two.id ), group_two.name )
        self.purge_group( self.security.encode_id( group_two.id ), group_two.name )
        # Make sure there are no UserGroupAssociations
        if get_user_group_associations_by_group( group_two ):
            raise AssertionError( "Purging the group did not delete the UserGroupAssociations for group_id '%s'" % group_two.id )
        # Make sure there are no GroupRoleAssociations
        if get_group_role_associations_by_group( group_two ):
            raise AssertionError( "Purging the group did not delete the GroupRoleAssociations for group_id '%s'" % group_two.id )
        # Undelete the group for later test runs
        self.undelete_group( self.security.encode_id( group_two.id ), group_two.name )

    def test_090_purge_role( self ):
        """Testing purging a role"""
        # Logged in as admin_user
        self.mark_role_deleted( self.security.encode_id( role_two.id ), role_two.name )
        self.purge_role( self.security.encode_id( role_two.id ), role_two.name )
        # Make sure there are no UserRoleAssociations
        if get_user_role_associations_by_role( role_two ):
            raise AssertionError( "Purging the role did not delete the UserRoleAssociations for role_id '%s'" % role_two.id )
        # Make sure there are no DefaultUserPermissions associated with the Role
        if get_default_user_permissions_by_role( role_two ):
            raise AssertionError( "Purging the role did not delete the DefaultUserPermissions for role_id '%s'" % role_two.id )
        # Make sure there are no DefaultHistoryPermissions associated with the Role
        if get_default_history_permissions_by_role( role_two ):
            raise AssertionError( "Purging the role did not delete the DefaultHistoryPermissions for role_id '%s'" % role_two.id )
        # Make sure there are no GroupRoleAssociations
        if get_group_role_associations_by_role( role_two ):
            raise AssertionError( "Purging the role did not delete the GroupRoleAssociations for role_id '%s'" % role_two.id )
        # Make sure there are no DatasetPermissionss
        if get_dataset_permissions_by_role( role_two ):
            raise AssertionError( "Purging the role did not delete the DatasetPermissionss for role_id '%s'" % role_two.id )

    def test_095_manually_unpurge_role( self ):
        """Testing manually un-purging a role"""
        # Logged in as admin_user
        # Manually unpurge, then undelete the role for later test runs
        # TODO: If we decide to implement the GUI feature for un-purging a role, replace this with a method call
        role_two.purged = False
        flush( role_two )
        self.undelete_role( self.security.encode_id( role_two.id ), role_two.name )

    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as admin_user
        ##################
        # Eliminate all non-private roles
        ##################
        for role in [ role_one, role_two, role_three ]:
            self.mark_role_deleted( self.security.encode_id( role.id ), role.name )
            self.purge_role( self.security.encode_id( role.id ), role.name )
            # Manually delete the role from the database
            refresh( role )
            database_contexts.galaxy_context.delete( role )
            database_contexts.galaxy_context.flush()
        ##################
        # Eliminate all groups
        ##################
        for group in [ group_zero, group_one, group_two ]:
            self.mark_group_deleted( self.security.encode_id( group.id ), group.name )
            self.purge_group( self.security.encode_id( group.id ), group.name )
            # Manually delete the group from the database
            refresh( group )
            database_contexts.galaxy_context.delete( group )
            database_contexts.galaxy_context.flush()
        ##################
        # Make sure all users are associated only with their private roles
        ##################
        for user in [ admin_user, regular_user1, regular_user2, regular_user3 ]:
            refresh( user )
            if len( user.roles) != 1:
                raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 1 )' % ( len( user.roles ), user.email ) )
