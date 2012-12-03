from tool_shed.base.twilltestcase import *
from tool_shed.base.test_db_util import *

admin_user = None
admin_user_private_role = None
admin_email = 'test@bx.psu.edu'
admin_username = 'admin-user'

regular_user = None
regular_user_private_role = None
regular_email = 'test-1@bx.psu.edu'
regular_username = 'user1'

repository_name = 'freebayes'
repository_description = "Galaxy's freebayes tool"
repository_long_description = "Long description of Galaxy's freebayes tool"

class TestFreebayesRepository( ShedTwillTestCase ):
    '''Testing freebayes with tool data table entries, .loc files, and tool dependencies.'''
    def test_0000_create_or_login_admin_user( self ):
        self.logout()
        self.login( email=admin_email, username=admin_username )
        admin_user = get_user( admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = get_private_role( admin_user )
    def test_0005_create_freebayes_repository_and_upload_tool_xml( self ):
        '''Upload freebayes.xml without tool_data_table_conf.xml.sample. This should result in an error and invalid tool.'''
        self.create_repository( repository_name, 
                                repository_description, 
                                repository_long_description=repository_long_description, 
                                categories=[ 'Text Manipulation' ], 
                                strings_displayed=[] )
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 
                          'freebayes/freebayes.xml', 
                          valid_tools_only=False,
                          strings_displayed=[ 'Metadata was defined', 'This file requires an entry', 'tool_data_table_conf' ], 
                          commit_message='Uploaded the tool xml.' )
        self.display_manage_repository_page( repository, strings_not_displayed=[ 'Valid tools' ] )
        tip = self.get_repository_tip( repository )
        self.check_repository_invalid_tools_for_changeset_revision( repository, 
                                                                    tip, 
                                                                    strings_displayed=[ 'requires an entry', 'tool_data_table_conf.xml' ] )
    def test_0010_upload_missing_tool_data_table_conf_file( self ):
        '''Upload the missing tool_data_table_conf.xml.sample file to the repository.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 
                          'freebayes/tool_data_table_conf.xml.sample', 
                          strings_displayed=[], 
                          commit_message='Uploaded the tool data table sample file.' )
    def test_0015_upload_missing_sample_loc_file( self ):
        '''Upload the missing sam_fa_indices.loc.sample file to the repository.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 
                          'freebayes/sam_fa_indices.loc.sample', 
                          strings_displayed=[], 
                          commit_message='Uploaded tool data table .loc file.' )
    def test_0020_upload_invalid_tool_dependency_xml( self ):
        '''Upload tool_dependencies.xml defining version 0.9.5 of the freebayes package.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 
                          os.path.join( 'freebayes', 'invalid_deps', 'tool_dependencies.xml' ),
                          strings_displayed=[ 'Name, version and type from a tool requirement tag does not match' ], 
                          commit_message='Uploaded invalid tool dependency XML.' )
    def test_0025_upload_valid_tool_dependency_xml( self ):
        '''Upload tool_dependencies.xml defining version 0.9.4_9696d0ce8a962f7bb61c4791be5ce44312b81cf8 of the freebayes package.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.upload_file( repository, 
                          os.path.join( 'freebayes', 'tool_dependencies.xml' ),
                          commit_message='Uploaded valid tool dependency XML.' )
    def test_0030_verify_tool_dependencies( self ):
        '''Verify that the uploaded tool_dependencies.xml specifies the correct package versions.'''
        repository = get_repository_by_name_and_owner( repository_name, admin_username )
        self.display_manage_repository_page( repository, 
                                strings_displayed=[ 'freebayes', '0.9.4_9696d0ce8a9', 'samtools', '0.1.18', 'Valid tools' ],
                                strings_not_displayed=[ 'Invalid tools' ] )
