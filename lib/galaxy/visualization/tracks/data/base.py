class TracksDataProvider( object ):
    """ Base class for tracks data providers. """
    
    def __init__( self, converted_dataset, original_dataset ):
        self.converted_dataset = converted_dataset
        self.original_dataset = original_dataset
        
    def get_data( self, chrom, start, end, **kwargs ):
        """ Returns data in region defined by chrom, start, and end. """
        # Override.
        pass