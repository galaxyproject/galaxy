import pkg_resources
pkg_resources.require('twill')

import StringIO
import os, sys, random, filecmp, time, unittest, urllib, logging, difflib, zipfile
from itertools import *

import twill
import twill.commands as tc
from twill.other_packages import ClientForm
from elementtree import ElementTree

buffer = StringIO.StringIO()

#Force twill to log to a buffer -- FIXME: Should this go to stdout and be captured by nose?
twill.set_output(buffer)
tc.config('use_tidy', 0)

# Dial ClientCookie logging down (very noisy)
logging.getLogger( "ClientCookie.cookies" ).setLevel( logging.WARNING )

class TwillTestCase( unittest.TestCase ):

    def setUp( self ):
        self.history_id = os.environ.get( 'GALAXY_TEST_HISTORY_ID', None )
        self.host = os.environ.get( 'GALAXY_TEST_HOST' )
        self.port = os.environ.get( 'GALAXY_TEST_PORT' )
        self.url = "http://%s:%s" % ( self.host, self.port )
        self.file_dir = os.environ.get( 'GALAXY_TEST_FILE_DIR' )
        self.home()
        self.set_history()

    """Functions associated with files"""
    def files_diff( self, file1, file2 ):
        """Checks the contents of 2 files for differences"""
        if not filecmp.cmp( file1, file2 ):
            files_differ = False
            local_file = open( file1, 'U' ).readlines()
            history_data = open( file2, 'U' ).readlines()
            if len( local_file ) == len( history_data ):
                for i in range( len( history_data ) ):
                    if local_file[i].rstrip( '\r\n' ) != history_data[i].rstrip( '\r\n' ):
                        files_differ = True
                        break
            else:
                files_differ = True
            if files_differ:
                diff = difflib.unified_diff( local_file, history_data, "local_file", "history_data" )
                diff_slice = list( islice( diff, 40 ) )
                if file1.endswith( '.pdf' ) or file2.endswith( 'pdf' ):
                    # PDF files contain both a creation and modification date, so we need to
                    # handle these differences.  As long as the rest of the PDF file does not differ,
                    # we're ok.
                    if len( diff_slice ) == 13 and \
                    diff_slice[6].startswith( '-/CreationDate' ) and diff_slice[7].startswith( '-/ModDate' ) \
                    and diff_slice[8].startswith( '+/CreationDate' ) and diff_slice[9].startswith( '+/ModDate' ):
                        return True
                raise AssertionError( "".join( diff_slice ) )
        return True

    def get_filename( self, filename ):
        full = os.path.join( self.file_dir, filename)
        return os.path.abspath(full)

    def save_log( *path ):
        """Saves the log to a file"""
        filename = os.path.join( *path )
        file(filename, 'wt').write(buffer.getvalue())

    def upload_file( self, filename, ftype='auto', dbkey='unspecified (?)' ):
        """Uploads a file"""
        filename = self.get_filename(filename)
        self.visit_page( "tool_runner/index?tool_id=upload1" )
        try: 
            tc.fv("1","file_type", ftype)
            tc.fv("1","dbkey", dbkey)
            tc.formfile("1","file_data", filename)
            tc.submit("runtool_btn")
            self.home()
        except AssertionError, err:
            errmsg = 'The file doesn\'t exsit. Please check' % file
            errmsg += str( err )
            raise AssertionError( errmsg )

    """Functions associated with histories"""
    def check_history_for_errors( self ):
        """Raises an exception if there are errors in a history"""
        self.visit_page( "history" )
        page = self.last_page()
        if page.find( 'error' ) > -1:
            raise AssertionError('Errors in the history for user %s' % self.user )

    def check_history_for_string( self, patt ):
        """Looks for 'string' in history page"""
        self.visit_page( "history" )
        for subpatt in patt.split():
            tc.find(subpatt)

    def clear_history( self ):
        """Empties a history of all datasets"""
        self.visit_page( "clear_history" )
        self.check_history_for_string( 'Your history is empty' )

    def delete_history( self, id=None ):
        """Deletes a history"""
        history_list = self.get_histories()
        self.assertTrue( history_list )
        if id is None:
            history = history_list[-1]
            id = history.get( 'id' )
        id = str( id )
        self.visit_page( "history_delete?id=%s" %(id) )

    def get_histories( self ):
        """Returns all histories"""
        tree = self.histories_as_xml_tree()
        data_list = [ elem for elem in tree.findall("data") ]
        return data_list

    def get_history( self ):
        """Returns a history"""
        tree = self.history_as_xml_tree()
        data_list = [ elem for elem in tree.findall("data") ]
        return data_list

    def history_as_xml_tree( self ):
        """Returns a parsed xml object of a history"""
        self.home()
        self.visit_page( 'history?as_xml=True' )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree

    def histories_as_xml_tree( self ):
        """Returns a parsed xml object of all histories"""
        self.home()
        self.visit_page( 'history_available?as_xml=True' )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree
    
    def history_options( self ):
        """Mimics user clicking on history options link"""
        self.visit_page( "history_options" )

    def new_history( self ):
        """Creates a new, empty history"""
        self.visit_page( "history_new" )
        self.check_history_for_string('Your history is empty')

    def rename_history( self, id=None, name='NewTestHistory' ):
        """Rename an existing history"""
        history_list = self.get_histories()
        self.assertTrue( history_list )
        if id is None: # take last id
            elem = history_list[-1]
        else:
            i = history_list.index( id )
            self.assertTrue( i )
            elem = history_list[i]
        id = elem.get( 'id' )
        self.assertTrue( id )
        old_name = elem.get( 'name' )
        self.assertTrue( old_name )
        id = str( id )
        self.visit_page( "history_rename?id=%s&name=%s" %(id, name) )
        return id, old_name, name

    def set_history( self ):
        """Sets the history (stores the cookies for this run)"""
        if self.history_id:
            self.visit_page( "history?id=%s" % self.history_id )
        else:
            self.new_history()

    def share_history( self, id=None, email='test2@bx.psu.edu' ):
        """Share a history with a different user"""
        self.create( email=email, password='testuser', confirm='testuser' )
        history_list = self.get_histories()
        self.assertTrue( history_list )
        if id is None: # take last id
            elem = history_list[-1]
        else:
            i = history_list.index( id )
            self.assertTrue( i )
            elem = history_list[i]
        id = elem.get( 'id' )
        self.assertTrue( id )
        id = str( id )
        name = elem.get( 'name' )
        self.assertTrue( name )
        self.visit_page( "history_share?id=%s&email=%s" %(id, email) )
        return id, name, email

    def switch_history( self, hid=None ):
        """Switches to a history in the current list of histories"""
        data_list = self.get_histories()
        self.assertTrue( data_list )
        if hid is None: # take last hid
            elem = data_list[-1]
            hid = elem.get('hid')
        if hid < 0:
            hid = len(data_list) + hid + 1
        hid = str(hid)
        elems = [ elem for elem in data_list if elem.get('hid') == hid ]
        self.assertEqual(len(elems), 1)
        self.visit_page( "history_switch?id=%s" % elems[0].get('id') )

    def view_stored_histories( self ):
        self.visit_page( "history_available" )

    """Functions associated with datasets (history items) and meta data"""
    def _assert_dataset_state( self, elem, state ):
        assert elem.get( 'state' ) == state, \
            "Expecting dataset state '%s' but is '%s'. Dataset blurb: %s" % ( state, elem.get('state'), elem.text.strip() )

    def check_metadata_for_string( self, patt, hid=None ):
        """Looks for 'patt' in the edit page when editing a dataset"""
        data_list = self.get_history()
        self.assertTrue( data_list )
        if hid is None: # take last hid
            elem = data_list[-1]
            hid = int( elem.get('hid') )
        self.assertTrue( hid )
        self.visit_page( "edit?hid=%d" % hid )
        for subpatt in patt.split():
            tc.find(subpatt)

    def delete_history_item( self, hid ):
        """Deletes an item from a history"""
        hid = str(hid)
        data_list = self.get_history()
        self.assertTrue( data_list )
        elems = [ elem for elem in data_list if elem.get('hid') == hid ]
        self.assertEqual(len(elems), 1)
        self.visit_page( "delete?id=%s" % elems[0].get('id') )

    def edit_metadata( self, hid=None, form=1, **kwd ):
        """Edits the metadata associated with a history item.  There are currently 3 forms on the edit page."""
        data_list = self.get_history()
        self.assertTrue( data_list )
        if hid is None: # take last hid
            elem = data_list[-1]
            hid = elem.get('hid')
        self.assertTrue( hid )
        self.visit_page( 'edit?hid=%d' % hid )
        if form == 1: button = "save"           #Edit Attributes form
        elif form == 2: button = "detect"       #Auto-detect Metadata Attributes
        elif form == 3: button = "convert_data" #Convert to new format form
        elif form == 4: button = "change"       #Change data type form
        if kwd:
            self.submit_form(form=form, button=button, **kwd)

    def get_dataset_ids_in_history( self ):
        """Returns the ids of datasets in a history"""
        data_list = self.get_history()
        hids = []
        for elem in data_list:
            hid = elem.get('hid')
            hids.append(hid)
        return hids

    def get_dataset_ids_in_histories( self ):
        """Returns the ids of datasets in all histories"""
        data_list = self.get_histories()
        hids = []
        for elem in data_list:
            hid = elem.get('hid')
            hids.append(hid)
        return hids

    def verify_dataset_correctness( self, filename, hid=None, wait=True ):
        """Verifies that the attributes and contents of a history item meet expectations"""
        if wait: self.wait() #wait for job to finish

        data_list = self.get_history()
        self.assertTrue( data_list )

        if hid is None: # take last hid
            elem = data_list[-1]
            hid = str( elem.get('hid') )
        else:
            hid = str( hid )
            elems = [ elem for elem in data_list if elem.get('hid') == hid ]
            self.assertTrue( len(elems) == 1 )
            elem = elems[0]

        self.assertTrue( hid )
        self._assert_dataset_state( elem, 'ok' )

        if self.is_zipped( filename ):
            errmsg = 'History item %s is a zip archive which includes invalid files:\n' % hid
            zip_file = zipfile.ZipFile( filename, "r" )
            name = zip_file.namelist()[0]
            test_ext = name.split( "." )[1].strip().lower()
            if not ( test_ext == 'scf' or test_ext == 'ab1' or test_ext == 'txt' ):
                raise AssertionError( errmsg )
            for name in zip_file.namelist():
                ext = name.split( "." )[1].strip().lower()
                if ext != test_ext:
                    raise AssertionError( errmsg )
        else:
            local_name = self.get_filename( filename )
            temp_name = self.get_filename( 'temp_%s' % filename )
            self.visit_page( "display?hid=" + hid )
            data = self.last_page()
            file( temp_name, 'wb' ).write(data)
            try:
                self.files_diff( local_name, temp_name )
            except AssertionError, err:
                os.remove(temp_name)
                errmsg = 'History item %s different than expected, difference:\n' % hid
                errmsg += str( err )
                raise AssertionError( errmsg )
            os.remove(temp_name)

    def is_zipped( self, filename ):
        if not zipfile.is_zipfile( filename ):
            return False
        return True

    def is_binary( self, filename ):
        temp = open( temp_name, "U" )
        lineno = 0
        for line in temp:
            lineno += 1
            line = line.strip()
            if line:
                for char in line:
                    if ord( char ) > 128:
                        return True
            if lineno > 10:
                break
        return False

    def verify_genome_build( self, dbkey='hg17' ):
        """Verifies that the last used genome_build at history id 'hid' is as expected"""
        data_list = self.get_history()
        self.assertTrue( data_list )
        elems = [ elem for elem in data_list ]
        elem = elems[-1]
        genome_build = elem.get('dbkey')
        self.assertTrue( genome_build == dbkey )

    """Functions associated with user accounts"""
    def create( self, email='test@bx.psu.edu', password='testuser', confirm='testuser' ):
        self.visit_page( "user/create?email=%s&password=%s&confirm=%s" %(email, password, confirm) )
        try:
            self.check_page_for_string( "User with that email already exists" )
        except:
            self.check_page_for_string( "Now logged in as %s" %email )
        self.home() #Reset our URL for future tests
        
    def login( self, email='test@bx.psu.edu', password='testuser'):
        self.create( email=email, password=password, confirm=password )
        self.visit_page( "user/login?email=%s&password=%s" % (email, password) )
        self.check_page_for_string( "Now logged in as %s" %email )
        self.home() #Reset our URL for future tests

    def logout( self ):
        self.visit_page( "user/logout" )
        self.check_page_for_string( "You are no longer logged in" )
        self.home() #Reset our URL for future tests

    """Functions associated with browsers, cookies, HTML forms and page visits"""
    def check_page_for_string( self, patt ):
        """Looks for 'patt' in the current browser page"""
        page = self.last_page()
        for subpatt in patt.split():
            if page.find( patt ) == -1:
                errmsg = "TwillAssertionError: no match to '%s'" %patt
                raise AssertionError( errmsg )

    def clear_cookies( self ):
        tc.clear_cookies()

    def clear_form( self, form=0 ):
        """Clears a form"""
        tc.formclear(str(form))

    def home( self ):
        self.visit_url( self.url )

    def last_page( self ):
        return tc.browser.get_html()

    def load_cookies( self, file ):
        filename = self.get_filename(file)
        tc.load_cookies(filename)

    def reload_page( self ):
        tc.reload()
        tc.code(200)

    def show_cookies( self ):
        return tc.show_cookies()

    def showforms( self ):
        """Shows form, helpful for debugging new tests"""
        return tc.browser.showforms()

    def submit_form( self, form=1, button="runtool_btn", **kwd ):
        """Populates and submits a form from the keyword arguments"""
        #Check for onchange attribute, submit a change if required
        for i, control in enumerate(tc.showforms()[form-1].controls):
            try:
                if 'refresh_on_change' in control.attrs.keys():
                    changed = False
                    for elem in kwd[control.name]:
                        """
                        For DataToolParameter, control.value is the index of the DataToolParameter select list, 
                        but elem is the filename.  The following loop gets the filename of that index.
                        """
                        param_text = ''
                        for param in tc.show().split('<select'):
                            param = ('<select' + param.split('select>')[0] + 'select>').replace('selected', 'selected="yes"')
                            if param.find('on_chang') != -1 and param.find('name="%s"' % control.name) != -1:
                                tree = ElementTree.fromstring(param)
                                for option in tree.findall('option'): 
                                    if option.get('value') in control.value:
                                        param_text = option.text.strip()
                                        break
                                break

                        if elem not in control.value and param_text.find(elem) == -1 :
                            changed = True
                            break
                    if changed:
                        # Clear Control and set to proper value - the command: 
                        # formvalue <formnum> <fieldname> <value>
                        # sets the given field in the given form to the given value. 
                        # For read-only form widgets/controls, the click may be recorded for use by submit, 
                        # but the value is not changed unless the 'config' command has changed the default behavior.
                        control.clear()
                        for elem in kwd[control.name]:
                            tc.formvalue(str(form), str(i+1), str(elem) )                        
                        #Create a new submit control, allows form to refresh, instead of going to next page
                        control = ClientForm.SubmitControl('SubmitControl','___refresh_grouping___',{'name':'refresh_grouping'})
                        control.add_to_form(tc.showforms()[form-1])
                        #submit for refresh
                        tc.submit('___refresh_grouping___')
                        #start over submit_form()
                        return self.submit_form(form, button, **kwd)
            except: continue
        
        for key, value in kwd.items():
            # needs to be able to handle multiple values per key
            if not isinstance(value, list):
                value = [ value ]

            for i, control in enumerate(tc.showforms()[form-1].controls):
                if control.name == key:
                    control.clear()
                    if control.is_of_kind("text"):
                        # set the given field in the given form to the given value. 
                        tc.formvalue(str(form), str(i+1), ",".join(value) )
                    else:
                        try:
                            for elem in value:
                                tc.formvalue(str(form), str(i+1), str(elem) )
                        except Exception, exc:
                            errmsg = "Attempting to set field '%s' to value '%s' threw exception: '%s'\n" % ( str( key ), str( elem ), str( exc ) )
                            errmsg += "control: %s\n" % str( control )
                            errmsg += "If the above control is a DataToolparameter whose data type class does not include a sniff() method,\n"
                            errmsg += "make sure to include a proper 'ftype' attribute to the tag for the control within the <test> tag set.\n"
                            raise AssertionError( errmsg )
                    break
        tc.submit(button)

    def visit_page( self, page ):
        tc.go("./%s" % page)
        tc.code( 200 )

    def visit_url( self, url ):
        tc.go("%s" % url)
        tc.code( 200 )

    """Functions associated with Galaxy tools"""
    def run_tool( self, tool_id, **kwd ):
        tool_id = tool_id.replace(" ", "+")
        """Runs the tool 'tool_id' and passes it the key/values from the *kwd"""
        self.visit_url( "%s/tool_runner/index?tool_id=%s" % (self.url, tool_id) )
        tc.find('runtool_btn')
        self.submit_form(**kwd)

    def wait( self, maxiter=20 ):
        """Waits for the tools to finish"""
        count = 0
        sleep_amount = 1
        self.home()
        while count < maxiter:
            count += 1
            self.visit_page( "history" )
            page = tc.browser.get_html()
            if page.find( '<!-- running: do not change this comment, used by TwillTestCase.wait -->' ) > -1:
                time.sleep( sleep_amount )
                sleep_amount += 1
            else:
                break
        self.assertNotEqual(count, maxiter)
