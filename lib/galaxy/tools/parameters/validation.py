"""
Classes related to parameter validation.
"""
import logging
import re

from six import string_types

from galaxy import (
    model,
    util
)

log = logging.getLogger( __name__ )


class Validator( object ):
    """
    A validator checks that a value meets some conditions OR raises ValueError
    """
    requires_dataset_metadata = False

    @classmethod
    def from_element( cls, param, elem ):
        type = elem.get( 'type', None )
        assert type is not None, "Required 'type' attribute missing from validator"
        return validator_types[type].from_element( param, elem )

    def validate( self, value, trans=None ):
        raise TypeError( "Abstract Method" )


class RegexValidator( Validator ):
    """
    Validator that evaluates a regular expression

    >>> from xml.etree.ElementTree import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build( None, XML( '''
    ... <param name="blah" type="text" size="10" value="10">
    ...     <validator type="regex" message="Not gonna happen">[Ff]oo</validator>
    ... </param>
    ... ''' ) )
    >>> t = p.validate( "Foo" )
    >>> t = p.validate( "foo" )
    >>> t = p.validate( "Fop" )
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    """

    @classmethod
    def from_element( cls, param, elem ):
        return cls( elem.get( 'message' ), elem.text )

    def __init__( self, message, expression ):
        self.message = message
        # Compile later. RE objects used to not be thread safe. Not sure about
        # the sre module.
        self.expression = expression

    def validate( self, value, trans=None ):
        if re.match( self.expression, value or '' ) is None:
            raise ValueError( self.message )


class ExpressionValidator( Validator ):
    """
    Validator that evaluates a python expression using the value

    >>> from xml.etree.ElementTree import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build( None, XML( '''
    ... <param name="blah" type="text" size="10" value="10">
    ...     <validator type="expression" message="Not gonna happen">value.lower() == "foo"</validator>
    ... </param>
    ... ''' ) )
    >>> t = p.validate( "Foo" )
    >>> t = p.validate( "foo" )
    >>> t = p.validate( "Fop" )
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    """

    @classmethod
    def from_element( cls, param, elem ):
        return cls( elem.get( 'message' ), elem.text, elem.get( 'substitute_value_in_message' ) )

    def __init__( self, message, expression, substitute_value_in_message ):
        self.message = message
        self.substitute_value_in_message = substitute_value_in_message
        # Save compiled expression, code objects are thread safe (right?)
        self.expression = compile( expression, '<string>', 'eval' )

    def validate( self, value, trans=None ):
        if not( eval( self.expression, dict( value=value ) ) ):
            message = self.message
            if self.substitute_value_in_message:
                message = message % value
            raise ValueError( message )


class InRangeValidator( Validator ):
    """
    Validator that ensures a number is in a specific range

    >>> from xml.etree.ElementTree import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build( None, XML( '''
    ... <param name="blah" type="integer" size="10" value="10">
    ...     <validator type="in_range" message="Not gonna happen" min="10" exclude_min="true" max="20"/>
    ... </param>
    ... ''' ) )
    >>> t = p.validate( 10 )
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate( 15 )
    >>> t = p.validate( 20 )
    >>> t = p.validate( 21 )
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    """

    @classmethod
    def from_element( cls, param, elem ):
        return cls( elem.get( 'message', None ), elem.get( 'min' ),
                    elem.get( 'max' ), elem.get( 'exclude_min', 'false' ),
                    elem.get( 'exclude_max', 'false' ) )

    def __init__( self, message, range_min, range_max, exclude_min=False, exclude_max=False ):
        """
        When the optional exclude_min and exclude_max attributes are set
        to true, the range excludes the end points (i.e., min < value < max),
        while if set to False ( the default), then range includes the end points
        (1.e., min <= value <= max).  Combinations of exclude_min and exclude_max
        values are allowed.
        """
        self.min = float( range_min if range_min is not None else '-inf' )
        self.exclude_min = util.asbool( exclude_min )
        self.max = float( range_max if range_max is not None else 'inf' )
        self.exclude_max = util.asbool( exclude_max )
        assert self.min <= self.max, 'min must be less than or equal to max'
        # Remove unneeded 0s and decimal from floats to make message pretty.
        self_min_str = str( self.min ).rstrip( '0' ).rstrip( '.' )
        self_max_str = str( self.max ).rstrip( '0' ).rstrip( '.' )
        op1 = '>='
        op2 = '<='
        if self.exclude_min:
            op1 = '>'
        if self.exclude_max:
            op2 = '<'
        self.message = message or "Value must be %s %s and %s %s" % ( op1, self_min_str, op2, self_max_str )

    def validate( self, value, trans=None ):
        if self.exclude_min:
            if not self.min < float( value ):
                raise ValueError( self.message )
        else:
            if not self.min <= float( value ):
                raise ValueError( self.message )
        if self.exclude_max:
            if not float( value ) < self.max:
                raise ValueError( self.message )
        else:
            if not float( value ) <= self.max:
                raise ValueError( self.message )


class LengthValidator( Validator ):
    """
    Validator that ensures the length of the provided string (value) is in a specific range

    >>> from xml.etree.ElementTree import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build( None, XML( '''
    ... <param name="blah" type="text" size="10" value="foobar">
    ...     <validator type="length" min="2" max="8"/>
    ... </param>
    ... ''' ) )
    >>> t = p.validate( "foo" )
    >>> t = p.validate( "bar" )
    >>> t = p.validate( "f" )
    Traceback (most recent call last):
        ...
    ValueError: Must have length of at least 2
    >>> t = p.validate( "foobarbaz" )
    Traceback (most recent call last):
        ...
    ValueError: Must have length no more than 8
    """

    @classmethod
    def from_element( cls, param, elem ):
        return cls( elem.get( 'message', None ), elem.get( 'min', None ), elem.get( 'max', None ) )

    def __init__( self, message, length_min, length_max ):
        self.message = message
        if length_min is not None:
            length_min = int( length_min )
        if length_max is not None:
            length_max = int( length_max )
        self.min = length_min
        self.max = length_max

    def validate( self, value, trans=None ):
        if self.min is not None and len( value ) < self.min:
            raise ValueError( self.message or ( "Must have length of at least %d" % self.min ) )
        if self.max is not None and len( value ) > self.max:
            raise ValueError( self.message or ( "Must have length no more than %d" % self.max ) )


class DatasetOkValidator( Validator ):
    """
    Validator that checks if a dataset is in an 'ok' state
    """

    def __init__( self, message=None ):
        self.message = message

    @classmethod
    def from_element( cls, param, elem ):
        return cls( elem.get( 'message', None ) )

    def validate( self, value, trans=None ):
        if value and value.state != model.Dataset.states.OK:
            if self.message is None:
                self.message = "The selected dataset is still being generated, select another dataset or wait until it is completed"
            raise ValueError( self.message )


class DatasetEmptyValidator( Validator ):
    """Validator that checks if a dataset has a positive file size."""
    def __init__( self, message=None ):
        self.message = message

    @classmethod
    def from_element( cls, param, elem ):
        return cls( elem.get( 'message', None ) )

    def validate( self, value, trans=None ):
        if value:
            if value.get_size() == 0:
                if self.message is None:
                    self.message = "The selected dataset is empty, this tool expects non-empty files."
                raise ValueError( self.message )


class MetadataValidator( Validator ):
    """
    Validator that checks for missing metadata
    """
    requires_dataset_metadata = True

    def __init__( self, message=None, check="", skip="" ):
        self.message = message
        self.check = check.split( "," )
        self.skip = skip.split( "," )

    @classmethod
    def from_element( cls, param, elem ):
        return cls( message=elem.get( 'message', None ), check=elem.get( 'check', "" ), skip=elem.get( 'skip', "" ) )

    def validate( self, value, trans=None ):
        if value:
            if not isinstance( value, model.DatasetInstance ):
                raise ValueError( 'A non-dataset value was provided.' )
            if value.missing_meta( check=self.check, skip=self.skip ):
                if self.message is None:
                    self.message = "Metadata missing, click the pencil icon in the history item to edit / save the metadata attributes"
                raise ValueError( self.message )


class UnspecifiedBuildValidator( Validator ):
    """
    Validator that checks for dbkey not equal to '?'
    """
    requires_dataset_metadata = True

    def __init__( self, message=None ):
        if message is None:
            self.message = "Unspecified genome build, click the pencil icon in the history item to set the genome build"
        else:
            self.message = message

    @classmethod
    def from_element( cls, param, elem ):
        return cls( elem.get( 'message', None ) )

    def validate( self, value, trans=None ):
        # if value is None, we cannot validate
        if value:
            dbkey = value.metadata.dbkey
            if isinstance( dbkey, list ):
                dbkey = dbkey[0]
            if dbkey == '?':
                raise ValueError( self.message )


class NoOptionsValidator( Validator ):
    """Validator that checks for empty select list"""

    def __init__( self, message=None ):
        self.message = message

    @classmethod
    def from_element( cls, param, elem ):
        return cls( elem.get( 'message', None ) )

    def validate( self, value, trans=None ):
        if value is None:
            if self.message is None:
                self.message = "No options available for selection"
            raise ValueError( self.message )


class EmptyTextfieldValidator( Validator ):
    """Validator that checks for empty text field"""

    def __init__( self, message=None ):
        self.message = message

    @classmethod
    def from_element( cls, param, elem ):
        return cls( elem.get( 'message', None ) )

    def validate( self, value, trans=None ):
        if value == '':
            if self.message is None:
                self.message = "Field requires a value"
            raise ValueError( self.message )


class MetadataInFileColumnValidator( Validator ):
    """
    Validator that checks if the value for a dataset's metadata item exists in a file.
    """
    requires_dataset_metadata = True

    @classmethod
    def from_element( cls, param, elem ):
        filename = elem.get( "filename", None )
        if filename:
            filename = "%s/%s" % ( param.tool.app.config.tool_data_path, filename.strip() )
        metadata_name = elem.get( "metadata_name", None )
        if metadata_name:
            metadata_name = metadata_name.strip()
        metadata_column = int( elem.get( "metadata_column", 0 ) )
        split = elem.get( "split", "\t" )
        message = elem.get( "message", "Value for metadata %s was not found in %s." % ( metadata_name, filename ) )
        line_startswith = elem.get( "line_startswith", None  )
        if line_startswith:
            line_startswith = line_startswith.strip()
        return cls( filename, metadata_name, metadata_column, message, line_startswith, split )

    def __init__( self, filename, metadata_name, metadata_column, message="Value for metadata not found.", line_startswith=None, split="\t" ):
        self.metadata_name = metadata_name
        self.message = message
        self.valid_values = []
        for line in open( filename ):
            if line_startswith is None or line.startswith( line_startswith ):
                fields = line.split( split )
                if metadata_column < len( fields ):
                    self.valid_values.append( fields[metadata_column].strip() )

    def validate( self, value, trans=None ):
        if not value:
            return
        if hasattr( value, "metadata" ):
            if value.metadata.spec[self.metadata_name].param.to_string( value.metadata.get( self.metadata_name ) ) in self.valid_values:
                return
        raise ValueError( self.message )


class MetadataInDataTableColumnValidator( Validator ):
    """
    Validator that checks if the value for a dataset's metadata item exists in a file.
    """
    requires_dataset_metadata = True

    @classmethod
    def from_element( cls, param, elem ):
        table_name = elem.get( "table_name", None )
        assert table_name, 'You must specify a table_name.'
        tool_data_table = param.tool.app.tool_data_tables[ table_name ]
        metadata_name = elem.get( "metadata_name", None )
        if metadata_name:
            metadata_name = metadata_name.strip()
        metadata_column = elem.get( "metadata_column", 0 )
        try:
            metadata_column = int( metadata_column )
        except:
            pass
        message = elem.get( "message", "Value for metadata %s was not found in %s." % ( metadata_name, table_name ) )
        line_startswith = elem.get( "line_startswith", None  )
        if line_startswith:
            line_startswith = line_startswith.strip()
        return cls( tool_data_table, metadata_name, metadata_column, message, line_startswith )

    def __init__( self, tool_data_table, metadata_name, metadata_column, message="Value for metadata not found.", line_startswith=None ):
        self.metadata_name = metadata_name
        self.message = message
        self.valid_values = []
        self._data_table_content_version = None
        self._tool_data_table = tool_data_table
        if isinstance( metadata_column, string_types ):
            metadata_column = tool_data_table.columns[ metadata_column ]
        self._metadata_column = metadata_column
        self._load_values()

    def _load_values( self ):
        self._data_table_content_version, data_fields = self._tool_data_table.get_version_fields()
        self.valid_values = []
        for fields in data_fields:
            if self._metadata_column < len( fields ):
                self.valid_values.append( fields[ self._metadata_column ] )

    def validate( self, value, trans=None ):
        if not value:
            return
        if hasattr( value, "metadata" ):
            if not self._tool_data_table.is_current_version( self._data_table_content_version ):
                log.debug( 'MetadataInDataTableColumnValidator values are out of sync with data table (%s), updating validator.', self._tool_data_table.name )
                self._load_values()
            if value.metadata.spec[self.metadata_name].param.to_string( value.metadata.get( self.metadata_name ) ) in self.valid_values:
                return
        raise ValueError( self.message )


validator_types = dict( expression=ExpressionValidator,
                        regex=RegexValidator,
                        in_range=InRangeValidator,
                        length=LengthValidator,
                        metadata=MetadataValidator,
                        unspecified_build=UnspecifiedBuildValidator,
                        no_options=NoOptionsValidator,
                        empty_field=EmptyTextfieldValidator,
                        empty_dataset=DatasetEmptyValidator,
                        dataset_metadata_in_file=MetadataInFileColumnValidator,
                        dataset_metadata_in_data_table=MetadataInDataTableColumnValidator,
                        dataset_ok_validator=DatasetOkValidator, )


def get_suite():
    """Get unittest suite for this module"""
    import doctest
    import sys
    return doctest.DocTestSuite( sys.modules[__name__] )
