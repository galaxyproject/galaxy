#!/usr/bin/python
"""

Data Transfer Script: Sequencer to Galaxy

This script is called from Galaxy LIMS once the lab admin starts the data 
transfer process using the user interface.

Usage:

python data_transfer.py <sequencer_host> 
                        <username> 
                        <password> 
                        <source_file> 
                        <sample_id>
                        <dataset_index>
                        <library_id>
                        <folder_id>
"""
 
import ConfigParser
import sys, os, time, traceback
import optparse
import urllib,urllib2, cookielib, shutil
import logging
from galaxydb_interface import GalaxyDbInterface

assert sys.version_info[:2] >= ( 2, 4 )
new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy.util.json import from_json_string, to_json_string
from galaxy import eggs
import pkg_resources
pkg_resources.require( "pexpect" )
import pexpect

pkg_resources.require( "simplejson" )
import simplejson

curr_dir = os.getcwd()
logfile = os.path.join(curr_dir, 'data_transfer.log')
logging.basicConfig(filename=logfile, level=logging.DEBUG, 
        format="%(asctime)s [%(levelname)s] %(message)s")

class DataTransfer(object):
    
    def __init__(self, host, username, password, remote_file, sample_id, 
                 dataset_index, library_id, folder_id):
        self.host = host
        self.username = username
        self.password = password
        self.remote_file = remote_file
        self.sample_id = sample_id
        self.dataset_index = dataset_index
        self.library_id = library_id
        self.folder_id = folder_id
        try:
            # Retrieve the upload user login information from the config file
            config = ConfigParser.ConfigParser()
            config.read('universe_wsgi.ini')
            self.server_host = config.get("server:main", "host")
            self.server_port = config.get("server:main", "port")
            self.database_connection = config.get("app:main", "database_connection")
            self.import_dir = config.get("app:main", "library_import_dir")
            # create the destination directory within the import directory
            self.server_dir = os.path.join( self.import_dir, 'datatx_'+str(os.getpid()) )
            os.mkdir(self.server_dir)
            if not os.path.exists(self.server_dir):
                raise Exception
        except:
            logging.error(traceback.format_exc())
            logging.error('FATAL ERROR')
            if self.database_connection:
                self.update_status('Error')
            sys.exit(1)
     
    def start(self):
        '''
        This method executes the file transfer from the sequencer, adds the dataset
        to the data library & finally updates the data transfer status in the db
        '''
        # datatx
        self.transfer_file()
        # add the dataset to the given library 
        self.add_to_library()
        # update the data transfer status in the db
        self.update_status('Complete')
        # cleanup
        self.cleanup()    
        sys.exit(0)
        
    def cleanup(self):
        '''
        remove the directory created to store the dataset files temporarily
        before adding the same to the data library
        '''
        try:
            shutil.rmtree( self.server_dir )
        except:
            self.error_and_exit()

            
    def error_and_exit(self):
        '''
        This method is called any exception is raised. This prints the traceback 
        and terminates this script
        '''
        logging.error(traceback.format_exc())
        logging.error('FATAL ERROR')
        self.update_status('Error')
        sys.exit(1)
        
    def transfer_file(self):
        '''
        This method executes a scp process using pexpect library to transfer
        the dataset file from the remote sequencer to the Galaxy server
        '''
        def print_ticks(d):
            pass
        try:
            cmd = "scp %s@%s:%s %s" % ( self.username,
                                        self.host,
                                        self.remote_file,
                                        self.server_dir)
            logging.debug(cmd)
            output = pexpect.run(cmd, events={'.ssword:*': self.password+'\r\n', 
                                              pexpect.TIMEOUT:print_ticks}, 
                                              timeout=10)
            logging.debug(output)
            if not os.path.exists(os.path.join(self.server_dir, os.path.basename(self.remote_file))):
                raise Exception
        except:
            self.error_and_exit()

        
    def add_to_library(self):
        '''
        This method adds the dataset file to the target data library & folder
        by opening the corresponding url in Galaxy server running.  
        '''
        try:
            logging.debug('Adding %s to library...' % os.path.basename(self.remote_file))
            # Retrieve the upload user login information from the config file
            config = ConfigParser.ConfigParser()
            config.read('transfer_datasets.ini')
            email = config.get("data_transfer_user_login_info", "email")
            password = config.get("data_transfer_user_login_info", "password")
            # create url
            base_url =  "http://%s:%s" % (self.server_host, self.server_port)
            # login 
            url = "%s/user/login?email=%s&password=%s" % (base_url, email, password)
            cj = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
            f = opener.open(url)
            if f.read().find("Now logged in as "+email) == -1:
                # if the user doesnt exist, create the user
                url = "%s/user/create?email=%s&username=%s&password=%s&confirm=%s&create_user_button=Submit" % ( base_url, email, email, password, password )
                f = opener.open(url)
                if f.read().find("Now logged in as "+email) == -1:
                    raise Exception
            # after login, add dataset to the library
            params = urllib.urlencode(dict( cntrller='library_admin',
                                            tool_id='upload1',
                                            tool_state='None',
                                            library_id=self.library_id,
                                            folder_id=self.folder_id,
                                            upload_option='upload_directory',
                                            file_type='auto',
                                            server_dir=os.path.basename(self.server_dir),
                                            dbkey='',
                                            runtool_btn='Upload to library'))
            #url = "http://localhost:8080/library_common/upload_library_dataset?cntrller=library_admin&tool_id=upload1&tool_state=None&library_id=adb5f5c93f827949&folder_id=adb5f5c93f827949&upload_option=upload_directory&file_type=auto&server_dir=003&dbkey=%3F&message=&runtool_btn=Upload+to+library"
            #url = base_url+"/library_common/upload_library_dataset?library_id=adb5f5c93f827949&tool_id=upload1&file_type=auto&server_dir=datatx_22858&dbkey=%3F&upload_option=upload_directory&folder_id=529fd61ab1c6cc36&cntrller=library_admin&tool_state=None&runtool_btn=Upload+to+library"
            url = base_url+"/library_common/upload_library_dataset"
            logging.debug(url)
            logging.debug(params)
            f = opener.open(url, params)
            #print f.read()
        except:
            self.error_and_exit()

    def update_status(self, status):
        '''
        
        '''
        try:
            galaxy = GalaxyDbInterface(self.database_connection)
            df = from_json_string(galaxy.get_sample_dataset_files(self.sample_id))
            logging.debug(df)
            df[self.dataset_index][1] = status
        
            galaxy.set_sample_dataset_files(self.sample_id, to_json_string(df))
            logging.debug("######################\n"+str(from_json_string(galaxy.get_sample_dataset_files(self.sample_id))[self.dataset_index]))
        except:
            logging.error(traceback.format_exc())
            logging.error('FATAL ERROR')
            sys.exit(1)

if __name__ == '__main__':
    logging.info('STARTING %i %s' % (os.getpid(), str(sys.argv)))
    logging.info('daemonized %i' % os.getpid())
    #
    # Start the daemon
    #    
    dt = DataTransfer(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
                      int(sys.argv[5]), int(sys.argv[6]), sys.argv[7], sys.argv[8])
    dt.start()


