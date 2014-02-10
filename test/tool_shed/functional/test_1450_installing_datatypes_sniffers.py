from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
repository_name = 'proteomics_datatypes_1450'
repository_description = "Proteomics datatypes"
repository_long_description = "Datatypes used in proteomics"

category_name = 'Test 1450 Datatype Sniffers'
category_description = 'Test 1450 - Installing Datatype Sniffers'
'''
1. Get a count of datatypes and sniffers.
2. Install proteomics_datatypes_1450.
3. Verify the count of datatypes and sniffers is the previous count + the datatypes contained within proteomics_datatypes_1450.
4. Deactivate proteomics_datatypes_1450, verify the count of datatypes and sniffers is equal to the count determined in step 1.
5. Reactivate proteomics_datatypes_1450, verify that the count of datatypes and sniffers has been increased by the contents of the repository.
6. Uninstall proteomics_datatypes_1450, verify the count of datatypes and sniffers is equal to the count determined in step 1.
7. Reinstall proteomics_datatypes_1450, verify that the count of datatypes and sniffers has been increased by the contents of the repository.
'''

base_datatypes_count = 0
repository_datatypes_count = 0
base_sniffers_count = 0

class TestInstallDatatypesSniffers( ShedTwillTestCase ):
    '''Test installing a repository that defines datatypes and datatype sniffers.'''
  
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        global base_datatypes_count
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        galaxy_admin_user = self.test_db_util.get_galaxy_user( common.admin_email )
        assert galaxy_admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        galaxy_admin_user_private_role = self.test_db_util.get_galaxy_private_role( galaxy_admin_user )
        base_datatypes_count = self.get_datatypes_count()
        base_sniffers_count = self.get_sniffers_count()
        
    def test_0005_ensure_repositories_and_categories_exist( self ):
        '''Create the 1450 category and proteomics_datatypes_1450 repository.'''
        global repository_datatypes_count
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=repository_name, 
                                                    description=repository_description, 
                                                    long_description=repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        if self.repository_is_new( repository ):
            self.upload_file( repository, 
                              filename='proteomics_datatypes/proteomics_datatypes.tar', 
                              filepath=None,
                              valid_tools_only=True,
                              uncompress_file=False,
                              remove_repo_files_not_in_tar=False,
                              commit_message='Uploaded datatype and sniffer definitions.',
                              strings_displayed=[], 
                              strings_not_displayed=[] )
        repository_datatypes_count = self.get_repository_datatypes_count( repository )
        
    def test_0010_install_datatypes_repository( self ):
        '''Install the proteomics_datatypes_1450 repository into the Galaxy instance.'''
        '''
        This includes steps 1 and 2 - Get a count of datatypes and sniffers.
        Store a count of the current datatypes registry and sniffers in global variables, to compare with the updated count
        after changing the installation status of the proteomics_datatypes_1450 repository.
        '''
        global repository_datatypes_count
        global base_datatypes_count
        global base_sniffers_count
        base_sniffers_count = self.get_sniffers_count()
        self.galaxy_logout()
        self.galaxy_login( email=common.admin_email, username=common.admin_username )
        strings_displayed = [ 'proteomics' ]
        self.install_repository( 'proteomics_datatypes_1450', 
                                 common.test_user_1_name, 
                                 category_name,
                                 strings_displayed=strings_displayed,
                                 new_tool_panel_section_label='test_1450' )
        installed_repository = self.test_db_util.get_installed_repository_by_name_owner( 'proteomics_datatypes_1450', common.test_user_1_name )
        strings_displayed = [ 'user1', 
                              self.url.replace( 'http://', '' ), 
                              installed_repository.installed_changeset_revision ]
        self.display_galaxy_browse_repositories_page( strings_displayed=strings_displayed )
    
    def test_0015_verify_datatypes_count( self ):
        '''Verify that datatypes were added in the previous step.'''
        '''
        This is step 3 - Verify the count of datatypes and sniffers is the previous count + the datatypes
                         contained within proteomics_datatypes_1450.
        Compare the current datatypes registry and sniffers with the values that were retrieved in the previous step.
        '''
        current_datatypes = self.get_datatypes_count()
        assert current_datatypes == base_datatypes_count + repository_datatypes_count, \
            'Found %d datatypes, expected %d.' % ( current_datatypes, base_datatypes_count + repository_datatypes_count )
        current_sniffers = self.get_sniffers_count()
        assert current_sniffers > base_sniffers_count, \
            'Sniffer count after installing proteomics_datatypes_1450 is %d, which is not greater than %d' % \
            ( current_sniffers, base_sniffers_count )
            
    def test_0020_deactivate_datatypes_repository( self ):
        '''Deactivate the installed proteomics_datatypes_1450 repository.'''
        '''
        This is step 4 - Deactivate proteomics_datatypes_1450, verify the count of datatypes and sniffers is equal to
                         the count determined in step 1.
        Deactivate proteomics_datatypes_1450 and check that the in-memory datatypes and sniffers match the base values
        determined in the first step.
        '''
        repository = self.test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        global repository_datatypes_count
        global base_datatypes_count
        global base_sniffers_count
        self.deactivate_repository( repository )
        new_datatypes_count = self.get_datatypes_count()
        assert new_datatypes_count == base_datatypes_count, 'Expected %d datatypes, got %d' % ( base_datatypes_count, new_datatypes_count )
        current_sniffers = self.get_sniffers_count()
        assert current_sniffers == base_sniffers_count, \
            'Sniffer count after deactivating proteomics_datatypes_1450 is %d, expected %d' % \
            ( current_sniffers, base_sniffers_count )
        
    def test_0025_reactivate_datatypes_repository( self ):
        '''Reactivate the deactivated proteomics_datatypes_1450 repository.'''
        '''
        This is step 5 - Reactivate proteomics_datatypes, verify that the count of datatypes and sniffers has been
                         increased by the contents of the repository.
        '''
        repository = self.test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        global repository_datatypes_count
        global base_datatypes_count
        global base_sniffers_count
        self.reactivate_repository( repository )
        new_datatypes_count = self.get_datatypes_count()
        assert new_datatypes_count == base_datatypes_count + repository_datatypes_count, \
            'Found %d datatypes, expected %d.' % ( new_datatypes_count, base_datatypes_count + repository_datatypes_count )
        current_sniffers = self.get_sniffers_count()
        assert current_sniffers > base_sniffers_count, \
            'Sniffer count after reactivating proteomics_datatypes_1450 is %d, which is not greater than %d' % \
            ( current_sniffers, base_sniffers_count )

    def test_0030_uninstall_datatypes_repository( self ):
        '''Uninstall the installed proteomics_datatypes_1450 repository.'''
        '''
        This is step 6 - Uninstall proteomics_datatypes_1450, verify the count of datatypes and sniffers is equal
                         to the count determined in step 1.
        Uninstall proteomics_datatypes_1450 and check that the in-memory datatypes and sniffers match the base values
        determined in the first step.
        '''
        repository = self.test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        global repository_datatypes_count
        global base_datatypes_count
        self.uninstall_repository( repository )
        new_datatypes_count = self.get_datatypes_count()
        assert new_datatypes_count == base_datatypes_count, 'Expected %d datatypes, got %d' % ( base_datatypes_count, new_datatypes_count )
        current_sniffers = self.get_sniffers_count()
        assert current_sniffers == base_sniffers_count, \
            'Sniffer count after uninstalling proteomics_datatypes_1450 is %d, expected %d' % \
            ( current_sniffers, base_sniffers_count )

    def test_0035_reinstall_datatypes_repository( self ):
        '''Reinstall the uninstalled proteomics_datatypes_1450 repository.'''
        '''
        This is step 7 - Reinstall proteomics_datatypes_1450, verify that the count of datatypes and sniffers has been
                         increased by the contents of the repository.
        '''
        repository = self.test_db_util.get_installed_repository_by_name_owner( repository_name, common.test_user_1_name )
        global repository_datatypes_count
        global base_datatypes_count
        self.reinstall_repository( repository )
        new_datatypes_count = self.get_datatypes_count()
        assert new_datatypes_count == base_datatypes_count + repository_datatypes_count, \
            'Found %d datatypes, expected %d.' % ( new_datatypes_count, base_datatypes_count + repository_datatypes_count )
        current_sniffers = self.get_sniffers_count()
        assert current_sniffers > base_sniffers_count, \
            'Sniffer count after reinstalling proteomics_datatypes_1450 is %d, which is not greater than %d' % \
            ( current_sniffers, base_sniffers_count )
