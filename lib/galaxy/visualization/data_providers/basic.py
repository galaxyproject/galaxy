import sys
from galaxy.datatypes.tabular import Tabular
from galaxy.util.json import from_json_string

class BaseDataProvider( object ):
    """
    Base class for data providers. Data providers (a) read and package data from datasets;
    and (b) write subsets of data to new datasets.
    """

    def __init__( self, converted_dataset=None, original_dataset=None, dependencies=None,
                  error_max_vals="Only the first %i values are returned." ):
        """ Create basic data provider. """
        self.converted_dataset = converted_dataset
        self.original_dataset = original_dataset
        self.dependencies = dependencies
        self.error_max_vals = error_max_vals
        
    def has_data( self, **kwargs ):
        """
        Returns true if dataset has data in the specified genome window, false
        otherwise.
        """
        raise Exception( "Unimplemented Function" )
        
    def get_iterator( self, **kwargs ):
        """
        Returns an iterator that provides data in the region chrom:start-end
        """
        raise Exception( "Unimplemented Function" )
        
    def process_data( self, iterator, start_val=0, max_vals=None, **kwargs ):
        """
        Process data from an iterator to a format that can be provided to client.
        """
        raise Exception( "Unimplemented Function" )        
        
    def get_data( self, start_val=0, max_vals=sys.maxint, **kwargs ):
        """ 
        Returns data as specified by kwargs. start_val is the first element to 
        return and max_vals indicates the number of values to return.
        
        Return value must be a dictionary with the following attributes:
            dataset_type, data
        """
        iterator = self.get_iterator( chrom, start, end )
        return self.process_data( iterator, start_val, max_vals, **kwargs )
    
    def write_data_to_file( self, filename, **kwargs ):
        """
        Write data in region defined by chrom, start, and end to a file.
        """
        raise Exception( "Unimplemented Function" )


class ColumnDataProvider( BaseDataProvider ):
    """ Data provider for columnar data """
    MAX_LINES_RETURNED = 30000
    
    def __init__( self, original_dataset, max_lines_returned=MAX_LINES_RETURNED ):
        # Compatibility check.
        if not isinstance( original_dataset.datatype, Tabular ):
            raise Exception( "Data provider can only be used with tabular data" )
            
        # Attribute init.
        self.original_dataset = original_dataset
        # allow throttling
        self.max_lines_returned = max_lines_returned
        
    def get_data( self, columns, start_val=0, max_vals=None, skip_comments=True, **kwargs ):
        """
        Returns data from specified columns in dataset. Format is list of lists 
        where each list is a line of data.
        """
        #TODO: validate kwargs
        try:
            max_vals = int( max_vals )
            max_vals = min([ max_vals, self.max_lines_returned ])
        except ( ValueError, TypeError ):
            max_vals = self.max_lines_returned
        
        try:
            start_val = int( start_val )
            start_val = max([ start_val, 0 ])
        except ( ValueError, TypeError ):
            start_val = 0
                
        # skip comment lines (if any/avail)
        # pre: should have original_dataset and
        if( skip_comments
        and start_val == 0
        and self.original_dataset.metadata.comment_lines ):
            start_val = int( self.original_dataset.metadata.comment_lines ) + 1
        
        response = {}
        response[ 'data' ] = data = []
        
        #TODO bail if columns None, not parsable, not within meta.columns
        # columns is an array of ints for now (should handle column names later)
        columns = from_json_string( columns )
        assert( all([ column < self.original_dataset.metadata.columns for column in columns ]) ),(
                "column index (%d) must be less" % ( column )
              + " than the number of columns: %d" % ( self.original_dataset.metadata.columns ) )
        
        #print columns, start_val, max_vals, skip_comments, kwargs
        
        # alter meta by column_selectors (if any)
        def cast_val( val, type ):
            """ Cast value based on type. """
            if type == 'int':
                try: val = int( val )
                except: return None
            elif type == 'float':
                try: val = float( val )
                except: return None
            return val
        
        f = open( self.original_dataset.file_name )
        #TODO: add f.seek if given fptr in kwargs
        for count, line in enumerate( f ):
            if count < start_val:
                continue
            
            if ( count - start_val ) >= max_vals:
                break
            
            fields = line.split()
            fields_len = len( fields )
            #TODO: this will return the wrong number of columns for abberrant lines
            line_data = [ cast_val( fields[c], self.original_dataset.metadata.column_types[c] )
                          for c in columns if ( c < fields_len ) ]
            data.append( line_data )
            
        response[ 'endpoint' ] = dict( last_line=( count - 1 ), file_ptr=f.tell() )
        f.close()

        return response

