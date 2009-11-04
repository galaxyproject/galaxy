import sys, os
import serial
import array
import time
import optparse
import ConfigParser
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger( 'ScannerInterface' )

class ScannerInterface( object ):
    cmdprefix = [22, 77, 13]
    response = { 6: 'ACK', 5: 'ENQ', 21: 'NAK' }
    
    def __init__( self, port ):
        if os.name in ['posix', 'mac']:
            self.port = port
        elif os.name == 'nt':
            self.port = int(port)
        if self.port:
            self.open()
            
    def open(self):
        try:
            self.serial_conn = serial.Serial(self.port)
        except serial.SerialException:
            log.exception('Unable to open port: %s' % str(self.port))
            sys.exit(1)
        log.debug('Port %s is open: %s' %( str(self.port), self.serial_conn.isOpen() ) )
        
    def is_open(self):
        return self.serial_conn.isOpen()
        
    def close(self):
        self.serial_conn.close()
        log.debug('Port %s is open: %s' %( str(self.port), self.serial_conn.isOpen() ) )
        
    def send(self, msg):
        message = self.cmdprefix + map(ord, msg)
        byte_array = array.array('B', message)
        log.debug('Sending message to %s: %s' % ( str(self.port), message) )
        bytes = self.serial_conn.write( byte_array.tostring() )
        log.debug('%i bytes out of %i bytes sent to the scanner' % ( bytes, len(message) ) )
        
    def recv(self):
        time.sleep(1)
        self.serial_conn.flush()
        nbytes = self.serial_conn.inWaiting()
        log.debug('%i bytes received' % nbytes)
        if nbytes:
            msg = self.serial_conn.read(nbytes)
            byte_array = map(ord, msg)
            log.debug('Message received [%s]: %s' % (self.response.get(byte_array[len(byte_array)-2], byte_array[len(byte_array)-2]),
                                                     msg))
            return msg
        else:
            log.error('Error!')
            return None
            
    def setup_recv(self, callback):
        self.recv_callback = callback
        
    def wait(self):
        nbytes = self.serial_conn.inWaiting()
        if nbytes:
            msg = self.serial_conn.read(nbytes)
            byte_array = map(ord, msg)
            log.debug('Message received [%s]: %s' % (self.response.get(byte_array[len(byte_array)-2], byte_array[len(byte_array)-2],
                                                     msg)))
            if self.recv_callback:
                self.recv_callback(msg)
            return
    
    
    