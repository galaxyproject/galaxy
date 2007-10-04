import pkg_resources
pkg_resources.require('twill')

import StringIO
import os, sys, random, filecmp, time, unittest, urllib, logging, difflib
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

    #Functions associated with files
    def files_diff( self, file1, file2 ):
        """Checks the contents of 2 files for differences"""
        if not filecmp.cmp(file1, file2):
            for line1, line2 in zip(file(file1), file(file2)):
                line1 = line1.rstrip('\r\n')
                line2 = line2.rstrip('\r\n')
                if line1 != line2:
                    # nicer message
                    fromlines = open( file1, 'U').readlines()
                    tolines = open( file2, 'U').readlines()
                    diff = difflib.unified_diff( fromlines, tolines, "local_file", "history_data" )
                    diff_slice = list( islice( diff, 40 ) )
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

    #Functions associated with histories
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

    def delete_history( self, hid ):
        """Deletes a history"""
        data_list = self.get_datasets_in_history()
        self.assertTrue( data_list )
        if hid < 0:
            hid = len(data_list) + hid + 1
        hid = str(hid)
        elems = [ elem for elem in data_list if elem.get('hid') == hid ]
        self.assertEqual(len(elems), 1)
        self.visit_page( "history_delete?id=%s" % elems[0].get('id') )

    def delete_history_item( self, hid ):
        """Deletes an item from a history"""
        hid = str(hid)
        data_list = self.get_datasets_in_history()
        self.assertTrue( data_list )
        elems = [ elem for elem in data_list if elem.get('hid') == hid ]
        self.assertEqual(len(elems), 1)
        self.visit_page( "delete?id=%s" % elems[0].get('id') )

    def history_as_xml_tree( self ):
        """Returns a parsed xml object of a history"""
        self.home()
        self.visit_page( 'history?template=history.xml' )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree

    def histories_as_xml_tree( self ):
        """Returns a parsed xml object of all histories"""
        self.home()
        self.visit_page( 'history?template=history_ids.xml' )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree

    def new_history( self ):
        """Creates a new, empty history"""
        self.visit_page( "history_new" )
        self.check_history_for_string('Your history is empty')

    def set_history( self ):
        """Sets the history (stores the cookies for this run)"""
        if self.history_id:
            self.visit_page( "history?id=%s" % self.history_id )
        else:
            self.new_history()

    def switch_history( self, hid=None ):
        """Switches to a history in the current list of histories"""
        data_list = self.get_datasets_in_histories()
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

    #unctions associated with datasets (history items) and meta data
    def _assert_dataset_state( self, elem, state ):
        assert elem.get( 'state' ) == state, \
            "Expecting dataset state '%s' but is '%s'. Dataset blurb: %s" % ( state, elem.get('state'), elem.text.strip() )

    def verify_dataset_correctness( self, filename, hid=None, wait=True ):
        """Verifies that the attributes and contents of a history item meet expectations"""
        if wait: self.wait() #wait for job to finish

        data_list = self.get_datasets_in_history()
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

        local_name = self.get_filename( filename )
        temp_name = self.get_filename( 'temp_%s' % filename )
        self.visit_page( "display?hid=" + hid )
        data = self.last_page()
        file( temp_name, 'wb' ).write(data)

        try:
            self.files_diff( local_name, temp_name )
        except AssertionError, err:
            errmsg = 'History item %s different than expected, difference:' % hid
            errmsg += str( err )
            raise AssertionError( errmsg )
        os.remove(temp_name)

    def verify_genome_build( self, dbkey='hg17' ):
        """Verifies that the last used genome_build at history id 'hid' is as expected"""
        data_list = self.get_datasets_in_history()
        self.assertTrue( data_list )
        elems = [ elem for elem in data_list ]
        elem = elems[-1]
        genome_build = elem.get('dbkey')
        self.assertTrue( genome_build == dbkey )

    def check_metadata_for_string( self, patt, hid=None ):
        """Looks for 'patt' in the edit page when editing a dataset"""
        data_list = self.get_datasets_in_history()
        self.assertTrue( data_list )
        if hid is None: # take last hid
            elem = data_list[-1]
            hid = elem.get('hid')
        self.assertTrue( hid )
        self.visit_page( "edit?hid=%d" % hid )
        for subpatt in patt.split():
            tc.find(subpatt)

    def edit_metadata( self, hid=None, form=1, **kwd ):
        """Edits the metadata associated with a history item.  There are currently 3 forms on the edit page."""
        data_list = self.get_datasets_in_history()
        self.assertTrue( data_list )
        if hid is None: # take last hid
            elem = data_list[-1]
            hid = elem.get('hid')
        self.assertTrue( hid )
        self.visit_page( 'edit?hid=%d' % hid )
        if form == 1: button = "save"           #Edit Attributes form
        elif form == 2: button = "convert_data" #Convert to new format form
        elif form == 3: button = "change"       #Change data type form
        if kwd:
            self.submit_form(form=form, button=button, **kwd)

    def get_datasets_in_history( self ):
        """Returns datasets in a history"""
        tree = self.history_as_xml_tree()
        data_list = [ elem for elem in tree.findall("data") ]
        return data_list

    def get_dataset_ids_in_history( self ):
        """Returns the ids of datasets in a history"""
        data_list = self.get_datasets_in_history()
        hids = []
        for elem in data_list:
            hid = elem.get('hid')
            hids.append(hid)
        return hids

    def get_datasets_in_histories( self ):
        """Returns all datasets in all histories"""
        tree = self.histories_as_xml_tree()
        data_list = [ elem for elem in tree.findall("data") ]
        return data_list

    def get_dataset_ids_in_histories( self ):
        """Returns the ids of datasets in all histories"""
        data_list = self.get_datasets_in_histories()
        hids = []
        for elem in data_list:
            hid = elem.get('hid')
            hids.append(hid)
        return hids

    #Functions associated with browsers, cookies, HTML forms and page visits
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
                if 'onchange' in control.attrs.keys():
                    changed = False
                    for elem in kwd[control.name]:
                        """
                        For file parameter, control.value is the index of the file list, but elem is the filename.
                        The following loop gets the filename of that index.
                        """
                        param_text = ''
                        for param in tc.show().split('<select') : 
                            param = ('<select' + param.split('select>')[0] + 'select>').replace('selected', 'selected="yes"')
                            if param.find('onchang') != -1 and param.find('name="%s"' % control.name) != -1: 
                                tree = ElementTree.fromstring(param)
                                for option in tree.findall('option') : 
                                    if option.get('value') in control.value:
                                        param_text = option.text.strip()
                                        break
                                break

                        if elem not in control.value and param_text.find(elem) == -1 :
                            changed = True
                            break
                    if changed:
                        #Clear Control and set to proper value
                        control.clear()
                        for elem in kwd[control.name]:
                            tc.fv(str(form), str(i+1), str(elem) )                        
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
                        tc.fv(str(form), str(i+1), ",".join(value) )
                    else:
                        for elem in value:
                            tc.fv(str(form), str(i+1), str(elem) )
                    break
        tc.submit(button)

    def visit_page( self, page ):
        tc.go("./%s" % page)
        tc.code( 200 )

    def visit_url( self, url ):
        tc.go("%s" % url)
        tc.code( 200 )

    #Functions associated with Galaxy tools
    def run_tool( self, tool_id, **kwd ):
        tool_id = tool_id.replace(" ", "+")
        """Runs the tool 'tool_id' and pass it the key/values from the *kwd"""
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
