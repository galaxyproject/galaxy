"""
API operations for samples in the Galaxy sample tracking system.
"""
import logging
from galaxy import util
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.util.bunch import Bunch

log = logging.getLogger( __name__ )

class SamplesAPIController( BaseController ):
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
            item = sample.get_api_value()
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
        if not trans.user_is_admin():
            trans.response.status = 403
            return "You are not authorized to update samples."
        requests_admin_controller = trans.webapp.controllers[ 'requests_admin' ]
        if update_type == 'run_details':
            status, output = requests_admin_controller.edit_template_info( trans,
                                                                           cntrller='api',
                                                                           item_type='sample',
                                                                           form_type=trans.model.FormDefinition.types.RUN_DETAILS_TEMPLATE,
                                                                           sample_id=sample_id,
                                                                           **payload )
            return status, output
