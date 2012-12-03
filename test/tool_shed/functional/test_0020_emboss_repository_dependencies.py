from tool_shed.base.twilltestcase import *
from tool_shed.base.test_db_util import *

admin_user = None
admin_user_private_role = None
admin_email = 'test@bx.psu.edu'
admin_username = 'admin-user'

test_user_1 = None
test_user_1_private_role = None
test_user_1_email = 'test-1@bx.psu.edu'
test_user_1_name = 'user1'

datatypes_repository_name = 'emboss_datatypes'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."

emboss_repository_name = 'emboss_5'
emboss_repository_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'
emboss_repository_long_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'

new_repository_dependencies_xml = '''<?xml version="1.0"?>
<repositories>
    <repository toolshed="${toolshed_url}" name="${repository_name}" owner="${owner}" changeset_revision="${changeset_revision}" />
</repositories>
'''

class TestEmbossRepositoryDependencies( ShedTwillTestCase ):
    '''Testing emboss 5 with repository dependencies.'''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts and login as an admin user."""
        self.logout()
        self.login( email=admin_email, username=admin_username )
        admin_user = get_user( admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = get_private_role( admin_user )
        self.logout()
        self.login( email=test_user_1_email, username=test_user_1_name )
        test_user_1 = get_user( test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % regular_email
        test_user_1_private_role = get_private_role( test_user_1 )
    def test_0005_create_categories( self ):
        """Create categories"""
        self.logout()
        self.login( email=admin_email, username=admin_username )
        self.create_category( 'Sequence Analysis', 'Tools for performing Protein and DNA/RNA analysis' )
    def test_0010_create_emboss_datatypes_repository_and_upload_tarball( self ):
        '''Create the emboss_datatypes repository and upload the tarball.'''
        self.logout()
        self.login( email=test_user_1_email, username=test_user_1_name )
        self.create_repository( datatypes_repository_name, 
                                datatypes_repository_description, 
                                repository_long_description=datatypes_repository_long_description, 
                                categories=[ 'Sequence Analysis' ], 
                                strings_displayed=[] )
        repository = get_repository_by_name_and_owner( datatypes_repository_name, test_user_1_name )
        self.upload_file( repository, 
                          'emboss_5/datatypes_conf.xml', 
                          commit_message='Uploaded datatypes_conf.xml.' )
    def test_0015_verify_datatypes_in_datatypes_repository( self ):
        '''Verify that the emboss_datatypes repository contains datatype entries.'''
        repository = get_repository_by_name_and_owner( datatypes_repository_name, test_user_1_name )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Datatypes', 'equicktandem', 'hennig86', 'vectorstrip' ] )
    def test_0020_generate_repository_dependencies_xml( self ):
        '''Generate the repository_dependencies.xml file for the emboss_5 repository.'''
        datatypes_repository = get_repository_by_name_and_owner( datatypes_repository_name, test_user_1_name )
        changeset_revision = self.get_repository_tip( datatypes_repository )
        template_parser = string.Template( new_repository_dependencies_xml )
        repository_dependency_xml = template_parser.safe_substitute( toolshed_url=self.url,
                                                                     owner=test_user_1_name,
                                                                     repository_name=datatypes_repository.name,
                                                                     changeset_revision=changeset_revision )
        # Save the generated xml to test-data/emboss_5/repository_dependencies.xml.
        file( self.get_filename( 'emboss_5/repository_dependencies.xml' ), 'w' ).write( repository_dependency_xml )
    def test_0025_create_emboss_5_repository_and_upload_files( self ):
        '''Create the emboss_5 repository and upload a tool tarball, then generate and upload repository_dependencies.xml.'''
        self.create_repository( emboss_repository_name, 
                                emboss_repository_description, 
                                repository_long_description=emboss_repository_long_description, 
                                categories=[ 'Text Manipulation' ], 
                                strings_displayed=[] )
        repository = get_repository_by_name_and_owner( emboss_repository_name, test_user_1_name )
        self.upload_file( repository, 'emboss_5/emboss_5.tar', commit_message='Uploaded emboss_5.tar' )
        self.upload_file( repository, 'emboss_5/repository_dependencies.xml', commit_message='Uploaded repository_dependencies.xml' )
    def test_0030_verify_emboss_5_repository_dependency_on_emboss_datatypes( self ):
        '''Verify that the emboss_5 repository now depends on the emboss_datatypes repository with correct name, owner, and changeset revision.'''
        repository = get_repository_by_name_and_owner( emboss_repository_name, test_user_1_name )
        datatypes_repository = get_repository_by_name_and_owner( datatypes_repository_name, test_user_1_name )
        changeset_revision = self.get_repository_tip( datatypes_repository )
        strings_displayed = [ datatypes_repository_name, test_user_1_name, changeset_revision, 'Repository dependencies' ]
        self.display_manage_repository_page( repository, strings_displayed=strings_displayed )
    def test_0035_cleanup( self ):
        '''Clean up generated test data.'''
        if os.path.exists( self.get_filename( 'emboss_5/repository_dependencies.xml' ) ):
            os.remove( self.get_filename( 'emboss_5/repository_dependencies.xml' ) )
