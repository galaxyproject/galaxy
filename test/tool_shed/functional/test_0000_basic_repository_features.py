from tool_shed.base.twilltestcase import *
from tool_shed.base.test_db_util import *

admin_user = None
admin_user_private_role = None
admin_email = 'test@bx.psu.edu'
admin_username = 'admin-user'

regular_user = None
regular_user_private_role = None
regular_email = 'test-1@bx.psu.edu'
regular_username = 'user1'

repository_name = 'filtering'
repository_description = "Galaxy's filtering tool"
repository_long_description = "Long description of Galaxy's filtering tool"

class TestBasicRepositoryFeatures( ShedTwillTestCase ):
 
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.login( email=regular_email, username=regular_username )
        regular_user = get_user( regular_email )
        assert regular_user is not None, 'Problem retrieving user with email %s from the database' % regular_email
        regular_user_private_role = get_private_role( regular_user )
        self.logout()
        self.login( email=admin_email, username=admin_username )
        admin_user = get_user( admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = get_private_role( admin_user )
    def test_0005_create_categories( self ):
        """Create categories"""
        self.create_category( 'Text Manipulation', 'Tools for manipulating text' )
        self.create_category( 'Text Analysis', 'Tools for analyzing text' )
    def test_0010_create_repository( self ):
        """Create the filtering repository"""
        strings_displayed = [ 'Repository %s' % "'%s'" % repository_name, 
                              'Repository %s has been created' % "'%s'" % repository_name ]
        self.create_repository( repository_name, 
                                repository_description, 
                                repository_long_description=repository_long_description, 
                                categories=[ 'Text Manipulation' ], 
                                strings_displayed=strings_displayed )
    def test_0015_edit_repository( self ):
        """Edit the repository name, description, and long description"""
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        new_name = "renamed_filtering"
        new_description = "Edited filtering tool"
        new_long_description = "Edited long description"
        self.edit_repository_information( repository, repo_name=new_name, description=new_description, long_description=new_long_description )
    def test_0020_change_repository_category( self ):
        """Change the categories associated with the filtering repository"""
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.edit_repository_categories( repository, categories_to_add=[ "Text Analysis" ], categories_to_remove=[ "Text Manipulation" ] )
    def test_0025_grant_write_access( self ):
        '''Grant write access to another user'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.grant_write_access( repository, usernames=[ regular_username ] )
        self.revoke_write_access( repository, regular_username )
    def test_0030_upload_filtering_1_1_0( self ):
        """Upload filtering_1.1.0.tar to the repository"""
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 'filtering_1.1.0.tar', commit_message="Uploaded filtering 1.1.0" )
    def test_0035_verify_repository( self ):
        '''Display basic repository pages'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        latest_changeset_revision = self.get_repository_tip( repository )
        self.check_for_valid_tools( repository, strings_displayed=[ 'Filter1' ] )
        self.check_count_of_metadata_revisions_associated_with_repository( repository, metadata_count=1 )
        tip = self.get_repository_tip( repository )
        self.check_repository_tools_for_changeset_revision( repository, tip )
        self.check_repository_metadata( repository, tip_only=False )
        self.browse_repository( repository, strings_displayed=[ 'Browse %s revision' % repository.name, '(repository tip)' ] )
        self.display_repository_clone_page( admin_username, 
                                            repository_name, 
                                            strings_displayed=[ 'Uploaded filtering 1.1.0', latest_changeset_revision ] )
    def test_0040_alter_repository_states( self ):
        '''Test toggling the malicious and deprecated repository flags.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.set_repository_malicious( repository, set_malicious=True, strings_displayed=[ 'The repository tip has been defined as malicious.' ] )
        self.set_repository_malicious( repository, 
                                       set_malicious=False, 
                                       strings_displayed=[ 'The repository tip has been defined as <b>not</b> malicious.' ] )
        self.set_repository_deprecated( repository, 
                                        strings_displayed=[ 'has been marked as deprecated', 'Mark as not deprecated' ] )
        self.manage_repository( repository, 
                                strings_displayed=[ 'This repository has been marked as deprecated' ],
                                strings_not_displayed=[ 'Upload files', 'Reset all repository metadata' ] )
        self.set_repository_deprecated( repository, 
                                        strings_displayed=[ 'has been marked as not deprecated', 'Mark as deprecated' ],
                                        set_deprecated=False )
    def test_0045_display_repository_tip_file( self ):
        '''Display the contents of filtering.xml in the repository tip revision'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.display_repository_file_contents( repository=repository,
                                               filename='filtering.xml',
                                               filepath=None,
                                               strings_displayed=[ '1.1.0' ],
                                               strings_not_displayed=[] )
    def test_0050_upload_filtering_txt_file( self ):
        '''Upload filtering.txt file associated with tool version 1.1.0.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 
                          'filtering.txt', 
                          commit_message="Uploaded filtering.txt", 
                          uncompress_file='No', 
                          remove_repo_files_not_in_tar='No' )
        self.manage_repository( repository, strings_displayed=[ 'Readme file for filtering 1.1.0' ] )
    def test_0055_upload_filtering_test_data( self ):
        '''Upload filtering test data.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 'filtering_test_data.tar', commit_message="Uploaded filtering test data", remove_repo_files_not_in_tar='No' )
        self.display_repository_file_contents( repository=repository,
                                               filename='1.bed',
                                               filepath='test-data',
                                               strings_displayed=[],
                                               strings_not_displayed=[] )
        self.check_repository_metadata( repository, tip_only=True )
    def test_0060_upload_filtering_2_2_0( self ):
        '''Upload filtering version 2.2.0'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 
                          'filtering_2.2.0.tar', 
                          commit_message="Uploaded filtering 2.2.0", 
                          remove_repo_files_not_in_tar='No' )
    def test_0065_verify_filtering_repository( self ):
        '''Verify the new tool versions and repository metadata.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        tip = self.get_repository_tip( repository )
        self.check_for_valid_tools( repository )
        strings_displayed = self.get_repository_metadata_revisions( repository ).append( 'Select a revision' )
        self.manage_repository( repository, strings_displayed=strings_displayed )
        self.check_count_of_metadata_revisions_associated_with_repository( repository, metadata_count=2 )
        self.check_repository_tools_for_changeset_revision( repository, tip )
        self.check_repository_metadata( repository, tip_only=False )
    def test_0070_upload_readme_txt_file( self ):
        '''Upload readme.txt file associated with tool version 2.2.0.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 'readme.txt', commit_message="Uploaded readme.txt" )
        self.manage_repository( repository, strings_displayed=[ 'This is a readme file.' ] )
        # Verify that there is a different readme file for each metadata revision.
        metadata_revisions = self.get_repository_metadata_revisions( repository )
        self.manage_repository( repository, strings_displayed=[ 'Readme file for filtering 1.1.0', 'This is a readme file.' ] )
    def test_0075_delete_readme_txt_file( self ):
        '''Delete the readme.txt file.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.delete_files_from_repository( repository, filenames=[ 'readme.txt' ] )
        self.check_count_of_metadata_revisions_associated_with_repository( repository, metadata_count=2 )
        self.manage_repository( repository, strings_displayed=[ 'Readme file for filtering 1.1.0' ] )
    def test_0080_search_for_valid_filter_tool( self ):
        '''Verify that the "search for valid tool" feature finds the filtering tool.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        tip_changeset = self.get_repository_tip( repository )
        search_options = dict( tool_id='Filter1', tool_name='filter', tool_version='2.2.0' )
        self.search_for_valid_tools( search_options=search_options, strings_displayed=[ tip_changeset ], strings_not_displayed=[] )
