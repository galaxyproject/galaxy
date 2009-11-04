import sys, os
import serial
import array
import time
import optparse
import ConfigParser, logging
from scanner_interface import ScannerInterface

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger( 'Scanner' )

# command prefix: SYN M CR
cmd = [22, 77, 13]
response = { 6: 'ACK', 5: 'ENQ', 21: 'NAK' }
image_scanner_report = 'RPTSCN.'
get_prefix1 = 'PREBK2?.'
get_prefix2 = ':4820:PREBK2?.'
set_prefix = 'PREBK2995859.'
clear_prefix = 'PRECA2.'

def get_prefix_cmd(name):
    return ':' + name + ':' + 'PREBK2?.'

def set_prefix_cmd(name, prefix):
    prefix_str = ''
    for c in prefix:
        prefix_str = prefix_str + hex(ord(c))[2:]
    return ':' + name + ':' + 'PREBK299' + prefix_str + '!'

def read_config_file(config_file):
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    count = 1
    scanners_list = []
    while True:
        section = 'scanner%i' % count
        if config.has_section(section):
            scanner = dict(name=config.get(section, 'name'),
                           prefix=config.get(section, 'prefix'),
                           state=config.get(section, 'state'))
            scanners_list.append(scanner)
            count = count + 1
        else:
            return scanners_list

def main():
    usage = "python %s -p PORT -c CONFIG_FILE [ OPTION ]" % sys.argv[0]
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-p', '--port', help='Name of the port where the scanner is connected', 
                      dest='port', action='store')
    parser.add_option('-c', '--config-file', help='config file with all the AMQP config parameters', 
                      dest='config_file', action='store')
    parser.add_option('-r', '--report', help='scanner report', 
                      dest='report', action='store_true', default=False)
    parser.add_option('-i', '--install', help='install the scanners', 
                      dest='install', action='store_true', default=False)
    (opts, args) = parser.parse_args()
    # validate 
    if not opts.port:
        parser.print_help()
        sys.exit(0)
    if ( opts.report or opts.install ) and not opts.config_file:
        parser.print_help()
        sys.exit(0)

    # create the scanner interface
    si = ScannerInterface(opts.port)
    if opts.install:
        scanners_list = read_config_file(opts.config_file)
        for scanner in scanners_list:
            msg = set_prefix_cmd(scanner['name'], scanner['prefix'])
            si.send(msg)
            response = si.recv()
            if not response:
                log.error("Scanner %s could not be installed." % scanner['name'])
    elif opts.report:
        si.send(image_scanner_report)
        rep = si.recv()
        log.info(rep)
        scanners_list = read_config_file(opts.config_file)
        for scanner in scanners_list:
            msg = get_prefix_cmd(scanner['name'])
            si.send(msg)
            response = si.recv()
            if response:
                log.info('PREFIX for scanner %s: %s' % (scanner['name'],  chr(int(response[8:12][:2], 16))+chr(int(response[8:12][2:], 16))   ))
    si.close()
    
    

if __name__ == "__main__":
    main()
