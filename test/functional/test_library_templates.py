import time

import pyparsing  # noqa: F401
import twill.commands as tc
from markupsafe import escape

import galaxy.model
from base.test_db_util import (
    get_folder,
    get_form,
    get_latest_hda,
    get_latest_ldda_by_name,
    get_library,
    get_private_role,
    get_user,
    get_user_address,
    mark_obj_deleted,
    refresh
)
from base.twilltestcase import TwillTestCase

AddressField_form = None
CheckboxField_form = None
SelectField_form = None
TextArea_form = None
TextField_form = None
WorkflowField_form = None
address_field_name = checkbox_field_name = select_field_name = None
workflow_field_name = textfield_name = textarea_name = None
user_address1 = user_address2 = None
ldda1 = library1 = library2 = library3 = library4 = library5 = library6 = None
folder1 = folder2 = folder3 = folder4 = folder5 = folder6 = None
admin_user = None
regular_user1 = regular_user2 = regular_user3 = None


class TestLibraryFeatures( TwillTestCase ):

    def add_folder( self, cntrller, library_id, folder_id, name='Folder One', description='This is Folder One' ):
        """Create a new folder"""
        url = "%s/library_common/create_folder?cntrller=%s&library_id=%s&parent_id=%s" % ( self.url, cntrller, library_id, folder_id )
        self.visit_url( url )
        self.check_page_for_string( 'Create a new folder' )
        tc.fv( "1", "name", name )
        tc.fv( "1", "description", description )
        tc.submit( "new_folder_button" )
        check_str = escape( "The new folder named '%s' has been added to the data library." % name )
        self.check_page_for_string( check_str )

    def add_template( self, cntrller, item_type, form_type, form_id, form_name,
                      library_id=None, folder_id=None, ldda_id=None, request_type_id=None, sample_id=None ):
        """
        Add a new template to an item - for library items, the template will ALWAYS BE SET TO INHERITABLE here.  If you want to
        dis-inherit your template, call the manage_library_template_inheritance() below immediately after you call this
        method in your test code.  Templates added to Requesttype objects are always inherited to samples.
        """
        params = dict( cntrller=cntrller, item_type=item_type, form_type=form_type, library_id=library_id )
        url = "/library_common/add_template"
        if item_type == 'folder':
            params[ 'folder_id' ] = folder_id
        elif item_type == 'ldda':
            params[ 'ldda_id' ] = ldda_id
        self.visit_url( url, params )
        self.check_page_for_string( "Select a template for the" )
        self.refresh_form( "form_id", form_id )
        # For some unknown reason, twill barfs if the form number ( 1 ) is used in the following
        # rather than the form anme ( select_template ), so we have to use the form name.
        tc.fv( "select_template", "inheritable", '1' )
        tc.submit( "add_template_button" )
        self.check_page_for_string = 'A template based on the form "%s" has been added to this' % form_name

    def browse_library( self, cntrller, library_id, show_deleted=False, strings_displayed=[], strings_not_displayed=[] ):
        self.visit_url( '%s/library_common/browse_library?cntrller=%s&id=%s&show_deleted=%s' % ( self.url, cntrller, library_id, str( show_deleted ) ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) incorrectly displayed when browsing library." % check_str )
            except:
                pass

    def create_library( self, name='Library One', description='This is Library One', synopsis='Synopsis for Library One' ):
        """Create a new library"""
        self.visit_url( "%s/library_admin/create_library" % self.url )
        self.check_page_for_string( 'Create a new data library' )
        tc.fv( "1", "name", name )
        tc.fv( "1", "description", description )
        tc.fv( "1", "synopsis", synopsis )
        tc.submit( "create_library_button" )
        check_str = escape( "The new library named '%s' has been created" % name )
        self.check_page_for_string( check_str )

    def create_form( self, name, description, form_type, field_type='TextField', form_layout_name='',
                     num_fields=1, num_options=0, field_name='1_field_name', strings_displayed=[],
                     strings_displayed_after_submit=[] ):
        """Create a new form definition."""
        self.visit_url( "%s/forms/create_form_definition" % self.url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( "create_form_definition", "name", name )
        tc.fv( "create_form_definition", "description", description )
        tc.fv( "create_form_definition", "form_type_select_field", form_type )
        tc.submit( "create_form_button" )
        if form_type == "Sequencing Sample Form":
            tc.submit( "add_layout_grid" )
            tc.fv( "edit_form_definition", "grid_layout0", form_layout_name )
        # if not adding any fields at this time, remove the default empty field
        if num_fields == 0:
            tc.submit( "remove_button" )
        # Add fields to the new form definition
        for index1 in range( num_fields ):
            field_label = 'field_label_%i' % index1
            field_contents = field_type
            field_help_name = 'field_helptext_%i' % index1
            field_help_contents = 'Field %i help' % index1
            field_default = 'field_default_0'
            field_default_contents = '%s default contents' % form_type
            tc.fv( "edit_form_definition", field_label, field_contents )
            tc.fv( "edit_form_definition", field_help_name, field_help_contents )
            if field_type == 'SelectField':
                # SelectField field_type requires a refresh_on_change
                self.refresh_form( 'field_type_0', field_type )
                # Add options so our select list is functional
                if num_options == 0:
                    # Default to 2 options
                    num_options = 2
                for index2 in range( 1, num_options + 1 ):
                    tc.submit( "addoption_0" )
                # Add contents to the new options fields
                for index2 in range( num_options ):
                    option_field_name = 'field_0_option_%i' % index2
                    option_field_value = 'Option%i' % index2
                    tc.fv( "edit_form_definition", option_field_name, option_field_value )
            else:
                tc.fv( "edit_form_definition", "field_type_0", field_type )
            tc.fv( "edit_form_definition", 'field_name_0', field_name )
            tc.fv( "edit_form_definition", field_default, field_default_contents )
        # All done... now save
        tc.submit( "save_changes_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def delete_library_item( self, cntrller, library_id, item_id, item_name, item_type='library_dataset' ):
        """Mark a library item as deleted"""
        params = dict( cntrller=cntrller, library_id=library_id, item_id=item_id, item_type=item_type )
        self.visit_url( "/library_common/delete_library_item", params )
        if item_type == 'library_dataset':
            item_desc = 'Dataset'
        else:
            item_desc = item_type.capitalize()
        check_str = "marked deleted"
        self.check_for_strings( strings_displayed=[ item_desc, check_str ] )

    def edit_template( self, cntrller, item_type, form_type, library_id, field_type, field_label_1, field_helptext_1, field_default_1,
                       folder_id='', ldda_id='', action='add_field'  ):
        """Edit the form fields defining a library template"""
        params = dict( cntrller=cntrller, item_type=item_type, form_type=form_type, library_id=library_id )
        self.visit_url( "/library_common/edit_template", params=params )
        self.check_page_for_string( "Edit form definition" )
        if action == 'add_field':
            tc.submit( "add_field_button" )
            tc.fv( "edit_form", "field_label_1", field_label_1 )
            tc.fv( "edit_form", "field_helptext_1", field_helptext_1 )
            if field_type == 'SelectField':
                # Performs a refresh_on_change in this case
                self.refresh_form( "field_type_1", field_type )
            else:
                tc.fv( "edit_form", "field_type_1", field_type )
            tc.fv( "edit_form", "field_default_1", field_default_1 )
        tc.submit( 'save_changes_button' )
        self.check_page_for_string( "The template for this data library has been updated with your changes." )

    def folder_info( self, cntrller, folder_id, library_id, name='', new_name='', description='', template_refresh_field_name='1_field_name',
                     template_refresh_field_contents='', template_fields=[], strings_displayed=[], strings_not_displayed=[],
                     strings_displayed_after_submit=[], strings_not_displayed_after_submit=[] ):
        """Add information to a library using an existing template with 2 elements"""
        self.visit_url( "%s/library_common/folder_info?cntrller=%s&id=%s&library_id=%s" %
                        ( self.url, cntrller, folder_id, library_id ) )
        if name and new_name and description:
            tc.fv( '1', "name", new_name )
            tc.fv( '1', "description", description )
            tc.submit( 'rename_folder_button' )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) incorrectly displayed." % check_str )
            except:
                pass
        if template_refresh_field_contents:
            # A template containing an AddressField is displayed on the form, so we need to refresh the form
            # with the received template_refresh_field_contents.  There are 2 forms on the folder_info page
            # when in edit mode, and the 2nd one is the one we want.
            self.refresh_form( template_refresh_field_name, template_refresh_field_contents, form_no=2 )
        if template_fields:
            # We have an information template associated with the folder, so
            # there are 2 forms on this page and the template is the 2nd form
            for field_name, field_value in template_fields:
                tc.fv( "edit_info", field_name, field_value )
            tc.submit( 'edit_info_button' )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed_after_submit:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) incorrectly displayed." % check_str )
            except:
                pass

    def ldda_edit_info( self, cntrller, library_id, folder_id, ldda_id, ldda_name, new_ldda_name='', template_refresh_field_name='1_field_name',
                        template_refresh_field_contents='', template_fields=[], strings_displayed=[], strings_not_displayed=[] ):
        """Edit library_dataset_dataset_association information, optionally template element information"""
        self.visit_url( "%s/library_common/ldda_edit_info?cntrller=%s&library_id=%s&folder_id=%s&id=%s" %
                        ( self.url, cntrller, library_id, folder_id, ldda_id ) )
        check_str = 'Edit attributes of %s' % ldda_name
        self.check_page_for_string( check_str )
        if new_ldda_name:
            tc.fv( '1', 'name', new_ldda_name )
            tc.submit( 'save' )
            check_str = escape( "Attributes updated for library dataset '%s'." % new_ldda_name )
            self.check_page_for_string( check_str )
        if template_refresh_field_contents:
            # A template containing an AddressField is displayed on the upload form, so we need to refresh the form
            # with the received template_refresh_field_contents.  There are 4 forms on this page, and the template is
            # contained in the 4th form named "edit_info".
            self.refresh_form( template_refresh_field_name, template_refresh_field_contents, form_no=4 )
        if template_fields:
            # We have an information template associated with the folder, so
            # there are 2 forms on this page and the template is the 2nd form
            for field_name, field_value in template_fields:
                tc.fv( "edit_info", field_name, field_value )
            tc.submit( 'edit_info_button' )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) should not have been displayed on ldda Edit Attributes page." % check_str )
            except:
                pass

    def library_info( self, cntrller, library_id, library_name='', new_name='', new_description='', new_synopsis='',
                      template_fields=[], strings_displayed=[] ):
        """Edit information about a library, optionally using an existing template with up to 2 elements"""
        self.visit_url( "%s/library_common/library_info?cntrller=%s&id=%s" % ( self.url, cntrller, library_id ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        if new_name and new_description and new_synopsis:
            tc.fv( '1', 'name', new_name )
            tc.fv( '1', 'description', new_description )
            tc.fv( '1', 'synopsis', new_synopsis )
            tc.submit( 'library_info_button' )
            self.check_page_for_string( "Information updated for library" )
        if template_fields:
            for field_name, field_value in template_fields:
                # The 2nd form on the page contains the template, and the form is named edit_info.
                # Set the template field value
                tc.fv( "edit_info", field_name, field_value )
            tc.submit( 'edit_info_button' )

    def library_wait( self, library_id, cntrller='library_admin', maxiter=90 ):
        """Waits for the tools to finish"""
        count = 0
        sleep_amount = 1
        while count < maxiter:
            count += 1
            self.visit_url( "%s/library_common/browse_library?cntrller=%s&id=%s" % ( self.url, cntrller, library_id ) )
            page = tc.browser.get_html()
            if page.find( '<!-- running: do not change this comment, used by TwillTestCase.library_wait -->' ) > -1:
                time.sleep( sleep_amount )
                sleep_amount += 1
            else:
                break
        self.assertNotEqual(count, maxiter)

    def manage_library_template_inheritance( self, cntrller, item_type, library_id, folder_id=None, ldda_id=None, inheritable=True ):
        # If inheritable is True, the item is currently inheritable.
        if item_type == 'library':
            url = "%s/library_common/manage_template_inheritance?cntrller=%s&item_type=%s&library_id=%s" % \
                ( self.url, cntrller, item_type, library_id )
        elif item_type == 'folder':
            url = "%s/library_common/manage_template_inheritance?cntrller=%s&item_type=%s&library_id=%s&folder_id=%s" % \
                ( self.url, cntrller, item_type, library_id, folder_id )
        elif item_type == 'ldda':
            url = "%s/library_common/manage_template_inheritance?cntrller=%s&item_type=%s&library_id=%s&folder_id=%s&ldda_id=%s" % \
                ( self.url, cntrller, item_type, library_id, folder_id, ldda_id )
        self.visit_url( url )
        if inheritable:
            self.check_page_for_string = 'will no longer be inherited to contained folders and datasets'
        else:
            self.check_page_for_string = 'will now be inherited to contained folders and datasets'

    def mark_form_deleted( self, form_id ):
        """Mark a form_definition as deleted"""
        url = "%s/forms/delete_form_definition?id=%s" % ( self.url, form_id )
        self.visit_url( url )
        check_str = "1 forms have been deleted."
        self.check_page_for_string( check_str )

    def purge_library( self, library_id, library_name ):
        """Purge a library"""
        params = dict( id=library_id )
        self.visit_url( "/library_admin/purge_library", params )
        check_str = "Library '%s' and all of its contents have been purged" % library_name
        self.check_page_for_string( check_str )

    def upload_library_dataset( self, cntrller, library_id, folder_id, filename='', server_dir='', replace_id='',
                                upload_option='upload_file', file_type='auto', dbkey='hg18', space_to_tab='',
                                link_data_only='copy_files', preserve_dirs='Yes', filesystem_paths='', roles=[],
                                ldda_message='', hda_ids='', template_refresh_field_name='1_field_name',
                                template_refresh_field_contents='', template_fields=[], show_deleted='False', strings_displayed=[] ):
        """Add datasets to library using any upload_option"""
        # NOTE: due to the library_wait() method call at the end of this method, no tests should be done
        # for strings_displayed_after_submit.
        params = dict( cntrller=cntrller, library_id=library_id, folder_id=folder_id )
        url = "/library_common/upload_library_dataset"
        if replace_id:
            # If we're uploading a new version of a library dataset, we have to include the replace_id param in the
            # request because the form field named replace_id will not be displayed on the upload form if we dont.
            params[ 'replace_id' ] = replace_id
        self.visit_url( url, params=params )
        if template_refresh_field_contents:
            # A template containing an AddressField is displayed on the upload form, so we need to refresh the form
            # with the received template_refresh_field_contents.
            self.refresh_form( template_refresh_field_name, template_refresh_field_contents )
        for tup in template_fields:
            tc.fv( "1", tup[0], tup[1] )
        tc.fv( "upload_library_dataset", "library_id", library_id )
        tc.fv( "upload_library_dataset", "folder_id", folder_id )
        tc.fv( "upload_library_dataset", "show_deleted", show_deleted )
        tc.fv( "upload_library_dataset", "ldda_message", ldda_message )
        tc.fv( "upload_library_dataset", "file_type", file_type )
        tc.fv( "upload_library_dataset", "dbkey", dbkey )
        if space_to_tab:
            tc.fv( "upload_library_dataset", "space_to_tab", space_to_tab )
        for role_id in roles:
            tc.fv( "upload_library_dataset", "roles", role_id )
        # Refresh the form by selecting the upload_option - we do this here to ensure
        # all previously entered form contents are retained.
        self.refresh_form( 'upload_option', upload_option )
        if upload_option == 'import_from_history':
            for check_str in strings_displayed:
                self.check_page_for_string( check_str )
            if hda_ids:
                # Twill cannot handle multi-checkboxes, so the form can only have 1 hda_ids checkbox
                try:
                    tc.fv( "add_history_datasets_to_library", "hda_ids", hda_ids )
                except:
                    tc.fv( "add_history_datasets_to_library", "hda_ids", '1' )
            tc.submit( 'add_history_datasets_to_library_button' )
        else:
            if upload_option in [ 'upload_paths', 'upload_directory' ]:
                tc.fv( "upload_library_dataset", "link_data_only", link_data_only )
            if upload_option == 'upload_paths':
                tc.fv( "upload_library_dataset", "filesystem_paths", filesystem_paths )
            if upload_option == 'upload_directory' and server_dir:
                tc.fv( "upload_library_dataset", "server_dir", server_dir )
            if upload_option == 'upload_file':
                if filename:
                    filename = self.get_filename( filename )
                    tc.formfile( "upload_library_dataset", "files_0|file_data", filename )
            for check_str in strings_displayed:
                self.check_page_for_string( check_str )
            tc.submit( "runtool_btn" )
        # Give the files some time to finish uploading
        self.library_wait( library_id )

    def view_form( self, id, form_type='', form_name='', form_desc='', form_layout_name='', field_dicts=[] ):
        '''View form details'''
        self.visit_url( "%s/forms/view_latest_form_definition?id=%s" % ( self.url, id ) )
        # self.check_page_for_string( form_type )
        self.check_page_for_string( form_name )
        # self.check_page_for_string( form_desc )
        self.check_page_for_string( form_layout_name )
        for i, field_dict in enumerate( field_dicts ):
            self.check_page_for_string( field_dict[ 'label' ] )
            self.check_page_for_string( field_dict[ 'desc' ] )
            self.check_page_for_string( field_dict[ 'type' ] )
            if field_dict[ 'type' ].lower() == 'selectfield':
                for option_index, option in enumerate( field_dict[ 'selectlist' ] ):
                    self.check_page_for_string( option )

    def upload_file( self, filename, ftype='auto', dbkey='unspecified (?)', space_to_tab=False, metadata=None, composite_data=None, name=None, wait=True ):
        """
        Uploads a file.  If shed_tool_id has a value, we're testing tools migrated from the distribution to the tool shed,
        so the tool-data directory of test data files is contained in the installed tool shed repository.
        """
        self.visit_url( "%s/tool_runner?tool_id=upload1" % self.url )
        try:
            self.refresh_form( "file_type", ftype )  # Refresh, to support composite files
            tc.fv( "tool_form", "dbkey", dbkey )
            if metadata:
                for elem in metadata:
                    tc.fv( "tool_form", "files_metadata|%s" % elem.get( 'name' ), elem.get( 'value' ) )
            if composite_data:
                for i, composite_file in enumerate( composite_data ):
                    filename = self.get_filename( composite_file.get( 'value' ) )
                    tc.formfile( "tool_form", "files_%i|file_data" % i, filename )
                    tc.fv( "tool_form", "files_%i|space_to_tab" % i, composite_file.get( 'space_to_tab', False ) )
            else:
                filename = self.get_filename( filename )
                tc.formfile( "tool_form", "file_data", filename )
                tc.fv( "tool_form", "space_to_tab", space_to_tab )
                if name:
                    # NAME is a hidden form element, so the following prop must
                    # set to use it.
                    tc.config("readonly_controls_writeable", 1)
                    tc.fv( "tool_form", "NAME", name )
            tc.submit( "runtool_btn" )
        except AssertionError as err:
            errmsg = "Uploading file resulted in the following exception.  Make sure the file (%s) exists.  " % filename
            errmsg += str( err )
            raise AssertionError( errmsg )
        if not wait:
            return
        # Make sure every history item has a valid hid
        hids = self.get_hids_in_history( self.get_latest_history()[ 'id' ] )
        for hid in hids:
            try:
                int( hid )
            except:
                raise AssertionError( "Invalid hid (%s) created when uploading file %s" % ( hid, filename ) )
        # Wait for upload processing to finish (TODO: this should be done in each test case instead)
        self.wait()

    def test_000_initiate_users( self ):
        """Ensuring all required user accounts exist"""
        self.login( email='test1@bx.psu.edu', username='regular-user1' )
        global regular_user1
        regular_user1 = get_user( 'test1@bx.psu.edu' )
        assert regular_user1 is not None, 'Problem retrieving user with email "test1@bx.psu.edu" from the database'
        global regular_user1_private_role
        regular_user1_private_role = get_private_role( regular_user1 )
        self.login( email='test2@bx.psu.edu', username='regular-user2' )
        global regular_user2
        regular_user2 = get_user( 'test2@bx.psu.edu' )
        assert regular_user2 is not None, 'Problem retrieving user with email "test2@bx.psu.edu" from the database'
        global regular_user2_private_role
        regular_user2_private_role = get_private_role( regular_user2 )
        self.login( email='test3@bx.psu.edu', username='regular-user3' )
        global regular_user3
        regular_user3 = get_user( 'test3@bx.psu.edu' )
        assert regular_user3 is not None, 'Problem retrieving user with email "test3@bx.psu.edu" from the database'
        global regular_user3_private_role
        regular_user3_private_role = get_private_role( regular_user3 )
        self.login( email='test@bx.psu.edu', username='admin-user' )
        global admin_user
        admin_user = get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
        global admin_user_private_role
        admin_user_private_role = get_private_role( admin_user )

    def test_005_create_library_templates( self ):
        """Testing creating several LibraryInformationTemplate form definitions"""
        # Logged in as admin_user
        for type in [ 'AddressField', 'CheckboxField', 'SelectField', 'TextArea', 'TextField', 'WorkflowField' ]:
            field_name = type.lower()
            form_desc = '%s description' % type
            num_options = 0
            if type == 'SelectField':
                # Pass number of options we want in our SelectField
                num_options = 2
            # Create form for library template
            strings_displayed_after_submit = [ "The form '%s' has been updated with the changes." % type ]
            self.create_form( name=type,
                              description=form_desc,
                              form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                              field_type=type,
                              num_options=num_options,
                              field_name=field_name,
                              strings_displayed_after_submit=strings_displayed_after_submit )
        # Get all of the new form definitions for later use
        global AddressField_form
        AddressField_form = get_form( 'AddressField' )
        # NOTE: each of these names need to be the same as field_name defined above
        # for each type.
        global address_field_name
        address_field_name = 'addressfield'

        global CheckboxField_form
        CheckboxField_form = get_form( 'CheckboxField' )
        global checkbox_field_name
        checkbox_field_name = 'checkboxfield'

        global SelectField_form
        SelectField_form = get_form( 'SelectField' )
        global select_field_name
        select_field_name = 'selectfield'

        global TextArea_form
        TextArea_form = get_form( 'TextArea' )
        global textarea_name
        textarea_name = 'textarea'

        global TextField_form
        TextField_form = get_form( 'TextField' )
        global textfield_name
        textfield_name = 'textfield'

        global WorkflowField_form
        WorkflowField_form = get_form( 'WorkflowField' )
        global workflow_field_name
        workflow_field_name = 'workflowfield'

    def test_010_create_libraries( self ):
        """Testing creating a new library for each template"""
        # Logged in as admin_user
        # library1 -> AddressField
        # library2 -> CheckboxField
        # library3 -> SelectField
        # library4 -> TextArea
        # library5 -> TextField
        # library6 -> WorkflowField
        for index, form in enumerate( [ AddressField_form, CheckboxField_form, SelectField_form, TextArea_form, TextField_form, WorkflowField_form ] ):
            name = 'library%s' % str( index + 1 )
            description = '%s description' % name
            synopsis = '%s synopsis' % name
            self.create_library( name=name, description=description, synopsis=synopsis )
        # Get the libraries for later use
        global library1
        library1 = get_library( 'library1', 'library1 description', 'library1 synopsis' )
        global library2
        library2 = get_library( 'library2', 'library2 description', 'library2 synopsis' )
        global library3
        library3 = get_library( 'library3', 'library3 description', 'library3 synopsis' )
        global library4
        library4 = get_library( 'library4', 'library4 description', 'library4 synopsis' )
        global library5
        library5 = get_library( 'library5', 'library5 description', 'library5 synopsis' )
        global library6
        library6 = get_library( 'library6', 'library6 description', 'library6 synopsis' )

    def test_015_add_template_to_library1( self ):
        """Testing add an inheritable template containing an AddressField to library1"""
        # Logged in as admin_user
        # Add a template containing an AddressField to library1
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                           form_id=self.security.encode_id( AddressField_form.id ),
                           form_name=AddressField_form.name,
                           library_id=self.security.encode_id( library1.id ) )

    def test_020_add_folder_to_library1( self ):
        """Testing adding a folder to library1"""
        # Logged in as admin_user
        # Add a folder to library1
        folder = library1.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library1.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder1
        folder1 = get_folder( folder.id, name, description )

    def test_025_check_library1( self ):
        """Checking library1 and its root folder"""
        # Logged in as admin_user
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ folder1.name, folder1.description ] )
        # Make sure the template and contents were inherited to folder1
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder1.id ),
                          library_id=self.security.encode_id( library1.id ),
                          template_refresh_field_name=address_field_name,
                          strings_displayed=[ AddressField_form.name,
                                              'This is an inherited template and is not required to be used with this folder' ] )

    def test_030_add_dataset_to_folder1( self ):
        """Testing adding a ldda1 to folder1, and adding a new UserAddress on the upload form."""
        # Logged in as admin_user
        # The AddressField template should be inherited to the library dataset upload form.  Passing
        # the value 'new' should submit the form via refresh_on_change and allow new UserAddress information
        # to be posted as part of the upload.
        filename = '1.bed'
        ldda_message = '1.bed message'
        short_desc = 'Office'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( folder1.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     template_refresh_field_name=address_field_name,
                                     ldda_message=ldda_message,
                                     template_refresh_field_contents='new',
                                     template_fields=[ ( '%s_short_desc' % address_field_name, short_desc ),
                                                       ( '%s_name' % address_field_name, 'Dick' ),
                                                       ( '%s_institution' % address_field_name, 'PSU' ),
                                                       ( '%s_address' % address_field_name, '32 O Street' ),
                                                       ( '%s_city' % address_field_name, 'Anywhere' ),
                                                       ( '%s_state' % address_field_name, 'AK' ),
                                                       ( '%s_postal_code' % address_field_name, '0000000' ),
                                                       ( '%s_country' % address_field_name, 'USA' ) ],
                                     strings_displayed=[ 'Upload files' ] )
        global user_address1
        user_address1 = get_user_address( admin_user, short_desc )
        assert user_address1 is not None, 'Problem retrieving user_address1 from the database'
        global ldda1
        ldda1 = get_latest_ldda_by_name( filename )
        assert ldda1 is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda1 from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             strings_displayed=[ ldda1.name, ldda1.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library1.id ),
                             self.security.encode_id( folder1.id ),
                             self.security.encode_id( ldda1.id ),
                             ldda1.name,
                             strings_displayed=[ 'Dick' ] )

    def test_035_edit_contents_of_ldda1_tempplate( self ):
        """Testing editing the contents of ldda1 AddressField template by adding a new user_address"""
        short_desc = 'Home'
        # Now add a new user_address to ldda1
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library1.id ),
                             self.security.encode_id( folder1.id ),
                             self.security.encode_id( ldda1.id ),
                             ldda1.name,
                             template_refresh_field_name=address_field_name,
                             template_refresh_field_contents='new',
                             template_fields=[ ( '%s_short_desc' % address_field_name, short_desc ),
                                               ( '%s_name' % address_field_name, 'Richard' ),
                                               ( '%s_institution' % address_field_name, 'PSU' ),
                                               ( '%s_address' % address_field_name, '32 O Street' ),
                                               ( '%s_city' % address_field_name, 'Anywhere' ),
                                               ( '%s_state' % address_field_name, 'AK' ),
                                               ( '%s_postal_code' % address_field_name, '0000000' ),
                                               ( '%s_country' % address_field_name, 'USA' ) ],
                             strings_displayed=[ short_desc ] )
        global user_address2
        user_address2 = get_user_address( admin_user, short_desc )
        assert user_address2 is not None, 'Problem retrieving user_address2 from the database'

    def test_040_edit_contents_of_folder1_template( self ):
        """Testing editing the contents of folder1 AddressField template"""
        # Make sure the template and contents were inherited to folder1
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder1.id ),
                          library_id=self.security.encode_id( library1.id ),
                          template_refresh_field_name=address_field_name,
                          template_refresh_field_contents=str( user_address2.id ),
                          strings_displayed=[ AddressField_form.name,
                                              'This is an inherited template and is not required to be used with this folder' ],
                          strings_displayed_after_submit=[ 'Richard' ] )

    def test_045_add_dataset_to_folder1( self ):
        """Testing adding another ldda to folder1"""
        # The upload form should now inherit user_address2 on the upload form
        filename = '2.bed'
        ldda_message = '2.bed message'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library1.id ),
                                     folder_id=self.security.encode_id( folder1.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     template_refresh_field_name=address_field_name,
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'Upload files' ] )
        # Make sure user_address2 is associated with ldda.
        self.ldda_edit_info( cntrller='library_admin',
                             library_id=self.security.encode_id( library1.id ),
                             folder_id=self.security.encode_id( folder1.id ),
                             ldda_id=self.security.encode_id( ldda1.id ),
                             ldda_name=ldda1.name,
                             template_refresh_field_name=address_field_name,
                             strings_displayed=[ user_address2.desc ] )

    def test_050_add_template_to_library2( self ):
        """ Testing add an inheritable template containing an CheckboxField to library2"""
        # Add a template containing an CheckboxField to library1
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                           form_id=self.security.encode_id( CheckboxField_form.id ),
                           form_name=CheckboxField_form.name,
                           library_id=self.security.encode_id( library2.id ) )
        # Check the CheckboxField to make sure the template contents are inherited
        self.library_info( 'library_admin',
                           self.security.encode_id( library2.id ),
                           template_fields=[ ( checkbox_field_name, '1' ) ] )

    def test_055_add_folder2_to_library2( self ):
        """Testing adding a folder to library2"""
        # Logged in as admin_user
        # Add a folder to library2
        folder = library2.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library2.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder2
        folder2 = get_folder( folder.id, name, description )

    def test_060_check_library2( self ):
        """Checking library2 and its root folder"""
        # Logged in as admin_user
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library2.id ),
                             strings_displayed=[ folder2.name, folder2.description ] )

    def test_065_save_folder2_inherited_template( self ):
        """Saving the inherited template for folder2"""
        # Logged in as admin_user
        # Save the inherited template
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder2.id ),
                          library_id=self.security.encode_id( library2.id ),
                          template_fields=[ ( checkbox_field_name, '1' ) ],
                          strings_displayed=[ CheckboxField_form.name,
                                              'This is an inherited template and is not required to be used with this folder' ] )

    def test_070_add_ldda_to_folder2( self ):
        """
        Testing adding a new library dataset to library2's folder, making sure the CheckboxField is
        checked on the upload form.
        """
        # Logged in as admin_user
        filename = '1.bed'
        ldda_message = '1.bed message'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library2.id ),
                                     folder_id=self.security.encode_id( folder2.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'CheckboxField', 'checked' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library2.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library2.id ),
                             self.security.encode_id( folder2.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'CheckboxField', 'checked' ] )

    def test_080_add_template_to_library3( self ):
        """ Testing add an inheritable template containing an SelectField to library3"""
        # Logged in as admin_user
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                           form_id=self.security.encode_id( SelectField_form.id ),
                           form_name=SelectField_form.name,
                           library_id=self.security.encode_id( library3.id ) )
        # Select the 2nd option in the SelectField to make sure the template contents are inherited
        # SelectField option names are zero-based
        self.library_info( 'library_admin',
                           self.security.encode_id( library3.id ),
                           template_fields=[ ( select_field_name, 'Option1' ) ] )

    def test_085_add_folder3_to_library3( self ):
        """Testing adding a folder to library3"""
        # Logged in as admin_user
        # Add a folder to library3
        folder = library3.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library3.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder3
        folder3 = get_folder( folder.id, name, description )

    def test_090_check_library3( self ):
        """Checking library3 and its root folder"""
        # Logged in as admin_user
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library3.id ),
                             strings_displayed=[ folder3.name, folder3.description ] )

    def test_095_save_folder3_inherited_template( self ):
        """Saving the inherited template for folder3"""
        # Logged in as admin_user
        # Save the inherited template
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder3.id ),
                          library_id=self.security.encode_id( library3.id ),
                          template_fields=[ ( select_field_name, 'Option1' ) ],
                          strings_displayed=[ SelectField_form.name,
                                              'This is an inherited template and is not required to be used with this folder',
                                              'Option1' ] )

    def test_100_add_ldda_to_folder3( self ):
        """
        Testing adding a new library dataset to library3's folder, making sure the SelectField setting is correct on the upload form.
        """
        filename = '3.bed'
        ldda_message = '3.bed message'
        # Logged in as admin_user
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library3.id ),
                                     folder_id=self.security.encode_id( folder3.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'SelectField', 'selected>Option1' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library3.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library3.id ),
                             self.security.encode_id( folder3.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'SelectField', 'Option1' ] )
        # Import a dataset from the current history
        filename = '8.bed'
        self.new_history( name='import+with+SelectField' )
        self.upload_file( filename )
        hda = get_latest_hda()
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library3.id ),
                                     folder_id=self.security.encode_id( folder3.id ),
                                     upload_option='import_from_history',
                                     hda_ids=self.security.encode_id( hda.id ),
                                     strings_displayed=[ '<select name="%s" last_selected_value="Option1">' % select_field_name ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library3.id ),
                             strings_displayed=[ ldda.name, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library3.id ),
                             self.security.encode_id( folder3.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'SelectField', 'Option1' ] )

    def test_105_add_template_to_library4( self ):
        """ Testing add an inheritable template containing an TextArea to library4"""
        # Logged in as admin_user
        # Add an inheritable template to library4
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                           form_id=self.security.encode_id( TextArea_form.id ),
                           form_name=TextArea_form.name,
                           library_id=self.security.encode_id( library4.id ) )
        # Select the 2nd option in the SelectField to make sure the template contents are inherited
        self.library_info( 'library_admin',
                           self.security.encode_id( library4.id ),
                           template_fields=[ ( textarea_name, 'This text should be inherited' ) ] )

    def test_110_add_folder4_to_library4( self ):
        """Testing adding a folder to library4"""
        # Logged in as admin_user
        # Add a folder to library4
        folder = library4.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library4.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder4
        folder4 = get_folder( folder.id, name, description )

    def test_115_save_folder4_inherited_template( self ):
        """Saving the inherited template for folder4"""
        # Logged in as admin_user
        # Save the inherited template
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder4.id ),
                          library_id=self.security.encode_id( library4.id ),
                          template_fields=[ ( textarea_name, 'This text should be inherited' ) ],
                          strings_displayed=[ TextArea_form.name,
                                              'This is an inherited template and is not required to be used with this folder',
                                              'This text should be inherited' ] )

    def test_120_add_ldda_to_folder4( self ):
        """
        Testing adding a new library dataset to library4's folder, making sure the TextArea setting is correct on the upload form.
        """
        filename = '4.bed'
        ldda_message = '4.bed message'
        # Logged in as admin_user
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library4.id ),
                                     folder_id=self.security.encode_id( folder4.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'TextArea', 'This text should be inherited' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library4.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library4.id ),
                             self.security.encode_id( folder4.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'TextArea', 'This text should be inherited' ] )

    def test_125_add_template_to_library5( self ):
        """ Testing add an inheritable template containing an TextField to library5"""
        # Add an inheritable template to library5
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                           form_id=self.security.encode_id( TextField_form.id ),
                           form_name=TextField_form.name,
                           library_id=self.security.encode_id( library5.id ) )
        # Select the 2nd option in the SelectField to make sure the template contents are inherited
        self.library_info( 'library_admin',
                           self.security.encode_id( library5.id ),
                           template_fields=[ ( textfield_name, 'This text should be inherited' ) ] )

    def test_130_add_folder5_to_library5( self ):
        """Testing adding a folder to library5"""
        # Logged in as admin_user
        # Add a folder to library5
        folder = library5.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library5.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder5
        folder5 = get_folder( folder.id, name, description )

    def test_135_save_folder5_inherited_template( self ):
        """Saving the inherited template for folder5"""
        # Logged in as admin_user
        # Save the inherited template
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder5.id ),
                          library_id=self.security.encode_id( library5.id ),
                          template_fields=[ ( textfield_name, 'This text should be inherited' ) ],
                          strings_displayed=[ TextField_form.name,
                                              'This is an inherited template and is not required to be used with this folder',
                                              'This text should be inherited' ] )

    def test_140_add_ldda_to_folder5( self ):
        """
        Testing adding a new library dataset to library5's folder, making sure the TextField setting is correct on the upload form.
        """
        # Logged in as admin_user
        filename = '5.bed'
        ldda_message = '5.bed message'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library5.id ),
                                     folder_id=self.security.encode_id( folder5.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'TextField', 'This text should be inherited' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library5.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library5.id ),
                             self.security.encode_id( folder5.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'TextField', 'This text should be inherited' ] )

    def test_145_edit_library5_template_layout( self ):
        """Test editing the layout of library5's template"""
        # Currently there is only a TextField, and we'll add a TextArea.
        self.edit_template( cntrller='library_admin',
                            item_type='library',
                            form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                            library_id=self.security.encode_id( library5.id ),
                            field_type='TextArea',
                            field_label_1=TextArea_form.name,
                            field_helptext_1='%s help' % TextArea_form.name,
                            field_default_1='%s default' % TextArea_form.name )

    def test_150_add_ldda_to_library5( self ):
        """
        Testing adding a new library dataset to library5's folder, making sure the TextField and new TextArea settings are correct on the upload form.
        """
        filename = '6.bed'
        ldda_message = '6.bed message'
        # Logged in as admin_user
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library5.id ),
                                     folder_id=self.security.encode_id( library5.root_folder.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'TextField',
                                                         'This text should be inherited',
                                                         'TextArea' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library5.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library5.id ),
                             self.security.encode_id( library5.root_folder.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'TextField',
                                                 'This text should be inherited',
                                                 'TextArea' ] )

    def test_155_add_template_to_library6( self ):
        """ Testing add an inheritable template containing an WorkflowField to library6"""
        # Add an inheritable template to library6
        # We won't select an option since we have no workflow to select
        self.add_template( cntrller='library_admin',
                           item_type='library',
                           form_type=galaxy.model.FormDefinition.types.LIBRARY_INFO_TEMPLATE,
                           form_id=self.security.encode_id( WorkflowField_form.id ),
                           form_name=WorkflowField_form.name,
                           library_id=self.security.encode_id( library6.id ) )

    def test_160_add_folder6_to_library6( self ):
        """Testing adding a folder to library6"""
        # Logged in as admin_user
        # Add a folder to library5
        folder = library6.root_folder
        name = "folder"
        description = "folder description"
        self.add_folder( 'library_admin',
                         self.security.encode_id( library6.id ),
                         self.security.encode_id( folder.id ),
                         name=name,
                         description=description )
        global folder6
        folder6 = get_folder( folder.id, name, description )

    def test_165_save_folder6_inherited_template( self ):
        """Saving the inherited template for folder6"""
        # Logged in as admin_user
        # Save the inherited template - we won't select an option since we have no workflow to select
        self.folder_info( cntrller='library_admin',
                          folder_id=self.security.encode_id( folder6.id ),
                          library_id=self.security.encode_id( library6.id ),
                          template_fields=[ ( workflow_field_name, 'none' ) ],
                          strings_displayed=[ WorkflowField_form.name,
                                              'This is an inherited template and is not required to be used with this folder',
                                              'none' ] )

    def test_170_add_ldda_to_folder6( self ):
        """
        Testing adding a new library dataset to library6's folder, making sure the WorkflowField setting is correct on the upload form.
        """
        # Logged in as admin_user
        filename = '7.bed'
        ldda_message = '7.bed message'
        self.upload_library_dataset( cntrller='library_admin',
                                     library_id=self.security.encode_id( library6.id ),
                                     folder_id=self.security.encode_id( folder6.id ),
                                     filename=filename,
                                     file_type='bed',
                                     dbkey='hg18',
                                     ldda_message=ldda_message,
                                     strings_displayed=[ 'WorkflowField', 'none' ] )
        ldda = get_latest_ldda_by_name( filename )
        assert ldda is not None, 'Problem retrieving LibraryDatasetDatasetAssociation ldda from the database'
        self.browse_library( cntrller='library_admin',
                             library_id=self.security.encode_id( library6.id ),
                             strings_displayed=[ ldda.name, ldda.message, 'bed' ] )
        # Make sure the library template contents were correctly saved
        self.ldda_edit_info( 'library_admin',
                             self.security.encode_id( library6.id ),
                             self.security.encode_id( folder6.id ),
                             self.security.encode_id( ldda.id ),
                             ldda.name,
                             strings_displayed=[ 'WorkflowField', 'none' ] )

    def test_999_reset_data_for_later_test_runs( self ):
        """Reseting data to enable later test runs to pass"""
        # Logged in as admin_user
        ##################
        # Delete all form definitions
        ##################
        for form in [ AddressField_form, CheckboxField_form, SelectField_form, TextArea_form, TextField_form, WorkflowField_form ]:
            self.mark_form_deleted( self.security.encode_id( form.form_definition_current.id ) )
        ##################
        # Mark all user_addresses deleted
        ##################
        for user_address in [ user_address1, user_address2 ]:
            mark_obj_deleted( user_address )
        ##################
        # Purge all libraries
        ##################
        for library in [ library1, library2, library3, library4, library5, library6 ]:
            self.delete_library_item( 'library_admin',
                                      self.security.encode_id( library.id ),
                                      self.security.encode_id( library.id ),
                                      library.name,
                                      item_type='library' )
            self.purge_library( self.security.encode_id( library.id ), library.name )
        ##################
        # Make sure all users are associated only with their private roles
        ##################
        for user in [ admin_user, regular_user1, regular_user2, regular_user3 ]:
            refresh( user )
            if len( user.roles) != 1:
                raise AssertionError( '%d UserRoleAssociations are associated with %s ( should be 1 )' % ( len( user.roles ), user.email ) )
