"""
RequestType
"""
import logging
from galaxy.model import RequestType
from sample import sample_state_factory

RENAME_DATASET_OPTIONS = dict( [ ( f_type.lower(), f_descript ) for f_type, f_descript in RequestType.rename_dataset_options.items() ] )

class RequestTypeFactory( object ):
    def __init__( self, sample_state_factory, rename_dataset_options ):
        self.sample_state_factory = sample_state_factory
        self.rename_dataset_options = rename_dataset_options
    def new( self, name, request_form, sample_form, external_service, description=None, sample_states = None ):
        """Return new RequestType."""
        assert name, 'RequestType requires a name'
        return RequestType( name=name, desc=description, request_form=request_form, sample_form=sample_form, external_service=external_service )
    def from_elem( self, elem, request_form, sample_form, external_service ):
        """Return RequestType created from an xml string."""
        name = elem.get( 'name', '' )
        description = elem.get( 'description', '' )
        rval = self.new( name, request_form, sample_form, external_service=external_service, description=description )
        #load states
        sample_states_elem = elem.find( 'sample_states' )
        if sample_states_elem:
            for sample_state_elem in sample_states_elem.findall( 'state' ):
                sample_state = self.sample_state_factory.from_elem( rval, sample_state_elem )
        return rval

request_type_factory = RequestTypeFactory( sample_state_factory, RENAME_DATASET_OPTIONS )
