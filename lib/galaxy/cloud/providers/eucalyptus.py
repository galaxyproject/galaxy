import subprocess, threading, os, errno
from Queue import Queue, Empty
from datetime import datetime

from galaxy import model # Database interaction class
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
    def __init__( self, app, user ):
        log.debug( "Using eucalyptus as default cloud provider." )
        self.conn = get_connection( user )
        
    
    def get_connection( user ):
        """
        Establishes EC2 connection using user's default credentials
        """
        log.debug( '##### Establishing cloud connection' )
        creds = model.CloudUserCredentials.filter_by( user=user, defaultCred=True ).first()
        if creds:
            a_key = creds.access_key
            s_key = creds.secret_key
            # Amazon EC2
            #conn = EC2Connection( a_key, s_key )
            # Eucalyptus Public Cloud
            # TODO: Add option in Galaxy config file to specify these values (i.e., for locally manages Eucalyptus deployments)
            euca_region = RegionInfo( None, "eucalyptus", "mayhem9.cs.ucsb.edu" )
            conn = EC2Connection( aws_access_key_id=a_key, aws_secret_access_key=s_key, is_secure=False, port=8773, region=euca_region, path="/services/Eucalyptus" )
            return conn
        else:
            log.debug( "User did not specify default credentials." )
            return 0

    
    def shutdown( self ):
        """Attempts to gracefully shut down the monitor thread"""
        log.info( "sending stop signal to worker threads in eucalyptus cloud manager" )
        self.queue.put( self.STOP_SIGNAL )
        log.info( "eucalyptus cloud manager stopped" )
        
    def createUCI( self, user, name, storage_size, zone=None):
        """ 
        Creates User Configured Instance (UCI). Essentially, creates storage volume on cloud provider
        and registers relevant information in Galaxy database.
        """
        conn = getConnection( user )
        # Capture user configured instance information
        uci = model.UCI()
        uci.name = name
        uci.user = user
        uci.state = "available" # Valid states include: "available", "running" or "pending"
        uci.total_size = storage_size # This is OK now because a new instance is being created. 
        # Capture store related information
        storage = model.CloudStore()
        storage.user = user
        storage.uci = uci
        storage.size = storage_size
        storage.availability_zone = "us-east-1a" # TODO: Give user choice here. Also, enable region selection.
        #self.conn.create_volume( storage_size, storage.availability_zone, snapshot=None )
        # TODO: get correct value from Eucalyptus
        storage.volume_id = "made up"
        # Persist
        uci.flush()
        storage.flush()
        session.flush()
        
    def deleteUCI( self, name ):
        """ 
        Deletes UCI. NOTE that this implies deletion of any and all data associated
        with this UCI from the cloud. All data will be deleted.
        """
    
    def addStorageToUCI( self, name ):
        """ Adds more storage to specified UCI """
        
    def startUCI( self, name, type ):
        """
        Starts an instance of named UCI on the cloud. This implies, mounting of
        storage and starting Galaxy instance. 
        """ 
        
    def stopUCI( self, name ):
        """ 
        Stops cloud instance associated with named UCI. This also implies 
        stopping of Galaxy and unmounting of the file system.
        """