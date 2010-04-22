#!/usr/bin/env python
"""

Data Transfer Script: Sequencer to Galaxy

This script is called from Galaxy LIMS once the lab admin starts the data 
transfer process using the user interface.

Usage:

python data_transfer.py <data_transfer_xml> <config_id_secret>


"""
import ConfigParser
import sys, os, time, traceback
import optparse
import urllib,urllib2, cookielib, shutil
import logging, time
import xml.dom.minidom

sp = sys.path[0]

from galaxydb_interface import GalaxyDbInterface

assert sys.version_info[:2] >= ( 2, 4 )
new_path = [ sp ]
new_path.extend( sys.path ) 
sys.path = new_path

from galaxyweb_interface import GalaxyWebInterface

assert sys.version_info[:2] >= ( 2, 4 )
new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path


from galaxy.util.json import from_json_string, to_json_string
from galaxy.model import Sample
from galaxy import eggs
import pkg_resources
pkg_resources.require( "pexpect" )
import pexpect

pkg_resources.require( "simplejson" )
import simplejson

log = logging.getLogger("datatx_"+str(os.getpid()))
log.setLevel(logging.DEBUG)
fh = logging.FileHandler("data_transfer.log")
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
fh.setFormatter(formatter)
log.addHandler(fh)


class DataTransfer(object):
    
    def __init__(self, msg, config_id_secret):
        log.info(msg)
        self.dom = xml.dom.minidom.parseString(msg)
        self.host = self.get_value(self.dom, 'data_host')
        self.username = self.get_value(self.dom, 'data_user')
        self.password = self.get_value(self.dom, 'data_password')
        self.sample_id = self.get_value(self.dom, 'sample_id')
        self.library_id = self.get_value(self.dom, 'library_id')
        self.folder_id = self.get_value(self.dom, 'folder_id')
        self.dataset_files = []
        self.config_id_secret = config_id_secret
        count=0
        while True:
           index = self.get_value_index(self.dom, 'index', count)
           file = self.get_value_index(self.dom, 'file', count)
           name = self.get_value_index(self.dom, 'name', count)
           if file:
               self.dataset_files.append(dict(name=name,
                                              index=int(index),
                                              file=file)) 
           else:
               break
           count=count+1
        try:
            # Retrieve the upload user login information from the config file
            config = ConfigParser.ConfigParser()
            config.read('transfer_datasets.ini')
            self.datatx_email = config.get("data_transfer_user_login_info", "email")
            self.datatx_password = config.get("data_transfer_user_login_info", "password")
            self.server_host = config.get("universe_wsgi_config", "host")
            self.server_port = config.get("universe_wsgi_config", "port")
            self.database_connection = config.get("universe_wsgi_config", "database_connection")
            self.import_dir = config.get("universe_wsgi_config", "library_import_dir")
            # create the destination directory within the import directory
            self.server_dir = os.path.join( self.import_dir, 'datatx_'+str(os.getpid()) )
            os.mkdir(self.server_dir)
            if not os.path.exists(self.server_dir):
                raise Exception
            # connect to db
            self.galaxydb = GalaxyDbInterface(self.database_connection)
        except:
            log.error(traceback.format_exc())
            log.error('FATAL ERROR')
            if self.database_connection:
                self.error_and_exit('Error')
            sys.exit(1)
     
    def start(self):
        '''
        This method executes the file transfer from the sequencer, adds the dataset
        to the data library & finally updates the data transfer status in the db
        '''
        # datatx
        self.transfer_files()
        # add the dataset to the given library
        self.add_to_library()
        # update the data transfer status in the db
        self.update_status(Sample.transfer_status.COMPLETE)
        # cleanup
        #self.cleanup()    
        sys.exit(0)
        
    def cleanup(self):
        '''
        remove the directory created to store the dataset files temporarily
        before adding the same to the data library
        '''
        try:
            time.sleep(60)
            shutil.rmtree( self.server_dir )
        except:
            self.error_and_exit()

            
    def error_and_exit(self, msg=''):
        '''
        This method is called any exception is raised. This prints the traceback 
        and terminates this script
        '''
        log.error(traceback.format_exc())
        log.error('FATAL ERROR.'+msg)
        self.update_status('Error', 'All', msg+"\n"+traceback.format_exc())
        sys.exit(1)
        
    def transfer_files(self):
        '''
        This method executes a scp process using pexpect library to transfer
        the dataset file from the remote sequencer to the Galaxy server
        '''
        def print_ticks(d):
            pass
        for i, df in enumerate(self.dataset_files):
            self.update_status(Sample.transfer_status.TRANSFERRING, df['index'])
            try:
                cmd = "scp %s@%s:%s %s/%s" % ( self.username,
                                            self.host,
                                            df['file'],
                                            self.server_dir,
                                            df['name'])
                log.debug(cmd)
                output = pexpect.run(cmd, events={'.ssword:*': self.password+'\r\n', 
                                                  pexpect.TIMEOUT:print_ticks}, 
                                                  timeout=10)
                log.debug(output)
                path = os.path.join(self.server_dir, os.path.basename(df['name']))
                if not os.path.exists(path):
                    msg = 'Could not find the local file after transfer (%s)' % path
                    log.error(msg)
                    raise Exception(msg)
            except Exception, e:
                msg = traceback.format_exc()
                self.update_status('Error', df['index'], msg)

        
    def add_to_library(self):
        '''
        This method adds the dataset file to the target data library & folder
        by opening the corresponding url in Galaxy server running.  
        '''
        try:
            self.update_status(Sample.transfer_status.ADD_TO_LIBRARY)
            log.debug("dir:%s, lib:%s, folder:%s" % (self.server_dir, str(self.library_id), str(self.folder_id)))
            galaxyweb = GalaxyWebInterface(self.server_host, self.server_port, 
                                           self.datatx_email, self.datatx_password,
                                           self.config_id_secret)
            galaxyweb.add_to_library(self.server_dir, self.library_id, self.folder_id)
            galaxyweb.logout()
        except Exception, e:
            log.debug(e)
            self.error_and_exit(str(e))
            
    def update_status(self, status, dataset_index='All', msg=''):
        '''
        Update the data transfer status for this dataset in the database
        '''
        try:
            log.debug('Setting status "%s" for dataset "%s"' % ( status, str(dataset_index) ) )
            df = from_json_string(self.galaxydb.get_sample_dataset_files(self.sample_id))
            if dataset_index == 'All':
                for dataset in self.dataset_files:
                    df[dataset['index']]['status'] = status
                    if status == 'Error':
                        df[dataset['index']]['error_msg'] = msg
                    else:
                        df[dataset['index']]['error_msg'] = ''
                        
            else:
                df[dataset_index]['status'] = status
                if status == 'Error':
                    df[dataset_index]['error_msg'] = msg
                else:
                    df[dataset_index]['error_msg'] = ''

            self.galaxydb.set_sample_dataset_files(self.sample_id, to_json_string(df))
            log.debug('done.')
        except:
            log.error(traceback.format_exc())
            log.error('FATAL ERROR')
            sys.exit(1)
            
    def get_value(self, dom, tag_name):
        '''
        This method extracts the tag value from the xml message
        '''
        nodelist = dom.getElementsByTagName(tag_name)[0].childNodes
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc
    
    def get_value_index(self, dom, tag_name, index):
        '''
        This method extracts the tag value from the xml message
        '''
        try:
            nodelist = dom.getElementsByTagName(tag_name)[index].childNodes
        except:
            return None
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc

if __name__ == '__main__':
    log.info('STARTING %i %s' % (os.getpid(), str(sys.argv)))
    #
    # Start the daemon
    #
    dt = DataTransfer(sys.argv[1], sys.argv[2])
    dt.start()
    sys.exit(0)

