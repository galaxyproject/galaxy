from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
from tool_shed.base.test_db_util import get_repository_by_name_and_owner, get_user, get_private_role

datatypes_repository_name = 'emboss_datatypes'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."

emboss_repository_name = 'emboss_0020'
emboss_repository_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'
emboss_repository_long_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'

class TestBasicRepositoryDependencies( ShedTwillTestCase ):
    '''Testing emboss 5 with repository dependencies.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % common.admin_email
        admin_user_private_role = get_private_role( admin_user )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % common.test_user_1_email
        test_user_1_private_role = get_private_role( test_user_1 )
    def test_0005_create_category( self ):
        """Create Sequence Analysis category"""
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        self.create_category( 'Sequence Analysis', 'Tools for performing Protein and DNA/RNA analysis' )
    def test_0010_create_emboss_datatypes_repository_and_upload_tarball( self ):
        '''Create and populate the emboss_datatypes repository.'''
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        self.create_repository( datatypes_repository_name, 
                                datatypes_repository_description, 
                                repository_long_description=datatypes_repository_long_description, 
                                categories=[ 'Sequence Analysis' ], 
                                strings_displayed=[] )
        repository = get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        self.upload_file( repository, 'emboss/datatypes/datatypes_conf.xml', commit_message='Uploaded datatypes_conf.xml.' )
    def test_0015_verify_datatypes_in_datatypes_repository( self ):
        '''Verify that the emboss_datatypes repository contains datatype entries.'''
        repository = get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Datatypes', 'equicktandem', 'hennig86', 'vectorstrip' ] )
    def test_0020_create_emboss_5_repository_and_upload_files( self ):
        '''Create and populate the emboss_5_0020 repository.'''
        self.create_repository( emboss_repository_name, 
                                emboss_repository_description, 
                                repository_long_description=emboss_repository_long_description, 
                                categories=[ 'Text Manipulation' ], 
                                strings_displayed=[] )
        repository = get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        self.upload_file( repository, 'emboss/emboss.tar', commit_message='Uploaded emboss_5.tar' )
    def test_0025_generate_and_upload_repository_dependencies_xml( self ):
        '''Generate and upload the repository_dependencies.xml file'''
        repository = get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        datatypes_repository = get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        self.generate_repository_dependency_xml( datatypes_repository, self.get_filename( 'emboss/5/repository_dependencies.xml' ) )
        self.upload_file( repository, 'emboss/5/repository_dependencies.xml', commit_message='Uploaded repository_dependencies.xml' )
    def test_0030_verify_emboss_5_repository_dependency_on_emboss_datatypes( self ):
        '''Verify that the emboss_5 repository now depends on the emboss_datatypes repository with correct name, owner, and changeset revision.'''
        repository = get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        datatypes_repository = get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        changeset_revision = self.get_repository_tip( datatypes_repository )
        strings_displayed = [ datatypes_repository_name, common.test_user_1_name, changeset_revision, 'Repository dependencies' ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
    def test_0035_cleanup( self ):
        '''Clean up generated test data.'''
        if os.path.exists( self.get_filename( 'emboss/5/repository_dependencies.xml' ) ):
            os.remove( self.get_filename( 'emboss/5/repository_dependencies.xml' ) )
