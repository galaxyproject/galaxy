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

class TestComplexRepositoryDependencies( ShedTwillTestCase ):
    '''Test features related to complex repository dependencies.'''
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
        category = self.create_category( name=category_name, description=category_description )
        self.logout()
        self.login( email=common.test_user_1_email, username=common.test_user_1_name )
        repository = self.get_or_create_repository( name=bwa_tool_repository_name, 
                                                    description=bwa_tool_repository_description, 
                                                    long_description=bwa_tool_repository_long_description, 
                                                    owner=common.test_user_1_name,
                                                    category_id=self.security.encode_id( category.id ), 
                                                    strings_displayed=[] )
        self.upload_file( repository, 
                          'bwa/complex/tool_dependencies.xml', 
                          strings_displayed=[], 
                          commit_message='Uploaded tool_dependencies.xml.' )
        self.display_manage_repository_page( repository, strings_displayed=[ 'Tool dependencies', 'may not be', 'in this repository' ] )
    def test_0010_create_bwa_base_repository( self ):
        '''Create and populate bwa_base_0100.'''
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
                          'bwa/complex/bwa_base.tar', 
                          strings_displayed=[], 
                          commit_message='Uploaded bwa_base.tar with tool wrapper XML, but without tool dependency XML.' )
    def test_0015_generate_complex_repository_dependency_invalid_shed_url( self ):
        '''Generate and upload a complex repository definition that specifies an invalid tool shed URL.'''
        dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'invalid' ] )
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
                          'tool_dependencies.xml',
                          valid_tools_only=False,
                          filepath=dependency_path, 
                          commit_message='Uploaded dependency on bwa_tool_0100 with invalid url.',
                          strings_displayed=strings_displayed )
    def test_0020_generate_complex_repository_dependency_invalid_repository_name( self ):
        '''Generate and upload a complex repository definition that specifies an invalid repository name.'''
        dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'invalid' ] )
        xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
        repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
        url = self.url
        name = 'invalid_repository!?'
        owner = tool_repository.user.username
        changeset_revision = self.get_repository_tip( tool_repository )
        self.generate_invalid_dependency_xml( xml_filename, url, name, owner, changeset_revision, complex=True, package='bwa', version='0.5.9' )
        strings_displayed = 'Invalid repository name <b>%s</b> defined.' % name 
        self.upload_file( repository, 
                          'tool_dependencies.xml', 
                          valid_tools_only=False,
                          filepath=dependency_path, 
                          commit_message='Uploaded dependency on bwa_tool_0100 with invalid repository name.',
                          strings_displayed=[ strings_displayed ] )
    def test_0025_generate_complex_repository_dependency_invalid_owner_name( self ):
        '''Generate and upload a complex repository definition that specifies an invalid owner.'''
        dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'invalid' ] )
        xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
        repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
        url = self.url
        name = tool_repository.name
        owner = 'invalid_owner!?'
        changeset_revision = self.get_repository_tip( tool_repository )
        self.generate_invalid_dependency_xml( xml_filename, url, name, owner, changeset_revision, complex=True, package='bwa', version='0.5.9' )
        strings_displayed = [ 'Invalid owner <b>%s</b> defined' % owner ]
        self.upload_file( repository, 
                          'tool_dependencies.xml', 
                          valid_tools_only=False,
                          filepath=dependency_path, 
                          commit_message='Uploaded dependency on bwa_tool_0100 with invalid owner.',
                          strings_displayed=strings_displayed )
    def test_0030_generate_complex_repository_dependency_invalid_changeset_revision( self ):
        '''Generate and upload a complex repository definition that specifies an invalid changeset revision.'''
        dependency_path = self.generate_temp_path( 'test_0100', additional_paths=[ 'complex', 'invalid' ] )
        xml_filename = self.get_filename( 'tool_dependencies.xml', filepath=dependency_path )
        repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
        url = self.url
        name = tool_repository.name
        owner = tool_repository.user.username
        changeset_revision = '1234abcd'
        self.generate_invalid_dependency_xml( xml_filename, url, name, owner, changeset_revision, complex=True, package='bwa', version='0.5.9' )
        strings_displayed = 'Invalid changeset revision <b>%s</b> defined.' % changeset_revision 
        self.upload_file( repository, 
                          'tool_dependencies.xml', 
                          valid_tools_only=False,
                          filepath=dependency_path, 
                          commit_message='Uploaded dependency on bwa_tool_0100 with invalid changeset revision.',
                          strings_displayed=[ strings_displayed ] )
    def test_0035_generate_complex_repository_dependency( self ):
        '''Generate and upload a valid tool_dependencies.xml file that specifies bwa_tool_repository_0100.'''
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
                          'tool_dependencies.xml', 
                          valid_tools_only=True,
                          filepath=dependency_path, 
                          commit_message='Uploaded valid complex dependency on bwa_tool_0100.' )
        self.check_repository_dependency( base_repository, tool_repository )
        self.display_manage_repository_page( base_repository, strings_displayed=[ 'bwa', '0.5.9', 'package' ] )
    def test_0040_update_base_repository( self ):
        '''Upload a new tool_dependencies.xml to the tool repository, and verify that the base repository displays the new changeset.'''
        base_repository = test_db_util.get_repository_by_name_and_owner( bwa_base_repository_name, common.test_user_1_name )
        tool_repository = test_db_util.get_repository_by_name_and_owner( bwa_tool_repository_name, common.test_user_1_name )
        previous_changeset = self.get_repository_tip( tool_repository )
        self.upload_file( tool_repository, 
                          'bwa/complex/readme/tool_dependencies.xml', 
                          strings_displayed=[], 
                          commit_message='Uploaded new tool_dependencies.xml.' )
        # Verify that the dependency display has been updated as a result of the new tool_dependencies.xml file.
        self.display_manage_repository_page( base_repository, 
                                             strings_displayed=[ self.get_repository_tip( tool_repository ), 'bwa', '0.5.9', 'package' ],
                                             strings_not_displayed=[ previous_changeset ] )

