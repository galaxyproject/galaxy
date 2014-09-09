from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os

import logging
log = logging.getLogger( __name__ )

category_name = 'Test 0460 Automatic repository revision completion'
category_description = 'Test 0460 Automatic repository revision completion'
datatypes_repository_name = 'emboss_datatypes_0460'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."
bwa_repository_name = 'package_bwa_0_5_9_0460'
bwa_repository_description = "Contains a tool dependency definition that downloads and compiles version 0.5.9 of the BWA package"
bwa_repository_long_description = "bwa (alignment via Burrows-Wheeler transformation) 0.5.9-r16 by Heng Li"

'''
For all steps, verify that the generated dependency points to the tip of the specified repository.

1)  Create and populate emboss_datatypes_0460.
 
2)  Create and populate package_bwa_0_5_9_0460

3)  Create complex_dependency_test_1_0460, complex_dependency_test_2_0460, complex_dependency_test_3_0460,
    complex_dependency_test_4_0460, complex_dependency_test_5_0460.

4)  Upload an uncompressed tool_dependencies.xml to complex_dependency_test_1_0460 that specifies a complex
    repository dependency on package_bwa_0_5_9_0460 without a specified changeset revision or tool shed url. 
    
5)  Upload a tarball to complex_dependency_test_2_0460 with a tool_dependencies.xml in the root of the tarball.

6)  Upload a tarball to complex_dependency_test_3_0460 with a tool_dependencies.xml in a subfolder within the tarball.

7)  Create hg_tool_dependency_0460 and hg_subfolder_tool_dependency_0460 and populate with tool dependencies.

8)  Upload to complex_dependency_test_4_0460 using the url hg://<tool shed url>/repos/user1/hg_tool_dependency_0460.

9)  Upload to complex_dependency_test_5_0460 using the url hg://<tool shed url>/repos/user1/hg_subfolder_tool_dependency_0460.

10) Create repository_dependency_test_1_0460, repository_dependency_test_2_0460, repository_dependency_test_3_0460,
    repository_dependency_test_4_0460, repository_dependency_test_4_0460.

11) Upload an uncompressed repository_dependencies.xml to repository_dependency_test_1_0460 that specifies a 
    repository dependency on emboss_datatypes_0460 without a specified changeset revision or tool shed url. 

12) Upload a tarball to repository_dependency_test_1_0460 with a repository_dependencies.xml in the root of the tarball.

13) Upload a tarball to repository_dependency_test_1_0460 with a repository_dependencies.xml in a subfolder within the tarball.

14) Create hg_repository_dependency_0460 and populate with repository_dependencies.xml.

15) Upload to repository_dependency_test_4_0460 using the url hg://<tool shed url>/repos/user1/hg_repository_dependency_0460.

16) Upload to repository_dependency_test_5_0460 using the url hg://<tool shed url>/repos/user1/hg_repository_dependency_0460.
'''


class TestAutomaticDependencyRevision( ShedTwillTestCase ):
    '''Test defining repository dependencies without specifying the changeset revision.'''
    
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.test_user_2_email, username=common.test_user_2_name )
        test_user_2 = self.test_db_util.get_user( common.test_user_2_email )
        assert test_user_2 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_2_email
        test_user_2_private_role = self.test_db_util.get_private_role( test_user_2 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
        
    def test_0005_create_datatypes_repository( self ):
        '''Create and populate the emboss_datatypes_0460 repository'''
        '''
        This is step 1 - Create and populate emboss_datatypes_0460.
        '''
        self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=datatypes_repository_name, 
                                                    description=datatypes_repository_description, 
                                                    long_description=datatypes_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='emboss/datatypes/datatypes_conf.xml', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate emboss_datatypes_0460 with datatype definitions.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
    
    def test_0010_create_bwa_package_repository( self ):
        '''Create and populate the package_bwa_0_5_9_0460 repository.'''
        '''
        This is step 2 - Create and populate package_bwa_0_5_9_0460.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name=bwa_repository_name, 
                                                    description=bwa_repository_description, 
                                                    long_description=bwa_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='bwa/complex/tool_dependencies.xml', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate package_bwa_0_5_9_0460 with a tool dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )

    def test_0015_create_tool_dependency_repositories( self ):
        '''Create repositories for testing complex dependency generation.'''
        '''
        This is step 3 - Create complex_dependency_test_1_0460, complex_dependency_test_2_0460, complex_dependency_test_3_0460,
        complex_dependency_test_4_0460, complex_dependency_test_5_0460. Each of these repositories will be populated in a way
        that tests a different way to achieve the same resulting dependency structure using complex tool dependencies.
        The different methods being tested are:
        - Upload an uncompressed tool_dependencies.xml to the root of the repository.
        - Upload a tool_dependencies.xml in a tarball, not in a subfolder.
        - Upload a tool_dependencies.xml in a subfolder within a tarball.
        - Upload via url, with the tool_dependencies.xml in the root of another repository.
        - Upload via url, with the tool_dependencies.xml in a subfolder within another repository.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository_base_name = 'complex_dependency_test_%d_0460'
        repository_base_description = 'Test #%d for complex repository dependency definitions.'
        repository_base_long_description = 'Test #%d for complex repository dependency definitions.'
        for number in range( 1, 6 ):
            repository = self.get_or_create_repository( name=repository_base_name % number, 
                                                        description=repository_base_description % number, 
                                                        long_description=repository_base_long_description % number, 
                                                        owner=common.test_user_1_name,
                                                        category_id=self.security.encode_id( category.id ), 
                                                        strings_displayed=[] )
            
    def test_0020_populate_complex_dependency_test_1_0460( self ):
        '''Populate complex_dependency_test_1_0460.'''
        '''
        This is step 4 - Upload an uncompressed tool_dependencies.xml to complex_dependency_test_1_0460 that specifies
        a complex repository dependency on package_bwa_0_5_9_0460 without a specified changeset revision or tool shed url.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( 'complex_dependency_test_1_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'package_bwa_0_5_9_0460', common.test_user_1_name )
        self.upload_file( repository, 
                          filename='0460_files/tool_dependencies.xml', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded complex repository dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'package_bwa_0_5_9_0460', 'bwa', '0.5.9', 'package', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, filename='tool_dependencies.xml', strings_displayed=[ changeset_revision ] )

    def test_0025_populate_complex_dependency_test_2_0460( self ):
        '''Populate complex_dependency_test_2_0460.'''
        '''
        This is step 5 - Upload an tarball with tool_dependencies.xml to complex_dependency_test_2_0460 that specifies
        a complex repository dependency on package_bwa_0_5_9_0460 without a specified changeset revision or tool shed url.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( 'complex_dependency_test_2_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'package_bwa_0_5_9_0460', common.test_user_1_name )
        self.upload_file( repository, 
                          filename='0460_files/tool_dependencies_in_root.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=True,
                          commit_message='Uploaded complex repository dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'package_bwa_0_5_9_0460', 'bwa', '0.5.9', 'package', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, filename='tool_dependencies.xml', strings_displayed=[ changeset_revision ] )

    def test_0030_populate_complex_dependency_test_3_0460( self ):
        '''Populate complex_dependency_test_3_0460.'''
        '''
        This is step 6 - Upload an tarball with tool_dependencies.xml in a subfolder to complex_dependency_test_3_0460 that
        specifies a complex repository dependency on package_bwa_0_5_9_0460 without a specified changeset revision or tool shed url.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( 'complex_dependency_test_3_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'package_bwa_0_5_9_0460', common.test_user_1_name )
        self.upload_file( repository, 
                          filename='0460_files/tool_dependencies_in_subfolder.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=True,
                          commit_message='Uploaded complex repository dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'package_bwa_0_5_9_0460', 'bwa', '0.5.9', 'package', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, 
                                               filename='tool_dependencies.xml', 
                                               filepath='subfolder', 
                                               strings_displayed=[ changeset_revision ] )

    def test_0035_create_repositories_for_url_upload( self ):
        '''Create and populate hg_tool_dependency_0460 and hg_subfolder_tool_dependency_0460.'''
        '''
        This is step 7 - Create hg_tool_dependency_0460 and hg_subfolder_tool_dependency_0460 and populate with tool dependencies.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name='hg_tool_dependency_0460', 
                                                    description=bwa_repository_description, 
                                                    long_description=bwa_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='0460_files/tool_dependencies.xml', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate hg_tool_dependency_0460 with a tool dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        repository = self.get_or_create_repository( name='hg_subfolder_tool_dependency_0460', 
                                                    description=bwa_repository_description, 
                                                    long_description=bwa_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='0460_files/tool_dependencies_in_subfolder.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate hg_subfolder_tool_dependency_0460 with a tool dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
    
    def test_0040_url_upload_to_complex_test( self ):
        '''Populate complex_dependency_test_4_0460.'''
        '''
        This is step 8 - Upload to complex_dependency_test_4_0460 using the url hg://<tool shed url>/repos/user1/hg_tool_dependency_0460.
        '''
        url = 'hg://%s:%s/repos/user1/hg_tool_dependency_0460' % ( self.host, self.port )
        repository = self.test_db_util.get_repository_by_name_and_owner( 'complex_dependency_test_4_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'package_bwa_0_5_9_0460', common.test_user_1_name )
        self.upload_url( repository, 
                         url=url, 
                         filepath=None,
                         valid_tools_only=True,
                         uncompress_file=False,
                         remove_repo_files_not_in_tar=True,
                         commit_message='Uploaded complex repository dependency definition.',
                         strings_displayed=[], 
                         strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'package_bwa_0_5_9_0460', 'bwa', '0.5.9', 'package', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, 
                                               filename='tool_dependencies.xml', 
                                               strings_displayed=[ changeset_revision ] )
        
    def test_0045_url_upload_to_complex_test( self ):
        '''Populate complex_dependency_test_4_0460.'''
        '''
        This is step 9 - Upload to complex_dependency_test_5_0460 using the url hg://<tool shed url>/repos/user1/hg_subfolder_tool_dependency_0460.
        '''
        url = 'hg://%s:%s/repos/user1/hg_subfolder_tool_dependency_0460' % ( self.host, self.port )
        repository = self.test_db_util.get_repository_by_name_and_owner( 'complex_dependency_test_5_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'package_bwa_0_5_9_0460', common.test_user_1_name )
        self.upload_url( repository, 
                         url=url, 
                         filepath=None,
                         valid_tools_only=True,
                         uncompress_file=False,
                         remove_repo_files_not_in_tar=True,
                         commit_message='Uploaded complex repository dependency definition.',
                         strings_displayed=[], 
                         strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'package_bwa_0_5_9_0460', 'bwa', '0.5.9', 'package', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, 
                                               filename='tool_dependencies.xml', 
                                               filepath='subfolder', 
                                               strings_displayed=[ changeset_revision ] )
        
    def test_0050_create_repositories_for_simple_dependencies( self ):
        '''Create repositories for testing simple dependency generation.'''
        '''
        This is step 10 - Create repository_dependency_test_1_0460, repository_dependency_test_2_0460, repository_dependency_test_3_0460,
        repository_dependency_test_4_0460, repository_dependency_test_4_0460.. Each of these repositories will be populated in a way
        that tests a different way to achieve the same resulting dependency structure using complex tool dependencies.
        The different methods being tested are:
        - Upload an uncompressed repository_dependencies.xml to the root of the repository.
        - Upload a repository_dependencies.xml in a tarball, not in a subfolder.
        - Upload a repository_dependencies.xml in a subfolder within a tarball.
        - Upload via url, with the repository_dependencies.xml in the root of another repository.
        - Upload via url, with the repository_dependencies.xml in a subfolder within another repository.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository_base_name = 'repository_dependency_test_%d_0460'
        repository_base_description = 'Test #%d for repository dependency definitions.'
        repository_base_long_description = 'Test #%d for repository dependency definitions.'
        for number in range( 1, 6 ):
            repository = self.get_or_create_repository( name=repository_base_name % number, 
                                                        description=repository_base_description % number, 
                                                        long_description=repository_base_long_description % number, 
                                                        owner=common.test_user_1_name,
                                                        category_id=self.security.encode_id( category.id ), 
                                                        strings_displayed=[] )
            
            
    def test_0055_populate_repository_dependency_test_1_0460( self ):
        '''Populate repository_dependency_test_1_0460.'''
        '''
        This is step 11 - Upload an uncompressed repository_dependencies.xml to repository_dependency_test_1_0460 that specifies a 
        repository dependency on emboss_datatypes_0460 without a specified changeset revision or tool shed url. 
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( 'repository_dependency_test_1_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'emboss_datatypes_0460', common.test_user_1_name )
        self.upload_file( repository, 
                          filename='0460_files/repository_dependencies.xml', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded complex repository dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'emboss_datatypes_0460', 'user1', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, filename='repository_dependencies.xml', strings_displayed=[ changeset_revision ] )

    def test_0060_populate_repository_dependency_test_2_0460( self ):
        '''Populate repository_dependency_test_2_0460.'''
        '''
        This is step 12 - Upload a tarball to repository_dependency_test_2_0460 with a repository_dependencies.xml in the root of the tarball.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( 'repository_dependency_test_2_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'emboss_datatypes_0460', common.test_user_1_name )
        self.upload_file( repository, 
                          filename='0460_files/repository_dependencies_in_root.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=True,
                          commit_message='Uploaded complex repository dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'emboss_datatypes_0460', 'user1', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, filename='repository_dependencies.xml', strings_displayed=[ changeset_revision ] )

    def test_0065_populate_repository_dependency_test_3_0460( self ):
        '''Populate repository_dependency_test_3_0460.'''
        '''
        This is step 13 - Upload a tarball to repository_dependency_test_3_0460 with a repository_dependencies.xml in a
        subfolder within the tarball.
        '''
        repository = self.test_db_util.get_repository_by_name_and_owner( 'repository_dependency_test_3_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'emboss_datatypes_0460', common.test_user_1_name )
        self.upload_file( repository, 
                          filename='0460_files/repository_dependencies_in_subfolder.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=True,
                          commit_message='Uploaded complex repository dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'emboss_datatypes_0460', 'user1', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, 
                                               filename='repository_dependencies.xml', 
                                               filepath='subfolder', 
                                               strings_displayed=[ changeset_revision ] )

    def test_0070_create_repositories_for_url_upload( self ):
        '''Create and populate hg_repository_dependency_0460 and hg_subfolder_repository_dependency_0460.'''
        '''
        This is step 14 - Create hg_repository_dependency_0460 and hg_subfolder_repository_dependency_0460 and populate
        with repository dependencies.
        '''
        category = self.test_db_util.get_category_by_name( category_name )
        repository = self.get_or_create_repository( name='hg_repository_dependency_0460', 
                                                    description=bwa_repository_description, 
                                                    long_description=bwa_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='0460_files/repository_dependencies.xml', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate hg_repository_dependency_0460 with a tool dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
        repository = self.get_or_create_repository( name='hg_subfolder_repository_dependency_0460', 
                                                    description=bwa_repository_description, 
                                                    long_description=bwa_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          filename='0460_files/repository_dependencies_in_subfolder.tar', 
                          filepath=None,
                          valid_tools_only=True,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Populate hg_subfolder_repository_dependency_0460 with a tool dependency definition.',
                          strings_displayed=[], 
                          strings_not_displayed=[] )
    
    def test_0075_url_upload_to_complex_test( self ):
        '''Populate repository_dependency_test_4_0460.'''
        '''
        This is step 15 - Upload to repository_dependency_test_4_0460 using the url
        hg://<tool shed url>/repos/user1/hg_repository_dependency_0460.
        '''
        url = 'hg://%s:%s/repos/user1/hg_repository_dependency_0460' % ( self.host, self.port )
        repository = self.test_db_util.get_repository_by_name_and_owner( 'repository_dependency_test_4_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'emboss_datatypes_0460', common.test_user_1_name )
        self.upload_url( repository, 
                         url=url, 
                         filepath=None,
                         valid_tools_only=True,
                         uncompress_file=False,
                         remove_repo_files_not_in_tar=True,
                         commit_message='Uploaded repository dependency definition.',
                         strings_displayed=[], 
                         strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'emboss_datatypes_0460', 'user1', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, 
                                               filename='repository_dependencies.xml', 
                                               strings_displayed=[ changeset_revision ] )
        
    def test_0080_url_upload_to_complex_test( self ):
        '''Populate repository_dependency_test_4_0460.'''
        '''
        This is step 16 - Upload to repository_dependency_test_5_0460 using the url
        hg://<tool shed url>/repos/user1/hg_subfolder_repository_dependency_0460.
        '''
        url = 'hg://%s:%s/repos/user1/hg_subfolder_repository_dependency_0460' % ( self.host, self.port )
        repository = self.test_db_util.get_repository_by_name_and_owner( 'repository_dependency_test_5_0460', common.test_user_1_name ) 
        package_repository = self.test_db_util.get_repository_by_name_and_owner( 'emboss_datatypes_0460', common.test_user_1_name )
        self.upload_url( repository, 
                         url=url, 
                         filepath=None,
                         valid_tools_only=True,
                         uncompress_file=False,
                         remove_repo_files_not_in_tar=True,
                         commit_message='Uploaded repository dependency definition.',
                         strings_displayed=[], 
                         strings_not_displayed=[] )
        changeset_revision = self.get_repository_tip( package_repository )
        strings_displayed = [ 'emboss_datatypes_0460', 'user1', changeset_revision ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
        self.display_repository_file_contents( repository, 
                                               filename='repository_dependencies.xml', 
                                               filepath='subfolder', 
                                               strings_displayed=[ changeset_revision ] )
