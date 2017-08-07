"""
Constructs for grouping tool parameters
"""
import logging
import os
import unicodedata

from six import (
    StringIO,
    text_type
)

from galaxy.datatypes import sniff
from galaxy.util import (
    inflector,
    relpath,
    sanitize_for_filename
)
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.expressions import ExpressionContext

log = logging.getLogger( __name__ )


class Group( object, Dictifiable ):

    dict_collection_visible_keys = ( 'name', 'type' )

    def __init__( self ):
        self.name = None

    @property
    def visible( self ):
        return True

    def value_to_basic( self, value, app ):
        """
        Convert value to a (possibly nested) representation using only basic
        types (dict, list, tuple, string_types, int, long, float, bool, None)
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

    def to_dict( self, trans ):
        group_dict = super( Group, self ).to_dict()
        return group_dict


class Repeat( Group ):

    dict_collection_visible_keys = ( 'name', 'type', 'title', 'help', 'default', 'min', 'max' )
    type = "repeat"

    def __init__( self ):
        Group.__init__( self )
        self.title = None
        self.inputs = None
        self.help = None
        self.default = 0
        self.min = None
        self.max = None

    @property
    def title_plural( self ):
        return inflector.pluralize( self.title )

    def label( self ):
        return "Repeat (%s)" % self.title

    def value_to_basic( self, value, app ):
        rval = []
        for d in value:
            rval_dict = {}
            # Propogate __index__
            if '__index__' in d:
                rval_dict['__index__'] = d['__index__']
            for input in self.inputs.values():
                rval_dict[ input.name ] = input.value_to_basic( d[input.name], app )
            rval.append( rval_dict )
        return rval

    def value_from_basic( self, value, app, ignore_errors=False ):
        rval = []
        try:
            for i, d in enumerate( value ):
                rval_dict = {}
                # If the special __index__ key is not set, create it (for backward
                # compatibility)
                rval_dict['__index__'] = d.get( '__index__', i )
                # Restore child inputs
                for input in self.inputs.values():
                    if ignore_errors and input.name not in d:
                        # If we do not have a value, and are ignoring errors, we simply
                        # do nothing. There will be no value for the parameter in the
                        # conditional's values dictionary.
                        pass
                    else:
                        rval_dict[ input.name ] = input.value_from_basic( d[input.name], app, ignore_errors )
                rval.append( rval_dict )
        except Exception as e:
            if not ignore_errors:
                raise e
        return rval

    def get_initial_value( self, trans, context ):
        rval = []
        for i in range( self.default ):
            rval_dict = { '__index__': i}
            for input in self.inputs.values():
                rval_dict[ input.name ] = input.get_initial_value( trans, context )
            rval.append( rval_dict )
        return rval

    def to_dict( self, trans ):
        repeat_dict = super( Repeat, self ).to_dict( trans )

        def input_to_dict( input ):
            return input.to_dict( trans )

        repeat_dict[ "inputs" ] = list(map( input_to_dict, self.inputs.values() ))
        return repeat_dict


class Section( Group ):

    dict_collection_visible_keys = ( 'name', 'type', 'title', 'help', 'expanded')
    type = "section"

    def __init__( self ):
        Group.__init__( self )
        self.title = None
        self.inputs = None
        self.help = None
        self.expanded = False

    @property
    def title_plural( self ):
        return inflector.pluralize( self.title )

    def label( self ):
        return "Section (%s)" % self.title

    def value_to_basic( self, value, app ):
        rval = {}
        for input in self.inputs.values():
            rval[ input.name ] = input.value_to_basic( value[input.name], app )
        return rval

    def value_from_basic( self, value, app, ignore_errors=False ):
        rval = {}
        try:
            for input in self.inputs.values():
                if not ignore_errors or input.name in value:
                    rval[ input.name ] = input.value_from_basic( value[ input.name ], app, ignore_errors )
        except Exception as e:
            if not ignore_errors:
                raise e
        return rval

    def get_initial_value( self, trans, context ):
        rval = {}
        child_context = ExpressionContext( rval, context )
        for child_input in self.inputs.values():
            rval[ child_input.name ] = child_input.get_initial_value( trans, child_context )
        return rval

    def to_dict( self, trans ):
        section_dict = super( Section, self ).to_dict( trans )

        def input_to_dict( input ):
            return input.to_dict( trans )

        section_dict[ "inputs" ] = list(map( input_to_dict, self.inputs.values() ))
        return section_dict


class UploadDataset( Group ):
    type = "upload_dataset"

    def __init__( self ):
        Group.__init__( self )
        self.title = None
        self.inputs = None
        self.file_type_name = 'file_type'
        self.default_file_type = 'txt'
        self.file_type_to_ext = { 'auto': self.default_file_type }
        self.metadata_ref = 'files_metadata'

    def get_composite_dataset_name( self, context ):
        # FIXME: HACK
        # Special case of using 'base_name' metadata for use as Dataset name needs to be done in a General Fashion, as defined within a particular Datatype.

        # We get two different types of contexts here, one straight from submitted parameters, the other after being parsed into tool inputs
        dataset_name = context.get('files_metadata|base_name', None )
        if dataset_name is None:
            dataset_name = context.get('files_metadata', {} ).get( 'base_name', None )
        if dataset_name is None:
            dataset_name = 'Uploaded Composite Dataset (%s)' % self.get_file_type( context )
        return dataset_name

    def get_file_base_name( self, context ):
        fd = context.get('files_metadata|base_name', 'Galaxy_Composite_file')
        return fd

    def get_file_type( self, context ):
        return context.get( self.file_type_name, self.default_file_type )

    def get_datatype_ext( self, trans, context ):
        ext = self.get_file_type( context )
        if ext in self.file_type_to_ext:
            ext = self.file_type_to_ext[ext]  # when using autodetect, we will use composite info from 'text', i.e. only the main file
        return ext

    def get_datatype( self, trans, context ):
        ext = self.get_datatype_ext( trans, context )
        return trans.app.datatypes_registry.get_datatype_by_extension( ext )

    @property
    def title_plural( self ):
        return inflector.pluralize(self.title)

    def group_title( self, context ):
        return "%s (%s)" % ( self.title, context.get( self.file_type_name, self.default_file_type ) )

    def title_by_index( self, trans, index, context ):
        d_type = self.get_datatype( trans, context )
        for i, ( composite_name, composite_file ) in enumerate( d_type.writable_files.items() ):
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
            for input in self.inputs.values():
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
            for input in self.inputs.values():
                if ignore_errors and input.name not in d:  # this wasn't tested
                    rval_dict[ input.name ] = input.get_initial_value( None, d )
                else:
                    rval_dict[ input.name ] = input.value_from_basic( d[input.name], app, ignore_errors )
            rval.append( rval_dict )
        return rval

    def get_initial_value( self, trans, context ):
        d_type = self.get_datatype( trans, context )
        rval = []
        for i, ( composite_name, composite_file ) in enumerate( d_type.writable_files.items() ):
            rval_dict = {}
            rval_dict['__index__'] = i  # create __index__
            for input in self.inputs.values():
                rval_dict[ input.name ] = input.get_initial_value( trans, context )
            rval.append( rval_dict )
        return rval

    def get_uploaded_datasets( self, trans, context, override_name=None, override_info=None ):
        def get_data_file_filename( data_file, override_name=None, override_info=None, purge=True ):
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
                return Bunch( type='file', path=data_file['local_filename'], name=dataset_name, purge_source=purge )
            except:
                # The uploaded file should've been persisted by the upload tool action
                return Bunch( type=None, path=None, name=None )

        def get_url_paste_urls_or_filename( group_incoming, override_name=None, override_info=None ):
            url_paste_file = group_incoming.get( 'url_paste', None )
            if url_paste_file is not None:
                url_paste = open( url_paste_file, 'r' ).read( 1024 )
                if url_paste.lstrip().lower().startswith( 'http://' ) or url_paste.lstrip().lower().startswith( 'ftp://' ) or url_paste.lstrip().lower().startswith( 'https://' ):
                    url_paste = url_paste.replace( '\r', '' ).split( '\n' )
                    for line in url_paste:
                        line = line.strip()
                        if line:
                            if not line.lower().startswith( 'http://' ) and not line.lower().startswith( 'ftp://' ) and not line.lower().startswith( 'https://' ):
                                continue  # non-url line, ignore
                            dataset_name = override_name
                            if not dataset_name:
                                dataset_name = line
                            dataset_info = override_info
                            if not dataset_info:
                                dataset_info = 'uploaded url'
                            yield Bunch( type='url', path=line, name=dataset_name )
                else:
                    dataset_name = dataset_info = 'Pasted Entry'  # we need to differentiate between various url pastes here
                    if override_name:
                        dataset_name = override_name
                    if override_info:
                        dataset_info = override_info
                    yield Bunch( type='file', path=url_paste_file, name=dataset_name )

        def get_one_filename( context ):
            data_file = context['file_data']
            url_paste = context['url_paste']
            ftp_files = context['ftp_files']
            name = context.get( 'NAME', None )
            info = context.get( 'INFO', None )
            uuid = context.get( 'uuid', None ) or None  # Turn '' to None
            warnings = []
            to_posix_lines = False
            if context.get( 'to_posix_lines', None ) not in [ "None", None, False ]:
                to_posix_lines = True
            space_to_tab = False
            if context.get( 'space_to_tab', None ) not in [ "None", None, False ]:
                space_to_tab = True
            file_bunch = get_data_file_filename( data_file, override_name=name, override_info=info )
            if file_bunch.path:
                if url_paste is not None and url_paste.strip():
                    warnings.append( "All file contents specified in the paste box were ignored." )
                if ftp_files:
                    warnings.append( "All FTP uploaded file selections were ignored." )
            elif url_paste is not None and url_paste.strip():  # we need to use url_paste
                for file_bunch in get_url_paste_urls_or_filename( context, override_name=name, override_info=info ):
                    if file_bunch.path:
                        break
                if file_bunch.path and ftp_files is not None:
                    warnings.append( "All FTP uploaded file selections were ignored." )
            elif ftp_files is not None and trans.user is not None:  # look for files uploaded via FTP
                user_ftp_dir = trans.user_ftp_dir
                for ( dirpath, dirnames, filenames ) in os.walk( user_ftp_dir ):
                    for filename in filenames:
                        for ftp_filename in ftp_files:
                            if ftp_filename == filename:
                                path = relpath( os.path.join( dirpath, filename ), user_ftp_dir )
                                if not os.path.islink( os.path.join( dirpath, filename ) ):
                                    ftp_data_file = { 'local_filename' : os.path.abspath( os.path.join( user_ftp_dir, path ) ),
                                                      'filename' : os.path.basename( path ) }
                                    purge = getattr(trans.app.config, 'ftp_upload_purge', True)
                                    file_bunch = get_data_file_filename(
                                        ftp_data_file,
                                        override_name=name,
                                        override_info=info,
                                        purge=purge,
                                    )
                                    if file_bunch.path:
                                        break
                        if file_bunch.path:
                            break
                    if file_bunch.path:
                        break
            file_bunch.to_posix_lines = to_posix_lines
            file_bunch.space_to_tab = space_to_tab
            file_bunch.uuid = uuid
            return file_bunch, warnings

        def get_filenames( context ):
            rval = []
            data_file = context['file_data']
            ftp_files = context['ftp_files']
            uuid = context.get( 'uuid', None ) or None  # Turn '' to None
            name = context.get( 'NAME', None )
            info = context.get( 'INFO', None )
            to_posix_lines = False
            if context.get( 'to_posix_lines', None ) not in [ "None", None, False ]:
                to_posix_lines = True
            space_to_tab = False
            if context.get( 'space_to_tab', None ) not in [ "None", None, False ]:
                space_to_tab = True
            file_bunch = get_data_file_filename( data_file, override_name=name, override_info=info )
            file_bunch.uuid = uuid
            if file_bunch.path:
                file_bunch.to_posix_lines = to_posix_lines
                file_bunch.space_to_tab = space_to_tab
                rval.append( file_bunch )
            for file_bunch in get_url_paste_urls_or_filename( context, override_name=name, override_info=info ):
                if file_bunch.path:
                    file_bunch.uuid = uuid
                    file_bunch.to_posix_lines = to_posix_lines
                    file_bunch.space_to_tab = space_to_tab
                    rval.append( file_bunch )
            # look for files uploaded via FTP
            valid_files = []
            if ftp_files is not None:
                # Normalize input paths to ensure utf-8 encoding is normal form c.
                # This allows for comparison when the filesystem uses a different encoding than the browser.
                ftp_files = [unicodedata.normalize('NFC', f) for f in ftp_files if isinstance(f, text_type)]
                if trans.user is None:
                    log.warning( 'Anonymous user passed values in ftp_files: %s' % ftp_files )
                    ftp_files = []
                    # TODO: warning to the user (could happen if session has become invalid)
                else:
                    user_ftp_dir = trans.user_ftp_dir
                    for ( dirpath, dirnames, filenames ) in os.walk( user_ftp_dir ):
                        for filename in filenames:
                            path = relpath( os.path.join( dirpath, filename ), user_ftp_dir )
                            if not os.path.islink( os.path.join( dirpath, filename ) ):
                                # Normalize filesystem paths
                                if isinstance(path, text_type):
                                    valid_files.append(unicodedata.normalize('NFC', path ))
                                else:
                                    valid_files.append(path)

            else:
                ftp_files = []
            for ftp_file in ftp_files:
                if ftp_file not in valid_files:
                    log.warning( 'User passed an invalid file path in ftp_files: %s' % ftp_file )
                    continue
                    # TODO: warning to the user (could happen if file is already imported)
                ftp_data_file = { 'local_filename' : os.path.abspath( os.path.join( user_ftp_dir, ftp_file ) ),
                                  'filename' : os.path.basename( ftp_file ) }
                purge = getattr(trans.app.config, 'ftp_upload_purge', True)
                file_bunch = get_data_file_filename( ftp_data_file, override_name=name, override_info=info, purge=purge )
                if file_bunch.path:
                    file_bunch.to_posix_lines = to_posix_lines
                    file_bunch.space_to_tab = space_to_tab
                    rval.append( file_bunch )
            return rval
        file_type = self.get_file_type( context )
        d_type = self.get_datatype( trans, context )
        dbkey = context.get( 'dbkey', None )
        writable_files = d_type.writable_files
        writable_files_offset = 0
        groups_incoming = [ None for _ in writable_files ]
        for group_incoming in context.get( self.name, [] ):
            i = int( group_incoming['__index__'] )
            groups_incoming[ i ] = group_incoming
        if d_type.composite_type is not None:
            # handle uploading of composite datatypes
            # Only one Dataset can be created
            dataset = Bunch()
            dataset.type = 'composite'
            dataset.file_type = file_type
            dataset.dbkey = dbkey
            dataset.datatype = d_type
            dataset.warnings = []
            dataset.metadata = {}
            dataset.composite_files = {}
            dataset.uuid = None
            # load metadata
            files_metadata = context.get( self.metadata_ref, {} )
            metadata_name_substition_default_dict = dict( ( composite_file.substitute_name_with_metadata, d_type.metadata_spec[ composite_file.substitute_name_with_metadata ].default ) for composite_file in d_type.composite_files.values() if composite_file.substitute_name_with_metadata )
            for meta_name, meta_spec in d_type.metadata_spec.items():
                if meta_spec.set_in_upload:
                    if meta_name in files_metadata:
                        meta_value = files_metadata[ meta_name ]
                        if meta_name in metadata_name_substition_default_dict:
                            meta_value = sanitize_for_filename( meta_value, default=metadata_name_substition_default_dict[ meta_name ] )
                        dataset.metadata[ meta_name ] = meta_value
            dataset.precreated_name = dataset.name = self.get_composite_dataset_name( context )
            if dataset.datatype.composite_type == 'auto_primary_file':
                # replace sniff here with just creating an empty file
                temp_name, is_multi_byte = sniff.stream_to_file( StringIO( d_type.generate_primary_file( dataset ) ), prefix='upload_auto_primary_file' )
                dataset.primary_file = temp_name
                dataset.to_posix_lines = True
                dataset.space_to_tab = False
            else:
                file_bunch, warnings = get_one_filename( groups_incoming[ 0 ] )
                writable_files_offset = 1
                dataset.primary_file = file_bunch.path
                dataset.to_posix_lines = file_bunch.to_posix_lines
                dataset.space_to_tab = file_bunch.space_to_tab
                dataset.warnings.extend( warnings )
            if dataset.primary_file is None:  # remove this before finish, this should create an empty dataset
                raise Exception( 'No primary dataset file was available for composite upload' )
            keys = [ value.name for value in writable_files.values() ]
            for i, group_incoming in enumerate( groups_incoming[ writable_files_offset : ] ):
                key = keys[ i + writable_files_offset ]
                if group_incoming is None and not writable_files[ list(writable_files.keys())[ keys.index( key ) ] ].optional:
                    dataset.warnings.append( "A required composite file (%s) was not specified." % ( key ) )
                    dataset.composite_files[ key ] = None
                else:
                    file_bunch, warnings = get_one_filename( group_incoming )
                    dataset.warnings.extend( warnings )
                    if file_bunch.path:
                        dataset.composite_files[ key ] = file_bunch.__dict__
                    else:
                        dataset.composite_files[ key ] = None
                        if not writable_files[ list(writable_files.keys())[ keys.index( key ) ] ].optional:
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
        self.value_ref_in_group = True  # When our test_param is not part of the conditional Group, this is False

    @property
    def label( self ):
        return "Conditional (%s)" % self.name

    def get_current_case( self, value ):
        # Convert value to user representation
        str_value = self.test_param.to_param_dict_string( value )
        # Find the matching case
        for index, case in enumerate( self.cases ):
            if str_value == case.value:
                return index
        raise ValueError( "No case matched value:", self.name, str_value )

    def value_to_basic( self, value, app ):
        rval = dict()
        rval[ self.test_param.name ] = self.test_param.value_to_basic( value[ self.test_param.name ], app )
        current_case = rval[ '__current_case__' ] = self.get_current_case( value[ self.test_param.name ] )
        for input in self.cases[ current_case ].inputs.values():
            if input.name in value:  # parameter might be absent in unverified workflow
                rval[ input.name ] = input.value_to_basic( value[ input.name ], app )
        return rval

    def value_from_basic( self, value, app, ignore_errors=False ):
        rval = dict()
        try:
            rval[ self.test_param.name ] = self.test_param.value_from_basic( value.get( self.test_param.name ), app, ignore_errors )
            current_case = rval[ '__current_case__' ] = self.get_current_case( rval[ self.test_param.name ] )
            # Inputs associated with current case
            for input in self.cases[ current_case ].inputs.values():
                # If we do not have a value, and are ignoring errors, we simply
                # do nothing. There will be no value for the parameter in the
                # conditional's values dictionary.
                if not ignore_errors or input.name in value:
                    rval[ input.name ] = input.value_from_basic( value[ input.name ], app, ignore_errors )
        except Exception as e:
            if not ignore_errors:
                raise e
        return rval

    def get_initial_value( self, trans, context ):
        # State for a conditional is a plain dictionary.
        rval = {}
        # Get the default value for the 'test element' and use it
        # to determine the current case
        test_value = self.test_param.get_initial_value( trans, context )
        current_case = self.get_current_case( test_value )
        # Store the current case in a special value
        rval['__current_case__'] = current_case
        # Store the value of the test element
        rval[ self.test_param.name ] = test_value
        # Fill in state for selected case
        child_context = ExpressionContext( rval, context )
        for child_input in self.cases[current_case].inputs.values():
            rval[ child_input.name ] = child_input.get_initial_value( trans, child_context )
        return rval

    def to_dict( self, trans ):
        cond_dict = super( Conditional, self ).to_dict( trans )

        def nested_to_dict( input ):
            return input.to_dict( trans )

        cond_dict[ "cases" ] = list(map( nested_to_dict, self.cases ))
        cond_dict[ "test_param" ] = nested_to_dict( self.test_param )
        return cond_dict


class ConditionalWhen( object, Dictifiable ):
    dict_collection_visible_keys = ( 'value', )

    def __init__( self ):
        self.value = None
        self.inputs = None

    def to_dict( self, trans ):
        when_dict = super( ConditionalWhen, self ).to_dict()

        def input_to_dict( input ):
            return input.to_dict( trans )

        when_dict[ "inputs" ] = list(map( input_to_dict, self.inputs.values() ))
        return when_dict
