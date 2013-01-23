from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

class UninstallingAndReinstallingRepositories( ShedTwillTestCase ):
    '''Test uninstalling and reinstalling a basic repository.'''
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
        '''Create the 0000 category and upload the filtering repository to the tool shed, if necessary.'''
        category = self.create_category( name='Test 0000 Basic Repository Features 1', description='Test 0000 Basic Repository Features 1' )
        self.create_category( name='Test 0000 Basic Repository Features 2', description='Test 0000 Basic Repository Features 2' )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name='filtering_0000', 
                                                    description="Galaxy's filtering tool for test 0000", 
                                                    long_description="Long description of Galaxy's filtering tool for test 0000", 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ) )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 'filtering/filtering_1.1.0.tar', commit_message="Uploaded filtering 1.1.0" )
            self.upload_file( repository, 'filtering/filtering_0000.txt', commit_message="Uploaded readme for 1.1.0", remove_repo_files_not_in_tar='No' )
            self.upload_file( repository, 'filtering/filtering_2.2.0.tar', commit_message="Uploaded filtering 2.2.0", remove_repo_files_not_in_tar='No' )
            self.upload_file( repository, 'readme.txt', commit_message="Uploaded readme for 2.2.0", remove_repo_files_not_in_tar='No' )
    def test_0010_install_filtering_repository( self ):
        '''Install the filtering repository into the Galaxy instance.'''
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.install_repository( 'filtering_0000', 
                                 common.test_user_1_name, 
                                 'Test 0000 Basic Repository Features 1', 
                                 new_tool_panel_section='test_1000' )
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        strings_displayed = [ installed_repository.name,
                              installed_repository.description,
                              installed_repository.owner, 
                              installed_repository.tool_shed, 
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
    def test_0015_uninstall_filtering_repository( self ):
        '''Uninstall the filtering repository.'''
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        self.uninstall_repository( installed_repository, remove_from_disk=True )
        strings_not_displayed = [ installed_repository.name,
                                  installed_repository.description,
                                  installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )
    def test_0020_reinstall_filtering_repository( self ):
        '''Reinstall the filtering repository.'''
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        self.reinstall_repository( installed_repository )
        strings_displayed = [ installed_repository.name,
                              installed_repository.description,
                              installed_repository.owner, 
                              installed_repository.tool_shed, 
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=[ 'Installed tool shed repository', 'Valid tools', 'Filter1' ] )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
    def test_0025_deactivate_filtering_repository( self ):
        '''Deactivate the filtering repository without removing it from disk.'''
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        self.uninstall_repository( installed_repository, remove_from_disk=False )
        strings_not_displayed = [ installed_repository.name,
                                  installed_repository.description,
                                  installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )
    def test_0030_reactivate_filtering_repository( self ):
        '''Reactivate the filtering repository and verify that it now shows up in the list of installed repositories.'''
        installed_repository = test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        self.reactivate_repository( installed_repository )
        strings_displayed = [ installed_repository.name,
                              installed_repository.description,
                              installed_repository.owner, 
                              installed_repository.tool_shed, 
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=[ 'Installed tool shed repository', 'Valid tools', 'Filter1' ] )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
