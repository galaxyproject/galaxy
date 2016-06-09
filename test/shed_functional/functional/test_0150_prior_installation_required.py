from shed_functional.base.twilltestcase import common, ShedTwillTestCase

column_repository_name = 'column_maker_0150'
column_repository_description = "Add column"
column_repository_long_description = "Compute an expression on every row"

convert_repository_name = 'convert_chars_0150'
convert_repository_description = "Convert delimiters"
convert_repository_long_description = "Convert delimiters to tab"

category_name = 'Test 0150 Simple Prior Installation'
category_description = 'Test 0150 Simple Prior Installation'

'''
Create column_maker and convert_chars.

Column maker repository dependency:
<repository toolshed="self.url" name="convert_chars" owner="test" changeset_revision="c3041382815c" prior_installation_required="True" />

Verify display.

Galaxy side:

Install column_maker.
Verify that convert_chars was installed first, contrary to the ordering that would be present without prior_installation_required.
'''


class TestSimplePriorInstallation( ShedTwillTestCase ):
    '''Test features related to datatype converters.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        self.test_db_util.get_private_role( test_user_1 )
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        self.test_db_util.get_private_role( admin_user )

    def test_0005_create_convert_repository( self ):
        '''Create and populate convert_chars_0150.'''
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=convert_repository_name,
                                                    description=convert_repository_description,
                                                    long_description=convert_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        self.upload_file( repository,
                          filename='convert_chars/convert_chars.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded convert_chars tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0010_create_column_repository( self ):
        '''Create and populate convert_chars_0150.'''
        category = self.create_category( name=category_name, description=category_description )
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
                          commit_message='Uploaded column_maker tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0015_create_repository_dependency( self ):
        '''Create a repository dependency specifying convert_chars.'''
        '''
        Column maker repository dependency:
            <repository toolshed="self.url" name="convert_chars" owner="test" changeset_revision="<tip>" prior_installation_required="True" />
        '''
        column_repository = self.test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        convert_repository = self.test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        dependency_xml_path = self.generate_temp_path( 'test_0150', additional_paths=[ 'column' ] )
        convert_tuple = ( self.url, convert_repository.name, convert_repository.user.username, self.get_repository_tip( convert_repository ) )
        self.create_repository_dependency( repository=column_repository,
                                           repository_tuples=[ convert_tuple ],
                                           filepath=dependency_xml_path,
                                           prior_installation_required=True )

    def test_0020_verify_repository_dependency( self ):
        '''Verify that the previously generated repositiory dependency displays correctly.'''
        column_repository = self.test_db_util.get_repository_by_name_and_owner( column_repository_name, common.test_user_1_name )
        convert_repository = self.test_db_util.get_repository_by_name_and_owner( convert_repository_name, common.test_user_1_name )
        self.check_repository_dependency( repository=column_repository,
                                          depends_on_repository=convert_repository,
                                          depends_on_changeset_revision=None,
                                          changeset_revision=None )
