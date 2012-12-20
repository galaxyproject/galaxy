from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

repository_name = 'freebayes_0070'
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
        self.create_category( name='Test 0070 Repository With Invalid Tool', description='Tests for a repository with an invalid tool.' )
    def test_0010_create_test_repository_and_upload_tool_xml( self ):
        '''Create and populate a freebayes repository. After this test, it should contain one valid tool and one invalid tool.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = test_db_util.get_category_by_name( 'Test 0070 Repository With Invalid Tool' )
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          'freebayes/freebayes.xml', 
                          valid_tools_only=False,
                          strings_displayed=[],
                          commit_message='Uploaded the tool xml.' )
        self.upload_file( repository, 
                          'filtering/filtering_1.1.0.tar', 
                          valid_tools_only=False,
                          strings_displayed=[],
                          commit_message='Uploaded the tool xml.',
                          remove_repo_files_not_in_tar='No' )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Valid tools', 'Invalid tools' ] )
        changeset_revision = self.get_repository_tip( repository )
        self.check_repository_tools_for_changeset_revision( repository, changeset_revision )
        self.check_repository_invalid_tools_for_changeset_revision( repository, 
                                                                    changeset_revision, 
                                                                    strings_displayed=[ 'requires an entry' ], 
                                                                    strings_not_displayed=[] )
