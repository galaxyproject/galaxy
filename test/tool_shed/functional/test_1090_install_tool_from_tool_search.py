from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
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

running_standalone = False

class TestToolSearchAndInstall( ShedTwillTestCase ):
    '''Verify that the code correctly handles circular dependencies down to n levels.'''
  
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
 
    def test_0005_create_bwa_base_repository( self ):
        '''Create and populate bwa_base_0090.'''
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        global running_standalone
        repository = self.get_or_create_repository( name=bwa_base_repository_name, 
                                                    description=bwa_base_repository_description, 
                                                    long_description=bwa_base_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
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
        global running_standalone
        repository = self.get_or_create_repository( name=bwa_color_repository_name, 
                                                    description=bwa_color_repository_description, 
                                                    long_description=bwa_color_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
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
        global running_standalone
        repository = self.get_or_create_repository( name=emboss_datatypes_repository_name, 
                                                    description=emboss_datatypes_repository_description, 
                                                    long_description=emboss_datatypes_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
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
        global running_standalone
        repository = self.get_or_create_repository( name=emboss_repository_name, 
                                                    description=emboss_repository_description, 
                                                    long_description=emboss_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
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
        global running_standalone
        repository = self.get_or_create_repository( name=filtering_repository_name, 
                                                    description=filtering_repository_description, 
                                                    long_description=filtering_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
            self.upload_file( repository, 
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
        global running_standalone
        repository = self.get_or_create_repository( name=freebayes_repository_name, 
                                                    description=freebayes_repository_description, 
                                                    long_description=freebayes_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            running_standalone = True
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
        global running_standalone
        if running_standalone:
            bwa_color_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_color_repository_name, common.test_user_1_name )
            bwa_base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
            emboss_datatypes_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_datatypes_repository_name, common.test_user_1_name )
            emboss_repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
            filtering_repository = self.test_db_util.get_repository_by_name_and_owner( filtering_repository_name, common.test_user_1_name )
            freebayes_repository = self.test_db_util.get_repository_by_name_and_owner( freebayes_repository_name, common.test_user_1_name )
            dependency_xml_path = self.generate_temp_path( 'test_0090', additional_paths=[ 'freebayes' ] )
            freebayes_tuple = ( self.url, freebayes_repository.name, freebayes_repository.user.username, self.get_repository_tip( freebayes_repository ) )
            emboss_tuple = ( self.url, emboss_repository.name, emboss_repository.user.username, self.get_repository_tip( emboss_repository ) )
            datatypes_tuple = ( self.url, emboss_datatypes_repository.name, emboss_datatypes_repository.user.username, self.get_repository_tip( emboss_datatypes_repository ) )
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
 
    def test_0045_install_freebayes_repository( self ):
        '''Install freebayes without repository dependencies.'''
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        # After this test, the repositories should be in the following states:
        # Installed: freebayes
        # Never installed: filtering, emboss, emboss_datatypes, bwa_color, bwa_base
        self.install_repository( freebayes_repository_name, 
                                 common.test_user_1_name, 
                                 category_name, 
                                 install_tool_dependencies=False, 
                                 install_repository_dependencies=False, 
                                 new_tool_panel_section_label='freebayes_1090' )
        installed_repositories = [ ( freebayes_repository_name, common.test_user_1_name ) ]
        strings_displayed = [ 'freebayes_0090' ]
        strings_not_displayed = [ 'filtering_0090', 'emboss_0090', 'emboss_datatypes_0090', 'bwa_color_0090', 'bwa_base_0090' ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )
        self.verify_installed_repositories( installed_repositories )
  
    def test_0050_install_deactivate_filtering_repository( self ):
        '''Install and deactivate filtering.'''
        global running_standalone
        original_datatypes = self.get_datatypes_count()
        # After this test, the repositories should be in the following states:
        # Installed: freebayes
        # Deactivated: filtering
        # Never installed: emboss, emboss_datatypes, bwa_color, bwa_base
        self.install_repository( filtering_repository_name, 
                                 common.test_user_1_name, 
                                 category_name, 
                                 install_tool_dependencies=False, 
                                 install_repository_dependencies=False, 
                                 new_tool_panel_section_label='filtering_1090' )
        installed_repositories = [ ( filtering_repository_name, common.test_user_1_name ), 
                                   ( freebayes_repository_name, common.test_user_1_name ) ]
        strings_displayed = [ 'filtering_0090', 'freebayes_0090' ]
        strings_not_displayed = [ 'emboss_0090', 'emboss_datatypes_0090', 'bwa_color_0090', 'bwa_base_0090' ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )
        self.verify_installed_repositories( installed_repositories )
        filtering_repository = self.test_db_util.get_installed_repository_by_name_owner( filtering_repository_name, common.test_user_1_name )
        self.deactivate_repository( filtering_repository )
        strings_displayed = [ 'freebayes_0090' ]
        strings_not_displayed = [ 'filtering_0090', 'emboss_0090', 'emboss_datatypes_0090', 'bwa_color_0090', 'bwa_base_0090' ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )
  
    def test_0055_install_uninstall_datatypes_repository( self ):
        '''Install and uninstall emboss_datatypes.'''
        # After this test, the repositories should be in the following states:
        # Installed: freebayes
        # Deactivated: filtering
        # Uninstalled: emboss_datatypes
        # Never installed: emboss, bwa_color, bwa_base
        self.install_repository( emboss_datatypes_repository_name, 
                                 common.test_user_1_name, 
                                 category_name,
                                 includes_tools_for_display_in_tool_panel=False )
        installed_repositories = [ ( emboss_datatypes_repository_name, common.test_user_1_name ),
                                   ( freebayes_repository_name, common.test_user_1_name ) ]
        uninstalled_repositories = [ ( emboss_repository_name, common.test_user_1_name ),
                                     ( filtering_repository_name, common.test_user_1_name ), 
                                     ( bwa_color_repository_name, common.test_user_1_name ),
                                     ( bwa_base_repository_name, common.test_user_1_name ) ]
        strings_displayed = [ 'emboss_datatypes_0090', 'freebayes_0090' ]
        strings_not_displayed = [ 'filtering_0090', 'emboss_0090', 'bwa_color_0090', 'bwa_base_0090' ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )
        self.verify_installed_repositories( installed_repositories )
        datatypes_repository = self.test_db_util.get_installed_repository_by_name_owner( emboss_datatypes_repository_name, common.test_user_1_name )
        self.uninstall_repository( datatypes_repository )
        strings_displayed = [ 'freebayes_0090' ]
        strings_not_displayed = [ 'emboss_datatypes_0090', 'filtering_0090', 'emboss_0090', 'bwa_color_0090', 'bwa_base_0090' ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed, strings_not_displayed=strings_not_displayed )

    def test_0060_search_for_bwa_tools( self ):
        '''Search for and install the repositories with BWA tools, and verify that this reinstalls emboss_datatypes and reactivates filtering.'''
        bwa_color_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_color_repository_name, common.test_user_1_name )
        bwa_base_repository = self.test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        bwa_base_revision = self.get_repository_tip( bwa_base_repository )
        bwa_color_revision = self.get_repository_tip( bwa_color_repository )
        self.search_for_valid_tools( search_fields={ 'tool_id': 'bwa' }, 
                                     exact_matches=False, from_galaxy=True, 
                                     strings_displayed=[ 'bwa_color_0090', 'bwa_base_0090', bwa_base_revision, bwa_color_revision  ] )
        strings_displayed=[ 'freebayes_0090', 'emboss_0090', 'filtering_0090' ]
        strings_displayed.extend( [ 'bwa_color_0090', 'bwa_base_0090' ] )
        strings_displayed.extend( [ 'bwa', 'Handle', 'tool dependencies' ] )
        repositories_to_install = [ bwa_color_repository, bwa_base_repository ]
        # BWA is a good candidate for testing the installation of tool dependencies, but it is a core requirement of functional 
        # tests that they be able to run independently of any network connection or remote data. 
        #
        # After this test, the repositories should be in the following state:
        # Installed: bwa_color, bwa_base, emboss_datatypes, emboss, filtering, freebayes
        self.install_repositories_from_search_results( repositories_to_install, 
                                                       install_repository_dependencies='True', 
                                                       install_tool_dependencies=False, 
                                                       new_tool_panel_section_label='bwa_1090',
                                                       strings_displayed=strings_displayed )
        
        installed_repositories = [ ( emboss_repository_name, common.test_user_1_name ),
                                   ( filtering_repository_name, common.test_user_1_name ), 
                                   ( bwa_color_repository_name, common.test_user_1_name ),
                                   ( bwa_base_repository_name, common.test_user_1_name ),
                                   ( emboss_datatypes_repository_name, common.test_user_1_name ),
                                   ( freebayes_repository_name, common.test_user_1_name ) ]
        strings_displayed = [ 'emboss_datatypes_0090', 'filtering_0090', 'emboss_0090', 'bwa_color_0090', 'bwa_base_0090', 'freebayes_0090' ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
        self.verify_installed_repositories( installed_repositories )
