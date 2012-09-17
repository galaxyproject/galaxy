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
    
    def __init__( self, original_dataset ):
        # Compatibility check.
        if not isinstance( original_dataset.datatype, Tabular ):
            raise Exception( "Data provider can only be used with tabular data" )
            
        # Attribute init.
        self.original_dataset = original_dataset
        
    def get_data( self, cols, start_val=0, max_vals=sys.maxint, **kwargs ):
        """
        Returns data from specified columns in dataset. Format is list of lists 
        where each list is a line of data.
        """

        cols = from_json_string( cols )
        
        def cast_val( val, type ):
            """ Cast value based on type. """
            if type == 'int':
                try: val = int( val )
                except: pass
            elif type == 'float':
                try: val = float( val )
                except: pass
            return val
        
        data = []
        f = open( self.original_dataset.file_name )
        for count, line in enumerate( f ):
            if count < start_val:
                continue
            if max_vals and count-start_val >= max_vals:
                message = self.error_max_vals % ( max_vals, "features" )
                break
            
            fields = line.split()
            #pre: column indeces should be avail in fields
            for col_index in cols:
                assert col_index < len( fields ), (
                    "column index (%d) must be less than fields length: %d" % ( col_index, len( fields ) ) )
                
            data.append( [ cast_val( fields[c], self.original_dataset.metadata.column_types[c] ) for c in cols ] )
            
        f.close()
            
        return data

class DataProviderRegistry( object ):
    """
    Registry for data providers that enables listing and lookup.
    """

    def __init__( self ):
        # Mapping from dataset type name to a class that can fetch data from a file of that
        # type. First key is converted dataset type; if result is another dict, second key
        # is original dataset type. TODO: This needs to be more flexible.
        self.dataset_type_name_to_data_provider = {
            "tabix": { 
                Vcf: VcfTabixDataProvider,
                Bed: BedTabixDataProvider,
                Gtf: GtfTabixDataProvider,
                ENCODEPeak: ENCODEPeakTabixDataProvider,
                Interval: IntervalTabixDataProvider,
                ChromatinInteractions: ChromatinInteractionsTabixDataProvider, 
                "default" : TabixDataProvider 
            },
            "interval_index": IntervalIndexDataProvider,
            "bai": BamDataProvider,
            "bam": SamDataProvider,
            "summary_tree": SummaryTreeDataProvider,
            "bigwig": BigWigDataProvider,
            "bigbed": BigBedDataProvider
        }

    def get_data_provider( name=None, original_dataset=None ):
        """
        Returns data provider class by name and/or original dataset.
        """
        data_provider = None
        if name:
            value = dataset_type_name_to_data_provider[ name ]
            if isinstance( value, dict ):
                # Get converter by dataset extension; if there is no data provider,
                # get the default.
                data_provider = value.get( original_dataset.datatype.__class__, value.get( "default" ) )
            else:
                data_provider = value
        elif original_dataset:
            # Look up data provider from datatype's informaton.
            try:
                # Get data provider mapping and data provider for 'data'. If 
                # provider available, use it; otherwise use generic provider.
                _ , data_provider_mapping = original_dataset.datatype.get_track_type()
                if 'data_standalone' in data_provider_mapping:
                    data_provider_name = data_provider_mapping[ 'data_standalone' ]
                else:
                    data_provider_name = data_provider_mapping[ 'data' ]
                if data_provider_name:
                    data_provider = self.get_data_provider( name=data_provider_name, original_dataset=original_dataset )
                else: 
                    data_provider = GenomeDataProvider
            except:
                pass
        return data_provider
        