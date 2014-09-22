from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
column_repository_name = 'column_maker_1087'
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = 'convert_chars_1087'
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

category_name = 'Test 1087 Advanced Circular Dependencies'
category_description = 'Test circular dependency features'

class TestRepositoryDependencies( ShedTwillTestCase ):
    '''Test installing a repository, then updating it to include repository dependencies.'''
 
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
  
    def test_0005_create_and_populate_column_repository( self ):
        """Create a category for this test suite and add repositories to it."""
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=column_repository_name, 
                                                    description=column_repository_description, 
                                                    long_description=column_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              filename='column_maker/column_maker.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded column_maker tarball.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
 
    def test_0010_create_and_populate_convert_repository( self ):
        '''Create and populate the convert_chars repository.'''
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=convert_repository_name, 
                                                    description=convert_repository_description, 
                                                    long_description=convert_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              filename='convert_chars/convert_chars.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded convert_chars tarball.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
 
    def test_0015_install_and_uninstall_column_repository( self ):
        '''Install and uninstall the column_maker repository.'''
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.install_repository( column_repository_name, 
                                 common.test_user_1_name, 
                                 category_name, 
                                 install_tool_dependencies=False,
                                 install_repository_dependencies=True,
                                 new_tool_panel_section_label='column_maker',
                                 strings_not_displayed=[ 'install_repository_dependencies' ] )
        installed_column_repository = self.test_db_util.get_installed_repository_by_name_owner( column_repository_name, common.test_user_1_name )
        self.uninstall_repository( installed_column_repository )
 
    def test_0020_upload_dependency_xml( self ):
        '''Upload a repository_dependencies.xml file to column_maker that specifies convert_chars.'''
        convert_repository = self.test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        column_repository = self.test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_1085', additional_paths=[ 'column' ] )
        convert_tuple = ( self.url, convert_repository.name, convert_repository.user.username, self.get_repository_tip( convert_repository ) )
        self.create_repository_dependency( repository=column_repository, repository_tuples=[ convert_tuple ], filepath=repository_dependencies_path )

    def test_0025_verify_repository_dependency( self ):
        '''Verify that the new revision of column_maker now depends on convert_chars.'''
        convert_repository = self.test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        column_repository = self.test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        self.check_repository_dependency( column_repository, convert_repository )
 
    def test_0030_reinstall_column_repository( self ):
        '''Reinstall column_maker and verify that it now shows repository dependencies.'''
        installed_column_repository = self.test_db_util.get_installed_repository_by_name_owner( column_repository_name, common.test_user_1_name )
        convert_repository = self.test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        strings_displayed=[ 'Handle repository dependencies', 'convert_chars_1087', self.get_repository_tip( convert_repository ) ]
        # Due to twill's limitations, only check for strings on the (redirected) reselect tool panel section page, don't actually reinstall.
        params = dict( operation='activate or reinstall', id=self.security.encode_id( installed_column_repository.id ) )
        url = '/admin_toolshed/browse_repositories'
        self.visit_galaxy_url( url, params )
        self.check_for_strings( strings_displayed )
        strings_not_displayed = [ 'column_maker_1087' ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )
