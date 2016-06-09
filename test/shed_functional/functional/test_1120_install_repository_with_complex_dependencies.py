import os

from shed_functional.base.twilltestcase import common, ShedTwillTestCase

bwa_base_repository_name = 'bwa_base_repository_0100'
bwa_base_repository_description = "BWA Base"
bwa_base_repository_long_description = "BWA tool that depends on bwa 0.5.9, with a complex repository dependency pointing at package_bwa_0_5_9_0100"

bwa_package_repository_name = 'package_bwa_0_5_9_0100'
bwa_package_repository_description = "BWA Package"
bwa_package_repository_long_description = "BWA repository with a package tool dependency defined to compile and install BWA 0.5.9."

category_name = 'Test 0100 Complex Repository Dependencies'
category_description = 'Test 0100 Complex Repository Dependencies'
running_standalone = False


class TestInstallingComplexRepositoryDependencies( ShedTwillTestCase ):
    '''Test features related to installing repositories with complex repository dependencies.'''

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

    def test_0005_create_bwa_package_repository( self ):
        '''Create and populate package_bwa_0_5_9_0100.'''
        global running_standalone
        category = self.create_category( name=category_name, description=category_description )
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=bwa_package_repository_name,
                                                    description=bwa_package_repository_description,
                                                    long_description=bwa_package_repository_long_description,
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ),
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
            old_tool_dependency = self.get_filename( os.path.join( 'bwa', 'complex', 'tool_dependencies.xml' ) )
            new_tool_dependency_path = self.generate_temp_path( 'test_1100', additional_paths=[ 'tool_dependency' ] )
            xml_filename = os.path.abspath( os.path.join( new_tool_dependency_path, 'tool_dependencies.xml' ) )
            open( xml_filename, 'w' ).write( open( old_tool_dependency, 'r' )
                                     .read().replace( '__PATH__', self.get_filename( 'bwa/complex' ) ) )
            self.upload_file( repository,
                              filename=xml_filename,
                              filepath=new_tool_dependency_path,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded tool_dependencies.xml.',
                              strings_displayed=[ 'This repository currently contains a single file named <b>tool_dependencies.xml</b>' ],
                              strings_not_displayed=[] )
            self.display_manage_repository_page( repository, strings_displayed=[ 'Tool dependencies', 'consider setting its type' ] )

    def test_0010_create_bwa_base_repository( self ):
        '''Create and populate bwa_base_0100.'''
        global running_standalone
        if running_standalone:
            category = self.create_category( name=category_name, description=category_description )
            self.login( email=common.test_user_1_email, username=common.test_user_1_name )
            repository = self.get_or_create_repository( name=bwa_base_repository_name,
                                                        description=bwa_base_repository_description,
                                                        long_description=bwa_base_repository_long_description,
                                                        owner=common.test_user_1_name,
                                                        category_id=self.security.encode_id( category.id ),
                                                        strings_displayed=[] )
            self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
            self.upload_file( repository,
                              filename='bwa/complex/bwa_base.tar',
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=True,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded bwa_base.tar with tool wrapper XML, but without tool dependency XML.',
                              strings_displayed=[],
                              strings_not_displayed=[] )

    def test_0015_generate_complex_repository_dependency_invalid_shed_url( self ):
        '''Generate and upload a complex repository definition that specifies an invalid tool shed URL.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'shed' ] )
            base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
            url = 'http://http://this is not an url!'
            name = tool_repository.name
            owner = tool_repository.user.username
            changeset_revision = self.get_repository_tip( tool_repository )
            strings_displayed = [ 'Repository dependencies are currently supported only within the same tool shed' ]
            repository_tuple = ( url, name, owner, changeset_revision )
            self.create_repository_dependency( repository=base_repository,
                                               filepath=dependency_path,
                                               repository_tuples=[ repository_tuple ],
                                               strings_displayed=strings_displayed,
                                               complex=True,
                                               package='bwa',
                                               version='0.5.9' )

    def test_0020_generate_complex_repository_dependency_invalid_repository_name( self ):
        '''Generate and upload a complex repository definition that specifies an invalid repository name.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'shed' ] )
            base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
            url = self.url
            name = 'invalid_repository!?'
            owner = tool_repository.user.username
            changeset_revision = self.get_repository_tip( tool_repository )
            strings_displayed = [ 'because the name is invalid.' ]
            repository_tuple = ( url, name, owner, changeset_revision )
            self.create_repository_dependency( repository=base_repository,
                                               filepath=dependency_path,
                                               repository_tuples=[ repository_tuple ],
                                               strings_displayed=strings_displayed,
                                               complex=True,
                                               package='bwa',
                                               version='0.5.9' )

    def test_0025_generate_complex_repository_dependency_invalid_owner_name( self ):
        '''Generate and upload a complex repository definition that specifies an invalid owner.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'shed' ] )
            base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
            url = self.url
            name = tool_repository.name
            owner = 'invalid_owner!?'
            changeset_revision = self.get_repository_tip( tool_repository )
            strings_displayed = [ 'because the owner is invalid.' ]
            repository_tuple = ( url, name, owner, changeset_revision )
            self.create_repository_dependency( repository=base_repository,
                                               filepath=dependency_path,
                                               repository_tuples=[ repository_tuple ],
                                               strings_displayed=strings_displayed,
                                               complex=True,
                                               package='bwa',
                                               version='0.5.9' )

    def test_0030_generate_complex_repository_dependency_invalid_changeset_revision( self ):
        '''Generate and upload a complex repository definition that specifies an invalid changeset revision.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'shed' ] )
            base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
            url = self.url
            name = tool_repository.name
            owner = tool_repository.user.username
            changeset_revision = '1234abcd'
            strings_displayed = [ 'because the changeset revision is invalid.' ]
            repository_tuple = ( url, name, owner, changeset_revision )
            self.create_repository_dependency( repository=base_repository,
                                               filepath=dependency_path,
                                               repository_tuples=[ repository_tuple ],
                                               strings_displayed=strings_displayed,
                                               complex=True,
                                               package='bwa',
                                               version='0.5.9' )

    def test_0035_generate_valid_complex_repository_dependency( self ):
        '''Generate and upload a valid tool_dependencies.xml file that specifies package_bwa_0_5_9_0100.'''
        global running_standalone
        if running_standalone:
            base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
            dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex' ] )
            url = self.url
            name = tool_repository.name
            owner = tool_repository.user.username
            changeset_revision = self.get_repository_tip( tool_repository )
            repository_tuple = ( url, name, owner, changeset_revision )
            self.create_repository_dependency( repository=base_repository,
                                               filepath=dependency_path,
                                               repository_tuples=[ repository_tuple ],
                                               complex=True,
                                               package='bwa',
                                               version='0.5.9' )
            self.check_repository_dependency( base_repository, tool_repository )
            self.display_manage_repository_page( base_repository, strings_displayed=[ 'bwa', '0.5.9', 'package' ] )

    def test_0040_update_tool_repository( self ):
        '''Upload a new tool_dependencies.xml to the tool repository, and verify that the base repository displays the new changeset.'''
        global running_standalone
        if running_standalone:
            base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
            previous_changeset = self.get_repository_tip( tool_repository )
            old_tool_dependency = self.get_filename( os.path.join( 'bwa', 'complex', 'readme', 'tool_dependencies.xml' ) )
            new_tool_dependency_path = self.generate_temp_path( 'test_1100', additional_paths=[ 'tool_dependency' ] )
            xml_filename = os.path.abspath( os.path.join( new_tool_dependency_path, 'tool_dependencies.xml' ) )
            open( xml_filename, 'w' ).write( open( old_tool_dependency, 'r' )
                                     .read().replace( '__PATH__', self.get_filename( 'bwa/complex' ) ) )
            self.upload_file( tool_repository,
                              filename=xml_filename,
                              filepath=new_tool_dependency_path,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded new tool_dependencies.xml.',
                              strings_displayed=[],
                              strings_not_displayed=[] )
            # Verify that the dependency display has been updated as a result of the new tool_dependencies.xml file.
            self.display_manage_repository_page( base_repository,
                                                 strings_displayed=[ self.get_repository_tip( tool_repository ), 'bwa', '0.5.9', 'package' ],
                                                 strings_not_displayed=[ previous_changeset ] )

    def test_0045_install_base_repository( self ):
        '''Verify installation of the repository with complex repository dependencies.'''
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
        preview_strings_displayed = [ tool_repository.name, self.get_repository_tip( tool_repository ) ]
        self.install_repository( bwa_base_repository_name,
                                 common.test_user_1_name,
                                 category_name,
                                 install_tool_dependencies=True,
                                 preview_strings_displayed=preview_strings_displayed,
                                 post_submit_strings_displayed=[ base_repository.name, tool_repository.name, 'New' ],
                                 includes_tools_for_display_in_tool_panel=True )

    def test_0050_verify_installed_repositories( self ):
        '''Verify that the installed repositories are displayed properly.'''
        base_repository = self.test_db_util.get_installed_repository_by_name_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = self.test_db_util.get_installed_repository_by_name_owner( bwa_package_repository_name, common.test_user_1_name )
        strings_displayed = [ 'bwa_base_repository_0100', 'user1', base_repository.installed_changeset_revision ]
        strings_displayed.extend( [ 'package_bwa_0_5_9_0100', 'user1', tool_repository.installed_changeset_revision ] )
        strings_displayed.append( self.url.replace( 'http://', '' ) )
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed, strings_not_displayed=[] )
        strings_displayed = [ 'package_bwa_0_5_9_0100', 'user1', tool_repository.installed_changeset_revision ]
        strings_not_displayed = [ 'Missing tool dependencies' ]
        self.display_installed_repository_manage_page( tool_repository,
                                                       strings_displayed=strings_displayed,
                                                       strings_not_displayed=strings_not_displayed )
        strings_displayed = [ 'bwa_base_repository_0100',
                              'user1',
                              'package_bwa_0_5_9_0100',
                              base_repository.installed_changeset_revision,
                              tool_repository.installed_changeset_revision ]
        strings_not_displayed = [ 'Missing tool dependencies' ]
        self.display_installed_repository_manage_page( base_repository,
                                                       strings_displayed=strings_displayed,
                                                       strings_not_displayed=strings_not_displayed )

    def test_0055_verify_complex_tool_dependency( self ):
        '''Verify that the generated env.sh contains the right data.'''
        base_repository = self.test_db_util.get_installed_repository_by_name_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = self.test_db_util.get_installed_repository_by_name_owner( bwa_package_repository_name, common.test_user_1_name )
        env_sh_path = self.get_env_sh_path( tool_dependency_name='bwa',
                                            tool_dependency_version='0.5.9',
                                            repository=base_repository )
        assert os.path.exists( env_sh_path ), 'env.sh was not generated in %s for this dependency.' % env_sh_path
        contents = open( env_sh_path, 'r' ).read()
        if tool_repository.installed_changeset_revision not in contents:
            raise AssertionError( 'Installed changeset revision %s not found in env.sh.\nContents of env.sh: %s' %
                                  ( tool_repository.installed_changeset_revision, contents ) )
        if 'package_bwa_0_5_9_0100' not in contents:
            raise AssertionError( 'Repository name package_bwa_0_5_9_0100 not found in env.sh.\nContents of env.sh: %s' % contents )

    def test_0060_verify_tool_dependency_uninstallation( self ):
        '''Uninstall the package_bwa_0_5_9_0100 repository.'''
        '''
        Uninstall the repository that defines a tool dependency relationship on BWA 0.5.9, and verify
        that this results in the compiled binary package also being removed.
        '''
        tool_repository = self.test_db_util.get_installed_repository_by_name_owner( bwa_package_repository_name, common.test_user_1_name )
        self.deactivate_repository( tool_repository )
        env_sh_path = os.path.join( self.galaxy_tool_dependency_dir,
                                    'bwa',
                                    '0.5.9',
                                    tool_repository.owner,
                                    tool_repository.name,
                                    tool_repository.installed_changeset_revision,
                                    'env.sh' )
        assert os.path.exists( env_sh_path ), 'Path %s does not exist after deactivating the repository that generated it.' % env_sh_path
