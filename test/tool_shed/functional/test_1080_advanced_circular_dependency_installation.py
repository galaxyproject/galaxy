from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

column_repository_name = 'column_maker_0080'
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = 'convert_chars_0080'
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

category_name = 'Test 0080 Advanced Circular Dependencies'
category_description = 'Test circular dependency features'

class TestRepositoryDependencies( ShedTwillTestCase ):
    '''Testing freebayes with tool data table entries, .loc files, and tool dependencies.'''
    def test_0000_create_or_login_admin_user( self ):
        """Create necessary user accounts and login as an admin user."""
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        galaxy_admin_user = test_db_util.get_galaxy_user( common.admin_email )
        assert galaxy_admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        galaxy_admin_user_private_role = test_db_util.get_galaxy_private_role( galaxy_admin_user )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
    def test_0005_initiate_test_data( self ):
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
                              'column_maker/column_maker.tar', 
                              strings_displayed=[], 
                              commit_message='Uploaded column_maker.tar.' )
            repository = self.get_or_create_repository( name=convert_repository_name, 
                                                        description=convert_repository_description, 
                                                        long_description=convert_repository_long_description, 
                                                        owner=common.test_user_1_name,
                                                        category_id=self.security.encode_id( category.id ), 
                                                        strings_displayed=[] )
            self.upload_file( repository, 
                              'convert_chars/convert_chars.tar', 
                              strings_displayed=[], 
                              commit_message='Uploaded convert_chars.tar.' )
            convert_repository = test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
            column_repository = test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
            repository_dependencies_path = self.generate_temp_path( 'test_1080', additional_paths=[ 'convert' ] )
            self.generate_repository_dependency_xml( [ convert_repository ], 
                                                     self.get_filename( 'repository_dependencies.xml', filepath=repository_dependencies_path ), 
                                                     dependency_description='Column maker depends on the convert repository.' )
            self.upload_file( column_repository, 
                              'repository_dependencies.xml', 
                              filepath=repository_dependencies_path, 
                              commit_message='Uploaded dependency on convert' )
            convert_repository = test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
            column_repository = test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
            repository_dependencies_path = self.generate_temp_path( 'test_1080', additional_paths=[ 'convert' ] )
            self.generate_repository_dependency_xml( [ column_repository ], 
                                                     self.get_filename( 'repository_dependencies.xml', filepath=repository_dependencies_path ), 
                                                     dependency_description='Convert chars depends on the column_maker repository.' )
            self.upload_file( convert_repository, 
                              'repository_dependencies.xml', 
                              filepath=repository_dependencies_path, 
                              commit_message='Uploaded dependency on column' )
    def test_0010_install_repositories( self ):
        '''Install convert_chars with repository dependencies check box - this should install both convert_chars and column_maker.'''
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.install_repository( convert_repository_name, 
                                 common.test_user_1_name, 
                                 category_name, 
                                 install_tool_dependencies=False,
                                 install_repository_dependencies='Yes',
                                 new_tool_panel_section='test_1080' )
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        browse_strings_displayed = [ installed_convert_repository.name,
                                     installed_convert_repository.description,
                                     installed_convert_repository.tool_shed, 
                                     installed_convert_repository.installed_changeset_revision ]
        strings_displayed = [ installed_convert_repository.name,
                              installed_convert_repository.description,
                              installed_convert_repository.tool_shed, 
                              installed_convert_repository.installed_changeset_revision,
                              installed_column_repository.name,
                              installed_column_repository.installed_changeset_revision,
                              'Installed' ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        strings_displayed.append( 'Installed repository dependencies' )
        self.display_installed_repository_manage_page( installed_convert_repository, 
                                                       strings_displayed=strings_displayed )
    def test_0015_deactivate_convert_repository( self ):
        '''Deactivate convert_chars - this should display column_maker as installed but missing repository dependencies'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.uninstall_repository( installed_convert_repository, remove_from_disk=False )
        strings_displayed = [ installed_column_repository.name,
                              installed_column_repository.description,
                              installed_column_repository.tool_shed, 
                              installed_column_repository.installed_changeset_revision,
                              installed_convert_repository.name,
                              installed_convert_repository.installed_changeset_revision,
                              'Missing repository dependencies',
                              'Deactivated' ]
        self.display_installed_repository_manage_page( installed_column_repository, 
                                                       strings_displayed=strings_displayed )
    def test_0020_reactivate_convert_repository( self ):
        '''Activate convert_chars - this should display both convert_chars and column_maker as installed with a green box'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.reactivate_repository( installed_convert_repository )
        strings_displayed = [ installed_convert_repository.name,
                              installed_convert_repository.description,
                              installed_convert_repository.tool_shed, 
                              installed_convert_repository.installed_changeset_revision,
                              installed_column_repository.name,
                              installed_column_repository.installed_changeset_revision,
                              'Installed repository dependencies' ]
    def test_0025_deactivate_column_repository( self ):
        '''Deactivate column_maker - this should display convert_chars installed but missing repository dependencies'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.uninstall_repository( installed_column_repository, remove_from_disk=False )
        strings_displayed = [ installed_convert_repository.name,
                              installed_convert_repository.description,
                              installed_convert_repository.tool_shed, 
                              installed_convert_repository.installed_changeset_revision,
                              installed_column_repository.name,
                              installed_column_repository.installed_changeset_revision,
                              'Missing repository dependencies',
                              'Deactivated' ]
        self.display_installed_repository_manage_page( installed_convert_repository, 
                                                       strings_displayed=strings_displayed )
    def test_0030_deactivate_convert_repository( self ):
        '''Deactivate convert_chars - both convert_chars and column_maker are deactivated'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.uninstall_repository( installed_convert_repository, remove_from_disk=False )
        strings_not_displayed = [ installed_column_repository.name,
                                  installed_column_repository.description,
                                  installed_column_repository.installed_changeset_revision,
                                  installed_convert_repository.name,
                                  installed_convert_repository.description,
                                  installed_convert_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )
    def test_0035_reactivate_column_repository( self ):
        '''Activate column_maker - this should not automatically activate convert_chars, so column_maker should be displayed as installed but missing repository dependencies'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.reactivate_repository( installed_column_repository )
        strings_displayed = [ installed_column_repository.name,
                              installed_column_repository.description,
                              installed_column_repository.tool_shed, 
                              installed_column_repository.installed_changeset_revision,
                              installed_convert_repository.name,
                              installed_convert_repository.installed_changeset_revision,
                              'Missing repository dependencies',
                              'Deactivated' ]
        self.display_installed_repository_manage_page( installed_column_repository, 
                                                       strings_displayed=strings_displayed )
    def test_0040_reactivate_convert_repository( self ):
        '''Activate convert_chars - this should display both convert_chars and column_maker as installed with a green box'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.reactivate_repository( installed_convert_repository )
        strings_displayed = [ installed_column_repository.name,
                              installed_column_repository.description,
                              installed_column_repository.tool_shed, 
                              installed_column_repository.installed_changeset_revision,
                              installed_convert_repository.name,
                              installed_convert_repository.installed_changeset_revision,
                              'Installed repository dependencies' ]
        self.display_installed_repository_manage_page( installed_column_repository, 
                                                       strings_displayed=strings_displayed )
        strings_displayed = [ installed_convert_repository.name,
                              installed_convert_repository.description,
                              installed_convert_repository.tool_shed, 
                              installed_convert_repository.installed_changeset_revision,
                              installed_column_repository.name,
                              installed_column_repository.installed_changeset_revision,
                              'Installed repository dependencies' ]
        self.display_installed_repository_manage_page( installed_convert_repository, 
                                                       strings_displayed=strings_displayed )
    def test_0045_uninstall_column_repository( self ):
        '''Uninstall column_maker - this should display convert_chars installed but missing repository dependencies'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.uninstall_repository( installed_column_repository, remove_from_disk=True )
        strings_displayed = [ installed_convert_repository.name,
                              installed_convert_repository.description,
                              installed_convert_repository.tool_shed, 
                              installed_convert_repository.installed_changeset_revision,
                              installed_column_repository.name,
                              installed_column_repository.installed_changeset_revision,
                              'Missing repository dependencies',
                              'Uninstalled' ]
        self.display_installed_repository_manage_page( installed_convert_repository, 
                                                       strings_displayed=strings_displayed )
    def test_0050_reinstall_column_repository( self ):
        '''Reinstall column_maker without repository dependencies, verify both convert_chars and column_maker are installed.'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.reinstall_repository( installed_column_repository, install_repository_dependencies=False )
        strings_displayed = [ installed_column_repository.name,
                              installed_column_repository.description,
                              installed_column_repository.tool_shed, 
                              installed_column_repository.installed_changeset_revision,
                              installed_convert_repository.name,
                              installed_convert_repository.installed_changeset_revision,
                              'Installed repository dependencies' ]
        self.display_installed_repository_manage_page( installed_column_repository, 
                                                       strings_displayed=strings_displayed )
        strings_displayed = [ installed_convert_repository.name,
                              installed_convert_repository.description,
                              installed_convert_repository.tool_shed, 
                              installed_convert_repository.installed_changeset_revision,
                              installed_column_repository.name,
                              installed_column_repository.installed_changeset_revision,
                              'Installed repository dependencies' ]
        self.display_installed_repository_manage_page( installed_convert_repository, 
                                                       strings_displayed=strings_displayed )
    def test_0055_uninstall_convert_repository( self ):
        '''Uninstall convert_chars, verify column_maker installed but missing repository dependencies'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.uninstall_repository( installed_convert_repository, remove_from_disk=True )
        strings_displayed = [ installed_column_repository.name,
                              installed_column_repository.description,
                              installed_column_repository.tool_shed, 
                              installed_column_repository.installed_changeset_revision,
                              installed_convert_repository.name,
                              installed_convert_repository.installed_changeset_revision,
                              'Missing repository dependencies',
                              'Uninstalled' ]
        self.display_installed_repository_manage_page( installed_column_repository, 
                                                       strings_displayed=strings_displayed )
    def test_0060_uninstall_column_repository( self ):
        '''Uninstall column_maker - both convert_chars and column_maker are uninstalled'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.uninstall_repository( installed_column_repository, remove_from_disk=True )
        strings_displayed = [ installed_convert_repository.name,
                              installed_convert_repository.description,
                              installed_convert_repository.tool_shed, 
                              installed_convert_repository.installed_changeset_revision,
                              installed_column_repository.name,
                              installed_column_repository.installed_changeset_revision,
                              'Missing repository dependencies',
                              'Activate or reinstall repository',
                              'Uninstalled' ]
        self.display_installed_repository_manage_page( installed_convert_repository, 
                                                       strings_displayed=strings_displayed )
    def test_0065_reinstall_convert_repository( self ):
        '''Reinstall convert_chars and check the handle repository dependencies check box - this should install both convert_chars and column_maker ( make sure )'''
        installed_convert_repository = test_db_util.get_installed_repository_by_name_owner( convert_repository_name, 
                                                                                            common.test_user_1_name )
        installed_column_repository = test_db_util.get_installed_repository_by_name_owner( column_repository_name, 
                                                                                            common.test_user_1_name )
        self.reinstall_repository( installed_convert_repository, install_repository_dependencies=True )
        strings_displayed = [ installed_column_repository.name,
                              installed_column_repository.description,
                              installed_column_repository.tool_shed, 
                              installed_column_repository.installed_changeset_revision,
                              installed_convert_repository.name,
                              installed_convert_repository.installed_changeset_revision,
                              'Installed repository dependencies' ]
        self.display_installed_repository_manage_page( installed_column_repository, 
                                                       strings_displayed=strings_displayed )
        strings_displayed = [ installed_convert_repository.name,
                              installed_convert_repository.description,
                              installed_convert_repository.tool_shed, 
                              installed_convert_repository.installed_changeset_revision,
                              installed_column_repository.name,
                              installed_column_repository.installed_changeset_revision,
                              'Installed repository dependencies' ]
        self.display_installed_repository_manage_page( installed_convert_repository, 
                                                       strings_displayed=strings_displayed )
