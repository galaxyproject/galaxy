from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

repository_name = 'freebayes_0010'
repository_description = "Galaxy's freebayes tool"
repository_long_description = "Long description of Galaxy's freebayes tool"

class TestFreebayesRepository( ShedTwillTestCase ):
    '''Testing freebayes with tool data table entries, .loc files, and tool dependencies.'''
    def test_0000_create_or_login_admin_user( self ):
        """Create necessary user accounts and login as an admin user."""
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
    def test_0005_create_category( self ):
        """Create a category for this test suite"""
        self.create_category( name='Test 0010 Repository With Tool Dependencies', description='Tests for a repository with tool dependencies.' )
    def test_0010_create_freebayes_repository_and_upload_tool_xml( self ):
        '''Create freebayes repository and upload freebayes.xml without tool_data_table_conf.xml.sample. This should result in an error message and invalid tool.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = test_db_util.get_category_by_name( 'Test 0010 Repository With Tool Dependencies' )
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='freebayes/freebayes.xml', 
                          filepath=None,
                          valid_tools_only=False,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded the tool xml.',
                          strings_displayed=[ 'Metadata may have been defined', 'This file requires an entry', 'tool_data_table_conf' ], 
                          strings_not_displayed=[] )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Invalid tools' ], strings_not_displayed=[ 'Valid tools' ] )
        tip = self.get_repository_tip( repository )
        self.check_repository_invalid_tools_for_changeset_revision( repository, 
                                                                    tip, 
                                                                    strings_displayed=[ 'requires an entry', 'tool_data_table_conf.xml' ] )
    def test_0015_upload_missing_tool_data_table_conf_file( self ):
        '''Upload the missing tool_data_table_conf.xml.sample file to the repository.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          filename='freebayes/tool_data_table_conf.xml.sample', 
                          filepath=None,
                          valid_tools_only=False,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded the tool data table sample file.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Invalid tools' ], strings_not_displayed=[ 'Valid tools' ] )
        tip = self.get_repository_tip( repository )
        self.check_repository_invalid_tools_for_changeset_revision( repository, 
                                                                    tip, 
                                                                    strings_displayed=[ 'refers to a file', 'sam_fa_indices.loc' ] )
    def test_0020_upload_missing_sample_loc_file( self ):
        '''Upload the missing sam_fa_indices.loc.sample file to the repository.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          filename='freebayes/sam_fa_indices.loc.sample', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded tool data table .loc file.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
    def test_0025_upload_malformed_tool_dependency_xml( self ):
        '''Upload tool_dependencies.xml with bad characters in the readme tag.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          filename=os.path.join( 'freebayes', 'malformed_tool_dependencies', 'tool_dependencies.xml' ), 
                          filepath=None,
                          valid_tools_only=False,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded malformed tool dependency XML.',
                          strings_displayed=[ 'Exception attempting to parse tool_dependencies.xml', 'not well-formed' ], 
                          strings_not_displayed=[] )
    def test_0030_upload_invalid_tool_dependency_xml( self ):
        '''Upload tool_dependencies.xml defining version 0.9.5 of the freebayes package.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          filename=os.path.join( 'freebayes', 'invalid_tool_dependencies', 'tool_dependencies.xml' ), 
                          filepath=None,
                          valid_tools_only=False,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded invalid tool dependency XML.',
                          strings_displayed=[ 'Name, version and type from a tool requirement tag does not match' ], 
                          strings_not_displayed=[] )
    def test_0035_upload_valid_tool_dependency_xml( self ):
        '''Upload tool_dependencies.xml defining version 0.9.4_9696d0ce8a962f7bb61c4791be5ce44312b81cf8 of the freebayes package.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.upload_file( repository, 
                          filename=os.path.join( 'freebayes', 'tool_dependencies.xml' ), 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded valid tool dependency XML.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
    def test_0040_verify_tool_dependencies( self ):
        '''Verify that the uploaded tool_dependencies.xml specifies the correct package versions.'''
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        self.display_manage_repository_page( repository, 
                                             strings_displayed=[ 'freebayes', '0.9.4_9696d0ce8a9', 'samtools', '0.1.18', 'Valid tools' ],
                                             strings_not_displayed=[ 'Invalid tools' ] )
