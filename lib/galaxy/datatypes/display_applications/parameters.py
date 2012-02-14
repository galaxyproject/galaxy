#Contains parameters that are used in Display Applications
import logging, urllib
from galaxy.util import string_as_bool
from galaxy.util.bunch import Bunch
from galaxy.util.template import fill_template
from galaxy.web import url_for
import mimetypes

DEFAULT_DATASET_NAME = 'dataset'

class DisplayApplicationParameter( object ):
    """ Abstract Class for Display Application Parameters """
    
    type = None
    
    @classmethod
    def from_elem( cls, elem, link ):
        param_type = elem.get( 'type', None )
        assert param_type, 'DisplayApplicationParameter requires a type'
        return parameter_type_to_class[ param_type ]( elem, link )
    def __init__( self, elem, link ):
        self.name = elem.get( 'name', None )
        assert self.name, 'DisplayApplicationParameter requires a name'
        self.link = link
        self.url = elem.get( 'url', self.name ) #name used in url for display purposes defaults to name; e.g. want the form of file.ext, where a '.' is not allowed as python variable name/keyword
        self.mime_type = elem.get( 'mimetype', None )
        self.guess_mime_type = string_as_bool( elem.get( 'guess_mimetype', 'False' ) )
        self.viewable = string_as_bool( elem.get( 'viewable', 'False' ) ) #only allow these to be viewed via direct url when explicitly set to viewable
        self.strip = string_as_bool( elem.get( 'strip', 'False' ) )
        self.strip_https = string_as_bool( elem.get( 'strip_https', 'False' ) )
    def get_value( self, other_values, dataset_hash, user_hash, trans ):
        raise Exception, 'Unimplemented'
    def prepare( self, other_values, dataset_hash, user_hash, trans ):
        return self.get_value( other_values, dataset_hash, user_hash, trans )
    def ready( self, other_values ):
        return True
    def is_preparing( self, other_values ):
        return False
    def build_url( self, other_values ):
        return fill_template( self.url, context = other_values )

class DisplayApplicationDataParameter( DisplayApplicationParameter ):
    """ Parameter that returns a file_name containing the requested content """
    
    type = 'data'
    
    def __init__( self, elem, link ):
        DisplayApplicationParameter.__init__( self, elem, link )
        self.extensions = elem.get( 'format', None )
        if self.extensions:
            self.extensions = self.extensions.split( "," )
        self.metadata = elem.get( 'metadata', None )
        self.dataset = elem.get( 'dataset', DEFAULT_DATASET_NAME ) # 'dataset' is default name assigned to dataset to be displayed
        assert not ( self.extensions and self.metadata ), 'A format or a metadata can be defined for a DisplayApplicationParameter, but not both.'
        self.viewable = string_as_bool( elem.get( 'viewable', 'True' ) ) #data params should be viewable
        self.force_url_param = string_as_bool( elem.get( 'force_url_param', 'False' ) )
        self.force_conversion = string_as_bool( elem.get( 'force_conversion', 'False' ) )
    @property
    def formats( self ):
        if self.extensions:
            return tuple( map( type, map( self.link.display_application.datatypes_registry.get_datatype_by_extension, self.extensions ) ) )
        return None
    def _get_dataset_like_object( self, other_values ):
        #this returned object has file_name, state, and states attributes equivalent to a DatasetAssociation
        data = other_values.get( self.dataset, None )
        assert data, 'Base dataset could not be found in values provided to DisplayApplicationDataParameter'
        if isinstance( data, DisplayDataValueWrapper ):
            data = data.value
        if self.metadata:
            rval = getattr( data.metadata, self.metadata, None )
            assert rval, 'Unknown metadata name (%s) provided for dataset type (%s).' % ( self.metadata, data.datatype.__class__.name )
            return Bunch( file_name = rval.file_name, state = data.state, states = data.states, extension='data' )
        elif self.extensions and ( self.force_conversion or not isinstance( data.datatype, self.formats ) ):
            for ext in self.extensions:
                rval = data.get_converted_files_by_type( ext )
                if rval:
                    return rval
            assert data.find_conversion_destination( self.formats )[0] is not None, "No conversion path found for data param: %s" % self.name
            return None
        return data
    def get_value( self, other_values, dataset_hash, user_hash, trans ):
        data = self._get_dataset_like_object( other_values )
        if data:
            return DisplayDataValueWrapper( data, self, other_values, dataset_hash, user_hash, trans )
        return None
    def prepare( self, other_values, dataset_hash, user_hash, trans ):
        data = self._get_dataset_like_object( other_values )
        if not data and self.formats:
            data = other_values.get( self.dataset, None )
            trans.sa_session.refresh( data )
            #start conversion
            #FIXME: Much of this is copied (more than once...); should be some abstract method elsewhere called from here
            #find target ext
            target_ext, converted_dataset = data.find_conversion_destination( self.formats, converter_safe = True )
            if target_ext and not converted_dataset:
                if isinstance( data, DisplayDataValueWrapper ):
                    data = data.value
                new_data = data.datatype.convert_dataset( trans, data, target_ext, return_output = True, visible = False ).values()[0]
                new_data.hid = data.hid
                new_data.name = data.name
                trans.sa_session.add( new_data )
                assoc = trans.app.model.ImplicitlyConvertedDatasetAssociation( parent = data, file_type = target_ext, dataset = new_data, metadata_safe = False )
                trans.sa_session.add( assoc )
                trans.sa_session.flush()
            elif converted_dataset and converted_dataset.state == converted_dataset.states.ERROR:
                raise Exception, "Dataset conversion failed for data parameter: %s" % self.name
        return self.get_value( other_values, dataset_hash, user_hash, trans )
    def is_preparing( self, other_values ):
        value = self._get_dataset_like_object( other_values )
        if value and value.state in ( value.states.NEW, value.states.UPLOAD, value.states.QUEUED, value.states.RUNNING ):
            return True
        return False
    def ready( self, other_values ):
        value = self._get_dataset_like_object( other_values )
        if value: 
            if value.state == value.states.OK:
                return True
            elif value.state == value.states.ERROR:
                raise Exception( 'A data display parameter is in the error state: %s' % ( self.name ) )
        return False

class DisplayApplicationTemplateParameter( DisplayApplicationParameter ):
    """ Parameter that returns a string containing the requested content """
    
    type = 'template'
    
    def __init__( self, elem, link ):
        DisplayApplicationParameter.__init__( self, elem, link )
        self.text = elem.text
    def get_value( self, other_values, dataset_hash, user_hash, trans ):
        value = fill_template( self.text, context = other_values )
        if self.strip:
            value = value.strip()
        return DisplayParameterValueWrapper( value, self, other_values, dataset_hash, user_hash, trans )

parameter_type_to_class = { DisplayApplicationDataParameter.type:DisplayApplicationDataParameter, DisplayApplicationTemplateParameter.type:DisplayApplicationTemplateParameter }

class DisplayParameterValueWrapper( object ):
    ACTION_NAME = 'param'
    def __init__( self, value, parameter, other_values, dataset_hash, user_hash, trans ):
        self.value = value
        self.parameter = parameter
        self.other_values = other_values
        self.trans = trans
        self._dataset_hash = dataset_hash
        self._user_hash = user_hash
        self._url = self.parameter.build_url( self.other_values )
    def __str__( self ):
        return str( self.value )
    def mime_type( self ):
        if self.parameter.mime_type is not None:
            return self.parameter.mime_type
        if self.parameter.guess_mime_type:
            mime, encoding = mimetypes.guess_type( self._url )
            if not mime:
                mime = self.trans.app.datatypes_registry.get_mimetype_by_extension( ".".split( self._url )[ -1 ], None ) 
            if mime:
                return mime
        return 'text/plain'
    @property
    def url( self ):
        base_url = self.trans.request.base
        if self.parameter.strip_https and base_url[ : 5].lower() == 'https':
            base_url = "http%s" % base_url[ 5: ]
        return "%s%s" % ( base_url,
                          url_for( controller='/dataset',
                                   action="display_application",
                                   dataset_id=self._dataset_hash,
                                   user_id=self._user_hash,
                                   app_name=urllib.quote_plus( self.parameter.link.display_application.id ),
                                   link_name=urllib.quote_plus( self.parameter.link.id ),
                                   app_action=self.action_name,
                                   action_param=self._url ) )
    @property
    def action_name( self ):
        return self.ACTION_NAME
    @property
    def qp( self ):
        #returns quoted str contents
        return self.other_values[ 'qp' ]( str( self ) )
    def __getattr__( self, key ):
        return getattr( self.value, key )

class DisplayDataValueWrapper( DisplayParameterValueWrapper ):
    ACTION_NAME = 'data'
    def __str__( self ):
        #string of data param is filename
        return str( self.value.file_name )
    def mime_type( self ):
        if self.parameter.mime_type is not None:
            return self.parameter.mime_type
        if self.parameter.guess_mime_type:
            mime, encoding = mimetypes.guess_type( self._url )
            if not mime:
                mime = self.trans.app.datatypes_registry.get_mimetype_by_extension( ".".split( self._url )[ -1 ], None ) 
            if mime:
                return mime
        return self.other_values[ DEFAULT_DATASET_NAME ].get_mime()
    @property
    def action_name( self ):
        if self.parameter.force_url_param:
            return super( DisplayParameterValueWrapper, self ).action_name
        return self.ACTION_NAME
    @property
    def qp( self ):
        #returns quoted url contents
        return self.other_values[ 'qp' ]( self.url )
