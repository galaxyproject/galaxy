import logging
from galaxy import web
from galaxy.model import ExternalService, Sample
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger( __name__ )

class_name_to_class = {}

for model_class in [Sample]:
    class_name_to_class[ model_class.__name__ ] = model_class

class ExternalServiceController( BaseUIController ):
    @web.expose
    @web.require_admin
    def access_action( self, trans, external_service_action, item, item_type, **kwd ):
        if item_type in class_name_to_class:
            item_type = class_name_to_class.get( item_type )
            item = item_type.get( item )
            external_service_action_parsed = external_service_action.split( '|' )
            populated_external_service = ExternalService.get( external_service_action_parsed.pop( 0 ) ).populate_actions( trans, item )
            populated_action = populated_external_service.perform_action_by_name( external_service_action_parsed )
            results = populated_action.handle_results( trans )
            return results
        else:
            raise 'unknown item class type'
