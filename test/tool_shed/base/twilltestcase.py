from base.twilltestcase import *
from tool_shed.base.test_db_util import *

class ShedTwillTestCase( TwillTestCase ):
    def setUp( self ):
        # Security helper
        self.security = security.SecurityHelper( id_secret='changethisinproductiontoo' )
        self.history_id = None
        self.host = os.environ.get( 'TOOL_SHED_TEST_HOST' )
        self.port = os.environ.get( 'TOOL_SHED_TEST_PORT' )
        self.url = "http://%s:%s" % ( self.host, self.port )
        self.file_dir = os.environ.get( 'TOOL_SHED_TEST_FILE_DIR', None )
        self.tool_shed_test_file = None
        self.shed_tools_dict = {}
        self.keepOutdir = os.environ.get( 'TOOL_SHED_TEST_SAVE', '' )
        if self.keepOutdir > '':
           try:
               os.makedirs( self.keepOutdir )
           except:
               pass
        self.home()
    def browse_repository( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/browse_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def check_for_strings( self, strings_displayed=[], strings_not_displayed=[] ):
        if strings_displayed:
            for string in strings_displayed:
                self.check_page_for_string( string )
        if strings_not_displayed:
            for string in strings_not_displayed:
                self.check_string_not_in_page( string )
    def check_for_valid_tools( self, repository ):
        self.manage_repository( repository )
        self.check_page_for_string( '<b>Valid tools</b><i> - click the name to preview the tool' )
    def check_repository_changelog( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/view_changelog?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def create_category( self, category_name, category_description ):
        self.visit_url( '/admin/manage_categories?operation=create' )
        tc.fv( "1", "name", category_name )
        tc.fv( "1", "description", category_description )
        tc.submit( "create_category_button" )
    def create_repository( self, repository_name, repository_description, repository_long_description=None, categories=[], strings_displayed=[], strings_not_displayed=[] ):
        self.visit_url( '/repository/create_repository' )
        tc.fv( "1", "name", repository_name )
        tc.fv( "1", "description", repository_description )
        if repository_long_description is not None:
            tc.fv( "1", "long_description", repository_long_description )
        for category in categories:
            tc.fv( "1", "category_id", "+%s" % category )
        tc.submit( "create_repository_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def display_repository_clone_page( self, owner_name, repository_name, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repos/%s/%s' % ( owner_name, repository_name )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def edit_repository_categories( self, repository, categories_to_add=[], categories_to_remove=[], restore_original=True ):
        url = '/repository/manage_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        strings_displayed = []
        strings_not_displayed = []
        for category in categories_to_add:
            tc.fv( "2", "category_id", '+%s' % category)
            strings_displayed.append( "selected>%s</option>" % category )
        for category in categories_to_remove:
            tc.fv( "2", "category_id", '-%s' % category)
            strings_not_displayed.append( "selected>%s</option>" % category )
        tc.submit( "manage_categories_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        if restore_original:
            strings_displayed = []
            strings_not_displayed = []
            for category in categories_to_remove:
                tc.fv( "2", "category_id", '+%s' % category)
                strings_displayed.append( "selected>%s</option>" % category )
            for category in categories_to_add:
                tc.fv( "2", "category_id", '-%s' % category)
                strings_not_displayed.append( "selected>%s</option>" % category )
            tc.submit( "manage_categories_button" )
            self.check_for_strings( strings_displayed, strings_not_displayed )
    def edit_repository_information( self, repository, **kwargs ):
        url = '/repository/manage_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        original_information = dict( repo_name=repository.name, description=repository.description, long_description=repository.long_description )
        strings_displayed = []
        strings_not_displayed = []
        for input_elem_name in [ 'repo_name', 'description', 'long_description' ]:
            if input_elem_name in kwargs:
                tc.fv( "1", input_elem_name, kwargs[ input_elem_name ] )
                strings_displayed.append( self.escape_html( kwargs[ input_elem_name ] ) )
        tc.submit( "edit_repository_button" )
        self.check_for_strings( strings_displayed )
        strings_displayed = []
        for input_elem_name in [ 'repo_name', 'description', 'long_description' ]:
            tc.fv( "1", input_elem_name, original_information[ input_elem_name ] )
            strings_displayed.append( self.escape_html( original_information[ input_elem_name ] ) )
        tc.submit( "edit_repository_button" )
        self.check_for_strings( strings_displayed )
    def escape_html( self, string ):
        html_entities = [ ('&', 'X' ), ( "'", '&#39;' ), ( '"', '&#34;' ) ]
        for character, replacement in html_entities:
            string = string.replace( character, replacement )
        return string
    def get_latest_repository_metadata_for_repository( self, repository ):
        return repository.metadata_revisions[ 0 ]
    def get_readme( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        repository_metadata = self.get_latest_repository_metadata_for_repository( repository )
        changeset_revision = repository_metadata.changeset_revision
        repository_id = self.security.encode_id( repository.id )
        self.visit_url( '/repository/view_readme?changeset_revision=%s&id=%s' % ( changeset_revision, repository_id ) )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def grant_write_access( self, repository, usernames=[], strings_displayed=[], strings_not_displayed=[] ):
        self.manage_repository( repository )
        tc.fv( "3", "allow_push", '-Select one' )
        for username in usernames:
            tc.fv( "3", "allow_push", '+%s' % username )
        tc.submit( 'user_access_button' )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def manage_repository( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/manage_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def set_repository_malicious( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        self.manage_repository( repository )
        tc.fv( "malicious", "malicious", True )
        tc.submit( "malicious_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def unset_repository_malicious( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        self.manage_repository( repository )
        tc.fv( "malicious", "malicious", False )
        tc.submit( "malicious_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def upload( self, repository, filename, strings_displayed=[], strings_not_displayed=[], **kwargs ):
        self.visit_url( '/upload/upload?repository_id=%s' % self.security.encode_id( repository.id ) )
        for key in kwargs:
            tc.fv( "1", key, kwargs[ key ] )
        tc.formfile( "1", "file_data", filename )
        tc.submit( "upload_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
