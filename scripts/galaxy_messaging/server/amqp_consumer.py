'''
Galaxy Messaging with AMQP (RabbitMQ)
Galaxy uses AMQ protocol to receive messages from external sources like 
bar code scanners. Galaxy has been tested against RabbitMQ AMQP implementation.
For Galaxy to receive messages from a message queue the RabbitMQ server has 
to be set up with a user account and other parameters listed in the [galaxy_amqp]
section in the universe_wsgi.ini config file
Once the RabbitMQ server has been setup and started with the given parameters,
this script can be run to receive messages and update the Galaxy database accordingly
'''

import ConfigParser
import sys, os
import optparse
import xml.dom.minidom
import subprocess
import urllib2

from xml_helper import get_value, get_value_index

from galaxydb_interface import GalaxyDbInterface

api_path = [ os.path.join( os.getcwd(), "scripts/api" ) ]
sys.path.extend( api_path )
import common as api

assert sys.version_info[:2] >= ( 2, 4 )
new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
from galaxy.web.api.requests import RequestsAPIController
import pkg_resources
pkg_resources.require( "amqplib" )
from amqplib import client_0_8 as amqp

import logging
log = logging.getLogger("GalaxyAMQP")
log.setLevel(logging.DEBUG)
fh = logging.FileHandler("galaxy_listener.log")
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
fh.setFormatter(formatter)
log.addHandler(fh)

# data transfer script
data_transfer_script = os.path.join( os.getcwd(), 
                                     "scripts/galaxy_messaging/server/data_transfer.py" )
global config
global config_file_name
global http_server_section


def start_data_transfer( message ):
    # fork a new process to transfer datasets
    cmd = '%s "%s" "%s" "%s"' % ( "python", 
                                  data_transfer_script, 
                                  message.body,
                                  config_file_name ) # Galaxy config file name
    pid = subprocess.Popen(cmd, shell=True).pid
    log.debug('Started process (%i): %s' % (pid, str(cmd)))
    
def update_sample_state( message ):
    dom = xml.dom.minidom.parseString(message.body)
    barcode = get_value(dom, 'barcode')
    state = get_value(dom, 'state')
    api_key = get_value(dom, 'api_key')
    log.debug('Barcode: ' + barcode)
    log.debug('State: ' + state)
    log.debug('API Key: ' + api_key)
    # validate 
    if not barcode or not state or not api_key:
        log.debug( 'Incomplete sample_state_update message received. Sample barcode, desired state and user API key is required.' )
        return
    # update the sample state in Galaxy db
    dbconnstr = config.get("app:main", "database_connection")
    galaxydb = GalaxyDbInterface( dbconnstr )
    sample_id = galaxydb.get_sample_id( field_name='bar_code', value=barcode )
    if sample_id == -1:
       log.debug( 'Invalid barcode.' ) 
       return
    galaxydb.change_state(sample_id, state)
    # after updating the sample state, update request status
    request_id = galaxydb.get_request_id(sample_id)
    update_request( api_key, request_id )
    
def update_request( api_key, request_id ):
    encoded_request_id = api.encode_id( config.get( "app:main", "id_secret" ), request_id )
    data = dict( update_type=RequestsAPIController.update_types.REQUEST )
    url = "http://%s:%s/api/requests/%s" % ( config.get(http_server_section, "host"),
                                             config.get(http_server_section, "port"),
                                             encoded_request_id )
    log.debug( 'Updating request %i' % request_id )
    try:
        retval = api.update( api_key, url, data, return_formatted=False )
        log.debug( str( retval ) )
    except Exception, e:
        log.debug( 'ERROR(update_request (%s)): %s' % ( str((self.api_key, url, data)), str(e) ) )

def recv_callback( message ):
    # check the meesage type.
    msg_type = message.properties['application_headers'].get('msg_type')
    log.debug( 'MESSAGE RECVD: ' + str( msg_type ) )
    if msg_type == 'data_transfer':
        log.debug( 'DATA TRANSFER' )
        start_data_transfer( message )
    elif msg_type == 'sample_state_update':
        log.debug( 'SAMPLE STATE UPDATE' )
        update_sample_state( message )

def main():
    parser = optparse.OptionParser()
    parser.add_option('-c', '--config-file', help='Galaxy configuration file', 
                      dest='config_file', action='store')
    parser.add_option('-s', '--http-server-section', help='Name of the HTTP server section in the Galaxy configuration file', 
                      dest='http_server_section', action='store')
    (opts, args) = parser.parse_args()
    log.debug( "GALAXY LISTENER PID: " + str(os.getpid()) + " - " + str( opts ) )
    # read the Galaxy config file
    global config_file_name
    config_file_name = opts.config_file
    global config
    config = ConfigParser.ConfigParser()
    config.read( opts.config_file )
    global http_server_section
    http_server_section = opts.http_server_section
    amqp_config = {}
    for option in config.options("galaxy_amqp"):
        amqp_config[option] = config.get("galaxy_amqp", option)
    log.debug( str( amqp_config ) )
    # connect 
    conn = amqp.Connection(host=amqp_config['host']+":"+amqp_config['port'], 
                           userid=amqp_config['userid'], 
                           password=amqp_config['password'], 
                           virtual_host=amqp_config['virtual_host'], 
                           insist=False)
    chan = conn.channel()
    chan.queue_declare( queue=amqp_config['queue'], 
                        durable=True, 
                        exclusive=True, 
                        auto_delete=False)
    chan.exchange_declare( exchange=amqp_config['exchange'], 
                           type="direct", 
                           durable=True, 
                           auto_delete=False,)    
    chan.queue_bind( queue=amqp_config['queue'], 
                     exchange=amqp_config['exchange'], 
                     routing_key=amqp_config['routing_key'])

    chan.basic_consume( queue=amqp_config['queue'], 
                        no_ack=True, 
                        callback=recv_callback, 
                        consumer_tag="testtag")
    log.debug('Connected to rabbitmq server - '+amqp_config['host']+":"+amqp_config['port'])
    while True:
        chan.wait()
    chan.basic_cancel("testtag")    
    chan.close()
    conn.close()

if __name__ == '__main__':
    main()


