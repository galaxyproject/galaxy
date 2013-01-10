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

class TestRepositoryCircularDependencies( ShedTwillTestCase ):
    '''Verify that the code correctly handles circular dependencies.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
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
    def test_0005_initiate_category_repositories( self ):
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
    def test_0020_create_repository_dependencies( self ):
        '''Upload a repository_dependencies.xml file that specifies the current revision of freebayes to the filtering_0040 repository.'''
        convert_repository = test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        column_repository = test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_0080', additional_paths=[ 'convert' ] )
        self.generate_repository_dependency_xml( [ convert_repository ], 
                                                 self.get_filename( 'repository_dependencies.xml', filepath=repository_dependencies_path ), 
                                                 dependency_description='Column maker depends on the convert repository.' )
        self.upload_file( column_repository, 
                          'repository_dependencies.xml', 
                          filepath=repository_dependencies_path, 
                          commit_message='Uploaded dependency on convert' )
    def test_0025_create_dependency_on_filtering( self ):
        '''Upload a repository_dependencies.xml file that specifies the current revision of filtering to the freebayes_0040 repository.'''
        convert_repository = test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        column_repository = test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        repository_dependencies_path = self.generate_temp_path( 'test_0080', additional_paths=[ 'convert' ] )
        self.generate_repository_dependency_xml( [ column_repository ], 
                                                 self.get_filename( 'repository_dependencies.xml', filepath=repository_dependencies_path ), 
                                                 dependency_description='Convert chars depends on the column_maker repository.' )
        self.upload_file( convert_repository, 
                          'repository_dependencies.xml', 
                          filepath=repository_dependencies_path, 
                          commit_message='Uploaded dependency on column' )
    def test_0030_verify_repository_dependencies( self ):
        '''Verify that each repository can depend on the other without causing an infinite loop.'''
        convert_repository = test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        column_repository = test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        self.check_repository_dependency( convert_repository, column_repository, self.get_repository_tip( column_repository ) )
        self.check_repository_dependency( column_repository, convert_repository, self.get_repository_tip( convert_repository ) )
    def test_0035_verify_repository_metadata( self ):
        '''Verify that resetting the metadata does not change it.'''
        column_repository = test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        convert_repository = test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        for repository in [ column_repository, convert_repository ]:
            self.verify_unchanged_repository_metadata( repository )
