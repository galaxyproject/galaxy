from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os

import logging
log = logging.getLogger( __name__ )

category_name = 'Test 1420 Tool dependency environment variable inheritance'
category_description = 'Test script 1420 for interpolation of inherited environment variables.'
package_atlas_repository_name = 'package_atlas_3_10_1420'
package_bzlib_repository_name = 'package_bzlib_1_0_1420'
package_boost_repository_name = 'package_boost_1_53_1420'
package_numpy_repository_name = 'package_numpy_1_7_1420'
package_rdkit_repository_name = 'package_rdkit_2012_12_1420'
package_lapack_repository_name = 'package_lapack_3_4_1420'
package_atlas_repository_description = 'Automatically Tuned Linear Algebra Software'
package_bzlib_repository_description = 'Contains a tool dependency definition that downloads and compiles version 1.0 of the bzlib library.'
package_boost_repository_description = 'Contains a tool dependency definition that downloads and compiles version 1.53 of the boost C++ libraries'
package_numpy_repository_description = 'Contains a tool dependency definition that downloads and compiles version 1.7 of the the python numpy package'
package_rdkit_repository_description = 'Contains a tool dependency definition that downloads and compiles version 2012-12 of the RDKit cheminformatics and machine-learning package.'
package_lapack_repository_description = 'Linear Algebra PACKage'
package_atlas_repository_long_description = '%s: %s' % ( package_atlas_repository_name, package_atlas_repository_description )
package_bzlib_repository_long_description = '%s: %s' % ( package_bzlib_repository_name, package_bzlib_repository_description )
package_boost_repository_long_description = '%s: %s' % ( package_boost_repository_name, package_boost_repository_description )
package_numpy_repository_long_description = '%s: %s' % ( package_numpy_repository_name, package_numpy_repository_description )
package_rdkit_repository_long_description = '%s: %s' % ( package_rdkit_repository_name, package_rdkit_repository_description )
package_lapack_repository_long_description = '%s: %s' % ( package_lapack_repository_name, package_lapack_repository_description )

'''
1. Create repository package_lapack_3_4_1420

2. Create repository package_atlas_3_10_1420

3. Create repository package_bzlib_1_0_1420

4. Create repository package_boost_1_53_1420

5. Create repository package_numpy_1_7_1420

6. Create repository package_rdkit_2012_12_1420

Repository dependency structure should be as follows:
    Repository package_rdkit_2012_12_1420
        Repository package_boost_1_53_1420 (prior install required)
            Repository package_bzlib_1_0_1420 (prior install required)
        Repository package_numpy_1_7_1420 (prior install required)
            Repository package_lapack_3_4_1420 (prior install required)
            Repository package_atlas_3_10_1420 (prior install required)

8. Install package_rdkit_2012_12 into Galaxy.

9. Verify that the env.sh file for package_rdkit_2012_12_1420 also defines the variables inherited from package_numpy_1_7_1420 and package_boost_1_53_1420.
'''


class TestEnvironmentInheritance( ShedTwillTestCase ):
    '''Test referencing environment variables that were defined in a separate tool dependency.'''
    
    def test_0000_initiate_users_and_category( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
        self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        test_user_2_private_role = self.test_db_util.get_private_role( test_user_2 )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        
    def test_0005_create_lapack_repository( self ):
        '''Create and populate package_lapack_3_4_1420.'''
        '''
        This is step 1 - Create repository package_lapack_3_4_1420.
        
        All tool dependency definitions should download and extract a tarball containing precompiled binaries from the local
        filesystem and install them into the path specified by $INSTALL_DIR.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=package_lapack_repository_name, 
                                                    description=package_lapack_repository_description, 
                                                    long_description=package_lapack_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        # Load the original tool dependency definition into memory, then fill in the __PATH__ placeholder with the
        # actual system path where the binary tarball is found.
        tool_dependency_path = self.generate_temp_path( '1420_tool_dependency', additional_paths=[ 'package_lapack_3_4_1420' ] )
        precompiled_binary_tarball = self.get_filename( '1420_files/binary_tarballs/lapack.tar' )
        edited_tool_dependency_filename = self.get_filename( filepath=tool_dependency_path, filename='tool_dependencies.xml' )
        original_tool_dependency = self.get_filename( '1420_files/package_lapack_3_4_1420/tool_dependencies.xml' )
        tool_dependency_definition = file( original_tool_dependency, 'r' ).read().replace( '__PATH__', precompiled_binary_tarball )
        file( edited_tool_dependency_filename, 'w' ).write( tool_dependency_definition )
        # Upload the edited tool dependency definition to the package_lapack_3_4_1420 repository.
        self.upload_file( repository, 
                          filename='tool_dependencies.xml', 
                          filepath=tool_dependency_path,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate package_lapack_3_4_1420 with tool dependency definitions.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )

    def test_0010_create_atlas_repository( self ):
        '''Create and populate package_atlas_3_10_1420.'''
        '''
        This is step 1 - Create repository package_atlas_3_10_1420.
        
        All tool dependency definitions should download and extract a tarball containing precompiled binaries from the local
        filesystem and install them into the path specified by $INSTALL_DIR.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=package_atlas_repository_name, 
                                                    description=package_atlas_repository_description, 
                                                    long_description=package_atlas_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        # Load the original tool dependency definition into memory, then fill in the __PATH__ placeholder with the
        # actual system path where the binary tarball is found.
        tool_dependency_path = self.generate_temp_path( '1420_tool_dependency', additional_paths=[ 'package_atlas_3_10_1420' ] )
        precompiled_binary_tarball = self.get_filename( '1420_files/binary_tarballs/atlas.tar' )
        edited_tool_dependency_filename = self.get_filename( filepath=tool_dependency_path, filename='tool_dependencies.xml' )
        original_tool_dependency = self.get_filename( '1420_files/package_atlas_3_10_1420/tool_dependencies.xml' )
        tool_dependency_definition = file( original_tool_dependency, 'r' ).read().replace( '__PATH__', precompiled_binary_tarball )
        file( edited_tool_dependency_filename, 'w' ).write( tool_dependency_definition )
        # Upload the edited tool dependency definition to the package_atlas_3_10_1420 repository.
        self.upload_file( repository, 
                          filename='tool_dependencies.xml', 
                          filepath=tool_dependency_path,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate package_atlas_3_10_1420 with tool dependency definitions.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        
    def test_0015_create_bzlib_repository( self ):
        '''Create and populate package_bzlib_1_0_1420.'''
        '''
        This is step 1 - Create repository package_bzlib_1_0_1420.
        
        All tool dependency definitions should download and extract a tarball containing precompiled binaries from the local
        filesystem and install them into the path specified by $INSTALL_DIR.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=package_bzlib_repository_name, 
                                                    description=package_bzlib_repository_description, 
                                                    long_description=package_bzlib_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        # Load the original tool dependency definition into memory, then fill in the __PATH__ placeholder with the
        # actual system path where the binary tarball is found.
        tool_dependency_path = self.generate_temp_path( '1420_tool_dependency', additional_paths=[ 'package_bzlib_1_0_1420' ] )
        precompiled_binary_tarball = self.get_filename( '1420_files/binary_tarballs/bzlib.tar' )
        edited_tool_dependency_filename = self.get_filename( filepath=tool_dependency_path, filename='tool_dependencies.xml' )
        original_tool_dependency = self.get_filename( '1420_files/package_bzlib_1_0_1420/tool_dependencies.xml' )
        tool_dependency_definition = file( original_tool_dependency, 'r' ).read().replace( '__PATH__', precompiled_binary_tarball )
        file( edited_tool_dependency_filename, 'w' ).write( tool_dependency_definition )
        # Upload the edited tool dependency definition to the package_bzlib_1_0_1420 repository.
        self.upload_file( repository, 
                          filename='tool_dependencies.xml', 
                          filepath=tool_dependency_path,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate package_bzlib_1_0_1420 with tool dependency definitions.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        
    def test_0020_create_boost_repository( self ):
        '''Create and populate package_boost_1_53_1420.'''
        '''
        This is step 1 - Create repository package_boost_1_53_1420.
        
        All tool dependency definitions should download and extract a tarball containing precompiled binaries from the local
        filesystem and install them into the path specified by $INSTALL_DIR.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=package_boost_repository_name, 
                                                    description=package_boost_repository_description, 
                                                    long_description=package_boost_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        # Load the original tool dependency definition into memory, then fill in the __PATH__ placeholder with the
        # actual system path where the binary tarball is found.
        tool_dependency_path = self.generate_temp_path( '1420_tool_dependency', additional_paths=[ 'package_boost_1_53_1420' ] )
        precompiled_binary_tarball = self.get_filename( '1420_files/binary_tarballs/boost.tar' )
        edited_tool_dependency_filename = self.get_filename( filepath=tool_dependency_path, filename='tool_dependencies.xml' )
        original_tool_dependency = self.get_filename( '1420_files/package_boost_1_53_1420/tool_dependencies.xml' )
        tool_dependency_definition = file( original_tool_dependency, 'r' ).read().replace( '__PATH__', precompiled_binary_tarball )
        file( edited_tool_dependency_filename, 'w' ).write( tool_dependency_definition )
        # Upload the edited tool dependency definition to the package_boost_1_53_1420 repository.
        self.upload_file( repository, 
                          filename='tool_dependencies.xml', 
                          filepath=tool_dependency_path,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate package_boost_1_53_1420 with tool dependency definitions.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )

    def test_0025_create_numpy_repository( self ):
        '''Create and populate package_numpy_1_7_1420.'''
        '''
        This is step 1 - Create repository package_numpy_1_7_1420.
        
        All tool dependency definitions should download and extract a tarball containing precompiled binaries from the local
        filesystem and install them into the path specified by $INSTALL_DIR.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=package_numpy_repository_name, 
                                                    description=package_numpy_repository_description, 
                                                    long_description=package_numpy_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        # Load the original tool dependency definition into memory, then fill in the __PATH__ placeholder with the
        # actual system path where the binary tarball is found.
        tool_dependency_path = self.generate_temp_path( '1420_tool_dependency', additional_paths=[ 'package_numpy_1_7_1420' ] )
        precompiled_binary_tarball = self.get_filename( '1420_files/binary_tarballs/numpy.tar' )
        edited_tool_dependency_filename = self.get_filename( filepath=tool_dependency_path, filename='tool_dependencies.xml' )
        original_tool_dependency = self.get_filename( '1420_files/package_numpy_1_7_1420/tool_dependencies.xml' )
        tool_dependency_definition = file( original_tool_dependency, 'r' ).read().replace( '__PATH__', precompiled_binary_tarball )
        file( edited_tool_dependency_filename, 'w' ).write( tool_dependency_definition )
        # Upload the edited tool dependency definition to the package_numpy_1_7_1420 repository.
        self.upload_file( repository, 
                          filename='tool_dependencies.xml', 
                          filepath=tool_dependency_path,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate package_numpy_1_7_1420 with tool dependency definitions.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )

    def test_0030_create_rdkit_repository( self ):
        '''Create and populate package_rdkit_2012_12_1420.'''
        '''
        This is step 1 - Create repository package_rdkit_2012_12_1420.
        
        All tool dependency definitions should download and extract a tarball containing precompiled binaries from the local
        filesystem and install them into the path specified by $INSTALL_DIR.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=package_rdkit_repository_name, 
                                                    description=package_rdkit_repository_description, 
                                                    long_description=package_rdkit_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        # Load the original tool dependency definition into memory, then fill in the __PATH__ placeholder with the
        # actual system path where the binary tarball is found.
        tool_dependency_path = self.generate_temp_path( '1420_tool_dependency', additional_paths=[ 'package_rdkit_2012_12_1420' ] )
        precompiled_binary_tarball = self.get_filename( '1420_files/binary_tarballs/rdkit.tar' )
        edited_tool_dependency_filename = self.get_filename( filepath=tool_dependency_path, filename='tool_dependencies.xml' )
        original_tool_dependency = self.get_filename( '1420_files/package_rdkit_2012_12_1420/tool_dependencies.xml' )
        tool_dependency_definition = file( original_tool_dependency, 'r' ).read().replace( '__PATH__', precompiled_binary_tarball )
        file( edited_tool_dependency_filename, 'w' ).write( tool_dependency_definition )
        # Upload the edited tool dependency definition to the package_rdkit_2012_12_1420 repository.
        self.upload_file( repository, 
                          filename='tool_dependencies.xml', 
                          filepath=tool_dependency_path,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate package_rdkit_2012_12_1420 with tool dependency definitions.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )

    def test_0035_install_rdkit_2012_12_repository( self ):
        '''Install the package_rdkit_2012_12_1420 repository into Galaxy.'''
        '''
        This is step 4 - Install package_rdkit_2012_12_1420 into Galaxy.
        
        Install package_rdkit_2012_12_1420 with tool dependencies selected to be installed. The result of this should be 
        package_atlas_3_10_1420, package_bzlib_1_0_1420, package_boost_1_53_1420, package_numpy_1_7_1420, package_rdkit_2012_12_1420,
        and package_lapack_3_4_1420 being installed, and an env.sh generated for package_rdkit_2012_12_1420 that
        contains environment variables defined in package_boost_1_53_1420 and package_numpy_1_7_1420.
        '''
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        post_submit_strings_displayed = [ 'package_rdkit_2012_12_1420', 'package_atlas_3_10_1420', 'package_bzlib_1_0_1420',
                                          'package_numpy_1_7_1420', 'package_lapack_3_4_1420', 'package_boost_1_53_1420' ]
        self.install_repository( 'package_rdkit_2012_12_1420', 
                                 common.test_user_1_name, 
                                 category_name,
                                 install_tool_dependencies=True,
                                 post_submit_strings_displayed=post_submit_strings_displayed )
        
    def test_0040_verify_env_sh_contents( self ):
        '''Check the env.sh file for the appropriate contents.'''
        '''
        This is step 5 - Verify that the env.sh file for package_rdkit_2012_12_1420 also defines the variables inherited from package_numpy_1_7_1420
        and package_boost_1_53_1420. Test for the numpy and boost tool dependency paths.
        '''
        package_rdkit_repository = self.test_db_util.get_installed_repository_by_name_owner( 'package_rdkit_2012_12_1420', common.test_user_1_name )
        package_numpy_repository = self.test_db_util.get_installed_repository_by_name_owner( 'package_numpy_1_7_1420', common.test_user_1_name )
        package_boost_repository = self.test_db_util.get_installed_repository_by_name_owner( 'package_boost_1_53_1420', common.test_user_1_name )
        rdkit_env_sh = self.get_env_sh_path( tool_dependency_name='rdkit', 
                                             tool_dependency_version='2012_12_1', 
                                             repository=package_rdkit_repository )
        numpy_tool_dependency_path = self.get_tool_dependency_path( tool_dependency_name='numpy', 
                                                                    tool_dependency_version='1.7.1', 
                                                                    repository=package_numpy_repository )
        boost_tool_dependency_path = self.get_tool_dependency_path( tool_dependency_name='boost', 
                                                                    tool_dependency_version='1.53.0', 
                                                                    repository=package_boost_repository )
        rdkit_env_file_contents = file( rdkit_env_sh, 'r' ).read()
        if numpy_tool_dependency_path not in rdkit_env_file_contents or boost_tool_dependency_path not in rdkit_env_file_contents:
            message = 'Environment file for package_rdkit_2012_12_1420 does not contain expected path.'
            message += '\nExpected:\n%s\n%s\nContents:\n%s' % ( numpy_tool_dependency_path, boost_tool_dependency_path, rdkit_env_file_contents )
            raise AssertionError( message )
