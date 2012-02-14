#Contains objects for using external display applications
import logging, urllib
from galaxy.util import parse_xml, string_as_bool
from galaxy.util.odict import odict
from galaxy.util.template import fill_template
from galaxy.web import url_for
from parameters import DisplayApplicationParameter, DEFAULT_DATASET_NAME
from urllib import quote_plus
from util import encode_dataset_user
from copy import deepcopy

log = logging.getLogger( __name__ )

#Any basic functions that we want to provide as a basic part of parameter dict should be added to this dict
BASE_PARAMS = { 'qp': quote_plus, 'url_for':url_for } #url_for has route memory...

class DisplayApplicationLink( object ):
    @classmethod
    def from_elem( cls, elem, display_application, other_values = None ):
        rval = DisplayApplicationLink( display_application )
        rval.id = elem.get( 'id', None )
        assert rval.id, 'Link elements require a id.'
        rval.name = elem.get( 'name', rval.id )
        rval.url = elem.find( 'url' )
        assert rval.url is not None, 'A url element must be provided for link elements.'
        rval.other_values = other_values
        rval.filters = elem.findall( 'filter' )
        for param_elem in elem.findall( 'param' ):
            param = DisplayApplicationParameter.from_elem( param_elem, rval )
            assert param, 'Unable to load parameter from element: %s' % param_elem
            rval.parameters[ param.name ] = param
            rval.url_param_name_map[ param.url ] = param.name
        return rval
    def __init__( self, display_application ):
        self.display_application = display_application
        self.parameters = odict() #parameters are populated in order, allowing lower listed ones to have values of higher listed ones
        self.url_param_name_map = {}
        self.url = None
        self.id = None
        self.name = None
    def get_display_url( self, data, trans ):
        dataset_hash, user_hash = encode_dataset_user( trans, data, None )
        return url_for( controller='/dataset',
                        action="display_application",
                        dataset_id=dataset_hash,
                        user_id=user_hash,
                        app_name=urllib.quote_plus( self.display_application.id ),
                        link_name=urllib.quote_plus( self.id ),
                        app_action=None )
    def get_inital_values( self, data, trans ):
        if self.other_values:
            rval = odict( self.other_values )
        else:
            rval = odict()
        rval.update( { 'BASE_URL': trans.request.base, 'APP': trans.app } ) #trans automatically appears as a response, need to add properties of trans that we want here
        for key, value in  BASE_PARAMS.iteritems(): #add helper functions/variables
            rval[ key ] = value
        rval[ DEFAULT_DATASET_NAME ] = data #always have the display dataset name available
        return rval
    def build_parameter_dict( self, data, dataset_hash, user_hash, trans ):
        other_values = self.get_inital_values( data, trans )
        other_values[ 'DATASET_HASH' ] = dataset_hash
        other_values[ 'USER_HASH' ] = user_hash
        for name, param in self.parameters.iteritems():
            assert name not in other_values, "The display parameter '%s' has been defined more than once." % name
            if param.ready( other_values ):
                other_values[ name ] = param.get_value( other_values, dataset_hash, user_hash, trans )#subsequent params can rely on this value
            else:
                other_values[ name ] = None
                return False, other_values #need to stop here, next params may need this value
        return True, other_values #we built other_values, lets provide it as well, or else we will likely regenerate it in the next step
    def filter_by_dataset( self, data, trans ):
        context = self.get_inital_values( data, trans )
        for filter_elem in self.filters:
            if fill_template( filter_elem.text, context = context ) != filter_elem.get( 'value', 'True' ):
                return False
        return True

class DynamicDisplayApplicationBuilder( object ):
    @classmethod
    def __init__( self, elem, display_application ):
        rval = []
        filename = elem.get( 'from_file', None )
        assert filename is not None, 'Filename and id attributes required for dynamic_links'
        skip_startswith = elem.get( 'skip_startswith', None )
        separator = elem.get( 'separator', '\t' )
        id_col = int( elem.get( 'id', None ) )
        name_col = int( elem.get( 'name', id_col ) )
        dynamic_params = {}
        max_col = max( id_col, name_col )
        for dynamic_param in elem.findall( 'dynamic_param' ):
            name = dynamic_param.get( 'name' )
            value = int( dynamic_param.get( 'value' ) )
            split = string_as_bool( dynamic_param.get( 'split', False ) )
            param_separator =  dynamic_param.get( 'separator', ',' )
            max_col = max( max_col, value )
            dynamic_params[name] = { 'column': value, 'split': split, 'separator': param_separator }
        for line in open( filename ):
            if not skip_startswith or not line.startswith( skip_startswith ):
                line = line.rstrip( '\n\r' )
                fields = line.split( separator )
                if len( fields ) >= max_col:
                    new_elem = deepcopy( elem )
                    new_elem.set( 'id', fields[id_col] )
                    new_elem.set( 'name', fields[name_col] )
                    dynamic_values = {}
                    for key, attributes in dynamic_params.iteritems():
                        value = fields[ attributes[ 'column' ] ]
                        if attributes['split']:
                            value = value.split( attributes['separator'] )
                        dynamic_values[key] = value
                    #now populate
                    rval.append( DisplayApplicationLink.from_elem( new_elem, display_application, other_values = dynamic_values ) )
        self.links = rval
    def __iter__( self ):
        return iter( self.links )

class PopulatedDisplayApplicationLink( object ):
    def __init__( self, display_application_link, data, dataset_hash, user_hash, trans ):
        self.link = display_application_link
        self.data = data
        self.dataset_hash = dataset_hash
        self.user_hash = user_hash
        self.trans = trans 
        self.ready, self.parameters = self.link.build_parameter_dict( self.data, self.dataset_hash, self.user_hash, trans )
    def display_ready( self ):
        return self.ready
    def get_param_value( self, name ):
        value = None
        if self.ready:
            value = self.parameters.get( name, None )
            assert value, 'Unknown parameter requested'
        return value
    def preparing_display( self ):
        if not self.ready:
            return self.link.parameters[ self.parameters.keys()[ -1 ] ].is_preparing( self.parameters )
        return False
    def prepare_display( self ):
        if not self.ready and not self.preparing_display():
            other_values = self.parameters
            for name, param in self.link.parameters.iteritems():
                if other_values.keys()[ -1 ] == name: #found last parameter to be populated
                    value = param.prepare( other_values, self.dataset_hash, self.user_hash, self.trans )
                    if value is None:
                        return #we can go no further until we have a value for this parameter
                    other_values[ name ] = value
    def display_url( self ):
        assert self.display_ready(), 'Display is not yet ready, cannot generate display link'
        return fill_template( self.link.url.text, context = self.parameters )
    def get_param_name_by_url( self, url ):
        for name, parameter in self.link.parameters.iteritems():
            if parameter.build_url( self.parameters ) == url:
                return name
        raise ValueError( "Unknown URL parameter name provided: %s" % url )

class DisplayApplication( object ):
    @classmethod
    def from_file( cls, filename, datatypes_registry ):
        return cls.from_elem( parse_xml( filename ).getroot(), datatypes_registry )
    @classmethod
    def from_elem( cls, elem, datatypes_registry ):
        display_id = elem.get( 'id', None )
        assert display_id, "ID tag is required for a Display Application"
        name = elem.get( 'name', display_id )
        version = elem.get( 'version', None )
        rval = DisplayApplication( display_id, name, datatypes_registry, version )
        for link_elem in elem.findall( 'link' ):
            link = DisplayApplicationLink.from_elem( link_elem, rval )
            if link:
                rval.links[ link.id ] = link
        for dynamic_links in elem.findall( 'dynamic_links' ):
            for link in DynamicDisplayApplicationBuilder( dynamic_links, rval ):
                rval.links[ link.id ] = link
        return rval
    def __init__( self, display_id, name, datatypes_registry, version = None ):
        self.id = display_id
        self.name = name
        self.datatypes_registry = datatypes_registry
        if version is None:
            version = "1.0.0"
        self.version = version
        self.links = odict()
    def get_link( self, link_name, data, dataset_hash, user_hash, trans ):
        #returns a link object with data knowledge to generate links
        return PopulatedDisplayApplicationLink( self.links[ link_name ], data, dataset_hash, user_hash, trans )
    def filter_by_dataset( self, data, trans ):
        filtered = DisplayApplication( self.id, self.name, self.datatypes_registry, version = self.version )
        for link_name, link_value in self.links.iteritems():
            if link_value.filter_by_dataset( data, trans ):
                filtered.links[link_name] = link_value
        return filtered
