import subprocess, threading, os, errno, time, datetime
from Queue import Queue, Empty
from datetime import datetime

from galaxy import model # Database interaction class
from galaxy.datatypes.data import nice_size

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
    STOP_SIGNAL = object()
    def __init__( self, app ):
        log.debug( "Using eucalyptus as default cloud provider." )
        self.zone = "epc"
        self.key_pair = "galaxy-keypair"
        
        #TODO: Use multiple threads to process requests?
        
    
    def get_connection( self, uci ):
        """
        Establishes EC2 connection using user's default credentials
        """
        log.debug( '##### Establishing cloud connection' )
#        creds = model.CloudUserCredentials.filter_by( user=user, defaultCred=True ).first()
        a_key = uci.credentials.access_key
        s_key = uci.credentials.secret_key
        # Amazon EC2
        #conn = EC2Connection( a_key, s_key )
        # Eucalyptus Public Cloud
        # TODO: Add option in Galaxy config file to specify these values (i.e., for locally manages Eucalyptus deployments)
        euca_region = RegionInfo( None, "eucalyptus", "mayhem9.cs.ucsb.edu" )
        conn = EC2Connection( aws_access_key_id=a_key, aws_secret_access_key=s_key, is_secure=False, port=8773, region=euca_region, path="/services/Eucalyptus" )
        return conn
        
    def get_keypair_name( self, uci, conn ):
        """
        Generate keypair using user's default credentials
        """
        log.debug( "Getting user's keypair" )
        kp = conn.get_key_pair( self.key_pair )
        
        try:
            for i, inst in enumerate( uci.instance ):
                uci.instance[i].keypair_name = kp.name
            return kp.name
        except AttributeError: # No keypair under this name exists so create it
            log.debug( "No keypair found, creating keypair '%s'" % self.key_pair )
            kp = conn.create_key_pair( self.key_pair )
            for i, inst in enumerate( uci.instance ):
                uci.instance[i].keypair_name = kp.name
                uci.instance[i].keypair_material = kp.material
                uci.flush()
            # TODO: Store key_pair.material into instance table - this is the only time private key can be retrieved
            #    Actually, probably return key_pair to calling method and store name & key from there...
            
        return kp.name
    
    def get_mi( self, type='small' ):
        """
        Get appropriate machine image (mi) based on instance size.
        TODO: Dummy method - need to implement logic
            For valid sizes, see http://aws.amazon.com/ec2/instance-types/
        """
        return model.CloudImage.filter( model.CloudImage.table.c.id==1 ).first() 
    
#    def get_instances( self, uci ):
#        """
#        Get objects of instances that are pending or running and are connected to uci object
#        """
#        instances = trans.sa_session.query( model.CloudInstance ) \
#            .filter_by( user=user, uci_id=uci.id ) \
#            .filter( or_(model.CloudInstance.table.c.state=="running", model.CloudInstance.table.c.state=="pending" ) ) \
#            .first()
#            #.all() #TODO: return all but need to edit calling method(s) to handle list
#        
#        instances = uci.instance
#            
#        return instances

        
    def shutdown( self ):
        """Attempts to gracefully shut down the monitor thread"""
        log.info( "sending stop signal to worker threads in eucalyptus cloud manager" )
        self.queue.put( self.STOP_SIGNAL )
        log.info( "eucalyptus cloud manager stopped" )
        
    def createUCI( self, uci ):
        """ 
        Creates User Configured Instance (UCI). Essentially, creates storage volume on cloud provider
        and registers relevant information in Galaxy database.
        """
        conn = self.get_connection( uci )
        # Temporary code - need to ensure user selects zone at UCI creation time!
        if uci.store[0].availability_zone=='':
            log.info( "Availability zone for storage volume was not selected, using default zone: %s" % self.zone )
            uci.store[0].availability_zone = self.zone
            uci.store[0].flush()
        
        #TODO: check if volume associated with UCI already exists (if server crashed for example) and don't recreate it
        log.debug( "Creating volume in zone '%s'..." % uci.store[0].availability_zone )
        vol = conn.create_volume( uci.store[0].size, uci.store[0].availability_zone, snapshot=None )
        uci.store[0].volume_id = vol.id
        
        # Wait for a while to ensure volume was created
#        vol_status = vol.status
#        for i in range( 30 ):
#            if vol_status is not "u'available'":
#                log.debug( 'Updating volume status; current status: %s' % vol_status )
#                vol_status = vol.status
#                time.sleep(3)
#            if i is 29:
#                log.debug( "Error while creating volume '%s'; stuck in state '%s'; deleting volume." % ( vol.id, vol_status ) )
#                conn.delete_volume( vol.id )
#                uci.state = 'error'
#                uci.flush()
#                return
        
        uci.state = 'available'
        uci.store[0].status = vol.status
        uci.store[0].flush()
        uci.flush()

    def deleteUCI( self, name ):
        """ 
        Deletes UCI. NOTE that this implies deletion of any and all data associated
        with this UCI from the cloud. All data will be deleted.
        """
    
    def addStorageToUCI( self, name ):
        """ Adds more storage to specified UCI """
        
    def startUCI( self, uci ):
        """
        Starts an instance of named UCI on the cloud. This implies, mounting of
        storage and starting Galaxy instance. 
        """ 
        conn = self.get_connection( uci )
        
        uci.instance[0].keypair_name = self.get_keypair_name( uci, conn )
        mi = self.get_mi( uci.instance[0].type )
        
#        log.debug( "mi: %s, mi.image_id: %s, uci.instance[0].keypair_name: %s" % ( mi, mi.image_id, uci.instance[0].keypair_name ) )
        uci.instance[0].image = mi
        
#            log.debug( '***** Setting up security group' )
            # If not existent, setup galaxy security group
#            try:
#                gSecurityGroup = conn.create_security_group('galaxy', 'Security group for Galaxy.')
#                gSecurityGroup.authorize( 'tcp', 80, 80, '0.0.0.0/0' ) # Open HTTP port
#                gSecurityGroup.authorize( 'tcp', 22, 22, '0.0.0.0/0' ) # Open SSH port
#            except:
#                pass
#                sgs = conn.get_all_security_groups()
#                for i in range( len( sgs ) ):
#                    if sgs[i].name == "galaxy":
#                        sg.append( sgs[i] )
#                        break # only 1 security group w/ this name can exist, so continue                    
            
        log.debug( "***** Starting UCI instance '%s'" % uci.name )
#        log.debug( 'Using following command: conn.run_instances( image_id=%s, key_name=%s )' % ( uci.instance[0].image.image_id, uci.instance[0].keypair_name ) )
        reservation = conn.run_instances( image_id=uci.instance[0].image.image_id, key_name=uci.instance[0].keypair_name )
        #reservation = conn.run_instances( image_id=instance.image, key_name=instance.keypair_name, security_groups=['galaxy'], instance_type=instance.type,  placement=instance.availability_zone )
        uci.instance[0].launch_time = datetime.utcnow()
        uci.launch_time = uci.instance[0].launch_time
        uci.instance[0].reservation_id = str( reservation ).split(":")[1]
        uci.instance[0].instance_id = str( reservation.instances[0]).split(":")[1]
        s = reservation.instances[0].state
        uci.instance[0].state = s
        uci.state = s
        uci.instance[0].flush()
        uci.flush()
        
        # Wait until instance gets running and then update the DB
        while s!="running":
            log.debug( "Waiting on instance '%s' to start up (reservation ID: %s); current state: %s" % ( uci.instance[0].instance_id, uci.instance[0].reservation_id, s ) )
            time.sleep( 15 )
            s = reservation.instances[0].update()
            
        uci.instance[0].state = s
        uci.state = s
        uci.instance[0].public_dns = reservation.instances[0].dns_name
        uci.instance[0].private_dns = reservation.instances[0].private_dns_name
        uci.instance[0].flush()
        uci.flush()
        
        
    def stopUCI( self, uci ):
        """ 
        Stops all of cloud instances associated with named UCI. 
        """
        conn = self.get_connection( uci )
        tl = [] # temination list
        
        for i, inst in enumerate( uci.instance ):
            tl.append( uci.instance[i].instance_id )
        
        instList = conn.get_all_instances( tl )
#        log.debug( 'instList: %s' % instList )
        
        for i, inst in enumerate( instList ):
#            log.debug( 'inst: %s' % inst )
            log.debug( 'Before stop - inst.instances[0].update(): %s' % inst.instances[0].update() )
            inst.instances[0].stop()
            log.debug( 'After stop - inst.instances[0].update(): %s' % inst.instances[0].update() )
            uci.instance[i].stop_time = datetime.utcnow()
                
        terminated=0
        while terminated!=len( instList ):
            for i, inst in enumerate( instList ):
                log.debug( "inst state: %s" % inst.instances[0].state )
                state = inst.instances[0].update()
                if state=='terminated':
                    uci.instance[i].state = state
                    uci.instance[i].flush()
                    terminated += 1
                time.sleep ( 5 )
                   
        uci.state = 'available'
        uci.launch_time = None
        uci.flush()
        
        log.debug( "All instances for UCI '%s' were terminated." % uci.name )



#        dbInstances = get_instances( trans, uci ) #TODO: handle list!
#        
#        # Get actual cloud instance object
#        cloudInstance = get_cloud_instance( conn, dbInstances.instance_id )
#        
#        # TODO: Detach persistent storage volume(s) from instance and update volume data in local database
#        stores = get_stores( trans, uci )
#        for i, store in enumerate( stores ):
#            log.debug( "Detaching volume '%s' to instance '%s'." % ( store.volume_id, dbInstances.instance_id ) )
#            mntDevice = store.device
#            volStat = None
##            Detaching volume does not work with Eucalyptus Public Cloud, so comment it out
##            try:
##                volStat = conn.detach_volume( store.volume_id, dbInstances.instance_id, mntDevice )
##            except:
##                log.debug ( 'Error detaching volume; still going to try and stop instance %s.' % dbInstances.instance_id )
#            store.attach_time = None
#            store.device = None
#            store.i_id = None
#            store.status = volStat
#            log.debug ( '***** volume status: %s' % volStat )
#   
#        
#        # Stop the instance and update status in local database
#        cloudInstance.stop()
#        dbInstances.stop_time = datetime.utcnow()
#        while cloudInstance.state != 'terminated':
#            log.debug( "Stopping instance %s state; current state: %s" % ( str( cloudInstance ).split(":")[1], cloudInstance.state ) )
#            time.sleep(3)
#            cloudInstance.update()
#        dbInstances.state = cloudInstance.state
#        
#        # Reset relevant UCI fields
#        uci.state = 'available'
#        uci.launch_time = None
#          
#        # Persist
#        session = trans.sa_session
##        session.save_or_update( stores )
#        session.save_or_update( dbInstances ) # TODO: Is this going to work w/ multiple instances stored in dbInstances variable?
#        session.save_or_update( uci )
#        session.flush()
#        trans.log_event( "User stopped cloud instance '%s'" % uci.name )
#        trans.set_message( "Galaxy instance '%s' stopped." % uci.name )
                    