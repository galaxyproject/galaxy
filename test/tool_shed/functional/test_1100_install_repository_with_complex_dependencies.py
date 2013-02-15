from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
import tool_shed.base.test_db_util as test_db_util

bwa_base_repository_name = 'bwa_base_repository_0100'
bwa_base_repository_description = "BWA Base"
bwa_base_repository_long_description = "BWA tool that depends on bwa 0.5.9, with a complex repository dependency pointing at bwa_tool_repository_0100"

bwa_tool_repository_name = 'bwa_tool_repository_0100'
bwa_tool_repository_description = "BWA Tool"
bwa_tool_repository_long_description = "BWA repository with a package tool dependency defined for BWA 0.5.9."

category_name = 'Test 0100 Complex Repository Dependencies'
category_description = 'Test 0100 Complex Repository Dependencies'
running_standalone = False

class TestInstallingComplexRepositoryDependencies( ShedTwillTestCase ):
    '''Test features related to installing repositories with complex repository dependencies.'''
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
    def test_0005_create_bwa_tool_repository( self ):
        '''Create and populate bwa_tool_0100.'''
        global running_standalone
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=bwa_tool_repository_name, 
                                                    description=bwa_tool_repository_description, 
                                                    long_description=bwa_tool_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
            old_tool_dependency = self.get_filename( os.path.join( 'bwa', 'complex', 'tool_dependencies.xml' ) )
            new_tool_dependency_path = self.generate_temp_path( 'test_1100', additional_paths=[ 'tool_dependency' ] )
            xml_filename = os.path.abspath( os.path.join( new_tool_dependency_path, 'tool_dependencies.xml' ) )
            file( xml_filename, 'w' ).write( file( old_tool_dependency, 'r' )
                                     .read().replace( '__PATH__', self.get_filename( 'bwa/complex' ) ) )
            self.upload_file( repository, 
                              filename=xml_filename,
                              filepath=new_tool_dependency_path,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded tool_dependencies.xml.',
                              strings_displayed=[ 'Name, version and type from a tool requirement tag does not match' ], 
                              strings_not_displayed=[] )
            self.display_manage_repository_page( repository, strings_displayed=[ 'Tool dependencies', 'may not be', 'in this repository' ] )
    def test_0010_create_bwa_base_repository( self ):
        '''Create and populate bwa_base_0100.'''
        global running_standalone
        if running_standalone:
            category = self.create_category( name=category_name, description=category_description )
            self.logout()
            self.login( email=common.test_user_1_email, username=common.test_user_1_name )
            repository = self.get_or_create_repository( name=bwa_base_repository_name, 
                                                        description=bwa_base_repository_description, 
                                                        long_description=bwa_base_repository_long_description, 
                                                        owner=common.test_user_1_name,
                                                        category_id=self.security.encode_id( category.id ), 
                                                        strings_displayed=[] )
            tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
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
            xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
            repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
            url = 'http://http://this is not an url!'
            name = tool_repository.name
            owner = tool_repository.user.username
            changeset_revision = self.get_repository_tip( tool_repository )
            self.generate_invalid_dependency_xml( xml_filename, url, name, owner, changeset_revision, complex=True, package='bwa', version='0.5.9' )
            strings_displayed = [ 'Invalid tool shed <b>%s</b> defined' % url ] 
            self.upload_file( repository, 
                              filename='tool_dependencies.xml',
                              filepath=dependency_path, 
                              valid_tools_only=False,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded dependency on bwa_tool_0100 with invalid url.',
                              strings_displayed=strings_displayed, 
                              strings_not_displayed=[] )
    def test_0020_generate_complex_repository_dependency_invalid_repository_name( self ):
        '''Generate and upload a complex repository definition that specifies an invalid repository name.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'shed' ] )
            xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
            base_repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
            url = self.url
            name = 'invalid_repository!?'
            owner = tool_repository.user.username
            changeset_revision = self.get_repository_tip( tool_repository )
            self.generate_invalid_dependency_xml( xml_filename, url, name, owner, changeset_revision, complex=True, package='bwa', version='0.5.9' )
            strings_displayed = [ 'Invalid repository name <b>%s</b> defined.' % name ]
            self.upload_file( base_repository, 
                              filename='tool_dependencies.xml',
                              filepath=dependency_path, 
                              valid_tools_only=False,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded dependency on bwa_tool_0100 with invalid repository name.',
                              strings_displayed=strings_displayed, 
                              strings_not_displayed=[] )
    def test_0025_generate_complex_repository_dependency_invalid_owner_name( self ):
        '''Generate and upload a complex repository definition that specifies an invalid owner.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'shed' ] )
            xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
            base_repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
            url = self.url
            name = tool_repository.name
            owner = 'invalid_owner!?'
            changeset_revision = self.get_repository_tip( tool_repository )
            self.generate_invalid_dependency_xml( xml_filename, url, name, owner, changeset_revision, complex=True, package='bwa', version='0.5.9' )
            strings_displayed = [ 'Invalid owner <b>%s</b> defined' % owner ]
            self.upload_file( base_repository, 
                              filename='tool_dependencies.xml',
                              filepath=dependency_path, 
                              valid_tools_only=False,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded dependency on bwa_tool_0100 with invalid owner.',
                              strings_displayed=strings_displayed, 
                              strings_not_displayed=[] )
    def test_0030_generate_complex_repository_dependency_invalid_changeset_revision( self ):
        '''Generate and upload a complex repository definition that specifies an invalid changeset revision.'''
        global running_standalone
        if running_standalone:
            dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'shed' ] )
            xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
            base_repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
            url = self.url
            name = tool_repository.name
            owner = tool_repository.user.username
            changeset_revision = '1234abcd'
            self.generate_invalid_dependency_xml( xml_filename, url, name, owner, changeset_revision, complex=True, package='bwa', version='0.5.9' )
            strings_displayed = [ 'Invalid changeset revision <b>%s</b> defined.' % changeset_revision ]
            self.upload_file( base_repository, 
                              filename='tool_dependencies.xml',
                              filepath=dependency_path, 
                              valid_tools_only=False,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded dependency on bwa_tool_0100 with invalid changeset revision.',
                              strings_displayed=strings_displayed, 
                              strings_not_displayed=[] )
    def test_0035_generate_valid_complex_repository_dependency( self ):
        '''Generate and upload a valid tool_dependencies.xml file that specifies bwa_tool_repository_0100.'''
        global running_standalone
        if running_standalone:
            base_repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
            dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex' ] )
            xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
            url = self.url
            name = tool_repository.name
            owner = tool_repository.user.username
            changeset_revision = self.get_repository_tip( tool_repository )
            self.generate_repository_dependency_xml( [ tool_repository ], xml_filename, complex=True, package='bwa', version='0.5.9' )
            self.upload_file( base_repository, 
                              filename='tool_dependencies.xml',
                              filepath=dependency_path, 
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False, 
                              commit_message='Uploaded valid complex dependency on bwa_tool_0100.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
            self.check_repository_dependency( base_repository, tool_repository )
            self.display_manage_repository_page( base_repository, strings_displayed=[ 'bwa', '0.5.9', 'package' ] )
    def test_0040_update_tool_repository( self ):
        '''Upload a new tool_dependencies.xml to the tool repository, and verify that the base repository displays the new changeset.'''
        global running_standalone
        if running_standalone:
            base_repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
            previous_changeset = self.get_repository_tip( tool_repository )
            old_tool_dependency = self.get_filename( os.path.join( 'bwa', 'complex', 'readme', 'tool_dependencies.xml' ) )
            new_tool_dependency_path = self.generate_temp_path( 'test_1100', additional_paths=[ 'tool_dependency' ] )
            xml_filename = os.path.abspath( os.path.join( new_tool_dependency_path, 'tool_dependencies.xml' ) )
            file( xml_filename, 'w' ).write( file( old_tool_dependency, 'r' )
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
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        base_repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
        preview_strings_displayed = [ tool_repository.name, self.get_repository_tip( tool_repository ) ]
        self.install_repository( bwa_base_repository_name, 
                                 common.test_user_1_name, 
                                 category_name,
                                 install_tool_dependencies=True, 
                                 preview_strings_displayed=preview_strings_displayed,
                                 post_submit_strings_displayed=[ base_repository.name, tool_repository.name, 'new' ],
                                 includes_tools=True )
    def test_0050_verify_installed_repositories( self ):
        '''Verify that the installed repositories are displayed properly.'''
        base_repository = test_db_util.get_installed_repository_by_name_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = test_db_util.get_installed_repository_by_name_owner( bwa_tool_repository_name, common.test_user_1_name )
        strings_displayed = [ base_repository.name, base_repository.owner, base_repository.installed_changeset_revision ]
        strings_displayed.extend( [ tool_repository.name, tool_repository.owner, tool_repository.installed_changeset_revision ] )
        strings_displayed.append( self.url.replace( 'http://', '' ) )
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed, strings_not_displayed=[] )
        checks = [ ( tool_repository,
                     [ 'bwa_tool_repository_0100', 'user1', tool_repository.installed_changeset_revision ],
                     [ 'Missing tool dependencies' ] ),
                   ( base_repository, 
                     [ 'bwa_base_repository_0100', 'user1', base_repository.installed_changeset_revision, 'bwa_tool_repository_0100', 
                       tool_repository.installed_changeset_revision ],
                     [ 'Missing tool dependencies' ] ) ]
        for repository, strings_displayed, strings_not_displayed in checks:
            self.display_installed_repository_manage_page( repository, strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )
    def test_0055_verify_complex_tool_dependency( self ):
        '''Verify that the generated env.sh contains the right data.'''
        base_repository = test_db_util.get_installed_repository_by_name_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = test_db_util.get_installed_repository_by_name_owner( bwa_tool_repository_name, common.test_user_1_name )
        env_sh_path = os.path.join( self.galaxy_tool_dependency_dir, 
                                    'bwa', 
                                    '0.5.9', 
                                    base_repository.owner, 
                                    base_repository.name, 
                                    base_repository.installed_changeset_revision, 
                                    'env.sh' )
        assert os.path.exists( env_sh_path ), 'env.sh was not generated in %s for this dependency.' % env_sh_path
        contents = file( env_sh_path, 'r' ).read()
        if tool_repository.installed_changeset_revision not in contents or tool_repository.name not in contents: 
            raise AssertionError( 'The env.sh file was not correctly generated. Contents: %s' % contents )
        
