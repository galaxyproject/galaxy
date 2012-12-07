from tool_shed.base.twilltestcase import ShedTwillTestCase, common, os
from tool_shed.base.test_db_util import get_repository_by_name_and_owner, get_user, get_private_role

datatypes_repository_name = 'emboss_datatypes'
datatypes_repository_description = "Galaxy applicable data formats used by Emboss tools."
datatypes_repository_long_description = "Galaxy applicable data formats used by Emboss tools.  This repository contains no tools."

emboss_repository_name = 'emboss'
emboss_5_repository_name = 'emboss_5_0030'
emboss_6_repository_name = 'emboss_6_0030'
emboss_repository_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'
emboss_repository_long_description = 'Galaxy wrappers for Emboss version 5.0.0 tools'

class TestRepositoryDependencyRevisions( ShedTwillTestCase ):
    '''Test dependencies on different revisions of a repository.'''
    ''' 
    create repository emboss_5_0030
    create repository emboss_6_0030
    create repository emboss_datatypes if necessary
    create repository emboss
    emboss_5 has repository_dependency.xml file that defines emboss_datatypes
    emboss_6 has repository_dependency.xml file that defines emboss_datatypes
    get information to create repository dependency imformation for emboss
    emboss depends on emboss_5
    then emboss depends on emboss_6
    verify per-changeset dependencies
    '''
    def test_0000_initiate_users( self ):
        """Create necessary user accounts."""
        self.logout()
        self.login( email=common.admin_email, username=common.admin_username )
        admin_user = get_user( common.admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = get_private_role( admin_user )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        test_user_1 = get_user( common.test_user_1_email )
        assert test_user_1 is not None, 'Problem retrieving user with email %s from the database' % regular_email
        test_user_1_private_role = get_private_role( test_user_1 )
    def test_0005_create_repositories( self ):
        '''Create the emboss_5_0030, emboss_6_0030, emboss_datatypes, and emboss repositories and populate the emboss_datatypes repository.'''
        emboss_5_repository = get_repository_by_name_and_owner( emboss_5_repository_name, common.test_user_1_name )
        if emboss_5_repository is None:
            self.create_repository( emboss_5_repository_name, 
                                    emboss_repository_description, 
                                    repository_long_description=emboss_repository_long_description, 
                                    categories=[ 'Sequence Analysis' ], 
                                    strings_displayed=[] )
            emboss_5_repository = get_repository_by_name_and_owner( emboss_5_repository_name, common.test_user_1_name )
            self.upload_file( emboss_5_repository, 'emboss/emboss.tar', commit_message='Uploaded tool tarball.' )
        emboss_6_repository = get_repository_by_name_and_owner( emboss_6_repository_name, common.test_user_1_name )
        if emboss_6_repository is None:
            self.create_repository( emboss_6_repository_name, 
                                    emboss_repository_description, 
                                    repository_long_description=emboss_repository_long_description, 
                                    categories=[ 'Sequence Analysis' ], 
                                    strings_displayed=[] )
            emboss_6_repository = get_repository_by_name_and_owner( emboss_6_repository_name, common.test_user_1_name )
            self.upload_file( emboss_6_repository, 'emboss/emboss.tar', commit_message='Uploaded tool tarball..' )
        datatypes_repository = get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        if datatypes_repository is None:
            self.create_repository( datatypes_repository_name, 
                                    datatypes_repository_description, 
                                    repository_long_description=datatypes_repository_long_description, 
                                    categories=[ 'Sequence Analysis' ], 
                                    strings_displayed=[] )
            datatypes_repository = get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        if self.repository_is_new( datatypes_repository ):
            self.upload_file( datatypes_repository, 'emboss/datatypes/datatypes_conf.xml', commit_message='Uploaded datatypes_conf.xml.' )
        emboss_repository = get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        if emboss_repository is None:
            self.create_repository( emboss_repository_name, 
                                    emboss_repository_description, 
                                    repository_long_description=emboss_repository_long_description, 
                                    categories=[ 'Sequence Analysis' ], 
                                    strings_displayed=[] )
            emboss_repository = get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
            self.upload_file( emboss_5_repository, 'emboss/emboss.tar', commit_message='Uploaded tool tarball.' )
    def test_0010_generate_repository_dependencies_for_emboss_5( self ):
        '''Generate a repository_dependencies.xml file specifying emboss_datatypes and upload it to the emboss_5 repository.'''
        datatypes_repository = get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        self.generate_repository_dependency_xml( datatypes_repository, self.get_filename( 'emboss/repository_dependencies.xml' ) )
        emboss_5_repository = get_repository_by_name_and_owner( emboss_5_repository_name, common.test_user_1_name )
        self.upload_file( emboss_5_repository, 'emboss/repository_dependencies.xml', commit_message='Uploaded repository_depepndencies.xml.' )
    def test_0015_generate_repository_dependencies_for_emboss_6( self ):
        '''Generate a repository_dependencies.xml file specifying emboss_datatypes and upload it to the emboss_6 repository.'''
        emboss_6_repository = get_repository_by_name_and_owner( emboss_6_repository_name, common.test_user_1_name )
        self.upload_file( emboss_6_repository, 'emboss/repository_dependencies.xml', commit_message='Uploaded repository_depepndencies.xml.' )
    def test_0020_generate_repository_dependency_on_emboss_5( self ):
        '''Create and upload repository_dependencies.xml for the emboss_5_0030 repository.'''
        emboss_repository = get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        emboss_5_repository = get_repository_by_name_and_owner( emboss_5_repository_name, common.test_user_1_name )
        self.generate_repository_dependency_xml( emboss_5_repository, 
                                                 self.get_filename( 'emboss/5/repository_dependencies.xml' ), 
                                                 dependency_description='Emboss requires the Emboss 5 repository.' )
        self.upload_file( emboss_repository, 
                          'emboss/5/repository_dependencies.xml', 
                          commit_message='Uploaded dependency configuration specifying emboss_5' )
    def test_0025_generate_repository_dependency_on_emboss_6( self ):
        '''Create and upload repository_dependencies.xml for the emboss_6_0030 repository.'''
        emboss_repository = get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        emboss_6_repository = get_repository_by_name_and_owner( emboss_6_repository_name, common.test_user_1_name )
        self.generate_repository_dependency_xml( emboss_6_repository, 
                                                 self.get_filename( 'emboss/6/repository_dependencies.xml' ), 
                                                 dependency_description='Emboss requires the Emboss 6 repository.' )
        self.upload_file( emboss_repository, 
                          'emboss/6/repository_dependencies.xml', 
                          commit_message='Uploaded dependency configuration specifying emboss_6' )
    def test_0030_verify_repository_dependency_revisions( self ):
        '''Verify that different metadata revisions of the emboss repository have different repository dependencies.'''
        repository = get_repository_by_name_and_owner( emboss_repository_name, common.test_user_1_name )
        # Reset emboss metadata to pick up the repository dependency changes. 
#        self.reset_repository_metadata( repository )
        repository_metadata = [ ( metadata.metadata, metadata.changeset_revision ) for metadata in self.get_repository_metadata( repository ) ]
        datatypes_repository = get_repository_by_name_and_owner( datatypes_repository_name, common.test_user_1_name )
        datatypes_tip = self.get_repository_tip( datatypes_repository )
        # Iterate through all metadata revisions and check for repository dependencies.
        for metadata, changeset_revision in repository_metadata:
            repository_dependency_metadata = metadata[ 'repository_dependencies' ][ 'repository_dependencies' ][ 0 ]
            # Remove the tool shed URL, because that's not displayed on the page (yet?)
            repository_dependency_metadata.pop( repository_dependency_metadata.index( self.url ) )
            # Add the dependency description and datatypes repository details to the strings to check.
            repository_dependency_metadata.extend( [ metadata[ 'repository_dependencies' ][ 'description' ], 
                                                     datatypes_repository_name, 
                                                     datatypes_repository.user.username, 
                                                     datatypes_tip ] )
            self.display_manage_repository_page( repository, 
                                                 changeset_revision=changeset_revision, 
                                                 strings_displayed=[ str( metadata ) for metadata in repository_dependency_metadata ] )
    def test_0035_cleanup( self ):
        '''Clean up generated repository dependency XML files.'''
        for filename in [ 'emboss/5/repository_dependencies.xml', 'emboss/6/repository_dependencies.xml', 'emboss/repository_dependencies.xml' ]:
            if os.path.exists( self.get_filename( filename ) ):
                os.remove( self.get_filename( filename ) )
