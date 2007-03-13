import pkg_resources
pkg_resources.require('twill')

import StringIO
import os, sys, random, filecmp, time, unittest, urllib, logging, difflib
from itertools import *

import twill
import twill.commands as tc
from elementtree import ElementTree

buffer = StringIO.StringIO()

# Force twill to log to a buffer -- FIXME: Should this go to stdout and be 
# captured by nose? 
twill.set_output(buffer)
tc.config('use_tidy', 0)

# Dial ClientCookie logging down (very noisy)
logging.getLogger( "ClientCookie.cookies" ).setLevel( logging.WARNING )

class TwillTestCase(unittest.TestCase):

    def setUp(self):
        self.history_id = os.environ.get( 'GALAXY_TEST_HISTORY_ID', None )
        self.host = os.environ.get( 'GALAXY_TEST_HOST' )
        self.port = os.environ.get( 'GALAXY_TEST_PORT' )
        self.url = "http://%s:%s" % ( self.host, self.port )
        self.file_dir = os.environ.get( 'GALAXY_TEST_FILE_DIR' )
        self.home()
        self.set_history()

    def get_fname(self, fname):
        full = os.path.join( self.file_dir, fname)
        return os.path.abspath(full)

    def home(self):
        tc.go("%s" % self.url)
        tc.code(200)

    def go2myurl(self, myurl):
        tc.go("%s" % myurl)
#       print "+++++++++++++++++++++++++++++"
#       print tc.show()
#       print "-----------------------------"
        tc.code(200)

    def reload_page(self):
        tc.reload()
        tc.code(200)

    def set_history(self):
        """Sets the history (stores the cookies for this run)"""
        if self.history_id:
            tc.go( "./history?id=%s" % self.history_id )
        else:
            tc.go( "./history" )
        tc.code(200)

    def clear_history(self):
        tc.go("./history_new")
        tc.go("./history")
        tc.find('Your history is empty')

    def upload_file(self, fname, ftype='auto', dbkey='hg17'):
        """Uploads a file"""
        fname = self.get_fname(fname)
        tc.go("./tool_runner/index?tool_id=upload1")
        tc.fv("1","file_type", ftype)
        tc.fv("1","dbkey", dbkey)
        tc.formfile("1","file_data", fname)
        tc.submit("runtool_btn")
        self.home()

    def edit_data(self, hid, check_patt=None, **kwd):
        """
        Edits data and sets parameters accordig to the keyword arguments
        """
        tc.go('./edit?hid=%d' % hid )
        if check_patt:
            tc.find(check_patt)
        if kwd:
            self.submit_form(form=1, button="edit_genome_btn", **kwd)

    def get_xml_history(self):
        """Returns a parsed xml object corresponding to the history"""
        self.home()
        tc.go('./history?template=history.xml' )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree

    def get_data_list(self):
        """Returns the data at history id 'hid'"""
        tree = self.get_xml_history()
        data_list = [ elem for elem in tree.findall("data") ]
        return data_list

    def delete_data(self, hid):
        """Deletes data at a certain history id"""
        hid = str(hid)
        data_list = self.get_data_list()
        self.assertTrue( data_list )
        elems = [ elem for elem in data_list if elem.get('hid') == hid ]
        self.assertEqual(len(elems), 1)
        tc.go("/delete?id=%s" % elems[0].get('id') )
        tc.code(200)


    def get_xml_history_ids(self):
        """Returns a parsed xml object corresponding to the history"""
        self.home()
        tc.go('./history?template=history_ids.xml' )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
#       print "xml=", xml
#       print "tree=", tree
        return tree

    def get_history_ids(self):
        """Returns the data at history id 'hid'"""
        tree = self.get_xml_history_ids()
        data_list = [ elem for elem in tree.findall("data") ]
#       print "data_list=", data_list
        return data_list

    def delete_history(self, hid):
        """Deletes a history at a certain id"""
        data_list = self.get_history_ids()
        self.assertTrue( data_list )
        if hid < 0:
            hid = len(data_list) + hid +1
            print hid
        hid = str(hid)
        elems = [ elem for elem in data_list if elem.get('hid') == hid ]
        self.assertEqual(len(elems), 1)
        tc.go("/history_delete?id=%s" % elems[0].get('id') )
        tc.code(200)

    def switch_history(self, hid=None):
        """Deletes a history at a certain id"""
        data_list = self.get_history_ids()
        self.assertTrue( data_list )
        if hid is None: # take last hid
            elem = data_list[-1]
            hid = elem.get('hid')
        if hid < 0:
            hid = len(data_list) + hid +1
            print hid
        hid = str(hid)
        elems = [ elem for elem in data_list if elem.get('hid') == hid ]
        self.assertEqual(len(elems), 1)
        tc.go("/history_switch?id=%s" % elems[0].get('id') )
        tc.code(200)


    def historyid(self):
        data_list = self.get_data_list()
        hid_old = -2
        hids = []
        same = 0
        for elem in data_list:
            hid = elem.get('hid')
            hids.append(hid)
            if int(hid) == hid_old + 1:
                if same == 0 :
                    print "-",
                same =1
            else :
                if hid_old > 0 :
                    print "%d," % hid_old,
                print "%s" % hid,
                same = 0
            hid_old = int(hid)
        if same == 1 :
            print "%s" % hid
        return hids

    def _assert_dataset_state( self, elem, state ):
        assert elem.get( 'state' ) == state, \
            "Expecting dataset state '%s' but is '%s'. Dataset blurb: %s" % ( state, elem.get('state'), elem.text.strip() )

    def check_data(self, fname, hid=None, wait=True):
        """
        Verifies that a data at a history id is indentical to
        the contents of a file
        """

        if wait:  # wait for tools to finish
            self.wait()

        data_list = self.get_data_list()
        self.assertTrue( data_list )

        if hid is None: # take last hid
            elem = data_list[-1]
        else:
            hid = str(hid)
            elems = [ elem for elem in data_list if elem.get('hid') == hid ]
            self.assertTrue( len(elems) == 1 )
            elem = elems[0]

        if elem.get('state') != 'ok':
            tc.go("./history")
            tc.code(200)
#          print tc.show()

        hid = elem.get('hid')
        self.assertTrue( hid )
        self._assert_dataset_state( elem, 'ok' )

        local_name = self.get_fname(fname)
        temp_name  = self.get_fname('temp_%s' % fname)
        tc.go("./display?hid=" + str(hid) )

        data = self.last_page()
        file(temp_name, 'wb').write(data)

        try:
            self.diff(local_name, temp_name)
        except AssertionError, err:
            errmsg = 'Data at history id %s does not match expected, diff:\n' % hid
            errmsg += str( err )
            raise AssertionError( errmsg )

        os.remove(temp_name)

    def submit_form(self, form=1, button="runtool_btn", **kwd):
        """Populates and submits a form from the keyword arguments"""
        for key, value in kwd.items():
            # needs to be able to handle multiple values per key
            if type(value) != type([]):
                value = [ value ]
            for elem in value:
                tc.fv(str(form), str(key), str(elem) )
        tc.submit(button)

    def last_page(self):
        return tc.browser.get_html()

    def clear_cookies(self):
        tc.clear_cookies()

    def load_cookies(self, file):
        fname = self.get_fname(file)
        tc.load_cookies(fname)

    def show_cookies(self):
        return tc.show_cookies()

    def showforms(self):
        """Shows form, helpful for debugging new tests"""
        return tc.browser.showforms()

    def run_tool(self, tool_id, **kwd):
        tool_id = tool_id.replace(" ", "+")
        """Runs the tool 'tool_id' and pass it the key/values from the *kwd"""
        tc.go("%s/tool_runner/index?tool_id=%s" % (self.url, tool_id) )
        tc.code(200)
        tc.find('runtool_btn')
        self.submit_form(**kwd)
        tc.code(200)

    def save_log(*path):
        """Saves the log to a file"""
        fname = os.path.join( *path )
        file(fname, 'wt').write(buffer.getvalue())

    def wait(self, maxiter=20):
        """Waits for the tools to finish"""
        count = 0
        sleep_amount = 1
        self.home()
        while count < maxiter:
            count += 1
            tc.go("./history")
            page = tc.browser.get_html()
            if page.find('add_refresh( 9 );') > -1:
                time.sleep( sleep_amount )
                sleep_amount += 1
            else:
                break
        self.assertNotEqual(count, maxiter)

    def check_history(self, patt):
        """Checks history for a pattern"""
        tc.go("./history")
        for subpatt in patt.split():
            tc.find(subpatt)

    def check_data_prop(self, patt, hid=None):
        """Check properties of data(hid=**) for patterns"""
        tc.go("./edit?hid=%d" % hid)
        for subpatt in patt.split():
            tc.find(subpatt)

    def check_errors(self):
        """Waits for the tools to finish"""
        tc.go("./history")
        page = self.last_page()
        if page.find('error') > -1:
            raise AssertionError('Errors in the history for user %s' % self.user )

    def diff(self, file1, file2):
        if not filecmp.cmp(file1, file2):
            #maybe it is just the line endings
            lc = 0
            for line1, line2 in zip(file(file1), file(file2)):
                lc += 1
                line1 = line1.strip()
                line2 = line2.strip()
                if line1 != line2:
                    # nicer message
                    fromlines = open( file1, 'U').readlines()
                    tolines = open( file2, 'U').readlines()
                    diff = difflib.unified_diff( fromlines, tolines, "local_file", "history_data" )
                    diff_slice = list( islice( diff, 40 ) )
                    raise AssertionError( "".join( diff_slice ) )
        return True
