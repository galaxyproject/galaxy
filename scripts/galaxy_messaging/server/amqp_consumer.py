'''
Galaxy Messaging with AMQP (RabbitMQ)
Galaxy uses AMQ protocol to receive messages from external sources like 
bar code scanners. Galaxy has been tested against RabbitMQ AMQP implementation.
For Galaxy to receive messages from a message queue the RabbitMQ server has 
to be set up with a user account and other parameters listed in the [galaxy:amq]
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
from galaxydb_interface import GalaxyDbInterface

api_path = [ os.path.join( os.getcwd(), "scripts/api" ) ]
sys.path.extend( api_path )
import common as api

assert sys.version_info[:2] >= ( 2, 4 )
new_path = [ os.path.join( os.getcwd(), "lib" ) ]
new_path.extend( sys.path[1:] ) # remove scripts/ from the path
sys.path = new_path

from galaxy import eggs
from galaxy.web.api.requests import RequestsController
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

global dbconnstr
global webconfig
global config

def get_value(dom, tag_name):
    '''
    This method extracts the tag value from the xml message
    '''
    nodelist = dom.getElementsByTagName(tag_name)[0].childNodes
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc

def get_value_index(dom, tag_name, index):
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

def start_data_transfer(message):
    # fork a new process to transfer datasets
    cmd = '%s "%s" "%s" "%s"' % ( "python", 
                                  data_transfer_script, 
                                  message.body,
                                  sys.argv[1] ) # Galaxy config file name
    pid = subprocess.Popen(cmd, shell=True).pid
    log.debug('Started process (%i): %s' % (pid, str(cmd)))
    
def update_sample_state(message):
    dom = xml.dom.minidom.parseString(message.body)
    barcode = get_value(dom, 'barcode')
    state = get_value(dom, 'state')
    log.debug('Barcode: ' + barcode)
    log.debug('State: ' + state)
    # update the sample state in Galaxy db
    galaxydb = GalaxyDbInterface(dbconnstr)
    sample_id = galaxydb.get_sample_id(field_name='bar_code', value=barcode)
    if sample_id == -1:
       log.debug('Invalid barcode.') 
       return
    galaxydb.change_state(sample_id, state)
    # after updating the sample state, update request status
    request_id = galaxydb.get_request_id(sample_id)
    update_request( request_id )
    
def update_request( request_id ):
    http_server_section = webconfig.get( "universe_wsgi_config", "http_server_section" )
    encoded_request_id = api.encode_id( config.get( "app:main", "id_secret" ), request_id )
    api_key = webconfig.get( "data_transfer_user_login_info", "api_key" )
    data = dict( update_type=RequestsController.update_types.REQUEST )
    url = "http://%s:%s/api/requests/%s" % ( config.get(http_server_section, "host"),
                                             config.get(http_server_section, "port"),
                                             encoded_request_id )
    log.debug( 'Updating request %i' % request_id )
    try:
        api.update( api_key, url, data, return_formatted=False )
    except urllib2.URLError, e:
        log.debug( 'ERROR(update_request (%s)): %s' % ( str((self.api_key, url, data)), str(e) ) )

def recv_callback(message):
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
    if len(sys.argv) < 2:
        print 'Usage: python amqp_consumer.py <Galaxy configuration file>'
        return
    global config
    config = ConfigParser.ConfigParser()
    config.read( sys.argv[1] )
    global dbconnstr
    dbconnstr = config.get("app:main", "database_connection")
    amqp_config = {}
    for option in config.options("galaxy_amqp"):
        amqp_config[option] = config.get("galaxy_amqp", option)
    log.debug("PID: " + str(os.getpid()) + ", " + str(amqp_config))
    # web server config
    global webconfig
    webconfig = ConfigParser.ConfigParser()
    webconfig.read('transfer_datasets.ini')
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


