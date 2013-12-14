from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
repository_name = 'filtering_0060'
repository_description="Galaxy's filtering tool for test 0060"
repository_long_description="Long description of Galaxy's filtering tool for test 0060"

workflow_filename = 'Workflow_for_0060_filter_workflow_repository.ga'
workflow_name = 'Workflow for 0060_filter_workflow_repository'
second_workflow_name = 'New workflow for 0060_filter_workflow_repository'

category_name = 'Test 0060 Workflow Features'
category_description = 'Test 0060 for workflow features'

workflow_repository_name = 'filtering_workflow_0060'
workflow_repository_description="Workflow referencing the filtering tool for test 0060"
workflow_repository_long_description="Long description of the workflow for test 0060"


class ToolWithRepositoryDependencies( ShedTwillTestCase ):
    '''Test installing a repository with repository dependencies.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
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
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
    def test_0005_ensure_category_exists( self ):
        '''Create the 0060 category.'''
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=repository_name,
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),  
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            workflow = file( self.get_filename( 'filtering_workflow/Workflow_for_0060_filter_workflow_repository.ga' ), 'r' ).read()
            workflow = workflow.replace(  '__TEST_TOOL_SHED_URL__', self.url.replace( 'http://', '' ) )
            workflow_filepath = self.generate_temp_path( 'test_1060', additional_paths=[ 'filtering_workflow' ] )
            if not os.path.exists( workflow_filepath ):
                os.makedirs( workflow_filepath )
            file( os.path.join( workflow_filepath, workflow_filename ), 'w+' ).write( workflow )
            self.upload_file( repository, 
                              filename=workflow_filename, 
                              filepath=workflow_filepath, 
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded filtering workflow.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
            self.upload_file( repository, 
                              filename='filtering/filtering_2.2.0.tar', 
                              filepath=None, 
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded filtering 2.2.0.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
    def test_0010_install_repository_with_workflow( self ):
        """Browse the available tool sheds in this Galaxy instance and preview the filtering tool."""
        self.preview_repository_in_tool_shed( repository_name, 
                                              common.test_user_1_name, 
                                              strings_displayed=[ repository_name, 'Valid tools', 'Workflows' ] )
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.install_repository( repository_name, 
                                 common.test_user_1_name, 
                                 'Test 0060 Workflow Features',
                                 install_tool_dependencies=False, 
                                 new_tool_panel_section_label='test_1060' )
    def test_0015_import_workflow_from_installed_repository( self ):
        '''Import the workflow from the installed repository and verify that it appears in the list of all workflows.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        self.display_installed_workflow_image( installed_repository, 
                                               workflow_name, 
                                               strings_displayed=[ '#EBD9B2' ],
                                               strings_not_displayed=[ '#EBBCB2' ] )
        self.display_all_workflows( strings_not_displayed=[ 'Workflow for 0060_filter_workflow_repository' ] )
        self.import_workflow( installed_repository, workflow_name )
        self.display_all_workflows( strings_displayed=[ 'Workflow for 0060_filter_workflow_repository' ] )
    def test_0020_create_filter_workflow_repository( self ):
        '''Create, if necessary, a filtering repository with only a workflow.'''
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=workflow_repository_name, 
                                                    description=workflow_repository_description, 
                                                    long_description=workflow_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            workflow = file( self.get_filename( 'filtering_workflow/Workflow_for_0060_filter_workflow_repository.ga' ), 'r' ).read()
            workflow = workflow.replace(  '__TEST_TOOL_SHED_URL__', self.url.replace( 'http://', '' ) )
            workflow = workflow.replace( 'Workflow for 0060_filter_workflow_repository', 
                                         'New workflow for 0060_filter_workflow_repository' )
            workflow_filepath = self.generate_temp_path( 'test_0060', additional_paths=[ 'filtering_workflow_2' ] )
            if not os.path.exists( workflow_filepath ):
                os.makedirs( workflow_filepath )
            file( os.path.join( workflow_filepath, workflow_filename ), 'w+' ).write( workflow )
            self.upload_file( repository, 
                              filename=workflow_filename, 
                              filepath=workflow_filepath, 
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded filtering workflow.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
            self.load_workflow_image_in_tool_shed( repository, 
                                                   'New workflow for 0060_filter_workflow_repository', 
                                                   strings_displayed=[ '#EBBCB2' ] )
    def test_0025_install_repository_with_workflow( self ):
        """Browse the available tool sheds in this Galaxy instance and preview the filtering workflow repository."""
        self.preview_repository_in_tool_shed( workflow_repository_name, 
                                              common.test_user_1_name, 
                                              strings_displayed=[ 'filtering_workflow_0060', 'Workflows' ],
                                              strings_not_displayed=[ 'Valid tools', 'Invalid tools' ] )
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        self.install_repository( workflow_repository_name, 
                                 common.test_user_1_name, 
                                 'Test 0060 Workflow Features',
                                 install_tool_dependencies=False,
                                 includes_tools_for_display_in_tool_panel=False )
    def test_0030_import_workflow_from_installed_repository( self ):
        '''Import the workflow from the installed repository and verify that it appears in the list of all workflows.'''
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( workflow_repository_name, common.test_user_1_name )
        self.display_installed_workflow_image( installed_repository, 
                                               'New workflow for 0060_filter_workflow_repository', 
                                               strings_displayed=[ '#EBD9B2' ],
                                               strings_not_displayed=[ '#EBBCB2' ] )
        self.display_all_workflows( strings_not_displayed=[ 'New workflow for 0060_filter_workflow_repository' ] )
        self.import_workflow( installed_repository, 
                              'New workflow for 0060_filter_workflow_repository',
                              strings_displayed=[ 'New workflow for 0060_filter_workflow_repository' ] )
        self.display_all_workflows( strings_displayed=[ 'New workflow for 0060_filter_workflow_repository' ] )
    
