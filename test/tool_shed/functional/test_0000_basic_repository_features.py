from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

repository_name = 'filtering_0000'
repository_description = "Galaxy's filtering tool for test 0000"
repository_long_description = "Long description of Galaxy's filtering tool for test 0000"

class TestBasicRepositoryFeatures( ShedTwillTestCase ):
 
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        test_user_1_private_role = test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
    def test_0005_create_categories( self ):
        """Create categories for this test suite"""
        self.create_category( name='Test 0000 Basic Repository Features 1', description='Test 0000 Basic Repository Features 1' )
        self.create_category( name='Test 0000 Basic Repository Features 2', description='Test 0000 Basic Repository Features 2' )
    def test_0010_create_repository( self ):
        """Create the filtering repository"""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = test_db_util.get_category_by_name( 'Test 0000 Basic Repository Features 1' )
        strings_displayed = [ 'Repository %s' % "'%s'" % repository_name, 
                              'Repository %s has been created' % "'%s'" % repository_name ]
        self.get_or_create_repository( name=repository_name, 
                                       description=repository_description, 
                                       long_description=repository_long_description, 
                                       owner=common.test_user_1_name,
                                       category_id=self.security.encode_id( category.id ), 
                                       strings_displayed=strings_displayed )
    def test_0015_edit_repository( self ):
        """Edit the repository name, description, and long description"""
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        new_name = "renamed_filtering"
        new_description = "Edited filtering tool"
        new_long_description = "Edited long description"
        self.edit_repository_information( repository, repo_name=new_name, description=new_description, long_description=new_long_description )
    def test_0020_change_repository_category( self ):
        """Change the categories associated with the filtering repository"""
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.edit_repository_categories( repository, 
                                         categories_to_add=[ "Test 0000 Basic Repository Features 2" ], 
                                         categories_to_remove=[ "Test 0000 Basic Repository Features 1" ] )
    def test_0025_grant_write_access( self ):
        '''Grant write access to another user'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.grant_write_access( repository, usernames=[ common.admin_username ] )
        self.revoke_write_access( repository, common.admin_username )
    def test_0030_upload_filtering_1_1_0( self ):
        """Upload filtering_1.1.0.tar to the repository"""
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 'filtering/filtering_1.1.0.tar', commit_message="Uploaded filtering 1.1.0" )
    def test_0035_verify_repository( self ):
        '''Display basic repository pages'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        latest_changeset_revision = self.get_repository_tip( repository )
        self.check_for_valid_tools( repository, strings_displayed=[ 'Filter1' ] )
        self.check_count_of_metadata_revisions_associated_with_repository( repository, metadata_count=1 )
        tip = self.get_repository_tip( repository )
        self.check_repository_tools_for_changeset_revision( repository, tip )
        self.check_repository_metadata( repository, tip_only=False )
        self.browse_repository( repository, strings_displayed=[ 'Browse %s revision' % repository.name, '(repository tip)' ] )
        self.display_repository_clone_page( common.test_user_1_name, 
                                            repository_name, 
                                            strings_displayed=[ 'Uploaded filtering 1.1.0', latest_changeset_revision ] )
    def test_0040_alter_repository_states( self ):
        '''Test toggling the malicious and deprecated repository flags.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        self.set_repository_malicious( repository, set_malicious=True, strings_displayed=[ 'The repository tip has been defined as malicious.' ] )
        self.set_repository_malicious( repository, 
                                       set_malicious=False, 
                                       strings_displayed=[ 'The repository tip has been defined as <b>not</b> malicious.' ] )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        self.set_repository_deprecated( repository, 
                                        strings_displayed=[ 'has been marked as deprecated', 'Mark as not deprecated' ] )
        self.display_manage_repository_page( repository, 
                                strings_displayed=[ 'This repository has been marked as deprecated' ],
                                strings_not_displayed=[ 'Upload files', 'Reset all repository metadata' ] )
        self.browse_repository( repository, strings_not_displayed=[ 'Upload files' ] )
        self.set_repository_deprecated( repository, 
                                        strings_displayed=[ 'has been marked as not deprecated', 'Mark as deprecated' ],
                                        set_deprecated=False )
    def test_0045_display_repository_tip_file( self ):
        '''Display the contents of filtering.xml in the repository tip revision'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.display_repository_file_contents( repository=repository,
                                               filename='filtering.xml',
                                               filepath=None,
                                               strings_displayed=[ '1.1.0' ],
                                               strings_not_displayed=[] )
    def test_0050_upload_filtering_txt_file( self ):
        '''Upload filtering.txt file associated with tool version 1.1.0.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          'filtering/filtering_0000.txt', 
                          commit_message="Uploaded filtering.txt", 
                          uncompress_file='No', 
                          remove_repo_files_not_in_tar='No' )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Readme file for filtering 1.1.0' ] )
    def test_0055_upload_filtering_test_data( self ):
        '''Upload filtering test data.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 'filtering/filtering_test_data.tar', commit_message="Uploaded filtering test data", remove_repo_files_not_in_tar='No' )
        self.display_repository_file_contents( repository=repository,
                                               filename='1.bed',
                                               filepath='test-data',
                                               strings_displayed=[],
                                               strings_not_displayed=[] )
        self.check_repository_metadata( repository, tip_only=True )
    def test_0060_upload_filtering_2_2_0( self ):
        '''Upload filtering version 2.2.0'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          'filtering/filtering_2.2.0.tar', 
                          commit_message="Uploaded filtering 2.2.0", 
                          remove_repo_files_not_in_tar='No' )
    def test_0065_verify_filtering_repository( self ):
        '''Verify the new tool versions and repository metadata.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        tip = self.get_repository_tip( repository )
        self.check_for_valid_tools( repository )
        strings_displayed = self.get_repository_metadata_revisions( repository ).append( 'Select a revision' )
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.check_count_of_metadata_revisions_associated_with_repository( repository, metadata_count=2 )
        self.check_repository_tools_for_changeset_revision( repository, tip )
        self.check_repository_metadata( repository, tip_only=False )
    def test_0070_upload_readme_txt_file( self ):
        '''Upload readme.txt file associated with tool version 2.2.0.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 'readme.txt', commit_message="Uploaded readme.txt" )
        self.display_manage_repository_page( repository, strings_displayed=[ 'This is a readme file.' ] )
        # Verify that there is a different readme file for each metadata revision.
        metadata_revisions = self.get_repository_metadata_revisions( repository )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Readme file for filtering 1.1.0', 'This is a readme file.' ] )
    def test_0075_delete_readme_txt_file( self ):
        '''Delete the readme.txt file.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.delete_files_from_repository( repository, filenames=[ 'readme.txt' ] )
        self.check_count_of_metadata_revisions_associated_with_repository( repository, metadata_count=2 )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Readme file for filtering 1.1.0' ] )
    def test_0080_search_for_valid_filter_tool( self ):
        '''Search for the filtering tool by tool ID, name, and version.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        tip_changeset = self.get_repository_tip( repository )
        search_fields = dict( tool_id='Filter1', tool_name='filter', tool_version='2.2.0' )
        self.search_for_valid_tools( search_fields=search_fields, strings_displayed=[ tip_changeset ], strings_not_displayed=[] )
    def test_0085_verify_repository_metadata( self ):
        '''Verify that resetting the metadata does not change it.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.verify_unchanged_repository_metadata( repository )
