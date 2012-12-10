from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
from tool_shed.base.test_db_util import get_repository_by_name_and_owner, get_user, get_private_role

repository_name = 'freebayes_0010'
repository_description = "Galaxy's freebayes tool"
repository_long_description = "Long description of Galaxy's freebayes tool"

class TestFreebayesRepository( ShedTwillTestCase ):
    '''Testing freebayes with tool data table entries, .loc files, and tool dependencies.'''
    def test_0000_create_or_login_admin_user( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = get_private_role( admin_user )
    def test_0005_create_category( self ):
        """Create a category for this test suite"""
        self.create_category( 'Test 0010 Repository With Tool Dependencies', 'Tests for a repository with tool dependencies.' )
    def test_0010_create_freebayes_repository_and_upload_tool_xml( self ):
        '''Create freebayes repository and upload freebayes.xml without tool_data_table_conf.xml.sample. This should result in an error message and invalid tool.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        self.create_repository( repository_name, 
                                repository_description, 
                                repository_long_description=repository_long_description, 
                                categories=[ 'Test 0010 Repository With Tool Dependencies' ], 
                                strings_displayed=[] )
        repository = get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          'freebayes/freebayes.xml', 
                          valid_tools_only=False,
                          strings_displayed=[ 'Metadata may have been defined', 'This file requires an entry', 'tool_data_table_conf' ], 
                          commit_message='Uploaded the tool xml.' )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Invalid tools' ], strings_not_displayed=[ 'Valid tools' ] )
        tip = self.get_repository_tip( repository )
        self.check_repository_invalid_tools_for_changeset_revision( repository, 
                                                                    tip, 
                                                                    strings_displayed=[ 'requires an entry', 'tool_data_table_conf.xml' ] )
    def test_0015_upload_missing_tool_data_table_conf_file( self ):
        '''Upload the missing tool_data_table_conf.xml.sample file to the repository.'''
        repository = get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          'freebayes/tool_data_table_conf.xml.sample', 
                          valid_tools_only=False,
                          strings_displayed=[], 
                          commit_message='Uploaded the tool data table sample file.' )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Invalid tools' ], strings_not_displayed=[ 'Valid tools' ] )
        tip = self.get_repository_tip( repository )
        self.check_repository_invalid_tools_for_changeset_revision( repository, 
                                                                    tip, 
                                                                    strings_displayed=[ 'refers to a file', 'sam_fa_indices.loc' ] )
    def test_0020_upload_missing_sample_loc_file( self ):
        '''Upload the missing sam_fa_indices.loc.sample file to the repository.'''
        repository = get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          'freebayes/sam_fa_indices.loc.sample', 
                          strings_displayed=[], 
                          commit_message='Uploaded tool data table .loc file.' )
    def test_0025_upload_invalid_tool_dependency_xml( self ):
        '''Upload tool_dependencies.xml defining version 0.9.5 of the freebayes package.'''
        repository = get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          os.path.join( 'freebayes', 'invalid_tool_dependencies', 'tool_dependencies.xml' ),
                          strings_displayed=[ 'Name, version and type from a tool requirement tag does not match' ], 
                          commit_message='Uploaded invalid tool dependency XML.' )
    def test_0030_upload_valid_tool_dependency_xml( self ):
        '''Upload tool_dependencies.xml defining version 0.9.4_9696d0ce8a962f7bb61c4791be5ce44312b81cf8 of the freebayes package.'''
        repository = get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          os.path.join( 'freebayes', 'tool_dependencies.xml' ),
                          commit_message='Uploaded valid tool dependency XML.' )
    def test_0035_verify_tool_dependencies( self ):
        '''Verify that the uploaded tool_dependencies.xml specifies the correct package versions.'''
        repository = get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.display_manage_repository_page( repository, 
                                             strings_displayed=[ 'freebayes', '0.9.4_9696d0ce8a9', 'samtools', '0.1.18', 'Valid tools' ],
                                             strings_not_displayed=[ 'Invalid tools' ] )
