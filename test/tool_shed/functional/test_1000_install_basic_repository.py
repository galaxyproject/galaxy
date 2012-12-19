from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

class BasicToolShedFeatures( ShedTwillTestCase ):
    '''Test installing a basic repository.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        galaxy_admin_user = test_db_util.get_galaxy_user( common.admin_email )
        assert galaxy_admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        galaxy_admin_user_private_role = test_db_util.get_galaxy_private_role( galaxy_admin_user )
    def test_0005_ensure_repositories_and_categories_exist( self ):
        '''Create the 0000 category and upload the filtering repository to it, if necessary.'''
        category = self.create_category( name='Test 0000 Basic Repository Features 1', description='Test 0000 Basic Repository Features 1' )
        self.create_category( name='Test 0000 Basic Repository Features 2', description='Test 0000 Basic Repository Features 2' )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name='filtering_0000', 
                                                    description="Galaxy's filtering tool", 
                                                    long_description="Long description of Galaxy's filtering tool", 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ) )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 'filtering/filtering_1.1.0.tar', commit_message="Uploaded filtering 1.1.0" )
            self.upload_file( repository, 'filtering/filtering_0000.txt', commit_message="Uploaded readme for 1.1.0", remove_repo_files_not_in_tar='No' )
            self.upload_file( repository, 'filtering/filtering_2.2.0.tar', commit_message="Uploaded filtering 2.2.0", remove_repo_files_not_in_tar='No' )
            self.upload_file( repository, 'readme.txt', commit_message="Uploaded readme for 2.2.0", remove_repo_files_not_in_tar='No' )
    def test_0010_browse_tool_sheds( self ):
        """Browse the available tool sheds in this Galaxy instance."""
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.visit_galaxy_url( '/admin_toolshed/browse_tool_sheds' )
        self.check_page_for_string( 'Embedded tool shed for functional tests' )
        self.browse_tool_shed( url=self.url, strings_displayed=[ 'Test 0000 Basic Repository Features 1', 'Test 0000 Basic Repository Features 2' ] )
    def test_0015_browse_test_0000_category( self ):
        '''Browse the category created in test 0000. It should contain the filtering_0000 repository also created in that test.'''
        category = test_db_util.get_category_by_name( 'Test 0000 Basic Repository Features 1' )
        self.browse_category( category, strings_displayed=[ 'filtering_0000' ] )
    def test_0020_preview_filtering_repository( self ):
        '''Load the preview page for the filtering_0000 repository in the tool shed.'''
        self.preview_repository_in_tool_shed( 'filtering_0000', common.test_user_1_name, strings_displayed=[ 'filtering_0000', 'Valid tools' ] )
    def test_0025_install_filtering_repository( self ):
        self.install_repository( 'filtering_0000', common.test_user_1_name, 'Test 0000 Basic Repository Features 1' )
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        self.verify_installed_repository_on_browse_page( installed_repository )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=[ 'Installed tool shed repository', 'Valid tools', 'Filter1' ] )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
    def test_0030_verify_installed_repository_metadata( self ):
        '''Verify that resetting the metadata on an installed repository does not change the metadata.'''
        self.verify_installed_repository_metadata_unchanged( 'filtering_0000', common.test_user_1_name )
