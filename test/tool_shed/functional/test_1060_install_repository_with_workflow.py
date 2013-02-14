from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util
import logging
log = logging.getLogger(__name__)
repository_name = 'filtering_0060'
repository_description="Galaxy's filtering tool for test 0060"
repository_long_description="Long description of Galaxy's filtering tool for test 0060"
workflow_filename = 'Workflow_for_0060_filter_workflow_repository.ga'
workflow_name = 'Workflow for 0060_filter_workflow_repository'
category_name = 'Test 0060 Workflow Features'
category_description = 'Test 0060 for workflow features'

class ToolWithRepositoryDependencies( ShedTwillTestCase ):
    '''Test installing a repository with repository dependencies.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
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
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = test_db_util.get_private_role( admin_user )
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
                                 new_tool_panel_section='test_1060' )
    def test_0015_import_workflow_from_installed_repository( self ):
        '''Import the workflow from the installed repository and verify that it appears in the list of all workflows.'''
        installed_repository = test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        self.display_installed_workflow_image( installed_repository, 
                                               workflow_name, 
                                               strings_displayed=[ '#EBD9B2' ],
                                               strings_not_displayed=[ '#EBBCB2' ] )
        self.display_all_workflows( strings_not_displayed=[ workflow_name ] )
        self.import_workflow( installed_repository, workflow_name )
        self.display_all_workflows( strings_displayed=[ workflow_name ] )
