import logging

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

log = logging.getLogger( __name__ )

category_name = 'Test 0480 Tool dependency definition validation'
category_description = 'Test script 0480 for validating tool dependency definitions.'
repository_name = 'package_invalid_tool_dependency_xml_1_0_0'
repository_description = "Contains a tool dependency definition that should return an error."
repository_long_description = "This repository is in the test suite 0480"

'''

1. Create a repository package_invalid_tool_dependency_xml_1_0_0
2. Upload a tool_dependencies.xml file to the repository with no <actions> tags around the <action> tags.
3. Verify error message is displayed.

'''


class TestDependencyDefinitionValidation( ShedTwillTestCase ):
    '''Test the tool shed's tool dependency XML validation.'''

    def test_0000_initiate_users_and_category( self ):
        """Create necessary user accounts and login as an admin user."""
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )
        self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        self.test_db_util.get_private_role( test_user_2 )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )

    def test_0005_create_tool_dependency_repository( self ):
        '''Create and populate package_invalid_tool_dependency_xml_1_0_0.'''
        '''
        This is step 1 - Create a repository package_invalid_tool_dependency_xml_1_0_0.

        Create a repository named package_invalid_tool_dependency_xml_1_0_0 that will contain only a single file named tool_dependencies.xml.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=repository_name,
                                                    description=repository_description,
                                                    long_description=repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        self.upload_file( repository,
                          filename='0480_files/tool_dependencies.xml',
                          filepath=None,
                          valid_tools_only=False,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate package_invalid_tool_dependency_xml_1_0_0 with an improperly defined tool dependency.',
                          strings_displayed=[ 'package cannot be installed because', 'missing either an &lt;actions&gt; tag set' ],
                          strings_not_displayed=[] )

    def test_0010_populate_tool_dependency_repository( self ):
        '''Verify package_invalid_tool_dependency_xml_1_0_0.'''
        '''
        This is step 3 - Verify repository. The uploaded tool dependency XML should not have resulted in a new changeset.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( repository_name, common.test_user_1_name )
        assert self.repository_is_new( repository ), 'Uploading an incorrectly defined tool_dependencies.xml resulted in a changeset being generated.'
