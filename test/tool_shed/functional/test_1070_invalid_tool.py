from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
repository_name = 'bismark_0070'
repository_description = "Galaxy's bismark wrapper"
repository_long_description = "Long description of Galaxy's bismark wrapper"
category_name = 'Test 0070 Invalid Tool Revisions'
category_description = 'Test 1070 for a repository with an invalid tool.'


class TestFreebayesRepository( ShedTwillTestCase ):
    '''Test repository with multiple revisions with invalid tools.'''
    def test_0000_create_or_login_admin_user( self ):
        """Create necessary user accounts and login as an admin user."""
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        galaxy_admin_user = self.test_db_util.get_galaxy_user( common.admin_email )
        assert galaxy_admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        galaxy_admin_user_private_role = self.test_db_util.get_galaxy_private_role( galaxy_admin_user )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
    def test_0005_ensure_existence_of_repository_and_category( self ):
        '''Create freebayes repository and upload only freebayes.xml. This should result in an error message and invalid tool.'''
        self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              filename='bismark/bismark.tar',
                              filepath=None,
                              valid_tools_only=False,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded bismark tarball.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
            self.upload_file( repository, 
                              filename='bismark/bismark_methylation_extractor.xml',
                              filepath=None,
                              valid_tools_only=False,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded an updated tool xml.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
    def test_0010_browse_tool_shed( self ):
        """Browse the available tool sheds in this Galaxy instance and preview the bismark repository."""
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.browse_tool_shed( url=self.url, strings_displayed=[ category_name ] )
        category = self.test_db_util.get_category_by_name( category_name )
        self.browse_category( category, strings_displayed=[ repository_name ] )
        self.preview_repository_in_tool_shed( repository_name, common.test_user_1_name, strings_displayed=[ repository_name ] )
    def test_0015_install_freebayes_repository( self ):
        '''Install the test repository without installing tool dependencies.'''
        self.install_repository( repository_name, 
                                 common.test_user_1_name, 
                                 category_name, 
                                 install_tool_dependencies=False, 
                                 new_tool_panel_section_label='test_1070' )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        strings_displayed = [ 'bismark_0070',
                              "Galaxy's bismark wrapper",
                              'user1', 
                              self.url.replace( 'http://', '' ), 
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        strings_displayed.extend( [ 'methylation extractor', 'Invalid tools' ] )
        self.display_installed_repository_manage_page( installed_repository, 
                                                       strings_displayed=strings_displayed,
                                                       strings_not_displayed=[ 'bisulfite mapper' ] )
        self.verify_tool_metadata_for_installed_repository( installed_repository )
        self.update_installed_repository( installed_repository, strings_displayed=[ "there are no updates available" ] )
        assert 'invalid_tools' in installed_repository.metadata, 'No invalid tools were defined in %s.' % \
            installed_repository.name
