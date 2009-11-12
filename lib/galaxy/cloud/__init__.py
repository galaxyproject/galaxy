import logging, threading, sys, os, time, subprocess, string, tempfile, re, traceback, shutil

from galaxy import util, model, config
from galaxy.model import mapping
from galaxy.model.orm import lazyload
from galaxy.datatypes.tabular import *
from galaxy.datatypes.interval import *
from galaxy.datatypes import metadata
from galaxy.util.bunch import Bunch
from sqlalchemy import or_

import pkg_resources
pkg_resources.require( "PasteDeploy" )

from paste.deploy.converters import asbool

from Queue import Queue, Empty

log = logging.getLogger( __name__ )

uci_states = Bunch(
    NEW_UCI = "newUCI",
    NEW = "new",
    DELETING_UCI = "deletingUCI",
    DELETING = "deleting",
    DELETED = "deleted",
    SUBMITTED_UCI = "submittedUCI",
    SUBMITTED = "submitted",
    SHUTTING_DOWN_UCI = "shutting-downUCI",
    SHUTTING_DOWN = "shutting-down",
    AVAILABLE = "available",
    RUNNING = "running",
    PENDING = "pending",
    ERROR = "error",
    SNAPSHOT_UCI = "snapshotUCI",
    SNAPSHOT = "snapshot"
)
instance_states = Bunch(
    TERMINATED = "terminated",
    SUBMITTED = "submitted",
    RUNNING = "running",
    PENDING = "pending",
    SHUTTING_DOWN = "shutting-down",
    ERROR = "error"
)

snapshot_status = Bunch(
    SUBMITTED = 'submitted',
    PENDING = 'pending',
    COMPLETED = 'completed',
    DELETE = 'delete',
    DELETED= 'deleted',
    ERROR = "error"
)

class CloudManager( object ):
    """
    Highest level interface to cloud management.
    """
    def __init__( self, app ):
        self.app = app
        if self.app.config.get_bool( "enable_cloud_execution", True ):
            # The dispatcher manager for underlying cloud instances - implements and contacts individual cloud providers
            self.provider = CloudProvider( app )
            # Monitor for updating status of cloud instances
            self.cloud_monitor = CloudMonitor( self.app, self.provider   )
        else:
            self.job_queue = self.job_stop_queue = NoopCloudMonitor()

    def shutdown( self ):
        self.cloud_monitor.shutdown()
        
class Sleeper( object ):
    """
    Provides a 'sleep' method that sleeps for a number of seconds *unless*
    the notify method is called (from a different thread).
    """
    def __init__( self ):
        self.condition = threading.Condition()
    def sleep( self, seconds ):
        self.condition.acquire()
        self.condition.wait( seconds )
        self.condition.release()
    def wake( self ):
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()

class CloudMonitor( object ):
    """
    Cloud manager, waits for user to instantiate a cloud instance and then invokes a 
    CloudProvider.
    """
    STOP_SIGNAL = object()
    def __init__( self, app, provider ):
        """Start the cloud manager"""
        self.app = app
        # Keep track of the pid that started the cloud manager, only it
        # has valid threads
        self.parent_pid = os.getpid()
       
        # Contains requests that are waiting (only use from monitor thread)
        self.waiting = []
                
        # Helper for interruptable sleep
        self.sleeper = Sleeper()
        self.running = True
        self.provider = provider
        self.monitor_thread = threading.Thread( target=self.__monitor )
        self.monitor_thread.start()        
        log.info( "Cloud manager started" )

    def __monitor( self ):
        """
        Daemon that continuously monitors cloud instance requests as well as state
        of running instances.
        """
        # HACK: Delay until after forking, we need a way to do post fork notification!!!
        time.sleep( 10 )
        
        cnt = 0 # Run global update only periodically so keep counter variable
        while self.running:
            try:
#                log.debug( "Calling monitor_step" )
                self.__monitor_step()
                if cnt%30 == 0: # Run global update every 30 iterations (1 minute)
                    self.provider.update()
                    cnt = 0
            except:
                log.exception( "Exception in cloud manager monitor_step" )
            # Sleep
            cnt += 1
            self.sleeper.sleep( 2 )

    def __monitor_step( self ):
        """
        Called repeatedly by `monitor` to process cloud instance requests.
        TODO: Update following description to match the code
        Gets any new cloud instance requests from the database, then iterates
        over all new and waiting jobs to check the state of the jobs each
        depends on. If the job has dependencies that have not finished, it
        it goes to the waiting queue. If the job has dependencies with errors,
        it is marked as having errors and removed from the queue. Otherwise,
        the job is dispatched.
        """
        # Get an orm (object relational mapping) session
        session = mapping.Session()
        new_requests = []
           
        for r in session.query( model.UCI ) \
                .filter( or_( model.UCI.c.state==uci_states.NEW_UCI,  
                              model.UCI.c.state==uci_states.SUBMITTED_UCI,
                              model.UCI.c.state==uci_states.SHUTTING_DOWN_UCI, 
                              model.UCI.c.state==uci_states.DELETING_UCI,
                              model.UCI.c.state==uci_states.SNAPSHOT_UCI ) ) \
                .all():
            uci_wrapper = UCIwrapper( r )
            new_requests.append( uci_wrapper )

        for uci_wrapper in new_requests:
            session.clear()
            self.put( uci_wrapper )
        
        # Done with the session
        mapping.Session.remove()
                 
    def put( self, uci_wrapper ):
        """Add a request to the queue."""
        self.provider.put( uci_wrapper )
        self.sleeper.wake()
    
    def shutdown( self ):
        """Attempts to gracefully shut down the worker thread"""
        if self.parent_pid != os.getpid():
            # We're not the real queue, do nothing
            return
        else:
            log.info( "Sending stop signal to worker thread" )
            self.running = False
            self.sleeper.wake()
            log.info( "cloud manager stopped" )
            self.dispatcher.shutdown()

class UCIwrapper( object ):
    """
    Wraps 'model.UCI' with convenience methods for state management
    """
    def __init__( self, uci ):
        self.uci_id = uci.id
        
    # --------- Setter methods -----------------
    
    def change_state( self, uci_state=None, instance_id=None, i_state=None ):
        """
        Sets state for UCI and/or UCI's instance with instance_id as provided by cloud provider and stored in local
        Galaxy database. 
        Need to provide either: (1) state for the UCI, or (2) instance_id and it's state, or (3) all arguments.
        """
#        log.debug( "Changing state - new uci_state: %s, instance_id: %s, i_state: %s" % ( uci_state, instance_id, i_state ) )
        if uci_state is not None:
            uci = model.UCI.get( self.uci_id )
            uci.refresh()
            uci.state = uci_state
            uci.flush()
        if ( instance_id is not None ) and ( i_state is not None ):
            instance = model.CloudInstance.filter_by( uci_id=self.uci_id, instance_id=instance_id).first()
            instance.state = i_state
            instance.flush()
        
    def set_mi( self, i_index, mi_id ):
        """
        Sets Machine Image (MI), e.g., 'ami-66fa190f', for UCI's instance with given index as it
        is stored in local Galaxy database. 
        """
        mi = model.CloudImage.filter( model.CloudImage.c.image_id==mi_id ).first()
        instance = model.CloudInstance.get( i_index )
        instance.image = mi
        instance.flush()
        
    def set_key_pair( self, key_name, key_material=None ):
        """
        Sets key pair value for current UCI.
        """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        uci.key_pair_name = key_name
        if key_material is not None:
            uci.key_pair_material = key_material
        uci.flush()
    
    def set_launch_time( self, launch_time, i_index=None, i_id=None ):
        """
        Stores launch time in local database for instance with specified index - i_index (as it is stored in local
        Galaxy database) or with specified instance ID - i_id (as obtained from the cloud provider AND stored
        in local Galaxy Database). Either 'i_index' or 'i_id' needs to be provided.
        """
        if i_index != None:
            instance = model.CloudInstance.get( i_index )
            instance.launch_time = launch_time
            instance.flush()
        elif i_id != None:
            instance = model.CloudInstance.filter_by( uci_id=self.uci_id, instance_id=i_id).first()
            instance.launch_time = launch_time
            instance.flush()
    
    def set_uci_launch_time( self, launch_time ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        uci.launch_time = launch_time
        uci.flush()
    
    def set_stop_time( self, stop_time, i_index=None, i_id=None ):
        """
        Stores stop time in local database for instance with specified index - i_index (as it is stored in local
        Galaxy database) or with specified instance ID - i_id (as obtained from the cloud provider AND stored
        in local Galaxy Database). Either 'i_index' or 'i_id' needs to be provided.
        """
        if i_index != None:
            instance = model.CloudInstance.get( i_index )
            instance.stop_time = stop_time
            instance.flush()
        elif i_id != None:
            instance = model.CloudInstance.filter_by( uci_id=self.uci_id, instance_id=i_id).first()
            instance.stop_time = stop_time
            instance.flush()
    
    def reset_uci_launch_time( self ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        uci.launch_time = None
        uci.flush()
        
    def set_security_group_name( self, security_group_name, i_index=None, i_id=None ):
        """
        Stores security group name in local database for instance with specified index - i_index (as it is stored in local
        Galaxy database) or with specified instance ID - i_id (as obtained from the cloud provider AND stored
        in local Galaxy Database). Either 'i_index' or 'i_id' needs to be provided.
        """
        if i_index != None:
            instance = model.CloudInstance.get( i_index )
            instance.security_group = security_group_name
            instance.flush()
        elif i_id != None:
            instance = model.CloudInstance.filter_by( uci_id=self.uci_id, instance_id=i_id).first()
            instance.security_group = security_group_name
            instance.flush()
    
    def set_reservation_id( self, i_index, reservation_id ):
        instance = model.CloudInstance.get( i_index )
        instance.reservation_id = reservation_id
        instance.flush()
        
    def set_instance_id( self, i_index, instance_id ):
        """
        i_index refers to UCI's instance ID as stored in local database
        instance_id refers to real-world, cloud resource ID (e.g., 'i-78hd823a') 
        """
        instance = model.CloudInstance.get( i_index )
        instance.instance_id = instance_id
        instance.flush()
    
    def set_public_dns( self, instance_id, public_dns ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        uci.instance[instance_id].public_dns = public_dns
        uci.instance[instance_id].flush()
    
    def set_private_dns( self, instance_id, private_dns ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        uci.instance[instance_id].private_dns = private_dns
        uci.instance[instance_id].flush()
    
    def set_store_device( self, store_id, device ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        uci.store[store_id].device = device
        uci.store[store_id].flush()
    
    def set_store_status( self, vol_id, status ):
        vol = model.CloudStore.filter( model.CloudStore.c.volume_id == vol_id ).first()
        vol.status = status
        vol.flush()
        
    def set_snapshot_id( self, snap_index, id ):
        snap = model.CloudSnapshot.get( snap_index )
        snap.snapshot_id = id
        snap.flush()

    def set_snapshot_status( self, status, snap_index=None, snap_id=None ):
        if snap_index != None:
            snap = model.CloudSnapshot.get( snap_index )
        elif snap_id != None:
            snap = model.CloudSnapshot.filter_by( snapshot_id = snap_id).first()
        else:
            return
        snap.status = status
        snap.flush()
    
    def set_snapshot_error( self, error, snap_index=None, snap_id=None, set_status=False ):
        if snap_index != None:
            snap = model.CloudSnapshot.get( snap_index )
        elif snap_id != None:
            snap = model.CloudSnapshot.filter_by( snapshot_id = snap_id).first()
        else:
            return
        snap.error = error
        
        if set_status:
            snap.status = snapshot_status.ERROR
            
        snap.flush()

    def set_store_availability_zone( self, availability_zone, vol_id=None ):
        """
        Sets availability zone of storage volumes for either ALL volumes associated with current
        UCI or for the volume whose volume ID (e.g., 'vol-39F80512') is provided as argument.
        """
        if vol_id is not None:
            vol = model.CloudStore.filter( model.CloudStore.c.volume_id == vol_id ).all()
        else:
            vol = model.CloudStore.filter( model.CloudStore.c.uci_id == self.uci_id ).all()
        
        for v in vol:
            v.availability_zone = availability_zone
            v.flush()
        
    def set_store_volume_id( self, store_id, volume_id ):
        """
        Given store ID associated with this UCI, set volume ID as it is registered 
        on the cloud provider (e.g., vol-39890501)
        """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        uci.store[store_id].volume_id = volume_id
        uci.store[store_id].flush()
        
    def set_store_instance( self, vol_id, instance_id ):
        """
        Stores instance ID that given store volume is attached to. Store volume ID should
        be given in following format: 'vol-78943248'
        """
        vol = model.CloudStore.filter( model.CloudStore.c.volume_id == vol_id ).first()
        vol.i_id = instance_id
        vol.flush()
        
    def set_error( self, error, set_state=False ):
        """
        Sets error field of given UCI in local Galaxy database as well as any instances associated with
        this UCI whose state is 'None' or 'SUBMITTED'. If set_state is set to 'true', 
        method also sets state of give UCI and corresponding instances to 'error'
        """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        uci.error = error
        if set_state:
            uci.state = uci_states.ERROR
            instances = model.CloudInstance \
                .filter_by( uci=uci ) \
                .filter( or_( model.CloudInstance.c.state==None, model.CloudInstance.c.state==instance_states.SUBMITTED ) ) \
                .all()
            for i in instances:
                i.error = error
                i.state = instance_states.ERROR
                i.flush()
        uci.flush()

    # --------- Getter methods -----------------
    
    def get_provider_type( self ):
        """ Returns type of cloud provider associated with given UCI. """ 
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
#        cred_id = uci.credentials_id
#        cred = model.CloudUserCredentials.get( cred_id )
        return uci.credentials.provider.type
    
    def get_type( self, i_index ):
        instance = model.CloudInstance.get( i_index )
        return instance.type 
        
    def get_state( self ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.state
    
    def get_instances_indexes( self, state=None ):
        """
        Returns indexes of instances associated with given UCI as they are stored in local Galaxy database and 
        whose state corresponds to passed argument. Returned values enable indexing instances from local Galaxy database.  
        """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        instances = model.CloudInstance.filter_by( uci=uci ).filter( model.CloudInstance.c.state==state ).all()
        il = []
        for i in instances:
            il.append( i.id )
            
        return il
    
    def get_instance_state( self, instance_id ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.instance[instance_id].state
    
    def get_instances_ids( self ):
        """ 
        Returns list IDs of all instances' associated with this UCI that are not in 'terminated' state
        (e.g., ['i-402906D2', 'i-q0290dsD2'] ).
        """
        il = model.CloudInstance.filter_by( uci_id=self.uci_id ).filter( model.CloudInstance.c.state != 'terminated' ).all()
        instanceList = []
        for i in il:
            instanceList.append( i.instance_id )
        return instanceList
        
    def get_name( self ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.name
    
    def get_key_pair_name( self ):
        """
        Returns keypair name associated with given UCI.
        """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.key_pair_name
    
    def get_key_pair_material( self ):
        """
        Returns keypair material (i.e., private key) associated with given UCI.
        """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.key_pair_material
        
    def get_security_group_name( self, i_index=None, i_id=None ):
        """
        Given EITHER instance index as it is stored in local Galaxy database OR instance ID as it is 
        obtained from cloud provider and stored in local Galaxy database, return security group name associated
        with given instance.
        """
        if i_index != None:
            instance = model.CloudInstance.get( i_index )
            return instance.security_group
        elif i_id != None:
            instance = model.CloudInstance.filter_by( uci_id=self.uci_id, instance_id=i_id).first()
            return instance.security_group
    
    def get_access_key( self ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.credentials.access_key
    
    def get_secret_key( self ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.credentials.secret_key
    
    def get_mi_id( self, instance_id=0 ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.instance[instance_id].mi_id
    
    def get_public_dns( self, instance_id=0 ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.instance[instance_id].public_dns
    
    def get_private_dns( self, instance_id=0 ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.instance[instance_id].private_dns
    
    def get_uci_availability_zone( self ):
        """
        Returns UCI's availability zone.
        Because all of storage volumes associated with a given UCI must be in the same
        availability zone, availability of a UCI is determined by availability zone of 
        any one storage volume. 
        """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.store[0].availability_zone
    
    def get_store_size( self, store_id=0 ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.store[store_id].size
    
    def get_store_volume_id( self, store_id=0 ):
        """
        Given store ID associated with this UCI, get volume ID as it is registered 
        on the cloud provider (e.g., 'vol-39890501')
        """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.store[store_id].volume_id
    
    def get_all_stores( self ):
        """ Returns all storage volumes' database objects associated with this UCI. """
        return model.CloudStore.filter( model.CloudStore.c.uci_id == self.uci_id ).all()
    
    def get_snapshots( self, status=None ):
        """ Returns database objects for all snapshots associated with this UCI and in given status."""
        return model.CloudSnapshot.filter_by( uci_id=self.uci_id, status=status ).all()
        
    def get_uci( self ):
        """ Returns database object for given UCI. """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci
    
    def get_provider( self ):
        """ Returns database object of cloud provider associated with credentials of given UCI. """
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.credentials.provider
    
    def uci_launch_time_set( self ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        return uci.launch_time
    
    def delete( self ):
        uci = model.UCI.get( self.uci_id )
        uci.refresh()
        uci.state = uci_states.DELETED # for bookkeeping reasons, mark as deleted but don't actually delete.
        uci.deleted = True
        uci.flush()
    
class CloudProvider( object ):
    def __init__( self, app ):
        import providers.eucalyptus
        import providers.ec2
        
        self.app = app
        self.cloud_provider = {}
        self.cloud_provider["eucalyptus"] = providers.eucalyptus.EucalyptusCloudProvider( app )
        self.cloud_provider["ec2"] = providers.ec2.EC2CloudProvider( app )
            
    def put( self, uci_wrapper ):
        """ Put given request for UCI manipulation into provider's request queue."""
        self.cloud_provider[uci_wrapper.get_provider_type()].put( uci_wrapper )
    
    def update( self ):
        """ 
        Runs a global status update across all providers for all UCIs in state other than 'terminated' and 'available'.
        Reason behind this method is to sync state of local DB and real world resources.
        """
        for provider in self.cloud_provider.keys():
#            log.debug( "Running global update for provider: '%s'" % provider )
            self.cloud_provider[provider].update()
        
    def shutdown( self ):
        for runner in self.cloud_provider.itervalues():
            runner.shutdown()

class NoopCloudMonitor( object ):
    """
    Implements the CloudMonitor interface but does nothing
    """
    def put( self, *args ):
        return
    def shutdown( self ):
        return

