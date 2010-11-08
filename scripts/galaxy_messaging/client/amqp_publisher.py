'''
This script gets barcode data from a barcode scanner using serial communication 
and sends the state representated by the barcode scanner & the barcode string
to the Galaxy LIMS RabbitMQ server. The message is sent in XML which has 2 tags, 
barcode & state. The state of the scanner should be set in the galaxy_amq.ini
file as a configuration variable. 
'''

from amqplib import client_0_8 as amqp
import ConfigParser
import sys, os
import serial
import array
import time
import optparse


xml = \
''' <sample>
        <barcode>%(BARCODE)s</barcode>
        <state>%(STATE)s</state>
        <api_key>%(API_KEY)s</api_key>
    </sample>'''


def handle_scan(states, amqp_config, barcode):
    if states.get(barcode[:2], None):
        values = dict( BARCODE=barcode[2:],
                       STATE=states.get(barcode[:2]),
                       API_KEY=amqp_config['api_key'] )
        print values
        data = xml % values
        print data
        conn = amqp.Connection(host=amqp_config['host']+":"+amqp_config['port'], 
                               userid=amqp_config['userid'], 
                               password=amqp_config['password'], 
                               virtual_host=amqp_config['virtual_host'], 
                               insist=False)    
        chan = conn.channel()
        msg = amqp.Message(data, 
                           content_type='text/plain', 
                           application_headers={'msg_type': 'sample_state_update'})
        msg.properties["delivery_mode"] = 2
        chan.basic_publish(msg,
                           exchange=amqp_config['exchange'],
                           routing_key=amqp_config['routing_key'])
        chan.close()
        conn.close()

def recv_data(states, amqp_config, s):
    while True:
        bytes = s.inWaiting()
        if bytes:
            print '%i bytes recvd' % bytes
            msg = s.read(bytes)
            print msg
            handle_scan(states, amqp_config, msg.strip())
            
        
def main():
    parser = optparse.OptionParser()
    parser.add_option('-c', '--config-file', help='config file with all the AMQP config parameters', 
                      dest='config_file', action='store')
    parser.add_option('-p', '--port', help='Name of the port where the scanner is connected', 
                      dest='port', action='store')
    (opts, args) = parser.parse_args()
    config = ConfigParser.ConfigParser()
    config.read(opts.config_file)
    amqp_config = {}
    states = {}
    for option in config.options("galaxy:amqp"):
        amqp_config[option] = config.get("galaxy:amqp", option)
    # abort if api_key is not set in the config file
    if not amqp_config['api_key']:
        print 'Error: Set the api_key config variable in the config file before starting the amqp_publisher script.'
        sys.exit( 1 )
    count = 1
    while True:
        section = 'scanner%i' % count
        if config.has_section(section):
            states[config.get(section, 'prefix')] = config.get(section, 'state')
            count = count + 1
        else:
            break    
    print amqp_config
    print states
    s = serial.Serial(int(opts.port))
    print 'Port %s is open: %s' %( opts.port, s.isOpen())
    recv_data(states, amqp_config, s)
    s.close()
    print 'Port %s is open: %s' %( opts.port, s.isOpen())

    
if __name__ == '__main__':
    main()
