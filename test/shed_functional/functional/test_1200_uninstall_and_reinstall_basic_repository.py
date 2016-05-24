from shed_functional.base.twilltestcase import common, ShedTwillTestCase


class UninstallingAndReinstallingRepositories( ShedTwillTestCase ):
    '''Test uninstalling and reinstalling a basic repository.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        galaxy_admin_user = self.test_db_util.get_galaxy_user( common.admin_email )
        assert galaxy_admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_galaxy_private_role( galaxy_admin_user )

    def test_0005_ensure_repositories_and_categories_exist( self ):
        '''Create the 0000 category and upload the filtering repository to the tool shed, if necessary.'''
        category = self.create_category( name='Test 0000 Basic Repository Features 1', description='Test 0000 Basic Repository Features 1' )
        self.create_category( name='Test 0000 Basic Repository Features 2', description='Test 0000 Basic Repository Features 2' )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name='filtering_0000',
                                                    description="Galaxy's filtering tool for test 0000",
                                                    long_description="Long description of Galaxy's filtering tool for test 0000",
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ) )
        if self.repository_is_new( repository ):
            self.upload_file( repository,
                              filename='filtering/filtering_1.1.0.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded filtering 1.1.0 tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( repository,
                              filename='filtering/filtering_0000.txt',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded readme for 1.1.0',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( repository,
                              filename='filtering/filtering_2.2.0.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded filtering 2.2.0 tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            self.upload_file( repository,
                              filename='readme.txt',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded readme for 2.2.0',
                              strings_displayed=[],
                              strings_not_displayed=[] )

    def test_0010_install_filtering_repository( self ):
        '''Install the filtering repository into the Galaxy instance.'''
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.install_repository( 'filtering_0000',
                                 common.test_user_1_name,
                                 'Test 0000 Basic Repository Features 1',
                                 new_tool_panel_section_label='test_1000' )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        strings_displayed = [ 'filtering_0000',
                              "Galaxy's filtering tool for test 0000",
                              'user1',
                              self.url.replace( 'http://', '' ),
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )

    def test_0015_uninstall_filtering_repository( self ):
        '''Uninstall the filtering repository.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        self.uninstall_repository( installed_repository )
        strings_not_displayed = [ 'filtering_0000',
                                  "Galaxy's filtering tool for test 0000",
                                  installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )

    def test_0020_reinstall_filtering_repository( self ):
        '''Reinstall the filtering repository.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        self.reinstall_repository( installed_repository )
        strings_displayed = [ 'filtering_0000',
                              "Galaxy's filtering tool for test 0000",
                              'user1',
                              self.url.replace( 'http://', '' ),
                              str( installed_repository.installed_changeset_revision ) ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        strings_displayed.extend( [ 'Installed tool shed repository', 'Valid tools', 'Filter1' ] )
        self.display_installed_repository_manage_page( installed_repository, strings_displayed=strings_displayed )
        self.verify_tool_metadata_for_installed_repository( installed_repository )

    def test_0025_deactivate_filtering_repository( self ):
        '''Deactivate the filtering repository without removing it from disk.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        self.deactivate_repository( installed_repository )
        strings_not_displayed = [ 'filtering_0000',
                                  "Galaxy's filtering tool for test 0000",
                                  installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )

    def test_0030_reactivate_filtering_repository( self ):
        '''Reactivate the filtering repository and verify that it now shows up in the list of installed repositories.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        self.reactivate_repository( installed_repository )
        strings_displayed = [ 'filtering_0000',
                              "Galaxy's filtering tool for test 0000",
                              'user1',
                              self.url.replace( 'http://', '' ),
                              str( installed_repository.installed_changeset_revision ) ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        strings_displayed.extend( [ 'Installed tool shed repository', 'Valid tools', 'Filter1' ] )
        self.display_installed_repository_manage_page( installed_repository, strings_displayed=strings_displayed )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
