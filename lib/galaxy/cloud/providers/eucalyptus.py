import subprocess, threading, os, errno
from Queue import Queue, Empty
from datetime import datetime

from galaxy import model
from galaxy.datatypes.data import nice_size

from time import sleep

import galaxy.eggs
galaxy.eggs.require("boto")
from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo

import logging
log = logging.getLogger( __name__ )

class EucalyptusCloudProvider( object ):
    """
    Eucalyptus-based cloud provider implementation for managing instances. 
    """
    def __init__( self, app ):
        log.debug( "In eucalyptus cloud provider." )
    
    def shutdown( self ):
        """Attempts to gracefully shut down the monitor thread"""
        log.info( "sending stop signal to worker threads in eucalyptus cloud manager" )
        self.queue.put( self.STOP_SIGNAL )
        log.info( "eucalyptus cloud manager stopped" )