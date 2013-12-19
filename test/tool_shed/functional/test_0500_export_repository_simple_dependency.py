from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os

import logging
log = logging.getLogger( __name__ )

emboss_repository_name = 'emboss_5_0500'
emboss_repository_description = "Galaxy wrappers for Emboss version 5.0.0 tools"
emboss_repository_long_description = "Galaxy wrappers for Emboss version 5.0.0 tools"
datatypes_repository_name = 'emboss_datatypes_0500'
datatypes_repository_description = 'Galaxy applicable data formats used by Emboss tools.'
datatypes_repository_long_description = 'Galaxy applicable data formats used by Emboss tools.  This repository contains no tools.'

category_name = 'Test 0500 Repository Dependency Import Export'
category_description = 'Test script 0500 for importing and exporting repositories with simple repository dependencies.'

'''
1. Export a repository with no dependencies, e.g. filter1.
2. Temporarily extract the repository capsule.
2a. For every owner in the manifest, set to a different user.
3. Import it into the same tool shed.
4. Check that the repository to be imported has no status in the status column.
5. Click the import button.
6. Verify the resulting page is correct.
'''


class TestExportImportRepository( ShedTwillTestCase ):
    '''Test exporting and importing repositories.'''
    
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = self.test_db_util.get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        test_user_1_private_role = self.test_db_util.get_private_role( test_user_1 )
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = self.test_db_util.get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = self.test_db_util.get_private_role( admin_user )
        
    def test_0005_create_category_and_repository( self ):
        """Create categories for this test suite"""
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        self.import_capsule( self.get_filename( 'repository_capsules/0500_emboss_5.tar.gz' ), 
                             strings_displayed=[ emboss_repository_name, datatypes_repository_name, '<b>Exists' ],
                             strings_not_displayed=[ ' Exists' ],
                             strings_displayed_after_submit=[ 'Repository <b>emboss_5_0500</b> has been created.',
                                                              'Repository <b>emboss_datatypes_0500</b> has been created.' ],
                             strings_not_displayed_after_submit=[ 'Import not necessary' ] )
        
    def test_0010_export_repository_capsule( self ):
        '''Export the repository that was imported in the previous step.'''
        '''
        This is step 2 - Export that repository.
        Export the repository to a temporary location.
        '''
        global capsule_filepath
        repository = self.test_db_util.get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        capsule_filepath = self.export_capsule( repository )
        log.debug( os.path.exists( capsule_filepath ) )
        
    def test_0015_verify_exported_capsule( self ):
        '''Verify the exported capsule contents.'''
        '''
        This is step 3 - Check the capsule's contents, verify that changeset revision and tool shed are not set.
        Extract the exported capsule tarball to a temporary path, and confirm that the manifest does not specify
        a tool shed or changeset revision.
        '''
        global capsule_filepath
        self.verify_capsule_contents( capsule_filepath, owner=common.test_user_1_name )
        
    def test_0020_import_repository_capsule( self ):
        '''Import the exported repository capsule.'''
        '''
        This is step 4 - Import the capsule again. Check that the repository to be imported is marked as preexisting.
        The string ' Exists' should be displayed, as should '<b>Exists</b>'.
        '''
        global capsule_filepath
        self.import_capsule( capsule_filepath,
                             strings_displayed=[ emboss_repository_name, datatypes_repository_name, ' Exists', self.url ],
                             strings_not_displayed_after_submit=[ 'Repository <b>emboss_5_0500</b> has been created.',
                                                                  'Repository <b>emboss_datatypes_0500</b> has been created.' ],
                             strings_displayed_after_submit=[ 'Import not necessary', ' Exists' ] )
