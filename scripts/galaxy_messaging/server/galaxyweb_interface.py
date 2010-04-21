import ConfigParser
import sys, os
import serial
import array
import time
import optparse,array
import shutil, traceback
import urllib,urllib2, cookielib

assert sys.version_info[:2] >= ( 2, 4 )
new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
import pkg_resources

import pkg_resources
pkg_resources.require( "pycrypto" )

from Crypto.Cipher import Blowfish
from Crypto.Util.randpool import RandomPool
from Crypto.Util import number


class GalaxyWebInterface(object):
    def __init__(self, server_host, server_port, datatx_email, datatx_password):
        self.server_host = server_host#config.get("main", "server_host")
        self.server_port = server_port#config.get("main", "server_port")
        self.datatx_email = datatx_email#config.get("main", "datatx_email")
        self.datatx_password = datatx_password#config.get("main", "datatx_password")
        try:
            # create url
            self.base_url =  "http://%s:%s" % (self.server_host, self.server_port)
            # login 
            url = "%s/user/login?email=%s&password=%s&login_button=Login" % (self.base_url, self.datatx_email, self.datatx_password)
            cj = cookielib.CookieJar()
            self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            #print url
            f = self.opener.open(url)
            if f.read().find("ogged in as "+self.datatx_email) == -1:
                # if the user doesnt exist, create the user
                url = "%s/user/create?email=%s&username=%s&password=%s&confirm=%s&create_user_button=Submit" % ( self.base_url, self.datatx_email, self.datatx_email, self.datatx_password, self.datatx_password )
                f = self.opener.open(url)
                if f.read().find("ogged in as "+self.datatx_email) == -1:
                    raise "The "+self.datatx_email+" user could not login to Galaxy"
        except:
            print traceback.format_exc()
            sys.exit(1)
            
    def add_to_library(self, server_dir, library_id, folder_id, dbkey=''):
        '''
        This method adds the dataset file to the target data library & folder
        by opening the corresponding url in Galaxy server running.  
        '''
        try:
            params = urllib.urlencode(dict( cntrller='library_admin',
                                            tool_id='upload1',
                                            tool_state='None',
                                            library_id=self.encode_id(library_id),
                                            folder_id=self.encode_id(folder_id),
                                            upload_option='upload_directory',
                                            file_type='auto',
                                            server_dir=os.path.basename(server_dir),
                                            dbkey=dbkey,
                                            show_dataset_id='True',
                                            runtool_btn='Upload to library'))
            #url = "http://localhost:8080/library_common/upload_library_dataset?cntrller=library_admin&tool_id=upload1&tool_state=None&library_id=adb5f5c93f827949&folder_id=adb5f5c93f827949&upload_option=upload_directory&file_type=auto&server_dir=003&dbkey=%3F&message=&runtool_btn=Upload+to+library"
            #url = base_url+"/library_common/upload_library_dataset?library_id=adb5f5c93f827949&tool_id=upload1&file_type=auto&server_dir=datatx_22858&dbkey=%3F&upload_option=upload_directory&folder_id=529fd61ab1c6cc36&cntrller=library_admin&tool_state=None&runtool_btn=Upload+to+library"
            url = self.base_url+"/library_common/upload_library_dataset"
            #print url
            #print params
            f = self.opener.open(url, params)
            if f.read().find("Data Library") == -1:
                raise "Dataset could not be uploaded to the data library"
        except:
            print traceback.format_exc()
            sys.exit(1)
            
    def import_to_history(self, ldda_id, library_id, folder_id):
        try:
            params = urllib.urlencode(dict( cntrller='library_admin',
                                            show_deleted='False',
                                            library_id=self.encode_id(library_id),
                                            folder_id=self.encode_id(folder_id),
                                            ldda_ids=self.encode_id(ldda_id),
                                            do_action='import_to_history',
                                            use_panels='False'))
            #url = "http://lion.bx.psu.edu:8080/library_common/act_on_multiple_datasets?library_id=adb5f5c93f827949&show_deleted=False&ldda_ids=adb5f5c93f827949&cntrller=library_admin&do_action=import_to_history&use_panels=False"
            #url = base_url+"/library_common/upload_library_dataset?library_id=adb5f5c93f827949&tool_id=upload1&file_type=auto&server_dir=datatx_22858&dbkey=%3F&upload_option=upload_directory&folder_id=529fd61ab1c6cc36&cntrller=library_admin&tool_state=None&runtool_btn=Upload+to+library"
            url = self.base_url+"/library_common/act_on_multiple_datasets"
            #print url
            #print params
            f = self.opener.open(url, params)
            x = f.read()
            if x.find("1 dataset(s) have been imported into your history.") == -1:
                #print x
                raise Exception("Dataset could not be imported into history")
        except:
            print traceback.format_exc()
            sys.exit(1)
            
            
    def run_workflow(self, workflow_id, hid, workflow_step):
        input = str(workflow_step)+'|input'
        try:
            params = urllib.urlencode({'id':self.encode_id(workflow_id),
                                       'run_workflow': 'Run workflow',
                                       input: hid})
            url = self.base_url+"/workflow/run"
            #print url+'?'+params
            f = self.opener.open(url, params)
#            if f.read().find("1 dataset(s) have been imported into your history.") == -1:
#                raise Exception("Error in running the workflow")
        except:
            print traceback.format_exc()
            sys.exit(1)
        
            
    def logout(self):
        # finally logout
        f = self.opener.open(self.base_url+'/user/logout')
            
    def encode_id(self,  obj_id ):
        id_secret = 'changethisinproductiontoo'
        id_cipher = Blowfish.new( id_secret )
        # Convert to string
        s = str( obj_id )
        # Pad to a multiple of 8 with leading "!" 
        s = ( "!" * ( 8 - len(s) % 8 ) ) + s
        # Encrypt
        return id_cipher.encrypt( s ).encode( 'hex' )
