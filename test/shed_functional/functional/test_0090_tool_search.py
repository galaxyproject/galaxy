from shed_functional.base.twilltestcase import common, ShedTwillTestCase

emboss_datatypes_repository_name = 'emboss_datatypes_0090'
emboss_datatypes_repository_description = "Datatypes for emboss"
emboss_datatypes_repository_long_description = "Long description of Emboss' datatypes"

emboss_repository_name = 'emboss_0090'
emboss_repository_description = "Galaxy's emboss tool"
emboss_repository_long_description = "Long description of Galaxy's emboss tool"

filtering_repository_name = 'filtering_0090'
filtering_repository_description = "Galaxy's filtering tool"
filtering_repository_long_description = "Long description of Galaxy's filtering tool"

freebayes_repository_name = 'freebayes_0090'
freebayes_repository_description = "Galaxy's freebayes tool"
freebayes_repository_long_description = "Long description of Galaxy's freebayes tool"

bwa_base_repository_name = 'bwa_base_0090'
bwa_base_repository_description = "BWA Base"
bwa_base_repository_long_description = "NT space mapping with BWA"

bwa_color_repository_name = 'bwa_color_0090'
bwa_color_repository_description = "BWA Color"
bwa_color_repository_long_description = "Color space mapping with BWA"

category_name = 'Test 0090 Tool Search And Installation'
category_description = 'Test 0090 Tool Search And Installation'


class TestRepositoryCircularDependenciesAgain( ShedTwillTestCase ):
    '''Test more features related to repository dependencies.'''

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

    def test_0005_create_bwa_base_repository( self ):
        '''Create and populate bwa_base_0090.'''
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=bwa_base_repository_name,
                                                    description=bwa_base_repository_description,
                                                    long_description=bwa_base_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        self.upload_file( repository,
                          filename='bwa/bwa_base.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded BWA tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0010_create_bwa_color_repository( self ):
        '''Create and populate bwa_color_0090.'''
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=bwa_color_repository_name,
                                                    description=bwa_color_repository_description,
                                                    long_description=bwa_color_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        self.upload_file( repository,
                          filename='bwa/bwa_color.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded BWA color tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0015_create_emboss_datatypes_repository( self ):
        '''Create and populate emboss_datatypes_0090.'''
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=emboss_datatypes_repository_name,
                                                    description=emboss_datatypes_repository_description,
                                                    long_description=emboss_datatypes_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        self.upload_file( repository,
                          filename='emboss/datatypes/datatypes_conf.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded datatypes_conf.xml.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0020_create_emboss_repository( self ):
        '''Create and populate emboss_0090.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=emboss_repository_name,
                                                    description=emboss_repository_description,
                                                    long_description=emboss_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        self.upload_file( repository,
                          filename='emboss/emboss.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded emboss tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0025_create_filtering_repository( self ):
        '''Create and populate filtering_0090.'''
        category = self.create_category( name=category_name, description=category_description )
        filtering_repository = self.get_or_create_repository( name=filtering_repository_name,
                                                              description=filtering_repository_description,
                                                              long_description=filtering_repository_long_description,
                                                              owner=common.test_user_1_name,
                                                              category_id=self.security.encode_id( category.id ),
                                                              strings_displayed=[] )
        self.upload_file( filtering_repository,
                          filename='filtering/filtering_1.1.0.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded filtering 1.1.0 tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0030_create_freebayes_repository( self ):
        '''Create and populate freebayes_0090.'''
        category = self.create_category( name=category_name, description=category_description )
        repository = self.get_or_create_repository( name=freebayes_repository_name,
                                                    description=freebayes_repository_description,
                                                    long_description=freebayes_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        self.upload_file( repository,
                          filename='freebayes/freebayes.tar',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=True,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded freebayes tarball.',
                          strings_displayed=[],
                          strings_not_displayed=[] )

    def test_0035_create_and_upload_dependency_definitions( self ):
        '''Create and upload repository dependency definitions.'''
        bwa_color_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_color_repository_name, common.test_user_1_name )
        bwa_base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_datatypes_repository_name, common.test_user_1_name )
        emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        filtering_repository = self.test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
        freebayes_repository = self.test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        dependency_xml_path = self.generate_temp_path( 'test_0090', additional_paths=[ 'freebayes' ] )
        freebayes_tuple = ( self.url, freebayes_repository.name, freebayes_repository.user.username, self.get_repository_tip( freebayes_repository ) )
        emboss_tuple = ( self.url, emboss_repository.name, emboss_repository.user.username, self.get_repository_tip( emboss_repository ) )
        datatypes_tuple = ( self.url, datatypes_repository.name, datatypes_repository.user.username, self.get_repository_tip( datatypes_repository ) )
        filtering_tuple = ( self.url, filtering_repository.name, filtering_repository.user.username, self.get_repository_tip( filtering_repository ) )
        self.create_repository_dependency( repository=emboss_repository, repository_tuples=[ datatypes_tuple ], filepath=dependency_xml_path )
        self.create_repository_dependency( repository=filtering_repository, repository_tuples=[ freebayes_tuple ], filepath=dependency_xml_path )
        self.create_repository_dependency( repository=bwa_base_repository, repository_tuples=[ emboss_tuple ], filepath=dependency_xml_path )
        self.create_repository_dependency( repository=bwa_color_repository, repository_tuples=[ filtering_tuple ], filepath=dependency_xml_path )

    def test_0040_verify_repository_dependencies( self ):
        '''Verify the generated dependency structure.'''
        bwa_color_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_color_repository_name, common.test_user_1_name )
        bwa_base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        emboss_datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_datatypes_repository_name, common.test_user_1_name )
        emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        filtering_repository = self.test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
        freebayes_repository = self.test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
        self.check_repository_dependency( emboss_repository, emboss_datatypes_repository )
        self.check_repository_dependency( filtering_repository, freebayes_repository )
        self.check_repository_dependency( bwa_base_repository, emboss_repository )
        self.check_repository_dependency( bwa_color_repository, filtering_repository )
