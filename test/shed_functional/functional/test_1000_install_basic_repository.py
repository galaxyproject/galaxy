from shed_functional.base.twilltestcase import common, ShedTwillTestCase


class BasicToolShedFeatures( ShedTwillTestCase ):
    '''Test installing a basic repository.'''

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
        '''Create the 0000 category and upload the filtering repository to it, if necessary.'''
        self.login( email=common.admin_email, username=common.admin_username )
        category = self.create_category( name='Test 0000 Basic Repository Features 2', description='Test Description 0000 Basic Repository Features 2' )
        category = self.create_category( name='Test 0000 Basic Repository Features 1', description='Test Description 0000 Basic Repository Features 1' )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name='filtering_0000',
                                                    description="Galaxy's filtering tool",
                                                    long_description="Long description of Galaxy's filtering tool",
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

    def test_0010_browse_tool_sheds( self ):
        """Browse the available tool sheds in this Galaxy instance."""
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.visit_galaxy_url( '/admin_toolshed/browse_tool_sheds' )
        self.check_page_for_string( 'Embedded tool shed for functional tests' )
        self.browse_tool_shed( url=self.url, strings_displayed=[ 'Test 0000 Basic Repository Features 1', 'Test 0000 Basic Repository Features 2' ] )

    def test_0015_browse_test_0000_category( self ):
        '''Browse the category created in test 0000. It should contain the filtering_0000 repository also created in that test.'''
        category = self.test_db_util.get_category_by_name( 'Test 0000 Basic Repository Features 1' )
        self.browse_category( category, strings_displayed=[ 'filtering_0000' ] )

    def test_0020_preview_filtering_repository( self ):
        '''Load the preview page for the filtering_0000 repository in the tool shed.'''
        self.preview_repository_in_tool_shed( 'filtering_0000', common.test_user_1_name, strings_displayed=[ 'filtering_0000', 'Valid tools' ] )

    def test_0025_install_filtering_repository( self ):
        self.install_repository( 'filtering_0000',
                                 common.test_user_1_name,
                                 'Test 0000 Basic Repository Features 1',
                                 new_tool_panel_section_label='test_1000' )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        strings_displayed = [ 'filtering_0000',
                              "Galaxy's filtering tool",
                              'user1',
                              self.url.replace( 'http://', '' ),
                              str( installed_repository.installed_changeset_revision ) ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        strings_displayed.extend( [ 'Installed tool shed repository', 'Valid tools', 'Filter1' ] )
        self.display_installed_repository_manage_page( installed_repository, strings_displayed=strings_displayed )
        self.verify_tool_metadata_for_installed_repository( installed_repository )

    def test_0030_install_filtering_repository_again( self ):
        '''Attempt to install the already installed filtering repository.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'filtering_0000', common.test_user_1_name )
        # The page displayed after installation is the ajaxian "Montior installing tool shed repositories" page.  Since the filter
        # repository was already installed, nothing will be in the process of being installed, so the grid will not display 'filtering_0000'.
        post_submit_strings_not_displayed = [ 'filtering_0000' ]
        self.install_repository( 'filtering_0000',
                                 common.test_user_1_name,
                                 'Test 0000 Basic Repository Features 1',
                                 post_submit_strings_not_displayed=post_submit_strings_not_displayed )
        strings_displayed = [ 'filtering_0000',
                              "Galaxy's filtering tool",
                              'user1',
                              self.url.replace( 'http://', '' ),
                              str( installed_repository.installed_changeset_revision ) ]
        self.display_installed_repository_manage_page( installed_repository, strings_displayed=strings_displayed )
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )

    def test_0035_verify_installed_repository_metadata( self ):
        '''Verify that resetting the metadata on an installed repository does not change the metadata.'''
        self.verify_installed_repository_metadata_unchanged( 'filtering_0000', common.test_user_1_name )
