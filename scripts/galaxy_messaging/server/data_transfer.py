#!/usr/bin/env python
"""

Data Transfer Script: Sequencer to Galaxy

This script is called from Galaxy RabbitMQ listener ( amqp_consumer.py ) once 
the lab admin starts the data transfer process using the user interface.

Usage:

python data_transfer.py <config_file>


"""
import ConfigParser
import sys, os, time, traceback
import optparse
import urllib,urllib2, cookielib, shutil
import logging, time, datetime
import xml.dom.minidom

log = logging.getLogger( "datatx_" + str( os.getpid() ) )
log.setLevel( logging.DEBUG )
fh = logging.FileHandler( "data_transfer.log" )
fh.setLevel( logging.DEBUG )
formatter = logging.Formatter( "%(asctime)s - %(name)s - %(message)s" )
fh.setFormatter( formatter )
log.addHandler( fh )

api_path = [ os.path.join( os.getcwd(), "scripts/api" ) ]
sys.path.extend( api_path )
import common as api

assert sys.version_info[:2] >= ( 2, 4 )
new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy.util.json import from_json_string, to_json_string
from galaxy.model import SampleDataset
from galaxy.web.api.requests import RequestsController
from galaxy import eggs
import pkg_resources
pkg_resources.require( "pexpect" )
import pexpect

pkg_resources.require( "simplejson" )
import simplejson

class DataTransfer( object ):

    def __init__( self, msg, config_file ):
        log.info( msg )
        self.dom = xml.dom.minidom.parseString( msg ) 
        self.sequencer_host = self.get_value( self.dom, 'data_host' )
        self.sequencer_username = self.get_value( self.dom, 'data_user' )
        self.sequencer_password = self.get_value( self.dom, 'data_password' )
        self.request_id = self.get_value( self.dom, 'request_id' )
        self.sample_id = self.get_value( self.dom, 'sample_id' )
        self.library_id = self.get_value( self.dom, 'library_id' )
        self.folder_id = self.get_value( self.dom, 'folder_id' )
        self.dataset_files = []
        count=0
        while True:
            dataset_id = self.get_value_index( self.dom, 'dataset_id', count )
            file = self.get_value_index( self.dom, 'file', count )
            name = self.get_value_index( self.dom, 'name', count )
            if file:
                self.dataset_files.append( dict( name=name,
                                                 dataset_id=int( dataset_id ),
                                                 file=file ) ) 
            else:
                break
            count=count+1
        try:
            # Retrieve the upload user login information from the config file
            transfer_datasets_config = ConfigParser.ConfigParser( )
            transfer_datasets_config.read( 'transfer_datasets.ini' )
            self.data_transfer_user_email = transfer_datasets_config.get( "data_transfer_user_login_info", "email" )
            self.data_transfer_user_password = transfer_datasets_config.get( "data_transfer_user_login_info", "password" )
            self.api_key = transfer_datasets_config.get( "data_transfer_user_login_info", "api_key" )
            self.http_server_section = transfer_datasets_config.get( "universe_wsgi_config", "http_server_section" )
        except:
            log.error( traceback.format_exc() )
            log.error( 'ERROR reading config values from transfer_datasets.ini.' )
            sys.exit(1)
        # read config variables
        config = ConfigParser.ConfigParser()
        retval = config.read( config_file )
        if not retval:
            error_msg = 'FATAL ERROR: Unable to open config file %s.' % config_file
            log.error( error_msg )
            sys.exit(1)
        try:
            self.server_host = config.get( self.http_server_section, "host" )
        except ConfigParser.NoOptionError,e:
            self.server_host = '127.0.0.1'
        try:
            self.server_port = config.get( self.http_server_section, "port" )
        except ConfigParser.NoOptionError,e:
            self.server_port = '8080'
        try:
            self.config_id_secret = config.get( "app:main", "id_secret" )
        except ConfigParser.NoOptionError,e:
            self.config_id_secret = "USING THE DEFAULT IS NOT SECURE!"
        try:
            self.import_dir = config.get( "app:main", "library_import_dir" )
        except ConfigParser.NoOptionError,e:
            log.error( 'ERROR: library_import_dir config variable is not set in %s. ' % config_file )
            sys.exit( 1 )
        # create the destination directory within the import directory
        self.server_dir = os.path.join( self.import_dir, 
                                        'datatx_' + str( os.getpid() ) + '_' + datetime.date.today( ).strftime( "%d%b%Y" ) )
        try:
            os.mkdir( self.server_dir )
        except Exception, e:
            self.error_and_exit( str( e ) )
     
    def start( self ):
        '''
        This method executes the file transfer from the sequencer, adds the dataset
        to the data library & finally updates the data transfer status in the db
        '''
        # datatx
        self.transfer_files()
        # add the dataset to the given library
        self.add_to_library()
        # update the data transfer status in the db
        self.update_status( SampleDataset.transfer_status.COMPLETE )
        # cleanup
        #self.cleanup()    
        sys.exit( 0 )
        
    def cleanup( self ):
        '''
        remove the directory created to store the dataset files temporarily
        before adding the same to the data library
        '''
        try:
            time.sleep( 60 )
            shutil.rmtree( self.server_dir )
        except:
            self.error_and_exit()

            
    def error_and_exit( self, msg='' ):
        '''
        This method is called any exception is raised. This prints the traceback 
        and terminates this script
        '''
        log.error( traceback.format_exc() )
        log.error( 'FATAL ERROR.' + msg )
        self.update_status( 'Error', 'All', msg )
        sys.exit( 1 )
        
    def transfer_files( self ):
        '''
        This method executes a scp process using pexpect library to transfer
        the dataset file from the remote sequencer to the Galaxy server
        '''
        def print_ticks( d ):
            pass
        for i, dataset_file in enumerate( self.dataset_files ):
            self.update_status( SampleDataset.transfer_status.TRANSFERRING, dataset_file[ 'dataset_id' ] )
            try:
                cmd = "scp %s@%s:'%s' '%s/%s'" % (  self.sequencer_username,
                                                    self.sequencer_host,
                                                    dataset_file[ 'file' ].replace( ' ', '\ ' ),
                                                    self.server_dir.replace( ' ', '\ ' ),
                                                    dataset_file[ 'name' ].replace( ' ', '\ ' ) )
                log.debug( cmd )
                output = pexpect.run( cmd, 
                                      events={ '.ssword:*': self.sequencer_password+'\r\n', 
                                               pexpect.TIMEOUT: print_ticks }, 
                                      timeout=10 )
                log.debug( output )
                path = os.path.join( self.server_dir, os.path.basename( dataset_file[ 'name' ] ) )
                if not os.path.exists( path ):
                    msg = 'Could not find the local file after transfer ( %s ).' % path
                    log.error( msg )
                    raise Exception( msg )
            except Exception, e:
                msg = traceback.format_exc()
                self.update_status( 'Error', dataset_file['dataset_id'], msg)

        
    def add_to_library( self ):
        '''
        This method adds the dataset file to the target data library & folder
        by opening the corresponding url in Galaxy server running.  
        '''
        self.update_status( SampleDataset.transfer_status.ADD_TO_LIBRARY )
        try:
            data = {}
            data[ 'folder_id' ] = api.encode_id( self.config_id_secret, '%s.%s' % (  'folder', self.folder_id ) )
            data[ 'file_type' ] = 'auto'
            data[ 'server_dir' ] = self.server_dir
            data[ 'dbkey' ] = ''
            data[ 'upload_option' ] = 'upload_directory'
            data[ 'create_type' ] = 'file'
            url = "http://%s:%s/api/libraries/%s/contents" % ( self.server_host, 
                                                               self.server_port, 
                                                               api.encode_id(  self.config_id_secret, self.library_id ) )
            log.debug(  str( ( self.api_key, url, data ) ) )
            retval = api.submit( self.api_key, url, data, return_formatted=False )
            log.debug(  str( retval ) )
        except Exception, e:
            self.error_and_exit( str(  e ) )
            
    def update_status( self, status, dataset_id='All', msg='' ):
        '''
        Update the data transfer status for this dataset in the database
        '''
        try:
            log.debug( 'Setting status "%s" for dataset "%s" of sample "%s"' % (  status, str( dataset_id ), str( self.sample_id) ) )
            sample_dataset_ids = []
            if dataset_id == 'All':
                for dataset in self.dataset_files:
                    sample_dataset_ids.append( api.encode_id( self.config_id_secret, dataset[ 'dataset_id' ] ) )
            else:
                sample_dataset_ids.append( api.encode_id( self.config_id_secret, dataset_id ) )
            # update the transfer status
            data = {}
            data[ 'update_type' ] = RequestsController.update_types.SAMPLE_DATASET
            data[ 'sample_dataset_ids' ] = sample_dataset_ids
            data[ 'new_status' ] = status
            data[ 'error_msg' ] = msg
            url = "http://%s:%s/api/requests/%s" % (  self.server_host,
                                                     self.server_port,
                                                     api.encode_id(  self.config_id_secret, self.request_id ) )
            log.debug( str( ( self.api_key, url, data)))
            retval = api.update( self.api_key, url, data, return_formatted=False )
            log.debug( str( retval ) )
        except urllib2.URLError, e:
            log.debug( 'ERROR( sample_dataset_transfer_status ( %s ) ): %s' % ( url, str( e ) ) )
            log.error( traceback.format_exc() )
        except:
            log.error( traceback.format_exc() )
            log.error( 'FATAL ERROR' )
            sys.exit( 1 )
            
    def get_value( self, dom, tag_name ):
        '''
        This method extracts the tag value from the xml message
        '''
        nodelist = dom.getElementsByTagName( tag_name )[ 0 ].childNodes
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc
    
    def get_value_index( self, dom, tag_name, dataset_id ):
        '''
        This method extracts the tag value from the xml message
        '''
        try:
            nodelist = dom.getElementsByTagName( tag_name )[ dataset_id ].childNodes
        except:
            return None
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc

if __name__ == '__main__':
    log.info( 'STARTING %i %s' % ( os.getpid(), str( sys.argv ) ) )
    #
    # Start the daemon
    #
    dt = DataTransfer( sys.argv[1], sys.argv[2])
    dt.start()
    sys.exit( 0 )

