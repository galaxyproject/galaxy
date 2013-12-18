from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os

import logging
log = logging.getLogger( __name__ )

category_name = 'Test 0450 Skip Tool Tests'
category_description = 'Test 0450 Skip Tool Tests'
repository_name = 'filtering_0450'
repository_description = "Galaxy's filtering tool for test 0450"
repository_long_description = "Long description of Galaxy's filtering tool for test 0450"
first_metadata_revision = None

'''
1)  Create and populate a repository so that it has a single metadata revision.
 
2)  Visit the Manage repository page and check the "Skip tool tests for this revision" checkbox
    and enter some text in the reason.

3)  Upload a README file to the repository so that the original metadata revision is moved upward
    in the changelog ( do not upload anything that will create a new metadata revision ).

4)  Visit the Manage repository page again, the checked "Skip tool tests" checkbox and the reason
    should still be displayed since it should now be associated with this metadata revision.

5)  Upload a new version of the tool to the repository so that a new metadata changeset revision
    is created (there should now be 3 revisions with 2 of them having associated metadata).

6)  Visit the Manage repository page for the tip revision - the Skip tools tests checkbox should
    not be checked and the reason should be empty.

7)  Visit the Manage repository page for the previous metadata revision (with the README file in it).
    The Skip tool tests checkbox should still be checked and the reason should be there.

8)  Set the skip setting on the new metadata revision.

9)  Upload a readme file to the repository again, and verify that the skip setting is updated.

10) Check the first revision, make sure the skip reason matches.

11) Check the second revision, make sure the skip reason matches.

13) Uncheck the checkbox for the first revision, and verify that the skip reason is no longer displayed.

14) Uncheck the checkbox for the second revision, and verify that the skip reason is no longer displayed.
'''


class TestSkipToolTestFeature( ShedTwillTestCase ):
    '''Test core repository features.'''
    
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        test_user_2_private_role = self.test_db_util.get_private_role( test_user_2 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
        
    def test_0005_create_repository( self ):
        '''Create and populate the filtering repository'''
        '''
        This is step 1 - Create and populate a repository so that it has a single metadata revision.
        '''
        self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.test_db_util.get_category_by_name( category_name )
        strings_displayed = [ 'Repository %s' % "'%s'" % repository_name, 
                              'Repository %s has been created' % "<b>%s</b>" % repository_name ]
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=strings_displayed )
        self.upload_file( repository, 
                          filename='filtering/filtering_1.1.0.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate filtering_0450 with version 1.1.0',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
    
    def test_0010_set_skip_tool_tests_flag( self ):
        '''Set the skip tool tests flag on filtering_0450.'''
        '''
        This is step 2 - Visit the Manage repository page and check the "Skip tool tests for this revision" checkbox and 
        enter some text in the reason.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.set_skip_tool_tsts_flag( repository=repository, flag_value=True, reason='Skip reason for first revision.' )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Skip reason for first revision.' ] )
        
    def test_0015_upload_readme_file( self ):
        '''Upload readme.txt to the filtering_0450 repository.'''
        '''
        This is step 3 - Upload a README file to the repository so that the original metadata revision is moved
        upward in the changelog. This should result in the skip_tool_tests setting being applied to the updated
        metadata revision.
        '''
        global first_metadata_revision
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          filename='filtering/readme.txt', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Add a readme file.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        first_metadata_revision = self.get_repository_tip( repository )
    
    def test_0020_verify_skip_on_new_revision( self ):
        '''Check that the skip tool tests setting was updated.'''
        '''
        This is step 4 - Visit the Manage repository page again, the checked "Skip tool tests" checkbox and
        the reason should still be displayed since it should now be associated with this metadata revision.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Skip reason for first revision.' ] )
        self.load_checkable_revisions( strings_not_displayed=[ self.get_repository_tip( repository ) ] )
        
    def test_0025_upload_new_tool_version( self ):
        '''Upload filtering 2.2.0.'''
        '''
        This is step 5 - Upload a new version of the tool to the repository so that a new metadata changeset
        revision is created (there should now be 3 revisions with 2 of them having associated metadata).
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          filename='filtering/filtering_2.2.0.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Upload the filtering 2.2.0 tarball.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        
    def test_0030_verify_skip_not_set( self ):
        '''Verify that skip tool tests is not set for the new metadata revision.'''
        '''
        This is step 6 - Visit the Manage repository page for the tip revision - the Skip tools tests checkbox
        should not be checked and the reason should be empty.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.load_checkable_revisions( strings_displayed=[ self.get_repository_tip( repository ) ] )
        self.display_manage_repository_page( repository, strings_not_displayed=[ 'Skip reason for first revision.' ] )
        
    def test_0045_verify_previous_revision_skip_setting( self ):
        '''Check that the previous metadata revision is still set to skip tool tests.'''
        '''
        This is step 7 - Visit the Manage repository page for the previous metadata revision (with the README
        file in it). The Skip tool tests checkbox should still be checked and the reason should be there.
        '''
        global first_metadata_revision
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.load_checkable_revisions( strings_not_displayed=[ first_metadata_revision ] )
        self.display_manage_repository_page( repository, 
                                             changeset_revision=first_metadata_revision, 
                                             strings_displayed=[ 'Skip reason for first revision.' ] )
        
    def test_0050_set_new_revision_not_to_be_tested( self ):
        '''Set the new changeset to skip tests.'''
        '''
        This is step 8 - Set the skip setting on the new metadata revision.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.set_skip_tool_tsts_flag( repository=repository, flag_value=True, reason='Skip reason for second revision.' )
        self.load_checkable_revisions( strings_not_displayed=[ self.get_repository_tip( repository ) ] )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Skip reason for second revision.' ] )
        
    def test_0060_upload_another_readme_file( self ):
        '''Upload readme.txt to the filtering_0450 repository.'''
        '''
        This is step 9 - Upload a README file to the repository so that the original metadata revision is moved
        upward in the changelog. This should result in the skip_tool_tests setting being applied to the updated
        metadata revision.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          filename='filtering/README', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Add a readme file.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        self.display_manage_repository_page( repository, 
                                             strings_displayed=[ 'Skip reason for second revision.' ] )
        self.load_checkable_revisions( strings_not_displayed=[ self.get_repository_tip( repository ) ] )
        
    def test_0065_verify_skip_setting_on_first_changeset( self ):
        '''Verify that the first changeset only displays its own skip reason.'''
        '''
        This is step 10 - Check the first revision, make sure the skip reason matches.
        '''
        global first_metadata_revision
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.display_manage_repository_page( repository, 
                                             changeset_revision=first_metadata_revision,
                                             strings_displayed=[ 'Skip reason for first revision.' ],
                                             strings_not_displayed=[ 'Skip reason for second revision.' ] )
        
    def test_0065_verify_skip_setting_on_second_changeset( self ):
        '''Verify that the second changeset only displays its own skip reason.'''
        '''
        This is step 12 - Check the second revision, make sure the skip reason matches.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.display_manage_repository_page( repository, 
                                             strings_displayed=[ 'Skip reason for second revision.' ],
                                             strings_not_displayed=[ 'Skip reason for first revision.' ] )
        
    def test_0070_unset_skip_setting_on_first_revision( self ):
        '''Set the first revision not to skip tests, verify setting.'''
        '''
        This is step 13 - Uncheck the checkbox for the first revision, and verify that the skip reason is no longer displayed.
        '''
        global first_metadata_revision
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.set_skip_tool_tsts_flag( repository=repository, flag_value=False, reason='', changeset_revision=first_metadata_revision )
        self.display_manage_repository_page( repository, 
                                             changeset_revision=first_metadata_revision,
                                             strings_not_displayed=[ 'Skip reason for second revision.', 'Skip reason for first revision.' ] )
        self.load_checkable_revisions( strings_displayed=[ first_metadata_revision ] )
        
    def test_0075_unset_skip_setting_on_second_revision( self ):
        '''Set the second revision not to skip tests, verify setting.'''
        '''
        This is step 14 - Uncheck the checkbox for the second revision, and verify that the skip reason is no longer displayed.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.set_skip_tool_tsts_flag( repository=repository, flag_value=False, reason='' )
        self.display_manage_repository_page( repository, 
                                             strings_not_displayed=[ 'Skip reason for second revision.', 'Skip reason for first revision.' ] )
        self.load_checkable_revisions( strings_displayed=[ self.get_repository_tip( repository ) ] )
        
