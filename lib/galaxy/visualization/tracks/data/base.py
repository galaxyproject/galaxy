from galaxy.datatypes.tabular import Vcf
from galaxy.visualization.tracks import data

class TracksDataProvider( object ):
    """ Base class for tracks data providers. """
    
    """ 
    Mapping from column name to index in data. This mapping is used to create
    filters.
    """
    col_name_data_index_mapping = {}
    
    def __init__( self, converted_dataset=None, original_dataset=None ):
        """ Create basic data provider. """
        self.converted_dataset = converted_dataset
        self.original_dataset = original_dataset
        
    def get_data( self, chrom, start, end, **kwargs ):
        """ Returns data in region defined by chrom, start, and end. """
        # Override.
        pass
        
    def get_filters( self ):
        """ 
        Returns filters for provider's data. Return value is a list of 
        filters; each filter is a dictionary with the keys 'name', 'index', 'value'.
        NOTE: This method uses the original dataset's datatype and metadata to 
        create the filters.
        """
        # Get column names.
        try:
            column_names = self.original_dataset.datatype.column_names
        except AttributeError:
            column_names = range( self.original_dataset.metadata.columns )
            
        # Dataset must have column types; if not, cannot create filters.
        try:
            column_types = self.original_dataset.metadata.column_types
        except AttributeError:
            return []
            
        # Create and return filters.
        filters = []
        if self.original_dataset.metadata.viz_filter_columns:
            for viz_col_index in self.original_dataset.metadata.viz_filter_columns:
                col_name = column_names[ viz_col_index ]
                # Make sure that column has a mapped index. If not, do not add filter.
                try:
                    index = self.col_name_data_index_mapping[ col_name ]
                except KeyError:
                    continue
                filters.append(
                    { 'name' : col_name, 'value' : column_types[viz_col_index], \
                    'index' : index } )
        return filters
        

#        
# Helper methods.
#

def dataset_to_data_provider( dataset=None ):
    """
    Returns data provider for a dataset.
    """
    # TODO: merge this method with the dict in tracks controller to provide a 
    # unified way to get data providers based on dataset/converted dataset type.
    if isinstance( dataset.datatype, Vcf ):
        return data.vcf.VcfDataProvider
    else:
        try:
            # If get_track_type is available, then generic data provider
            # should work.
            dataset.datatype.get_track_type()
            return TracksDataProvider
        except e:
            return None