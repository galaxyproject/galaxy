from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os

import logging
log = logging.getLogger( __name__ )

bwa_base_repository_name = 'bwa_base_repository_0100'
bwa_base_repository_description = "BWA Base"
bwa_base_repository_long_description = "BWA tool that depends on bwa 0.5.9, with a complex repository dependency pointing at package_bwa_0_5_9_0100"

bwa_package_repository_name = 'package_bwa_0_5_9_0100'
bwa_package_repository_description = "BWA Tool"
bwa_package_repository_long_description = "BWA repository with a package tool dependency defined for BWA 0.5.9."

category_name = 'Test 0100 Complex Repository Dependencies'
category_description = 'Test 0100 Complex Repository Dependencies'

class TestComplexRepositoryDependencies( ShedTwillTestCase ):
    '''Test features related to complex repository dependencies.'''

    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )

    def test_0005_create_bwa_package_repository( self ):
        '''Create and populate package_bwa_0_5_9_0100.'''
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        # Create a repository named package_bwa_0_5_9_0100 owned by user1.
        repository = self.get_or_create_repository( name=bwa_package_repository_name, 
                                                    description=bwa_package_repository_description, 
                                                    long_description=bwa_package_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='bwa/complex/tool_dependencies.xml',
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False, 
                          commit_message='Uploaded tool_dependencies.xml.',
                          strings_displayed=[ 'This repository currently contains a single file named <b>tool_dependencies.xml</b>' ], 
                          strings_not_displayed=[] )
        # Visit the manage repository page for package_bwa_0_5_9_0100.
        self.display_manage_repository_page( repository, strings_displayed=[ 'Tool dependencies', 'will not be', 'to this repository' ] )

    def test_0010_create_bwa_base_repository( self ):
        '''Create and populate bwa_base_0100.'''
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        # Create a repository named bwa_base_repository_0100 owned by user1.
        repository = self.get_or_create_repository( name=bwa_base_repository_name, 
                                                    description=bwa_base_repository_description, 
                                                    long_description=bwa_base_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        # Populate the repository named bwa_base_repository_0100 with a bwa_base tool archive.
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
        dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'invalid' ] )
        xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
        # The repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
        url = 'http://http://this is not an url!'
        name = 'package_bwa_0_5_9_0100'
        owner = 'user1'
        changeset_revision = self.get_repository_tip( tool_repository )
        strings_displayed = [ 'Repository dependencies are currently supported only within the same tool shed' ] 
        # Populate the dependent repository named bwa_base_repository_0100 with an invalid tool_dependencies.xml file.
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
        dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'invalid' ] )
        xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
        url = self.url
        name = 'invalid_repository!?'
        owner = 'user1'
        changeset_revision = self.get_repository_tip( tool_repository )
        strings_displayed = [ 'because the name is invalid' ]
        # Populate the dependent base_repository named package_bwa_0_5_9_0100 with an invalid tool_dependencies.xml file.
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
        dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'invalid' ] )
        xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
        url = self.url
        name = 'package_bwa_0_5_9_0100'
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
        dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'invalid' ] )
        xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
        url = self.url
        name = 'package_bwa_0_5_9_0100'
        owner = 'user1'
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
 
    def test_0035_generate_complex_repository_dependency( self ):
        '''Generate and upload a valid tool_dependencies.xml file that specifies package_bwa_0_5_9_0100.'''
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
        dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex' ] )
        url = self.url
        name = 'package_bwa_0_5_9_0100'
        owner = 'user1'
        changeset_revision = self.get_repository_tip( tool_repository )
        repository_tuple = ( url, name, owner, changeset_revision )
        self.create_repository_dependency( repository=base_repository, 
                                           filepath=dependency_path, 
                                           repository_tuples=[ repository_tuple ],
                                           complex=True,
                                           package='bwa',
                                           version='0.5.9' )
        self.check_repository_dependency( base_repository, depends_on_repository=tool_repository )
        self.display_manage_repository_page( base_repository, strings_displayed=[ 'bwa', '0.5.9', 'package', changeset_revision ] )
 
    def test_0040_generate_tool_dependency( self ):
        '''Generate and upload a new tool_dependencies.xml file that specifies an arbitrary file on the filesystem, and verify that bwa_base depends on the new changeset revision.'''
        # The base_repository named bwa_base_repository_0100 is the dependent repository.
        base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        # The repository named package_bwa_0_5_9_0100 is the required repository.
        tool_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_package_repository_name, common.test_user_1_name )
        previous_changeset = self.get_repository_tip( tool_repository )
        old_tool_dependency = self.get_filename( os.path.join( 'bwa', 'complex', 'readme', 'tool_dependencies.xml' ) )
        new_tool_dependency_path = self.generate_temp_path( 'test_1100', additional_paths=[ 'tool_dependency' ] )
        xml_filename = os.path.abspath( os.path.join( new_tool_dependency_path, 'tool_dependencies.xml' ) )
        # Generate a tool_dependencies.xml file that points to an arbitrary file in the local filesystem.
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
        repository_tip = self.get_repository_tip( tool_repository )
        strings_displayed = [ 'bwa', '0.5.9', 'package' ]
        strings_displayed.append( repository_tip )
        strings_not_displayed=[ previous_changeset ]
        self.display_manage_repository_page( tool_repository, 
                                             strings_displayed=strings_displayed,
                                             strings_not_displayed=strings_not_displayed )
        # Visit the manage page of the package_bwa_0_5_9_0100 to confirm the valid tool dependency definition.
        self.display_manage_repository_page( tool_repository, 
                                             strings_displayed=strings_displayed,
                                             strings_not_displayed=strings_not_displayed )
        # Visit the manage page of the bwa_base_repository_0100 to confirm the valid tool dependency definition
        # and the updated changeset revision (updated tip) of the package_bwa_0_5_9_0100 repository is displayed
        # as the required repository revision.  The original revision defined in the previously uploaded
        # tool_dependencies.xml file will be updated.
        self.display_manage_repository_page( base_repository, 
                                             strings_displayed=strings_displayed,
                                             strings_not_displayed=strings_not_displayed )
