from galaxy.web.base.controller import *

import pkg_resources
pkg_resources.require( "simplejson" )
import simplejson

from galaxy.tools.parameters import *
from galaxy.tools import DefaultToolState
from galaxy.tools.parameters.grouping import Repeat, Conditional
from galaxy.datatypes.data import Data
from galaxy.util.odict import odict
from galaxy.util.bunch import Bunch
from galaxy.util.topsort import topsort, topsort_levels, CycleError
from galaxy.workflow.modules import *
from galaxy.model.mapping import desc
from galaxy.model.orm import *
from datetime import datetime, timedelta

pkg_resources.require( "WebHelpers" )
from webhelpers import *

# Required for Cloud tab
import galaxy.eggs
galaxy.eggs.require("boto")
from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo
from galaxy.cloud import CloudManager

import logging
log = logging.getLogger( __name__ )

class CloudController( BaseController ):
    
#    def __init__( self ):
#        self.cloudManager = CloudManager()
    
    @web.expose
    def index( self, trans ):
        return trans.fill_template( "cloud/index.mako" )
                                   
    @web.expose
    @web.require_login( "use Galaxy cloud" )
    def list( self, trans ):
        """
        Render cloud main page (management of cloud resources)
        """
        user = trans.get_user()
#        pendingInstances = trans.sa_session.query( model.UCI ) \
#            .filter_by( user=user, state="pending" ) \
#            .all()
#            
#        for i inupdate_in range( len ( pendingInstances ) ):
#            stance_state( trans, pendingInstances[i].id )
        
        cloudCredentials = trans.sa_session.query( model.CloudUserCredentials ) \
            .filter_by( user=user ) \
            .order_by( desc( model.CloudUserCredentials.c.update_time ) ) \
            .all()
        
        liveInstances = trans.sa_session.query( model.UCI ) \
            .filter_by( user=user ) \
            .filter( or_( model.UCI.c.state=="running", 
                          model.UCI.c.state=="pending",
                          model.UCI.c.state=="submitted", 
                          model.UCI.c.state=="submittedUCI",
                          model.UCI.c.state=="shutting-down",
                          model.UCI.c.state=="shutting-downUCI" ) ) \
            .order_by( desc( model.UCI.c.update_time ) ) \
            .all()
            
        prevInstances = trans.sa_session.query( model.UCI ) \
            .filter_by( user=user ) \
            .filter( or_( model.UCI.c.state=="available", 
                          model.UCI.c.state=="new", 
                          model.UCI.c.state=="newUCI", 
                          model.UCI.c.state=="error", 
                          model.UCI.c.state=="deleting",
                          model.UCI.c.state=="deletingUCI" ) ) \
            .order_by( desc( model.UCI.c.update_time ) ) \
            .all()
        
        # Check after update there are instances in pending state; if so, display message
        # TODO: Auto-refresh once instance is running
        pendingInstances = trans.sa_session.query( model.UCI ) \
            .filter_by( user=user ) \
            .filter( or_( model.UCI.c.state=="pending" , \
                          model.UCI.c.state=="submitted" , \
                          model.UCI.c.state=="submittedUCI" ) ) \
            .all()
        if pendingInstances:
            trans.set_message( "Galaxy instance started. NOTE: Please wait about 3-5 minutes for the instance to " 
                    "start up and then refresh this page. A button to connect to the instance will then appear alongside "
                    "instance description." )         
        
        return trans.fill_template( "cloud/configure_cloud.mako",
                                    cloudCredentials = cloudCredentials,
                                    liveInstances = liveInstances,
                                    prevInstances = prevInstances )
    
    @web.expose
    @web.require_login( "use Galaxy cloud" )
    def makeDefault( self, trans, id=None ):
        """ 
        Set current credentials as default.
        """
        currentDefault = get_default_credentials (trans)
        if currentDefault:
            currentDefault.defaultCred = False
        
        newDefault = get_stored_credentials( trans, id )
        newDefault.defaultCred = True
        trans.sa_session.flush()
        trans.set_message( "Credentials '%s' set as default." % newDefault.name )
        
        # TODO: Fix bug that when this function returns, top Galaxy tab bar is missing from the webpage  
        return self.list( trans ) #trans.fill_template( "cloud/configure_cloud.mako",
               #awsCredentials = awsCredentials )
               

    @web.expose
    @web.require_login( "start Galaxy cloud instance" )
    def start( self, trans, id, type='m1.small' ):
        """
        Start a new cloud resource instance
        """
        # TODO: Add choice of instance type before starting one
        #if type:
        user = trans.get_user()
        mi = get_mi( trans, type )
        uci = get_uci( trans, id )
        stores = get_stores( trans, uci ) 
#        log.debug(self.app.config.job_working_directory)
        if ( len(stores) is not 0 ) and \
           ( uci.state != 'submitted' ) and \
           ( uci.state != 'submittedUCI' ) and \
           ( uci.state != 'pending' ) and \
           ( uci.state != 'deleting' ) and \
           ( uci.state != 'deletingUCI' ) and \
           ( uci.state != 'error' ):
            instance = model.CloudInstance()
            instance.user = user
            instance.image = mi
            instance.uci = uci
            instance.availability_zone = stores[0].availability_zone # Bc. all EBS volumes need to be in the same avail. zone, just check 1st
            instance.type = type
#            instance.keypair_name = get_keypair_name( trans )
#            conn = get_connection( trans )
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
            
#            log.debug( '***** Starting an instance' )
#            log.debug( 'Using following command: conn.run_instances( image_id=%s, key_name=%s )' % ( instance.image.image_id, instance.keypair_name ) )
#            reservation = conn.run_instances( image_id=instance.image.image_id, key_name=instance.keypair_name )
            #reservation = conn.run_instances( image_id=instance.image, key_name=instance.keypair_name, security_groups=['galaxy'], instance_type=instance.type,  placement=instance.availability_zone )
#            instance.launch_time = datetime.utcnow()
#            uci.launch_time = instance.launch_time
#            instance.reservation_id = str( reservation ).split(":")[1]
#            instance.instance_id = str( reservation.instances[0]).split(":")[1]
#            instance.state = "pending"
#            instance.state = reservation.instances[0].state
            uci.state = 'submittedUCI'
            
            # Persist
            session = trans.sa_session
            session.save_or_update( instance )
            session.save_or_update( uci )
            session.flush()
                        
            trans.log_event ("User initiated starting of cloud instance '%s'." % uci.name )
            trans.set_message( "Galaxy instance started. NOTE: Please wait about 3-5 minutes for the instance to " 
                    "start up and then refresh this page. A button to connect to the instance will then appear alongside "
                    "instance description." )
            return self.list( trans )
        
        trans.show_error_message( "Cannot start instance that is in state '%s'." % uci.state )
        return self.list( trans )
        
#        return trans.show_form( 
#            web.FormBuilder( web.url_for(), "Start instance size", submit_text="Start" )
#                .add_input( "radio","Small","size", value='small' ) 
#                .add_input( "radio","Medium","size", value='medium' ) )
                    
    
    @web.expose
    @web.require_login( "stop Galaxy cloud instance" )
    def stop( self, trans, id ):
        """
        Stop a cloud UCI instance. This implies stopping Galaxy server and disconnecting/unmounting relevant file system(s).
        """
        uci = get_uci( trans, id )
        uci.state = 'shutting-downUCI'
        session = trans.sa_session
#        session.save_or_update( stores )
        session.save_or_update( uci )
        session.flush()
        trans.log_event( "User stopped cloud instance '%s'" % uci.name )
        trans.set_message( "Galaxy instance '%s' stopped." % uci.name )
        
#        dbInstances = get_instances( trans, uci ) #TODO: handle list!
#        
#        conn = get_connection( trans )
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
#                    
        return self.list( trans )
    
    @web.expose
    @web.require_login( "delete user configured Galaxy cloud instance" )
    def deleteInstance( self, trans, id ):
        """
        Deletes User Configured Instance (UCI) from the cloud and local database. NOTE that this implies deletion of 
        any and all storage associated with this UCI!
        """
        uci = get_uci( trans, id )
        
        if ( uci.state != 'deletingUCI' ) and ( uci.state != 'deleting' ) and ( uci.state != 'error' ):
            name = uci.name
            uci.state = "deletingUCI"
    #        dbInstances = get_instances( trans, uci ) #TODO: handle list!
    #        
    #        conn = get_connection( trans )
            session = trans.sa_session
    #        
    #        # Delete volume(s) associated with given uci 
    #        stores = get_stores( trans, uci )
    #        for i, store in enumerate( stores ):
    #            log.debug( "Deleting volume '%s' that is associated with UCI '%s'." % ( store.volume_id, uci.name ) )
    #            volStat = None
    #            try:
    #                volStat = conn.delete_volume( store.volume_id )
    #            except:
    #                log.debug ( 'Error deleting volume %s' % store.volume_id )
    #            
    #            if volStat:
    #                session.delete( store )
    #            
    #        # Delete UCI from table
    #        uciName = uci.name # Store name for logging
    #        session.delete( uci )
            
            session.flush()
            trans.log_event( "User deleted cloud instance '%s'" % name )
            trans.set_message( "Galaxy instance '%s' marked for deletion." % name )
            return self.list( trans )
        
        trans.set_message( "Instance '%s' is already marked for deletion." % uci.name )
        return self.list( trans )
    
    @web.expose
    @web.require_login( "add instance storage" )
    def addStorage( self, trans, id ):
        instance = get_uci( trans, id )
        
        
        error( "Adding storage to instance '%s' is not supported yet." % instance.name )
                    
        return self.list( trans )
    
    @web.expose
    @web.require_login( "use Galaxy cloud" )
    def configureNew( self, trans, instanceName='', credName='', volSize='', zone=''):
        """
        Configure and add new cloud instance to user's instance pool
        """
        inst_error = vol_error = cred_error = None
        error = {}
        user = trans.get_user()
        # TODO: Hack until present user w/ bullet list w/ registered credentials
        storedCreds = trans.sa_session.query( model.CloudUserCredentials ).filter_by( user=user ).all()
        if len( storedCreds ) == 0:
            return trans.show_error_message( "You must register credentials before configuring a Galaxy instance." )

        providersToZones = {}
        for storedCred in storedCreds:
            if storedCred.provider_name == 'ec2':
                ec2_zones = ['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d']
                providersToZones[storedCred.name] = ec2_zones 
            elif storedCred.provider_name == 'eucalyptus':
                providersToZones[storedCred.name] = ['epc']
        
        if instanceName:
            # Create new user configured instance
            try:
                if trans.app.model.UCI.filter(  and_( trans.app.model.UCI.table.c.name==instanceName, trans.app.model.UCI.table.c.state!='deleted' ) ).first():
                    error['inst_error'] = "An instance with that name already exist."
                elif instanceName=='' or len( instanceName ) > 255:
                    error['inst_error'] = "Instance name must be between 1 and 255 characters long."
                elif credName=='':
                    error['cred_error'] = "You must select credentials."
                elif volSize == '':
                    error['vol_error'] = "You must specify volume size as an integer value between 1 and 1000."
                elif ( int( volSize ) < 1 ) or ( int( volSize ) > 1000 ):
                    error['vol_error'] = "Volume size must be integer value between 1 and 1000."
#                elif type( volSize ) != type( 1 ): # Check if volSize is int
#                    log.debug( "volSize='%s'" % volSize )
#                    error['vol_error'] = "Volume size must be integer value between 1 and 1000."
                elif zone=='':
                    error['zone_error'] = "You must select zone where this UCI will be registered."
                else:
                    # Capture user configured instance information
                    uci = model.UCI()
                    uci.name = instanceName
                    uci.credentials = trans.app.model.CloudUserCredentials.filter(
                        trans.app.model.CloudUserCredentials.table.c.name==credName ).first()
                    uci.user= user
                    uci.total_size = volSize # This is OK now because new instance is being created. 
                    uci.state = "newUCI"
                    
                    storage = model.CloudStore()
                    storage.user = user
                    storage.uci = uci
                    storage.size = volSize
                    storage.availability_zone = zone # TODO: Give user choice here. Also, enable region selection.
                    # Persist
                    session = trans.sa_session
                    session.save_or_update( uci )
                    session.save_or_update( storage )
                    session.flush()
                    # Log and display the management page
                    trans.log_event( "User configured new cloud instance" )
                    trans.set_message( "New Galaxy instance '%s' configured. Once instance status shows 'available' you will be able to start the instance." % instanceName )
                    return self.list( trans )
            except ValueError:
                vol_error = "Volume size must be specified as an integer value only, between 1 and 1000."
            except AttributeError, ae:
                inst_error = "No registered cloud images. You must contact administrator to add some before proceeding."
                log.debug("AttributeError: %s " % str( ae ) )
        
        #TODO: based on user credentials (i.e., provider) selected, zone options will be different (e.g., EC2: us-east-1a vs EPC: epc)
        
        return trans.fill_template( "cloud/configure_uci.mako", 
                                    instanceName = instanceName, 
                                    credName = storedCreds, 
                                    volSize = volSize, 
                                    zone = zone, 
                                    error = error, 
                                    providersToZones = providersToZones )
                
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Configure new instance", submit_text="Add" )
                .add_text( "instanceName", "Instance name", value="Unnamed instance", error=inst_error ) 
                .add_text( "credName", "Name of registered credentials to use", value="", error=cred_error )
                .add_text( "volSize", "Permanent storage size (1GB - 1000GB)"  
                    "<br />Note: you will be able to add more storage later", value='', error=vol_error ) )
        
    @web.expose
    @web.require_login( "add a cloud image" )
    #@web.require_admin
    def addNewImage( self, trans, image_id='', manifest='', state=None ):
        error = None
        if image_id:
            if len( image_id ) > 255:
                error = "Image ID name exceeds maximum allowable length."
            elif trans.app.model.CloudUserCredentials.filter(  
                    trans.app.model.CloudImage.table.c.image_id==image_id ).first():
                error = "Image with that ID is already registered."
            else:
                # Create new image
                image = model.CloudImage()
                image.image_id = image_id
                image.manifest = manifest
                # Persist
                session = trans.sa_session
                session.save_or_update( image )
                session.flush()
                # Log and display the management page
                trans.log_event( "New cloud image added: '%s'" % image.image_id )
                trans.set_message( "Cloud image '%s' added." % image.image_id )
                if state:
                    image.state= state
                return self.list( trans )
            
        return trans.show_form(
            web.FormBuilder( web.url_for(), "Add new cloud image", submit_text="Add" )
                .add_text( "image_id", "Machine Image ID (AMI or EMI)", value='', error=error )
                .add_text( "manifest", "Manifest", value='', error=error ) )
            
    @web.expose
    @web.require_login( "use Galaxy cloud" )
    def rename( self, trans, id, new_name=None ):
        stored = get_stored_credentials( trans, id )
        if new_name is not None:
            stored.name = new_name
            trans.sa_session.flush()
            trans.set_message( "Credentials renamed to '%s'." % new_name )
            return self.list( trans )
        else:
            return form( url_for( id=trans.security.encode_id(stored.id) ), "Rename credentials", submit_text="Rename" ) \
                .add_text( "new_name", "Credentials Name", value=stored.name )
   
    @web.expose
    @web.require_login( "use Galaxy cloud" )
    def renameInstance( self, trans, id, new_name=None ):
        instance = get_uci( trans, id )
        if new_name is not None:
            instance.name = new_name
            trans.sa_session.flush()
            trans.set_message( "Instance renamed to '%s'." % new_name )
            return self.list( trans )
        else:
            return form( url_for( id=trans.security.encode_id(instance.id) ), "Rename instance", submit_text="Rename" ) \
                .add_text( "new_name", "Instance name", value=instance.name )
   
    @web.expose
    @web.require_login( "add credentials" )
    def add( self, trans, credName='', accessKey='', secretKey='', providerName='' ):
        """
        Add user's cloud credentials stored under name `credName`.
        """
        user = trans.get_user()
        error = {}
        
        if credName:
            if len( credName ) > 255:
                error['cred_error'] = "Credentials name exceeds maximum allowable length."
            elif trans.app.model.CloudUserCredentials.filter(  
                    trans.app.model.CloudUserCredentials.table.c.name==credName ).first():
                error['cred_error'] = "Credentials with that name already exist."
            elif ( ( providerName.lower()!='ec2' ) and ( providerName.lower()!='eucalyptus' ) ):
                error['provider_error'] = "You specified an unsupported cloud provider."
            elif accessKey=='' or len( accessKey ) > 255:
                error['access_key_error'] = "Access key must be between 1 and 255 characters long."
            elif secretKey=='' or len( secretKey ) > 255:
                error['secret_key_error'] = "Secret key must be between 1 and 255 characters long."
            else:
                # Create new user stored credentials
                credentials = model.CloudUserCredentials()
                credentials.name = credName
                credentials.user = user
                credentials.access_key = accessKey
                credentials.secret_key = secretKey
                credentials.provider_name = providerName.lower()
                # Persist
                session = trans.sa_session
                session.save_or_update( credentials )
                session.flush()
                # Log and display the management page
                trans.log_event( "User added new credentials" )
                trans.set_message( "Credential '%s' created" % credentials.name )
#                if defaultCred:
#                    self.makeDefault( trans, credentials.id)
                return self.list( trans )
        
        return trans.fill_template( "cloud/add_credentials.mako", \
                                    credName = credName, \
                                    providerName = providerName, \
                                    accessKey = accessKey, \
                                    secretKey = secretKey, \
                                    error = error
                                    )
        
#        return trans.show_form( 
#            web.FormBuilder( web.url_for(), "Add credentials", submit_text="Add" )
#                .add_text( "credName", "Credentials name", value="Unnamed credentials", error=cred_error )
#                .add_text( "providerName", "Cloud provider name", value="ec2 or eucalyptus", error=provider_error )
#                .add_text( "accessKey", "Access key", value='', error=accessKey_error ) 
#                .add_password( "secretKey", "Secret key", value='', error=secretKey_error ) )
        
    @web.expose
    @web.require_login( "view credentials" )
    def view( self, trans, id=None ):
        """
        View details for user credentials 
        """        
        # Load credentials from database
        stored = get_stored_credentials( trans, id )
        
        return trans.fill_template( "cloud/view.mako", 
                                   credDetails = stored )

    @web.expose
    @web.require_login( "view instance details" )
    def viewInstance( self, trans, id=None ):
        """
        View details about running instance
        """
        uci = get_uci( trans, id )
        instances = get_instances( trans, uci ) # TODO: Handle list (will probably need to be done in mako template)
        
        return trans.fill_template( "cloud/viewInstance.mako",
                                    liveInstance = instances )
        

    @web.expose
    @web.require_login( "delete credentials" )
    def delete( self, trans, id=None ):
        """
        Delete user's cloud credentials
        TODO: Because UCI's depend on specific credentials, need to handle case where given credentials are being used by a UCI 
        """
        # Load credentials from database
        stored = get_stored_credentials( trans, id )
        # Delete and save
        sess = trans.sa_session
        sess.delete( stored )
        stored.flush()
        # Display the management page
        trans.set_message( "Credentials '%s' deleted." % stored.name )
        return self.list( trans )
    
    @web.expose
    @web.require_login( "edit workflows" )
    def editor( self, trans, id=None ):
        """
        Render the main workflow editor interface. The canvas is embedded as
        an iframe (neccesary for scrolling to work properly), which is
        rendered by `editor_canvas`.
        """
        if not id:
            error( "Invalid workflow id" )
        id = trans.security.decode_id( id )
        return trans.fill_template( "workflow/editor.mako", workflow_id=id )
        
    @web.json
    def editor_form_post( self, trans, type='tool', tool_id=None, **incoming ):
        """
        Accepts a tool state and incoming values, and generates a new tool
        form and some additional information, packed into a json dictionary.
        This is used for the form shown in the right pane when a node
        is selected.
        """
        trans.workflow_building_mode = True
        module = module_factory.from_dict( trans, {
            'type': type,
            'tool_id': tool_id,
            'tool_state': incoming.pop("tool_state")
        } )
        module.update_state( incoming )
        return {
            'tool_state': module.get_state(),
            'data_inputs': module.get_data_inputs(),
            'data_outputs': module.get_data_outputs(),
            'tool_errors': module.get_errors(),
            'form_html': module.get_config_form()
        }
        
    @web.json
    def get_new_module_info( self, trans, type, **kwargs ):
        """
        Get the info for a new instance of a module initialized with default
        paramters (any keyword arguments will be passed along to the module).
        Result includes data inputs and outputs, html representation
        of the initial form, and the initial tool state (with default values).
        This is called asynchronously whenever a new node is added.
        """
        trans.workflow_building_mode = True
        module = module_factory.new( trans, type, **kwargs )
        return {
            'type': module.type,
            'name':  module.get_name(),
            'tool_id': module.get_tool_id(),
            'tool_state': module.get_state(),
            'data_inputs': module.get_data_inputs(),
            'data_outputs': module.get_data_outputs(),
            'form_html': module.get_config_form()
        }
                
    @web.json
    def load_workflow( self, trans, id ):
        """
        Get the latest Workflow for the StoredWorkflow identified by `id` and
        encode it as a json string that can be read by the workflow editor
        web interface.
        """
        user = trans.get_user()
        id = trans.security.decode_id( id )
        trans.workflow_building_mode = True
        # Load encoded workflow from database
        stored = trans.sa_session.query( model.StoredWorkflow ).get( id )
        assert stored.user == user
        workflow = stored.latest_workflow
        # Pack workflow data into a dictionary and return
        data = {}
        data['name'] = workflow.name
        data['steps'] = {}
        data['upgrade_messages'] = {}
        # For each step, rebuild the form and encode the state
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step( trans, step )
            # Fix any missing parameters
            upgrade_message = module.check_and_update_state()
            if upgrade_message:
                data['upgrade_messages'][step.order_index] = upgrade_message
            # Pack atrributes into plain dictionary
            step_dict = {
                'id': step.order_index,
                'type': module.type,
                'tool_id': module.get_tool_id(),
                'name': module.get_name(),
                'tool_state': module.get_state(),
                'tool_errors': module.get_errors(),
                'data_inputs': module.get_data_inputs(),
                'data_outputs': module.get_data_outputs(),
                'form_html': module.get_config_form(),
            }
            # Connections
            input_conn_dict = {}
            for conn in step.input_connections:
                input_conn_dict[ conn.input_name ] = \
                    dict( id=conn.output_step.order_index, output_name=conn.output_name )
            step_dict['input_connections'] = input_conn_dict
            # Position
            step_dict['position'] = step.position
            # Add to return value
            data['steps'][step.order_index] = step_dict
        print data['upgrade_messages']
        return data

    @web.json
    def save_workflow( self, trans, id, workflow_data ):
        """
        Save the workflow described by `workflow_data` with id `id`.
        """
        # Get the stored workflow
        stored = get_stored_workflow( trans, id )
        # Put parameters in workflow mode
        trans.workflow_building_mode = True
        # Convert incoming workflow data from json
        data = simplejson.loads( workflow_data )
        # Create new workflow from incoming data
        workflow = model.Workflow()
        # Just keep the last name (user can rename later)
        workflow.name = stored.name
        # Assume no errors until we find a step that has some
        workflow.has_errors = False
        # Create each step
        steps = []
        # The editor will provide ids for each step that we don't need to save,
        # but do need to use to make connections
        steps_by_external_id = {}
        # First pass to build step objects and populate basic values
        for key, step_dict in data['steps'].iteritems():
            # Create the model class for the step
            step = model.WorkflowStep()
            steps.append( step )
            steps_by_external_id[ step_dict['id' ] ] = step
            # FIXME: Position should be handled inside module
            step.position = step_dict['position']
            module = module_factory.from_dict( trans, step_dict )
            module.save_to_step( step )
            if step.tool_errors:
                workflow.has_errors = True
            # Stick this in the step temporarily
            step.temp_input_connections = step_dict['input_connections']
        # Second pass to deal with connections between steps
        for step in steps:
            # Input connections
            for input_name, conn_dict in step.temp_input_connections.iteritems():
                if conn_dict:
                    conn = model.WorkflowStepConnection()
                    conn.input_step = step
                    conn.input_name = input_name
                    conn.output_name = conn_dict['output_name']
                    conn.output_step = steps_by_external_id[ conn_dict['id'] ]
            del step.temp_input_connections
        # Order the steps if possible
        attach_ordered_steps( workflow, steps )
        # Connect up
        workflow.stored_workflow = stored
        stored.latest_workflow = workflow
        # Persist
        trans.sa_session.flush()
        # Return something informative
        errors = []
        if workflow.has_errors:
            errors.append( "Some steps in this workflow have validation errors" )
        if workflow.has_cycles:
            errors.append( "This workflow contains cycles" )
        if errors:
            rval = dict( message="Workflow saved, but will not be runnable due to the following errors",
                         errors=errors )
        else:
            rval = dict( message="Workflow saved" )
        rval['name'] = workflow.name
        return rval

    @web.json
    def get_datatypes( self, trans ):
        ext_to_class_name = dict()
        classes = []
        for k, v in trans.app.datatypes_registry.datatypes_by_extension.iteritems():
            c = v.__class__
            ext_to_class_name[k] = c.__module__ + "." + c.__name__
            classes.append( c )
        class_to_classes = dict()
        def visit_bases( types, cls ):
            for base in cls.__bases__:
                if issubclass( base, Data ):
                    types.add( base.__module__ + "." + base.__name__ )
                visit_bases( types, base )
        for c in classes:      
            n =  c.__module__ + "." + c.__name__
            types = set( [ n ] )
            visit_bases( types, c )
            class_to_classes[ n ] = dict( ( t, True ) for t in types )
        return dict( ext_to_class_name=ext_to_class_name, class_to_classes=class_to_classes )
    
    @web.expose
    def build_from_current_history( self, trans, job_ids=None, dataset_ids=None, workflow_name=None ):
        user = trans.get_user()
        history = trans.get_history()
        if not user:
            return trans.show_error_message( "Must be logged in to create workflows" )
        if ( job_ids is None and dataset_ids is None ) or workflow_name is None:
            jobs, warnings = get_job_dict( trans )
            # Render
            return trans.fill_template(
                        "workflow/build_from_current_history.mako", 
                        jobs=jobs,
                        warnings=warnings,
                        history=history )
        else:
            # Ensure job_ids and dataset_ids are lists (possibly empty)
            if job_ids is None:
                job_ids = []
            elif type( job_ids ) is not list:
                job_ids = [ job_ids ]
            if dataset_ids is None:
                dataset_ids = []
            elif type( dataset_ids ) is not list:
                dataset_ids = [ dataset_ids ]
            # Convert both sets of ids to integers
            job_ids = [ int( id ) for id in job_ids ]
            dataset_ids = [ int( id ) for id in dataset_ids ]
            # Find each job, for security we (implicately) check that they are
            # associated witha job in the current history. 
            jobs, warnings = get_job_dict( trans )
            jobs_by_id = dict( ( job.id, job ) for job in jobs.keys() )
            steps = []
            steps_by_job_id = {}
            hid_to_output_pair = {}
            # Input dataset steps
            for hid in dataset_ids:
                step = model.WorkflowStep()
                step.type = 'data_input'
                hid_to_output_pair[ hid ] = ( step, 'output' )
                steps.append( step )
            # Tool steps
            for job_id in job_ids:
                assert job_id in jobs_by_id, "Attempt to create workflow with job not connected to current history"
                job = jobs_by_id[ job_id ]
                tool = trans.app.toolbox.tools_by_id[ job.tool_id ]
                param_values = job.get_param_values( trans.app )
                associations = cleanup_param_values( tool.inputs, param_values )
                step = model.WorkflowStep()
                step.type = 'tool'
                step.tool_id = job.tool_id
                step.tool_inputs = tool.params_to_strings( param_values, trans.app )
                # NOTE: We shouldn't need to do two passes here since only
                #       an earlier job can be used as an input to a later
                #       job.
                for other_hid, input_name in associations:
                    if other_hid in hid_to_output_pair:
                        other_step, other_name = hid_to_output_pair[ other_hid ]
                        conn = model.WorkflowStepConnection()
                        conn.input_step = step
                        conn.input_name = input_name
                        # Should always be connected to an earlier step
                        conn.output_step = other_step
                        conn.output_name = other_name
                steps.append( step )
                steps_by_job_id[ job_id ] = step                
                # Store created dataset hids
                for assoc in job.output_datasets:
                    hid_to_output_pair[ assoc.dataset.hid ] = ( step, assoc.name )
            # Workflow to populate
            workflow = model.Workflow()
            workflow.name = workflow_name
            # Order the steps if possible
            attach_ordered_steps( workflow, steps )
            # And let's try to set up some reasonable locations on the canvas
            # (these are pretty arbitrary values)
            levorder = order_workflow_steps_with_levels( steps )
            base_pos = 10
            for i, steps_at_level in enumerate( levorder ):
                for j, index in enumerate( steps_at_level ):
                    step = steps[ index ]
                    step.position = dict( top = ( base_pos + 120 * j ),
                                          left = ( base_pos + 220 * i ) )
            # Store it
            stored = model.StoredWorkflow()
            stored.user = user
            stored.name = workflow_name
            workflow.stored_workflow = stored
            stored.latest_workflow = workflow
            trans.sa_session.save_or_update( stored )
            trans.sa_session.flush()
            # Index page with message
            return trans.show_message( "Workflow '%s' created from current history." % workflow_name )
            ## return trans.show_ok_message( "<p>Workflow '%s' created.</p><p><a target='_top' href='%s'>Click to load in workflow editor</a></p>"
            ##     % ( workflow_name, web.url_for( action='editor', id=trans.security.encode_id(stored.id) ) ) )       
        
    @web.expose
    def run( self, trans, id, check_user=True, **kwargs ):
        stored = get_stored_workflow( trans, id, check_ownership=False )
        if check_user:
            user = trans.get_user()
            if stored.user != user:
                if trans.sa_session.query( model.StoredWorkflowUserShareAssociation ) \
                        .filter_by( user=user, stored_workflow=stored ).count() == 0:
                    error( "Workflow is not owned by or shared with current user" )
        # Get the latest revision
        workflow = stored.latest_workflow
        # It is possible for a workflow to have 0 steps
        if len( workflow.steps ) == 0:
            error( "Workflow cannot be run because it does not have any steps" )
        #workflow = Workflow.from_simple( simplejson.loads( stored.encoded_value ), trans.app )
        if workflow.has_cycles:
            error( "Workflow cannot be run because it contains cycles" )
        if workflow.has_errors:
            error( "Workflow cannot be run because of validation errors in some steps" )
        # Build the state for each step
        errors = {}
        if kwargs:
            # If kwargs were provided, the states for each step should have
            # been POSTed
            for step in workflow.steps:
                # Connections by input name
                step.input_connections_by_name = \
                    dict( ( conn.input_name, conn ) for conn in step.input_connections ) 
                # Extract just the arguments for this step by prefix
                p = "%s|" % step.id
                l = len(p)
                step_args = dict( ( k[l:], v ) for ( k, v ) in kwargs.iteritems() if k.startswith( p ) )
                step_errors = None
                if step.type == 'tool' or step.type is None:
                    module = module_factory.from_workflow_step( trans, step )
                    # Any connected input needs to have value DummyDataset (these
                    # are not persisted so we need to do it every time)
                    module.add_dummy_datasets( connections=step.input_connections )    
                    # Get the tool
                    tool = module.tool
                    # Get the state
                    step.state = state = module.state
                    # Get old errors
                    old_errors = state.inputs.pop( "__errors__", {} )
                    # Update the state
                    step_errors = tool.update_state( trans, tool.inputs, step.state.inputs, step_args,
                                                     update_only=True, old_errors=old_errors )
                else:
                    module = step.module = module_factory.from_workflow_step( trans, step )
                    state = step.state = module.decode_runtime_state( trans, step_args.pop( "tool_state" ) )
                    step_errors = module.update_runtime_state( trans, state, step_args )
                if step_errors:
                    errors[step.id] = state.inputs["__errors__"] = step_errors   
            if 'run_workflow' in kwargs and not errors:
                # Run each step, connecting outputs to inputs
                outputs = odict()
                for i, step in enumerate( workflow.steps ):
                    if step.type == 'tool' or step.type is None:
                        tool = trans.app.toolbox.tools_by_id[ step.tool_id ]
                        input_values = step.state.inputs
                        # Connect up
                        def callback( input, value, prefixed_name, prefixed_label ):
                            if isinstance( input, DataToolParameter ):
                                if prefixed_name in step.input_connections_by_name:
                                    conn = step.input_connections_by_name[ prefixed_name ]
                                    return outputs[ conn.output_step.id ][ conn.output_name ]
                        visit_input_values( tool.inputs, step.state.inputs, callback )
                        # Execute it
                        outputs[ step.id ] = tool.execute( trans, step.state.inputs )
                    else:
                        outputs[ step.id ] = step.module.execute( trans, step.state )
                        
                return trans.fill_template( "workflow/run_complete.mako",
                                            workflow=stored,
                                            outputs=outputs )
        else:
            for step in workflow.steps:
                if step.type == 'tool' or step.type is None:
                    # Restore the tool state for the step
                    module = module_factory.from_workflow_step( trans, step )
                    # Any connected input needs to have value DummyDataset (these
                    # are not persisted so we need to do it every time)
                    module.add_dummy_datasets( connections=step.input_connections )                  
                    # Store state with the step
                    step.module = module
                    step.state = module.state
                    # Error dict
                    if step.tool_errors:
                        errors[step.id] = step.tool_errors
                else:
                    ## Non-tool specific stuff?
                    step.module = module_factory.from_workflow_step( trans, step )
                    step.state = step.module.get_runtime_state()
                # Connections by input name
                step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )
        # Render the form
        return trans.fill_template(
                    "workflow/run.mako", 
                    steps=workflow.steps,
                    workflow=stored,
                    errors=errors,
                    incoming=kwargs )
    
    @web.expose
    def configure_menu( self, trans, workflow_ids=None ):
        user = trans.get_user()
        if trans.request.method == "POST":
            if workflow_ids is None:
                workflow_ids = []
            elif type( workflow_ids ) != list:
                workflow_ids = [ workflow_ids ]
            sess = trans.sa_session
            # This explicit remove seems like a hack, need to figure out
            # how to make the association do it automatically.
            for m in user.stored_workflow_menu_entries:
                sess.delete( m )
            user.stored_workflow_menu_entries = []
            q = sess.query( model.StoredWorkflow )
            # To ensure id list is unique
            seen_workflow_ids = set()
            for id in workflow_ids:
                if id in seen_workflow_ids:
                    continue
                else:
                    seen_workflow_ids.add( id )
                m = model.StoredWorkflowMenuEntry()
                m.stored_workflow = q.get( id )
                user.stored_workflow_menu_entries.append( m )
            sess.flush()
            return trans.show_message( "Menu updated", refresh_frames=['tools'] )
        else:                
            user = trans.get_user()
            ids_in_menu = set( [ x.stored_workflow_id for x in user.stored_workflow_menu_entries ] )
            workflows = trans.sa_session.query( model.StoredWorkflow ) \
                .filter_by( user=user, deleted=False ) \
                .order_by( desc( model.StoredWorkflow.c.update_time ) ) \
                .all()
            shared_by_others = trans.sa_session \
                .query( model.StoredWorkflowUserShareAssociation ) \
                .filter_by( user=user ) \
                .filter( model.StoredWorkflow.c.deleted == False ) \
                .all()
            return trans.fill_template( "workflow/configure_menu.mako",
                                        workflows=workflows,
                                        shared_by_others=shared_by_others,
                                        ids_in_menu=ids_in_menu )
    
## ---- Utility methods -------------------------------------------------------

def get_UCIs_state( trans ):
    user = trans.get_user()
    instances = trans.sa_session.query( model.UCI ).filter_by( user=user ).filter( model.UCI.c.state != "deleted" ).all()
    insd = {} # instance name-state dict
    for inst in instances:
        insd[inst.name] = inst.state
        
    
def get_UCIs_time_ago( trans ):
    user = trans.get_user()
    instances = trans.sa_session.query( model.UCI ).filter_by( user=user ).all()
    intad = {} # instance name-time-ago dict
    for inst in instances:
        if inst.launch_time != None:
            intad[inst.name] = str(date.distance_of_time_in_words (inst.launch_time, date.datetime.utcnow() ) )
                
def get_stored_credentials( trans, id, check_ownership=True ):
    """
    Get StoredUserCredentials from the database by id, verifying ownership. 
    """
    # Check if 'id' is in int (i.e., it was called from this program) or
    #    it was passed from the web (in which case decode it)
    if not isinstance( id, int ):
        id = trans.security.decode_id( id )

    stored = trans.sa_session.query( model.CloudUserCredentials ).get( id )
    if not stored:
        error( "Credentials not found" )
    # Verify ownership
    user = trans.get_user()
    if not user:
        error( "Must be logged in to use the cloud." )
    if check_ownership and not( stored.user == user ):
        error( "Credentials are not owned by current user." )
    # Looks good
    return stored

def get_default_credentials( trans, check_ownership=True ):
    """
    Get a StoredUserCredntials from the database by 'default' setting, verifying ownership. 
    """
    user = trans.get_user()
    # Load credentials from database
    stored = trans.sa_session.query( model.CloudUserCredentials ) \
        .filter_by (user=user, defaultCred=True) \
        .first()

    return stored

def get_uci( trans, id, check_ownership=True ):
    """
    Get a UCI object from the database by id, verifying ownership. 
    """
    # Check if 'id' is in int (i.e., it was called from this program) or
    #    it was passed from the web (in which case decode it)
    if not isinstance( id, int ):
        id = trans.security.decode_id( id )

    live = trans.sa_session.query( model.UCI ).get( id )
    if not live:
        error( "Galaxy instance not found." )
    # Verify ownership
    user = trans.get_user()
    if not user:
        error( "Must be logged in to use the cloud." )
    if check_ownership and not( live.user == user ):
        error( "Instance is not owned by current user." )
    # Looks good
    return live

def get_mi( trans, size='m1.small' ):
    """
    Get appropriate machine image (mi) based on instance size.
    TODO: Dummy method - need to implement logic
        For valid sizes, see http://aws.amazon.com/ec2/instance-types/
    """
    return trans.app.model.CloudImage.filter(
        trans.app.model.CloudImage.table.c.id==2).first() 

def get_stores( trans, uci ):
    """
    Get stores objects that are connected to uci object
    """
    user = trans.get_user()
    stores = trans.sa_session.query( model.CloudStore ) \
            .filter_by( user=user, uci_id=uci.id ) \
            .all()
            
    return stores

def get_instances( trans, uci ):
    """
    Get objects of instances that are pending or running and are connected to uci object
    """
    user = trans.get_user()
    instances = trans.sa_session.query( model.CloudInstance ) \
            .filter_by( user=user, uci_id=uci.id ) \
            .filter( or_(model.CloudInstance.table.c.state=="running", model.CloudInstance.table.c.state=="pending" ) ) \
            .first()
            #.all() #TODO: return all but need to edit calling method(s) to handle list
            
    return instances

def get_cloud_instance( conn, instance_id ):
    """
    Returns a cloud instance representation of the instance id, i.e., cloud instance object that cloud API can be invoked on
    """
    # get_all_instances func. takes a list of desired instance id's, so create a list first
    idLst = list() 
    idLst.append( instance_id )
    # Retrieve cloud instance based on passed instance id. get_all_instances( idLst ) method returns reservation ID. Because
    # we are passing only 1 ID, we can retrieve only the first element of the returning list. Furthermore, because (for now!)
    # only 1 instance corresponds each individual reservation, grab only the first element of the returned list of instances.
    cloudInstance = conn.get_all_instances( [instance_id] )[0].instances[0]
    return cloudInstance

def get_connection( trans, credName ):
    """
    Establishes EC2 connection using user's default credentials
    """
    log.debug( '##### Establishing cloud connection.' )
    user = trans.get_user()
    creds = trans.sa_session.query( model.CloudUserCredentials ).filter_by( user=user, name=credName ).first()
    if creds:
        a_key = creds.access_key
        s_key = creds.secret_key
        # Amazon EC2
        #conn = EC2Connection( a_key, s_key )
        # Eucalyptus Public Cloud
        euca_region = RegionInfo( None, "eucalyptus", "mayhem9.cs.ucsb.edu" )
        conn = EC2Connection( aws_access_key_id=a_key, aws_secret_access_key=s_key, is_secure=False, port=8773, region=euca_region, path="/services/Eucalyptus" )
        return conn
    else:
        error( "You must specify default credentials before starting an instance." )
        return 0

def get_keypair_name( trans ):
    """
    Generate keypair using user's default credentials
    """
    conn = get_connection( trans )
    
    log.debug( "Getting user's keypair" )
    key_pair = conn.get_key_pair( 'galaxy-keypair' )
    
    try:
        return key_pair.name
    except AttributeError: # No keypair under this name exists so create it
        log.debug( 'No keypair found, creating keypair' )
        key_pair = conn.create_key_pair( 'galaxy-keypair' )
        # TODO: Store key_pair.material into instance table - this is the only time private key can be retrieved
        #    Actually, probably return key_pair to calling method and store name & key from there...
        
    return key_pair.name

def update_instance_state( trans, id ):
    """
    Update state of instances associated with given UCI id and store state in local database. Also update
    state of the given UCI.  
    """
    uci = get_uci( trans, id )
    # Get list of instances associated with given uci as they are stored in local database
    dbInstances = get_instances( trans, uci ) # TODO: handle list (currently only 1 instance can correspond to 1 UCI)
    oldState = dbInstances.state
    # Establish connection with cloud
    conn = get_connection( trans )
    # Get actual cloud instance object
    cloudInstance = get_cloud_instance( conn, dbInstances.instance_id )
    # Update instance status
    cloudInstance.update()
    dbInstances.state = cloudInstance.state
    log.debug( "Updating instance %s state; current state: %s" % ( str( cloudInstance ).split(":")[1], cloudInstance.state ) )
    # Update state of UCI (TODO: once more than 1 instance is assoc. w/ 1 UCI, this will be need to be updated differently) 
    uci.state = dbInstances.state
    # Persist
    session = trans.sa_session
    session.save_or_update( dbInstances )
    session.save_or_update( uci )
    session.flush()
    
    # If instance is now running, update/process instance (i.e., mount file system, start Galaxy, update DB with DNS)
    if oldState=="pending" and dbInstances.state=="running":
        update_instance( trans, dbInstances, cloudInstance, conn, uci )
    
    
def update_instance( trans, dbInstance, cloudInstance, conn, uci ):
    """
    Update instance: connect EBS volume, mount file system, start Galaxy, and update local DB w/ DNS info
    
    Keyword arguments:
    trans -- current transaction
    dbInstance -- object of 'instance' as it is stored in local database
    cloudInstance -- object of 'instance' as it resides in the cloud. Functions supported by the cloud API can be
        instantiated directly on this object.
    conn -- cloud connection object
    uci -- UCI object 
    """
    dbInstance.public_dns = cloudInstance.dns_name
    dbInstance.private_dns = cloudInstance.private_dns_name

    # Attach storage volume(s) to instance
    stores = get_stores( trans, uci )
    for i, store in enumerate( stores ):
        log.debug( "Attaching volume '%s' to instance '%s'." % ( store.volume_id, dbInstance.instance_id ) )
        mntDevice = '/dev/sdb'+str(i)
        volStat = conn.attach_volume( store.volume_id, dbInstance.instance_id, mntDevice )
        store.attach_time = datetime.utcnow()
        store.device = mntDevice
        store.i_id = dbInstance.instance_id
        store.status = volStat
        log.debug ( '***** volume status: %s' % volStat )
    
    # Wait until instances have attached and add file system
    
    
    
    # TODO: mount storage through ZFS
    # TODO: start Galaxy 
    
    # Persist
    session = trans.sa_session
    session.save_or_update( dbInstance )
    session.flush()

def attach_ordered_steps( workflow, steps ):
    ordered_steps = order_workflow_steps( steps )
    if ordered_steps:
        workflow.has_cycles = False
        for i, step in enumerate( ordered_steps ):
            step.order_index = i
            workflow.steps.append( step )
    else:
        workflow.has_cycles = True
        workflow.steps = steps

def edgelist_for_workflow_steps( steps ):
    """
    Create a list of tuples representing edges between `WorkflowSteps` based
    on associated `WorkflowStepConnection`s
    """
    edges = []
    steps_to_index = dict( ( step, i ) for i, step in enumerate( steps ) )
    for step in steps:
        edges.append( ( steps_to_index[step], steps_to_index[step] ) )
        for conn in step.input_connections:
            edges.append( ( steps_to_index[conn.output_step], steps_to_index[conn.input_step] ) )
    return edges

def order_workflow_steps( steps ):
    """
    Perform topological sort of the steps, return ordered or None
    """
    try:
        edges = edgelist_for_workflow_steps( steps )
        node_order = topsort( edges )
        return [ steps[i] for i in node_order ]
    except CycleError:
        return None
    
def order_workflow_steps_with_levels( steps ):
    try:
        return topsort_levels( edgelist_for_workflow_steps( steps ) )
    except CycleError:
        return None
    
class FakeJob( object ):
    """
    Fake job object for datasets that have no creating_job_associations,
    they will be treated as "input" datasets.
    """
    def __init__( self, dataset ):
        self.is_fake = True
        self.id = "fake_%s" % dataset.id
    
def get_job_dict( trans ):
    """
    Return a dictionary of Job -> [ Dataset ] mappings, for all finished
    active Datasets in the current history and the jobs that created them.
    """
    history = trans.get_history()
    # Get the jobs that created the datasets
    warnings = set()
    jobs = odict()
    for dataset in history.active_datasets:
        # FIXME: Create "Dataset.is_finished"
        if dataset.state in ( 'new', 'running', 'queued' ):
            warnings.add( "Some datasets still queued or running were ignored" )
            continue
        
        #if this hda was copied from another, we need to find the job that created the origial hda
        job_hda = dataset
        while job_hda.copied_from_history_dataset_association:
            job_hda = job_hda.copied_from_history_dataset_association
        
        if not job_hda.creating_job_associations:
            jobs[ FakeJob( dataset ) ] = [ ( None, dataset ) ]
        
        for assoc in job_hda.creating_job_associations:
            job = assoc.job
            if job in jobs:
                jobs[ job ].append( ( assoc.name, dataset ) )
            else:
                jobs[ job ] = [ ( assoc.name, dataset ) ]
    return jobs, warnings    

def cleanup_param_values( inputs, values ):
    """
    Remove 'Data' values from `param_values`, along with metadata cruft,
    but track the associations.
    """
    associations = []
    names_to_clean = []
    # dbkey is pushed in by the framework
    if 'dbkey' in values:
        del values['dbkey']
    root_values = values
    # Recursively clean data inputs and dynamic selects
    def cleanup( prefix, inputs, values ):
        for key, input in inputs.items():
            if isinstance( input, ( SelectToolParameter, DrillDownSelectToolParameter ) ):
                if input.is_dynamic:
                    values[key] = UnvalidatedValue( values[key] )
            if isinstance( input, DataToolParameter ):
                tmp = values[key]
                values[key] = None
                # HACK: Nested associations are not yet working, but we
                #       still need to clean them up so we can serialize
                # if not( prefix ):
                if tmp: #this is false for a non-set optional dataset
                    associations.append( ( tmp.hid, prefix + key ) )
                # Cleanup the other deprecated crap associated with datasets
                # as well. Worse, for nested datasets all the metadata is
                # being pushed into the root. FIXME: MUST REMOVE SOON
                key = prefix + key + "_"
                for k in root_values.keys():
                    if k.startswith( key ):
                        del root_values[k]            
            elif isinstance( input, Repeat ):
                group_values = values[key]
                for i, rep_values in enumerate( group_values ):
                    rep_index = rep_values['__index__']
                    prefix = "%s_%d|" % ( key, rep_index )
                    cleanup( prefix, input.inputs, group_values[i] )
            elif isinstance( input, Conditional ):
                group_values = values[input.name]
                current_case = group_values['__current_case__']
                prefix = "%s|" % ( key )
                cleanup( prefix, input.cases[current_case].inputs, group_values )
    cleanup( "", inputs, values )
    return associations





