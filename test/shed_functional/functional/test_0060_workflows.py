import os

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

repository_name = 'filtering_0060'
repository_description = "Galaxy's filtering tool for test 0060"
repository_long_description = "Long description of Galaxy's filtering tool for test 0060"

workflow_filename = 'Workflow_for_0060_filter_workflow_repository.ga'
workflow_name = 'Workflow for 0060_filter_workflow_repository'

category_name = 'Test 0060 Workflow Features'
category_description = 'Test 0060 for workflow features'

workflow_repository_name = 'filtering_workflow_0060'
workflow_repository_description = "Workflow referencing the filtering tool for test 0060"
workflow_repository_long_description = "Long description of the workflow for test 0060"


class TestToolShedWorkflowFeatures( ShedTwillTestCase ):
    '''Test valid and invalid workflows.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )

    def test_0005_create_categories( self ):
        """Create categories for this test suite"""
        self.create_category( name='Test 0060 Workflow Features', description='Test 0060 - Workflow Features' )

    def test_0010_create_repository( self ):
        """Create and populate the filtering repository"""
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        self.get_or_create_repository( name=repository_name,
                                       description=repository_description,
                                       long_description=repository_long_description,
                                       owner=common.test_user_1_name,
                                       category_id=self.security.encode_id( category.id ),
                                       strings_displayed=[] )

    def test_0015_upload_workflow( self ):
        '''Upload a workflow with a missing tool, and verify that the tool specified is marked as missing.'''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        workflow = open( self.get_filename( 'filtering_workflow/Workflow_for_0060_filter_workflow_repository.ga' ), 'r' ).read()
        workflow = workflow.replace(  '__TEST_TOOL_SHED_URL__', self.url.replace( 'http://', '' ) )
        workflow_filepath = self.generate_temp_path( 'test_0060', additional_paths=[ 'filtering_workflow' ] )
        if not os.path.exists( workflow_filepath ):
            os.makedirs( workflow_filepath )
        open( os.path.join( workflow_filepath, workflow_filename ), 'w+' ).write( workflow )
        self.upload_file( repository,
                          filename=workflow_filename,
                          filepath=workflow_filepath,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded filtering workflow.',
                          strings_displayed=[],
                          strings_not_displayed=[] )
        self.load_workflow_image_in_tool_shed( repository, workflow_name, strings_displayed=[ '#EBBCB2' ] )

    def test_0020_upload_tool( self ):
        '''Upload the missing tool for the workflow in the previous step, and verify that the error is no longer present.'''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository,
                          filename='filtering/filtering_2.2.0.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded filtering 2.2.0.',
                          strings_displayed=[],
                          strings_not_displayed=[] )
        self.load_workflow_image_in_tool_shed( repository, workflow_name, strings_not_displayed=[ '#EBBCB2' ] )

    def test_0025_create_repository_with_only_workflow( self ):
        """Create and populate the filtering_workflow_0060 repository"""
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        self.get_or_create_repository( name=workflow_repository_name,
                                       description=workflow_repository_description,
                                       long_description=workflow_repository_long_description,
                                       owner=common.test_user_1_name,
                                       category_id=self.security.encode_id( category.id ),
                                       strings_displayed=[] )
        workflow = open( self.get_filename( 'filtering_workflow/Workflow_for_0060_filter_workflow_repository.ga' ), 'r' ).read()
        workflow = workflow.replace(  '__TEST_TOOL_SHED_URL__', self.url.replace( 'http://', '' ) )
        workflow = workflow.replace( 'Workflow for 0060_filter_workflow_repository',
                                     'New workflow for 0060_filter_workflow_repository' )
        workflow_filepath = self.generate_temp_path( 'test_0060', additional_paths=[ 'filtering_workflow_2' ] )
        if not os.path.exists( workflow_filepath ):
            os.makedirs( workflow_filepath )
        open( os.path.join( workflow_filepath, workflow_filename ), 'w+' ).write( workflow )
        repository = self.test_db_util.get_repository_by_name_and_owner( workflow_repository_name, common.test_user_1_name )
        self.upload_file( repository,
                          filename=workflow_filename,
                          filepath=workflow_filepath,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded filtering workflow.',
                          strings_displayed=[],
                          strings_not_displayed=[] )
        self.load_workflow_image_in_tool_shed( repository, workflow_name, strings_displayed=[ '#EBBCB2' ] )

    def test_0030_check_workflow_repository( self ):
        """Check for strings on the manage page for the filtering_workflow_0060 repository."""
        repository = self.test_db_util.get_repository_by_name_and_owner( workflow_repository_name, common.test_user_1_name )
        strings_displayed = [ 'Workflows', 'New workflow for 0060_filter', '0.1' ]
        strings_not_displayed = [ 'Valid tools', 'Invalid tools' ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )

    def test_0035_verify_repository_metadata( self ):
        '''Verify that resetting the metadata does not change it.'''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.verify_unchanged_repository_metadata( repository )
