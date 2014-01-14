from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os, logging
column_repository_name = 'column_maker_1085'
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = 'convert_chars_1085'
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

category_name = 'Test 1085 Advanced Circular Dependencies'
category_description = 'Test circular dependency features'

log = logging.getLogger( __name__ )

class TestRepositoryDependencies( ShedTwillTestCase ):
    '''Testing the behavior of repository dependencies with tool panel sections.'''
 
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
 
    def test_0015_create_and_upload_dependency_files( self ):
        convert_repository = self.test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        column_repository = self.test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_1085', additional_paths=[ 'column' ] )
        repository_tuple = ( self.url, convert_repository.name, convert_repository.user.username, self.get_repository_tip( convert_repository ) )
        self.create_repository_dependency( repository=column_repository, repository_tuples=[ repository_tuple ], filepath=repository_dependencies_path )
        repository_tuple = ( self.url, column_repository.name, column_repository.user.username, self.get_repository_tip( column_repository ) )
        self.create_repository_dependency( repository=convert_repository, repository_tuples=[ repository_tuple ], filepath=repository_dependencies_path )
 
    def test_0020_install_repositories( self ):
        '''Install column_maker into column_maker tool panel section and install repository dependencies.'''
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.install_repository( column_repository_name, 
                                 common.test_user_1_name, 
                                 category_name, 
                                 install_tool_dependencies=False,
                                 install_repository_dependencies=True,
                                 new_tool_panel_section_label='column_maker',
                                 strings_displayed=[ 'install_repository_dependencies' ] )
        installed_convert_repository = self.test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = self.test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        browse_strings_displayed = [ 'convert_chars_1085',
                                     'Convert delimiters',
                                     self.url.replace( 'http://', '' ), 
                                     installed_convert_repository.installed_changeset_revision,
                                     'column_maker_1085',
                                     'Add column',
                                     installed_column_repository.installed_changeset_revision ]
        strings_displayed = [ 'convert_chars_1085',
                              'Convert delimiters',
                              self.url.replace( 'http://', '' ), 
                              installed_convert_repository.installed_changeset_revision,
                              'column_maker_1085',
                              installed_column_repository.installed_changeset_revision,
                              'Installed repository dependencies' ]
        self.display_galaxy_browse_repositories_page( strings_displayed=browse_strings_displayed )
        self.display_installed_repository_manage_page( installed_convert_repository, 
                                                       strings_displayed=strings_displayed )

    def test_0025_uninstall_column_repository( self ):
        '''uninstall column_maker, verify same section'''
        installed_column_repository = self.test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.uninstall_repository( installed_column_repository )
        self.test_db_util.ga_refresh( installed_column_repository )
        self.check_galaxy_repository_tool_panel_section( installed_column_repository, 'column_maker' )
 
    def test_0030_uninstall_convert_repository( self ):
        installed_convert_repository = self.test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        self.uninstall_repository( installed_convert_repository )
        self.test_db_util.ga_refresh( installed_convert_repository )
        self.check_galaxy_repository_tool_panel_section( installed_convert_repository, 'column_maker' )
  
    def test_0035_reinstall_column_repository( self ):
        '''reinstall column_maker into new section 'new_column_maker' (no_changes = false), no dependencies'''
        installed_column_repository = self.test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.reinstall_repository( installed_column_repository, 
                                   install_tool_dependencies=False, 
                                   install_repository_dependencies=False, 
                                   new_tool_panel_section_label='new_column_maker',
                                   no_changes=False )
        strings_displayed = [ 'column_maker_1085',
                              'Add column',
                              self.url.replace( 'http://', '' ), 
                              installed_column_repository.installed_changeset_revision ]
        self.display_installed_repository_manage_page( installed_column_repository, 
                                                       strings_displayed=strings_displayed )
  
    def test_0040_reinstall_convert_repository( self ):
        '''reinstall convert_chars into new section 'new_convert_chars' (no_changes = false), no dependencies'''
        installed_convert_repository = self.test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        self.reinstall_repository( installed_convert_repository, 
                                   install_tool_dependencies=False, 
                                   install_repository_dependencies=False, 
                                   new_tool_panel_section_label='new_convert_chars',
                                   no_changes=False )
        strings_displayed = [ 'convert_chars_1085',
                              'Convert delimiters',
                              self.url.replace( 'http://', '' ), 
                              installed_convert_repository.installed_changeset_revision ]
        self.display_installed_repository_manage_page( installed_convert_repository, 
                                                       strings_displayed=strings_displayed )
  
    def test_0045_uninstall_and_verify_tool_panel_sections( self ):
        '''uninstall both and verify tool panel sections'''
        installed_convert_repository = self.test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = self.test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.uninstall_repository( installed_convert_repository )
        self.uninstall_repository( installed_column_repository )
        self.test_db_util.ga_refresh( installed_convert_repository )
        self.test_db_util.ga_refresh( installed_column_repository )
        self.check_galaxy_repository_tool_panel_section( installed_column_repository, 'new_column_maker' )
        self.check_galaxy_repository_tool_panel_section( installed_convert_repository, 'new_convert_chars' )
