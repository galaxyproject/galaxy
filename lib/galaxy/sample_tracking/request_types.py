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
    def new( self, name, request_form, sample_form, description=None, hostname=None, username=None, password=None, rename_dataset=None, data_dir=None, sample_states = None ):
        """
        Return new RequestType.
        """
        assert rename_dataset in self.rename_dataset_options.values(), 'Invalid RequestType type (%s not in %s)' % ( rename_dataset, self.rename_dataset_options.values() )
        assert name, 'RequestType requires a name'
        if description is None:
            description = ''
        if hostname is None:
            hostname = ''
        if username is None:
            username = ''            
        if password is None:
            password = ''
        if data_dir is None:
            data_dir = ''
        datatx_info = dict( host=hostname, username=username, password=password, data_dir=data_dir, rename_dataset=rename_dataset )
        
        return RequestType( name=name, desc=description, request_form=request_form, sample_form=sample_form, datatx_info=datatx_info )
    def from_elem( self, elem, request_form, sample_form ):
        """
        Return RequestType created from an xml string.
        """
        name = elem.get( 'name', '' )
        description = elem.get( 'description', '' )
        #login info
        login_info = elem.find( 'login' )
        if login_info is not None:
            hostname = login_info.get( 'hostname', None )
            username = login_info.get( 'username', None )
            password = login_info.get( 'password', None )
            rename_dataset = login_info.get( 'rename_dataset', None )
            data_dir = login_info.get( 'data_directory', None )
        else:
            hostname = username = password = rename_dataset = data_dir = None
        if rename_dataset not in self.rename_dataset_options:
            rename_dataset = 'no' #default setting?
        rename_dataset= self.rename_dataset_options.get( rename_dataset )
        rval = self.new( name, request_form, sample_form, description=description, hostname=hostname, username=username, password=password, rename_dataset=rename_dataset, data_dir=data_dir )
        #load states
        sample_states_elem = elem.find( 'sample_states' )
        if sample_states_elem:
            for sample_state_elem in sample_states_elem.findall( 'state' ):
                sample_state = self.sample_state_factory.from_elem( rval, sample_state_elem )
        return rval

request_type_factory = RequestTypeFactory( sample_state_factory, RENAME_DATASET_OPTIONS )
