import tempfile, time, re, tempfile, os, shutil
import galaxy.webapps.community.model
from galaxy.util import parse_xml, string_as_bool
from galaxy.util.shed_util import clean_tool_shed_url
from galaxy.model.orm import *
from tool_shed.base.twilltestcase import *
from tool_shed.base.test_db_util import *

admin_user = None
admin_user_private_role = None
admin_email = 'test@bx.psu.edu'
admin_username = 'admin-user'

regular_user = None
regular_user_private_role = None
regular_email = 'test-1@bx.psu.edu'
regular_username = 'user1'

repository_name = 'filter'
repository_description = "Galaxy's filter tool"
repository_long_description = "Long description of Galaxy's filter tool"
files_path = os.path.abspath( os.path.join( "test", "tool_shed", "test_data" ) )
filter_filename = os.path.join( files_path, "filtering_1.1.0.tar" )

class TestCreateRepository( ShedTwillTestCase ):
 
    def test_0000_initiate_users( self ):
        """Create necessary users and login as an admin user."""
        self.login( email=regular_email, username=regular_username )
        regular_user = get_user( regular_email )
        assert regular_user is not None, 'Problem retrieving user with email %s from the database' % regular_email
        regular_user_private_role = get_private_role( regular_user )
        self.logout()
        self.login( email=admin_email, username=admin_username )
        admin_user = get_user( admin_email )
        assert admin_user is not None, 'Problem retrieving user with email %s from the database' % admin_email
        admin_user_private_role = get_private_role( admin_user )
    def test_0005_create_categories( self ):
        """Create a category"""
        self.create_category( 'Text Manipulation', 'Tools for manipulating text' )
        self.create_category( 'Text Analysis', 'Tools for analyzing text' )
    def test_0010_create_repository( self ):
        """Create a repository"""
        strings_displayed = [ '<div class="toolFormTitle">Repository %s</div>' % "'%s'" % repository_name, \
                              'Repository %s has been created' % "'%s'" % repository_name ]
        self.create_repository( repository_name, repository_description, \
                                repository_long_description=repository_long_description, \
                                categories=[ 'Text Manipulation' ], \
                                strings_displayed=strings_displayed )
    def test_0015_edit_repository( self ):
        """Edit the repository name, description, and long description"""
        repository = get_repository_by_name( repository_name, admin_username )
        new_name = "renamed_filter"
        new_description = "Edited filter tool"
        new_long_description = "Edited long description"
        self.edit_repository_information( repository, repo_name=new_name, description=new_description, long_description=new_long_description )
    def test_0020_change_repository_category( self ):
        """Change the category of a repository"""
        repository = get_repository_by_name( repository_name, admin_username )
        self.edit_repository_categories( repository, categories_to_add=[ "Text Analysis" ], categories_to_remove=[ "Text Manipulation" ] )
#    def test_0025_grant_write_access( self ):
#        '''Grant write access to another user'''
#        repository = get_repository_by_name( repository_name, admin_username )
#        self.grant_write_access( repository, usernames=[ regular_username ] )
    def test_0030_upload_tarball( self ):
        """Upload filtering_1.1.0.tar to the repository"""
        repository = get_repository_by_name( repository_name, admin_username )
        self.upload( repository, filter_filename, \
                     strings_displayed=[ "The file '%s' has been successfully uploaded to the repository." % filter_filename ], \
                     commit_message="Uploaded filtering 1.1.0" )
        self.check_for_valid_tools( repository )
        latest_repository_metadata = self.get_latest_repository_metadata_for_repository( repository )
        changeset_revision = latest_repository_metadata.changeset_revision
        self.check_repository_changelog( repository, strings_displayed=[ 'Repository metadata is associated with this change set.' ] )
        self.set_repository_malicious( repository, strings_displayed=[ 'The repository tip has been defined as malicious.' ] )
        self.unset_repository_malicious( repository, strings_displayed=[ 'The repository tip has been defined as <b>not</b> malicious.' ] )
        self.load_display_tool_page( repository, tool_xml_filename='filtering.xml', \
                                     changeset_revision=changeset_revision, \
                                     strings_displayed=[ 'Filter (version 1.1.0)', "c1=='chr1'" ], \
                                     strings_not_displayed=[] )
        tool = latest_repository_metadata.metadata[ 'tools' ][0]
        metadata_strings_displayed = [ tool[ 'guid' ], tool[ 'version' ], tool[ 'id' ], tool[ 'name' ], tool[ 'description' ], changeset_revision ]
        self.check_for_tool_metadata( repository, changeset_revision, 'Filter1', strings_displayed=metadata_strings_displayed )
    def test_0035_repository_browse_page( self ):
        '''Visit the repository browse page'''
        repository = get_repository_by_name( repository_name, admin_username )
        self.browse_repository( repository, strings_displayed=[ 'Browse %s revision' % repository.name, '(repository tip)' ] )
    def test_0040_visit_clone_url_via_hgweb( self ):
        '''Visit the repository clone URL via hgweb'''
        repository = get_repository_by_name( repository_name, admin_username )
        latest_changeset_revision = self.get_latest_repository_metadata_for_repository( repository )
        self.display_repository_clone_page( admin_username, \
                                            repository_name, \
                                            strings_displayed=[ 'Uploaded filtering 1.1.0', latest_changeset_revision.changeset_revision ] )
