from shed_functional.base.twilltestcase import common, ShedTwillTestCase

datatypes_repository_name = 'emboss_datatypes_0110'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."

emboss_repository_name = 'emboss_0110'
emboss_repository_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'
emboss_repository_long_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'

category_name = 'Test 0110 Invalid Repository Dependencies'
category_desc = 'Test 0110 Invalid Repository Dependencies'
running_standalone = False


class TestBasicRepositoryDependencies( ShedTwillTestCase ):
    '''Testing emboss 5 with repository dependencies.'''

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

    def test_0005_create_category( self ):
        """Create a category for this test suite"""
        self.create_category( name=category_name, description=category_desc )

    def test_0010_create_emboss_datatypes_repository_and_upload_tarball( self ):
        '''Create and populate the emboss_datatypes repository.'''
        global running_standalone
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=datatypes_repository_name,
                                             description=datatypes_repository_description,
                                             long_description=datatypes_repository_long_description,
                                             owner=common.test_user_1_name,
                                             category_id=self.security.encode_id( category.id ),
                                             strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
            self.upload_file( repository,
                              filename='emboss/datatypes/datatypes_conf.xml',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded datatypes_conf.xml.',
                              strings_displayed=[],
                              strings_not_displayed=[] )

    def test_0015_verify_datatypes_in_datatypes_repository( self ):
        '''Verify that the emboss_datatypes repository contains datatype entries.'''
        repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Datatypes', 'equicktandem', 'hennig86', 'vectorstrip' ] )

    def test_0020_create_emboss_5_repository_and_upload_files( self ):
        '''Create and populate the emboss_5_0110 repository.'''
        global running_standalone
        if running_standalone:
            category = self.test_db_util.get_category_by_name( category_name )
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
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded emboss tool tarball.',
                              strings_displayed=[],
                              strings_not_displayed=[] )

    def test_0025_generate_repository_dependency_with_invalid_url( self ):
        '''Generate a repository dependency for emboss 5 with an invalid URL.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_1110', additional_paths=[ 'simple' ] )
            datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
            emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
            url = 'http://http://this is not an url!'
            name = datatypes_repository.name
            owner = datatypes_repository.user.username
            changeset_revision = self.get_repository_tip( datatypes_repository )
            strings_displayed = [ 'Repository dependencies are currently supported only within the same tool shed' ]
            repository_tuple = ( url, name, owner, changeset_revision )
            self.create_repository_dependency( repository=emboss_repository,
                                               filepath=dependency_path,
                                               repository_tuples=[ repository_tuple ],
                                               strings_displayed=strings_displayed,
                                               complex=False )

    def test_0030_generate_repository_dependency_with_invalid_name( self ):
        '''Generate a repository dependency for emboss 5 with an invalid name.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_1110', additional_paths=[ 'simple' ] )
            repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
            emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
            url = self.url
            name = '!?invalid?!'
            owner = repository.user.username
            changeset_revision = self.get_repository_tip( repository )
            strings_displayed = [ 'because the name is invalid.' ]
            repository_tuple = ( url, name, owner, changeset_revision )
            self.create_repository_dependency( repository=emboss_repository,
                                               filepath=dependency_path,
                                               repository_tuples=[ repository_tuple ],
                                               strings_displayed=strings_displayed,
                                               complex=False )

    def test_0035_generate_repository_dependency_with_invalid_owner( self ):
        '''Generate a repository dependency for emboss 5 with an invalid owner.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_1110', additional_paths=[ 'simple' ] )
            repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
            emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
            url = self.url
            name = repository.name
            owner = '!?invalid?!'
            changeset_revision = self.get_repository_tip( repository )
            strings_displayed = [ 'because the owner is invalid.' ]
            repository_tuple = ( url, name, owner, changeset_revision )
            self.create_repository_dependency( repository=emboss_repository,
                                               filepath=dependency_path,
                                               repository_tuples=[ repository_tuple ],
                                               strings_displayed=strings_displayed,
                                               complex=False )

    def test_0040_generate_repository_dependency_with_invalid_changeset_revision( self ):
        '''Generate a repository dependency for emboss 5 with an invalid changeset revision.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_1110', additional_paths=[ 'simple', 'invalid' ] )
            repository = self.test_db_util.get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
            emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
            url = self.url
            name = repository.name
            owner = repository.user.username
            changeset_revision = '!?invalid?!'
            strings_displayed = [ 'because the changeset revision is invalid.' ]
            repository_tuple = ( url, name, owner, changeset_revision )
            self.create_repository_dependency( repository=emboss_repository,
                                               filepath=dependency_path,
                                               repository_tuples=[ repository_tuple ],
                                               strings_displayed=strings_displayed,
                                               complex=False )

    def test_0045_install_repository_with_invalid_repository_dependency( self ):
        '''Install the repository and verify that galaxy detects invalid repository dependencies.'''
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        preview_strings_displayed = [ 'emboss_0110', self.get_repository_tip( repository ), 'Ignoring repository dependency definition' ]
        self.install_repository( emboss_repository_name,
                                 common.test_user_1_name,
                                 category_name,
                                 install_tool_dependencies=False,
                                 install_repository_dependencies=True,
                                 preview_strings_displayed=preview_strings_displayed,
                                 post_submit_strings_displayed=[ repository.name, repository.name, 'New' ],
                                 includes_tools_for_display_in_tool_panel=True )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( emboss_repository_name, common.test_user_1_name )
        self.display_installed_repository_manage_page( installed_repository=installed_repository,
                                                       strings_displayed=[],
                                                       strings_not_displayed=[ 'Repository dependencies' ] )
