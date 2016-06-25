import logging

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

log = logging.getLogger( __name__ )

repository_name = 'filtering_0530'
repository_description = 'Filtering repository for test 0530'
repository_long_description = 'This is the filtering repository for test 0530.'
category_name = 'Test 0530 Repository Admin Role'
category_description = 'Verify the functionality of the code that handles the repository admin role.'

'''
1. Create new repository as user user1.

2. Check to make sure a new role was created named <repo_name>_user1_admin.

3. Check to make sure a new repository_role_association record was created with appropriate repository id and role id.

4. Change the name of the repository created in step 1 - this can be done as long as the repository has not been installed or cloned.

5. Make sure the name of the role initially inspected in Step 2 has been changed to reflect the new repository name from Step 4.

6. Log into the Tool Shed as a user that is not the repository owner (e.g., user2) and make sure the repository name
   and description cannot be changed.

7. As user user1, add user user2 as a repository admin user.

8. Log into the Tool Shed as user user2 and make sure the repository name and description can now be changed.
'''


class TestRepositoryAdminRole( ShedTwillTestCase ):
    '''Verify that the code correctly handles the repository admin role.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        self.test_db_util.get_private_role( test_user_2 )
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )

    def test_0005_create_filtering_repository( self ):
        """Create and populate the filtering_0530 repository."""
        '''
        This is step 1 - Create new repository as user user1.
        '''
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=repository_name,
                                                    description=repository_description,
                                                    long_description=repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        self.upload_file( repository,
                          filename='filtering/filtering_1.1.0.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded filtering 1.1.0 tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0010_verify_repository_admin_role_exists( self ):
        '''Verify that the role filtering_0530_user1_admin exists.'''
        '''
        This is step 2 - Check to make sure a new role was created named filtering_0530_user1_admin.
        '''
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        repository_admin_role = self.test_db_util.get_role( test_user_1, 'filtering_0530_user1_admin' )
        assert repository_admin_role is not None, 'Admin role for filtering_0530 was not created.'

    def test_0015_verify_repository_role_association( self ):
        '''Verify that the filtering_0530_user1_admin role is associated with the filtering_0530 repository.'''
        '''
        This is step 3 - Check to make sure a new repository_role_association record was created with appropriate repository id and role id.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        repository_admin_role = self.test_db_util.get_role( test_user_1, 'filtering_0530_user1_admin' )
        repository_role_association = self.test_db_util.get_repository_role_association( repository.id, repository_admin_role.id )
        assert repository_role_association is not None, 'Repository filtering_0530 is not associated with the filtering_0530_user1_admin role.'

    def test_0020_rename_repository( self ):
        '''Rename the repository to renamed_filtering_0530.'''
        '''
        This is step 4 - Change the name of the repository created in step 1 - this can be done as long as the repository has not
        been installed or cloned.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.edit_repository_information( repository, revert=False, repo_name='renamed_filtering_0530' )
        self.test_db_util.refresh( repository )
        assert repository.name == 'renamed_filtering_0530', 'Repository was not renamed to renamed_filtering_0530.'

    def test_0025_check_admin_role_name( self ):
        return
        '''Check that a role renamed_filtering_0530_user1_admin now exists, and filtering_0530_user1_admin does not.'''
        '''
        This is step 5 - Make sure the name of the role initially inspected in Step 2 has been changed to reflect the
        new repository name from Step 4.
        '''
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        old_repository_admin_role = self.test_db_util.get_role( test_user_1, 'filtering_0530_%s_admin' % test_user_1.username )
        assert old_repository_admin_role is None, 'Admin role filtering_0530_user1_admin incorrectly exists.'
        new_repository_admin_role = self.test_db_util.get_role( test_user_1, 'renamed_filtering_0530_%s_admin' % test_user_1.username )
        assert new_repository_admin_role is not None, 'Admin role renamed_filtering_0530_user1_admin does not exist.'

    def test_0030_verify_access_denied( self ):
        '''Make sure a non-admin user can't modify the repository.'''
        '''
        This is step 6 - Log into the Tool Shed as a user that is not the repository owner (e.g., user2) and make sure the repository
        name and description cannot be changed.
        '''
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( 'renamed_filtering_0530', common.test_user_1_name )
        strings_not_displayed = [ 'Manage repository' ]
        strings_displayed = [ 'View repository' ]
        self.display_manage_repository_page( repository, strings_not_displayed=strings_not_displayed )
        self.submit_form( button='edit_repository_button', description='This description has been modified.' )
        strings_displayed = [ 'You are not the owner of this repository, so you cannot administer it.' ]
        strings_not_displayed = [ 'The repository information has been updated.' ]
        self.check_for_strings( strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )

    def test_0035_grant_admin_role( self ):
        '''Grant the repository admin role to user2.'''
        '''
        This is step 7 - As user user1, add user user2 as a repository admin user.
        '''
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        repository = self.test_db_util.get_repository_by_name_and_owner( 'renamed_filtering_0530', common.test_user_1_name )
        self.assign_admin_role( repository, test_user_2 )

    def test_0040_rename_repository_as_repository_admin( self ):
        '''Rename the repository as user2.'''
        '''
        This is step 8 - Log into the Tool Shed as user user2 and make sure the repository name and description can now be changed.
        '''
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        repository = self.test_db_util.get_repository_by_name_and_owner( 'renamed_filtering_0530', common.test_user_1_name )
        self.edit_repository_information( repository, revert=False, repo_name='filtering_0530' )
        self.test_db_util.refresh( repository )
        assert repository.name == 'filtering_0530', 'User with admin role failed to rename repository.'
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        old_repository_admin_role = self.test_db_util.get_role( test_user_1, 'renamed_filtering_0530_user1_admin' )
        assert old_repository_admin_role is None, 'Admin role renamed_filtering_0530_user1_admin incorrectly exists.'
        new_repository_admin_role = self.test_db_util.get_role( test_user_1, 'filtering_0530_user1_admin' )
        assert new_repository_admin_role is not None, 'Admin role filtering_0530_user1_admin does not exist.'
