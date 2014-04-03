from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os

import logging
log = logging.getLogger( __name__ )

category_name = 'Test 1430 Repair installed repository'
category_description = 'Test script 1430 for repairing an installed repository.'
filter_repository_name = 'filter_1430'
column_repository_name = 'column_1430'
filter_repository_description = "Galaxy's filter tool for test 1430"
column_repository_description = 'Add a value as a new column'
filter_repository_long_description = '%s: %s' % ( filter_repository_name, filter_repository_description )
column_repository_long_description = '%s: %s' % ( column_repository_name, column_repository_description )

'''
In the Tool Shed:

1) Create and populate the filter_1430 repository

2) Create and populate the column_1430 repository

3) Upload a repository_dependencies.xml file to the column_1430 repository that creates a repository dependency on the filter_1430 repository.

In Galaxy:

1) Install the column_1430 repository, making sure to check the checkbox to Handle repository dependencies so that the filter
   repository is also installed. Make sure to install the repositories in a specified section of the tool panel.

2) Uninstall the filter_1430 repository.

3) Repair the column_1430 repository.

4) Make sure the filter_1430 repository is reinstalled and the tool is loaded into the tool panel in the same section specified in step 1.
'''


class TestRepairRepository( ShedTwillTestCase ):
    '''Test repairing an installed repository.'''
    
    def test_0000_initiate_users_and_category( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
        self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        test_user_2_private_role = self.test_db_util.get_private_role( test_user_2 )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        
    def test_0005_create_filter_repository( self ):
        '''Create and populate the filter_1430 repository.'''
        '''
        This is step 1 - Create and populate the filter_1430 repository.
        
        This repository will be depended on by the column_1430 repository.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=filter_repository_name, 
                                                    description=filter_repository_description, 
                                                    long_description=filter_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='filtering/filtering_1.1.0.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate filter_1430 with version 1.1.0.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        
    def test_0010_create_column_repository( self ):
        '''Create and populate the column_1430 repository.'''
        '''
        This is step 2 - Create and populate the column_1430 repository.
        
        This repository will depend on the filter_1430 repository.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=column_repository_name, 
                                                    description=column_repository_description, 
                                                    long_description=column_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='column_maker/column_maker.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate column_1430 with tool definitions.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        
    def test_0015_create_repository_dependency( self ):
        '''Create a dependency on filter_1430.'''
        '''
        This is step 3 - Upload a repository_dependencies.xml file to the column_1430 repository that creates a repository
        dependency on the filter_1430 repository.
        '''
        column_repository = self.test_db_util.get_repository_by_name_and_owner( 'column_1430', common.test_user_1_name )
        filter_repository = self.test_db_util.get_repository_by_name_and_owner( 'filter_1430', common.test_user_1_name )
        tool_shed_url = self.url
        name = filter_repository.name
        owner = filter_repository.user.username
        changeset_revision = self.get_repository_tip( filter_repository )
        repository_dependency_tuple = ( tool_shed_url, name, owner, changeset_revision )
        filepath = self.generate_temp_path( '1430_repository_dependency' )
        self.create_repository_dependency( column_repository, [ repository_dependency_tuple ], filepath=filepath )
        
    def test_0020_install_column_repository( self ):
        '''Install the column_1430 repository into Galaxy.'''
        '''
        This is step 1 (galaxy side) - Install the column_1430 repository, making sure to check the checkbox to
        handle repository dependencies so that the filter_1430 repository is also installed. Make sure to install
        the repositories in a specified section of the tool panel.
        '''
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        post_submit_strings_displayed = [ 'column_1430', 'filter_1430' ]
        self.install_repository( 'column_1430', 
                                 common.test_user_1_name, 
                                 category_name,
                                 new_tool_panel_section_label='repair',
                                 post_submit_strings_displayed=post_submit_strings_displayed,
                                 install_tool_dependencies=False, 
                                 install_repository_dependencies=True )
    
    def test_0025_uninstall_filter_repository( self ):
        '''Uninstall the filter_1430 repository from Galaxy.'''
        '''
        This is step 2 - Uninstall the filter_1430 repository.
        '''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'filter_1430', common.test_user_1_name )
        strings_displayed = [ 'Uninstalling this repository will result in the following' ]
        strings_not_displayed = []
        self.uninstall_repository( installed_repository, 
                                   strings_displayed=strings_displayed, 
                                   strings_not_displayed=strings_not_displayed  )
        strings_not_displayed = [ 'filter_1430',
                                  "Galaxy's filter tool for test 1430",
                                  installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_not_displayed=strings_not_displayed )

    def test_0030_repair_column_repository( self ):
        '''Repair the column_1430 repository.'''
        '''
        This is step 3 - Repair the column_1430 repository.
        '''
        column_repository = self.test_db_util.get_installed_repository_by_name_owner( 'column_1430', common.test_user_1_name )
        self.repair_installed_repository( column_repository )
        
    def test_0035_verify_tool_panel_section( self ):
        '''Check the tool panel section after repairing.'''
        '''
        This is step 4 - Make sure the filter_1430 repository is reinstalled and the tool is loaded into the tool panel
        in the same section specified in step 1.
        '''
        filter_repository = self.test_db_util.get_installed_repository_by_name_owner( 'filter_1430', common.test_user_1_name )
        strings_displayed = [ 'filter_1430',
                              "Galaxy's filter tool for test 1430",
                              filter_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        self.check_galaxy_repository_tool_panel_section( repository=filter_repository, expected_tool_panel_section='repair' )
        
