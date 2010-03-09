"""
Constructs for grouping tool parameters
"""

from basic import ToolParameter
from galaxy.util.expressions import ExpressionContext

import logging
log = logging.getLogger( __name__ )

import StringIO, os, urllib
from galaxy.datatypes import sniff
from galaxy.util.bunch import Bunch
from galaxy.util.odict import odict
from galaxy.util import json

class Group( object ):
    def __init__( self ):
        self.name = None
    def value_to_basic( self, value, app ):
        """
        Convert value to a (possibly nested) representation using only basic
        types (dict, list, tuple, str, unicode, int, long, float, bool, None)
        """
        return value
    def value_from_basic( self, value, app, ignore_errors=False ):
        """
        Convert a basic representation as produced by `value_to_basic` back
        into the preferred value form.
        """
        return value
    def get_initial_value( self, trans, context ):
        """
        Return the initial state/value for this group
        """
        raise TypeError( "Not implemented" )
        
class Repeat( Group ):
    type = "repeat"
    def __init__( self ):
        Group.__init__( self )
        self.title = None
        self.inputs = None
    @property
    def title_plural( self ):
        if self.title.endswith( "s" ):
            return self.title
        else:
            return self.title + "s"
    def label( self ):
        return "Repeat (%s)" % self.title
    def value_to_basic( self, value, app ):
        rval = []
        for d in value:
            rval_dict = {}
            # Propogate __index__
            if '__index__' in d:
                rval_dict['__index__'] = d['__index__']
            for input in self.inputs.itervalues():
                rval_dict[ input.name ] = input.value_to_basic( d[input.name], app )
            rval.append( rval_dict )
        return rval
    def value_from_basic( self, value, app, ignore_errors=False ):
        rval = []
        for i, d in enumerate( value ):
            rval_dict = {}
            # If the special __index__ key is not set, create it (for backward
            # compatibility)
            rval_dict['__index__'] = d.get( '__index__', i )
            # Restore child inputs
            for input in self.inputs.itervalues():
                if ignore_errors and input.name not in d:
                    # If we do not have a value, and are ignoring errors, we simply
                    # do nothing. There will be no value for the parameter in the
                    # conditional's values dictionary.     
                    pass
                else:
                    rval_dict[ input.name ] = input.value_from_basic( d[input.name], app, ignore_errors )
            rval.append( rval_dict )
        return rval 
    def visit_inputs( self, prefix, value, callback ):
        for i, d in enumerate( value ):
            for input in self.inputs.itervalues():
                new_prefix = prefix + "%s_%d|" % ( self.name, i )
                if isinstance( input, ToolParameter ):
                    callback( new_prefix, input, d[input.name], parent = d )
                else:
                    input.visit_inputs( new_prefix, d[input.name], callback )
    def get_initial_value( self, trans, context ):
        return []

class UploadDataset( Group ):
    type = "upload_dataset"
    def __init__( self ):
        Group.__init__( self )
        self.title = None
        self.inputs = None
        self.file_type_name = 'file_type'
        self.default_file_type = 'txt'
        self.file_type_to_ext = { 'auto':self.default_file_type }
        self.metadata_ref = 'files_metadata'
    def get_file_type( self, context ):
        return context.get( self.file_type_name, self.default_file_type )
    def get_datatype_ext( self, trans, context ):
        ext = self.get_file_type( context )
        if ext in self.file_type_to_ext:
            ext = self.file_type_to_ext[ext] #when using autodetect, we will use composite info from 'text', i.e. only the main file
        return ext
    def get_datatype( self, trans, context ):
        ext = self.get_datatype_ext( trans, context )
        return trans.app.datatypes_registry.get_datatype_by_extension( ext )
    @property
    def title_plural( self ):
        if self.title.endswith( "s" ):
            return self.title
        else:
            return self.title + "s"
    def group_title( self, context ):
        return "%s (%s)" % ( self.title, context.get( self.file_type_name, self.default_file_type ) )
    def title_by_index( self, trans, index, context ):
        d_type = self.get_datatype( trans, context )
        for i, ( composite_name, composite_file ) in enumerate( d_type.writable_files.iteritems() ):
            if i == index:
                rval = composite_name
                if composite_file.description:
                    rval = "%s (%s)" % ( rval, composite_file.description )
                if composite_file.optional:
                    rval = "%s [optional]" % rval
                return rval
        return None
    def value_to_basic( self, value, app ):
        rval = []
        for d in value:
            rval_dict = {}
            # Propogate __index__
            if '__index__' in d:
                rval_dict['__index__'] = d['__index__']
            for input in self.inputs.itervalues():
                rval_dict[ input.name ] = input.value_to_basic( d[input.name], app )
            rval.append( rval_dict )
        return rval
    def value_from_basic( self, value, app, ignore_errors=False ):
        rval = []
        for i, d in enumerate( value ):
            rval_dict = {}
            # If the special __index__ key is not set, create it (for backward
            # compatibility)
            rval_dict['__index__'] = d.get( '__index__', i )
            # Restore child inputs
            for input in self.inputs.itervalues():
                if ignore_errors and input.name not in d: #this wasn't tested
                    rval_dict[ input.name ] = input.get_initial_value( None, d )
                else:
                    rval_dict[ input.name ] = input.value_from_basic( d[input.name], app, ignore_errors )
            rval.append( rval_dict )
        return rval 
    def visit_inputs( self, prefix, value, callback ):
        for i, d in enumerate( value ):
            for input in self.inputs.itervalues():
                new_prefix = prefix + "%s_%d|" % ( self.name, i )
                if isinstance( input, ToolParameter ):
                    callback( new_prefix, input, d[input.name], parent = d )
                else:
                    input.visit_inputs( new_prefix, d[input.name], callback )
    def get_initial_value( self, trans, context ):
        d_type = self.get_datatype( trans, context )
        rval = []
        for i, ( composite_name, composite_file ) in enumerate( d_type.writable_files.iteritems() ):
            rval_dict = {}
            rval_dict['__index__'] = i # create __index__
            for input in self.inputs.itervalues():
                rval_dict[ input.name ] = input.get_initial_value( trans, context ) #input.value_to_basic( d[input.name], app )
            rval.append( rval_dict )
        return rval
    def get_uploaded_datasets( self, trans, context, override_name = None, override_info = None ):
        def get_data_file_filename( data_file, override_name = None, override_info = None ):
            dataset_name = override_name
            dataset_info = override_info
            def get_file_name( file_name ):
                file_name = file_name.split( '\\' )[-1]
                file_name = file_name.split( '/' )[-1]
                return file_name
            try:
                # Use the existing file
                if not dataset_name and 'filename' in data_file:
                    dataset_name = get_file_name( data_file['filename'] )
                if not dataset_info:
                    dataset_info = 'uploaded file'
                return Bunch( type='file', path=data_file['local_filename'], name=get_file_name( data_file['filename'] ) )
                #return 'file', data_file['local_filename'], get_file_name( data_file.filename ), dataset_name, dataset_info
            except:
                # The uploaded file should've been persisted by the upload tool action
                return Bunch( type=None, path=None, name=None )
                #return None, None, None, None, None
        def get_url_paste_urls_or_filename( group_incoming, override_name = None, override_info = None ):
            filenames = []
            url_paste_file = group_incoming.get( 'url_paste', None )
            if url_paste_file is not None:
                url_paste = open( url_paste_file, 'r' ).read( 1024 )
                if url_paste.lstrip().lower().startswith( 'http://' ) or url_paste.lstrip().lower().startswith( 'ftp://' ):
                    url_paste = url_paste.replace( '\r', '' ).split( '\n' )
                    for line in url_paste:
                        line = line.strip()
                        if line:
                            if not line.lower().startswith( 'http://' ) and not line.lower().startswith( 'ftp://' ):
                                continue # non-url line, ignore
                            precreated_name = line
                            dataset_name = override_name
                            if not dataset_name:
                                dataset_name = line
                            dataset_info = override_info
                            if not dataset_info:
                                dataset_info = 'uploaded url'
                            yield Bunch( type='url', path=line, name=precreated_name )
                            #yield ( 'url', line, precreated_name, dataset_name, dataset_info )
                else:
                    dataset_name = dataset_info = precreated_name = 'Pasted Entry' #we need to differentiate between various url pastes here
                    if override_name:
                        dataset_name = override_name
                    if override_info:
                        dataset_info = override_info
                    yield Bunch( type='file', path=url_paste_file, name=precreated_name )
                    #yield ( 'file', url_paste_file, precreated_name, dataset_name, dataset_info )
        def get_one_filename( context ):
            data_file = context['file_data']
            url_paste = context['url_paste']
            name = context.get( 'NAME', None )
            info = context.get( 'INFO', None )
            warnings = []
            space_to_tab = False 
            if context.get( 'space_to_tab', None ) not in ["None", None]:
                space_to_tab = True
            file_bunch = get_data_file_filename( data_file, override_name = name, override_info = info )
            if file_bunch.path and url_paste:
                if url_paste.strip():
                    warnings.append( "All file contents specified in the paste box were ignored." )
            else: #we need to use url_paste
                for file_bunch in get_url_paste_urls_or_filename( context, override_name = name, override_info = info ):
                    if file_bunch.path:
                        break
            return file_bunch, warnings
        def get_filenames( context ):
            rval = []
            data_file = context['file_data']
            url_paste = context['url_paste']
            name = context.get( 'NAME', None )
            info = context.get( 'INFO', None )
            space_to_tab = False
            if context.get( 'space_to_tab', None ) not in ["None", None]:
                space_to_tab = True
            warnings = []
            file_bunch = get_data_file_filename( data_file, override_name = name, override_info = info )
            if file_bunch.path:
                file_bunch.space_to_tab = space_to_tab
                rval.append( file_bunch )
            for file_bunch in get_url_paste_urls_or_filename( context, override_name = name, override_info = info ):
                if file_bunch.path:
                    file_bunch.space_to_tab = space_to_tab
                    rval.append( file_bunch )
            return rval
        file_type = self.get_file_type( context )
        d_type = self.get_datatype( trans, context )
        dbkey = context.get( 'dbkey', None )
        writable_files = d_type.writable_files
        writable_files_offset = 0
        groups_incoming = [ None for filename in writable_files ]
        for group_incoming in context.get( self.name, [] ):
            i = int( group_incoming['__index__'] )
            groups_incoming[ i ] = group_incoming
        if d_type.composite_type is not None:
            #handle uploading of composite datatypes
            #Only one Dataset can be created
            dataset = Bunch()
            dataset.type = 'composite'
            dataset.file_type = file_type
            dataset.dbkey = dbkey
            dataset.datatype = d_type
            dataset.warnings = []
            dataset.metadata = {}
            dataset.composite_files = {}
            #load metadata
            files_metadata = context.get( self.metadata_ref, {} )
            for meta_name, meta_spec in d_type.metadata_spec.iteritems():
                if meta_spec.set_in_upload:
                    if meta_name in files_metadata:
                        dataset.metadata[ meta_name ] = files_metadata[ meta_name ]
            dataset_name = None
            dataset_info = None
            if dataset.datatype.composite_type == 'auto_primary_file':
                #replace sniff here with just creating an empty file
                temp_name, is_multi_byte = sniff.stream_to_file( StringIO.StringIO( d_type.generate_primary_file( dataset ) ), prefix='upload_auto_primary_file' )
                dataset.primary_file = temp_name
                dataset.space_to_tab = False
                dataset.precreated_name = dataset.name = 'Uploaded Composite Dataset (%s)' % ( file_type )
            else:
                file_bunch, warnings = get_one_filename( groups_incoming[ 0 ] )
                if dataset.datatype.composite_type:
                    precreated_name = 'Uploaded Composite Dataset (%s)' % ( file_type )
                writable_files_offset = 1
                dataset.primary_file = file_bunch.path
                dataset.space_to_tab = file_bunch.space_to_tab
                dataset.precreated_name = file_bunch.precreated_name
                dataset.name = file_bunch.precreated_name
                dataset.warnings.extend( file_bunch.warnings )
            if dataset.primary_file is None:#remove this before finish, this should create an empty dataset
                raise Exception( 'No primary dataset file was available for composite upload' )
            keys = [ value.name for value in writable_files.values() ]
            for i, group_incoming in enumerate( groups_incoming[ writable_files_offset : ] ):
                key = keys[ i + writable_files_offset ]
                if group_incoming is None and not writable_files[ writable_files.keys()[ keys.index( key ) ] ].optional:
                    dataset.warnings.append( "A required composite file (%s) was not specified." % ( key ) )
                    dataset.composite_files[ key ] = None
                else:
                    file_bunch, warnings = get_one_filename( group_incoming )
                    if file_bunch.path:
                        dataset.composite_files[ key ] = file_bunch.__dict__
                    else:
                        dataset.composite_files[ key ] = None
                        if not writable_files[ writable_files.keys()[ keys.index( key ) ] ].optional:
                            dataset.warnings.append( "A required composite file (%s) was not specified." % ( key ) )
            return [ dataset ]
        else:
            datasets = get_filenames( context[ self.name ][0] )
            rval = []
            for dataset in datasets:
                dataset.file_type = file_type
                dataset.datatype = d_type
                dataset.ext = self.get_datatype_ext( trans, context )
                dataset.dbkey = dbkey
                rval.append( dataset )
            return rval

class Conditional( Group ):
    type = "conditional"
    def __init__( self ):
        Group.__init__( self )
        self.test_param = None
        self.cases = []
        self.value_ref = None
        self.value_ref_in_group = True #When our test_param is not part of the conditional Group, this is False
    @property
    def label( self ):
        return "Conditional (%s)" % self.name
    def get_current_case( self, value, trans ):
        # Convert value to user representation
        str_value = self.test_param.filter_value( value, trans )
        # Find the matching case
        for index, case in enumerate( self.cases ):
            if str_value == case.value:
                return index
        raise Exception( "No case matched value:", self.name, str_value )
    def value_to_basic( self, value, app ):
        rval = dict()
        current_case = rval['__current_case__'] = value['__current_case__']
        rval[ self.test_param.name ] = self.test_param.value_to_basic( value[ self.test_param.name ], app )
        for input in self.cases[current_case].inputs.itervalues():
            rval[ input.name ] = input.value_to_basic( value[ input.name ], app )
        return rval
    def value_from_basic( self, value, app, ignore_errors=False ):
        rval = dict()
        current_case = rval['__current_case__'] = value['__current_case__']
        # Test param
        if ignore_errors and self.test_param.name not in value:
            # If ignoring errors, do nothing. However this is potentially very
            # problematic since if we are missing the value of test param,
            # the entire conditional is wrong.
            pass
        else:
            rval[ self.test_param.name ] = self.test_param.value_from_basic( value[ self.test_param.name ], app, ignore_errors )
        # Inputs associated with current case
        for input in self.cases[current_case].inputs.itervalues():
            if ignore_errors and input.name not in value:
                # If we do not have a value, and are ignoring errors, we simply
                # do nothing. There will be no value for the parameter in the
                # conditional's values dictionary.                 
                pass
            else:
                rval[ input.name ] = input.value_from_basic( value[ input.name ], app, ignore_errors )
        return rval
    def visit_inputs( self, prefix, value, callback ):
        current_case = value['__current_case__']
        new_prefix = prefix + "%s|" % ( self.name )
        for input in self.cases[current_case].inputs.itervalues():
            if isinstance( input, ToolParameter ):
                callback( prefix, input, value[input.name], parent = value )
            else:
                input.visit_inputs( prefix, value[input.name], callback )
    def get_initial_value( self, trans, context ):
        # State for a conditional is a plain dictionary. 
        rval = {}
        # Get the default value for the 'test element' and use it
        # to determine the current case
        test_value = self.test_param.get_initial_value( trans, context )
        current_case = self.get_current_case( test_value, trans )
        # Store the current case in a special value
        rval['__current_case__'] = current_case
        # Store the value of the test element
        rval[ self.test_param.name ] = test_value
        # Fill in state for selected case
        child_context = ExpressionContext( rval, context )
        for child_input in self.cases[current_case].inputs.itervalues():
            rval[ child_input.name ] = child_input.get_initial_value( trans, child_context )
        return rval
                         
class ConditionalWhen( object ):
    def __init__( self ):
        self.value = None
        self.inputs = None
