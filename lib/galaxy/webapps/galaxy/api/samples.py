"""
API operations for samples in the Galaxy sample tracking system.
"""
import logging
from galaxy import util
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.util.bunch import Bunch

log = logging.getLogger( __name__ )

class SamplesAPIController( BaseAPIController ):
    update_types = Bunch( SAMPLE = [ 'sample_state', 'run_details' ],
                          SAMPLE_DATASET = [ 'sample_dataset_transfer_status' ] )
    update_type_values = []
    for k, v in update_types.items():
        update_type_values.extend( v )
    @web.expose_api
    def index( self, trans, **kwd ):
        """
        GET /api/requests/{encoded_request_id}/samples
        Displays a collection (list) of sample of a sequencing request.
        """
        try:
            request_id = trans.security.decode_id( kwd[ 'request_id' ] )
        except TypeError:
            trans.response.status = 400
            return "Malformed  request id ( %s ) specified, unable to decode." % str( encoded_request_id )
        try:
            request = trans.sa_session.query( trans.app.model.Request ).get( request_id )
        except:
            request = None
        if not request or not ( trans.user_is_admin() or request.user.id == trans.user.id ):
            trans.response.status = 400
            return "Invalid request id ( %s ) specified." % str( request_id )
        rval = []
        for sample in request.samples:
            item = sample.to_dict()
            item['url'] = url_for( 'samples',
                                   request_id=trans.security.encode_id( request_id ),
                                   id=trans.security.encode_id( sample.id ) )
            item['id'] = trans.security.encode_id( item['id'] )
            rval.append( item )
        return rval
    @web.expose_api
    def update( self, trans, id, payload, **kwd ):
        """
        PUT /api/samples/{encoded_sample_id}
        Updates a sample or objects related ( mapped ) to a sample.
        """
        update_type = None
        if 'update_type' not in payload:
            trans.response.status = 400
            return "Missing required 'update_type' parameter, consult the API documentation for help."
        else:
            update_type = payload.pop( 'update_type' )
        if update_type not in self.update_type_values:
            trans.response.status = 400
            return "Invalid value for 'update_type' parameter (%s) specified, consult the API documentation for help." % update_type
        sample_id = util.restore_text( id )
        try:
            decoded_sample_id = trans.security.decode_id( sample_id )
        except TypeError:
            trans.response.status = 400
            return "Malformed sample_id (%s) specified, unable to decode." % str( sample_id )
        try:
            sample = trans.sa_session.query( trans.app.model.Sample ).get( decoded_sample_id )
        except:
            sample = None
        if not sample:
            trans.response.status = 400
            return "Invalid sample id ( %s ) specified." % str( sample_id )
        if not trans.user_is_admin():
            trans.response.status = 403
            return "You are not authorized to update samples."
        requests_admin_controller = trans.webapp.controllers[ 'requests_admin' ]
        if update_type == 'run_details':
            deferred_plugin = payload.pop( 'deferred_plugin', None )
            if deferred_plugin:
                try:
                    trans.app.job_manager.deferred_job_queue.plugins[deferred_plugin].create_job( trans, sample=sample, **payload )
                except:
                    log.exception( 'update() called with a deferred job plugin (%s) but creating the deferred job failed:' % deferred_plugin )
            status, output = requests_admin_controller.edit_template_info( trans,
                                                                           cntrller='api',
                                                                           item_type='sample',
                                                                           form_type=trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE,
                                                                           sample_id=sample_id,
                                                                           **payload )
            return status, output
        elif update_type == 'sample_state':
            return self.__update_sample_state( trans, sample, sample_id, **payload )
        elif update_type == 'sample_dataset_transfer_status':
            # update sample_dataset transfer status
            return self.__update_sample_dataset_status( trans, **payload )

    def __update_sample_state( self, trans, sample, encoded_sample_id, **payload ):
        # only admin user may update sample state in Galaxy sample tracking
        if not trans.user_is_admin():
            trans.response.status = 403
            return "only an admin user may update sample state in Galaxy sample tracking."
        if 'new_state' not in payload:
            trans.response.status = 400
            return "Missing required parameter: 'new_state'."
        new_state_name = payload.pop( 'new_state' )
        comment = payload.get( 'comment', '' )
        # check if the new state is a valid sample state
        possible_states = sample.request.type.states
        new_state = None
        for state in possible_states:
            if state.name == new_state_name:
                new_state = state
        if not new_state:
            trans.response.status = 400
            return "Invalid sample state requested ( %s )." % new_state_name
        requests_common_cntrller = trans.webapp.controllers[ 'requests_common' ]
        status, output = requests_common_cntrller.update_sample_state( trans=trans,
                                                                       cntrller='api',
                                                                       sample_ids=[ encoded_sample_id ],
                                                                       new_state=new_state,
                                                                       comment=comment )
        return status, output
    def __update_sample_dataset_status( self, trans, **payload ):
        # only admin user may transfer sample datasets in Galaxy sample tracking
        if not trans.user_is_admin():
            trans.response.status = 403
            return "Only an admin user may transfer sample datasets in Galaxy sample tracking and thus update transfer status."
        if 'sample_dataset_ids' not in payload or 'new_status' not in payload:
            trans.response.status = 400
            return "Missing one or more required parameters: 'sample_dataset_ids' and 'new_status'."
        sample_dataset_ids = payload.pop( 'sample_dataset_ids' )
        new_status = payload.pop( 'new_status' )
        error_msg = payload.get( 'error_msg', '' )
        requests_admin_cntrller = trans.webapp.controllers[ 'requests_admin' ]
        status, output = requests_admin_cntrller.update_sample_dataset_status( trans=trans,
                                                                               cntrller='api',
                                                                               sample_dataset_ids=sample_dataset_ids,
                                                                               new_status=new_status,
                                                                               error_msg=error_msg )
        return status, output

