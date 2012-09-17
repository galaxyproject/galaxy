from galaxy.visualization.data_providers.basic import ColumnDataProvider
from galaxy.visualization.data_providers.genome import *

class DataProviderRegistry( object ):
    """
    Registry for data providers that enables listing and lookup.
    """

    def __init__( self ):
        # Mapping from dataset type name to a class that can fetch data from a file of that
        # type. First key is converted dataset type; if result is another dict, second key
        # is original dataset type.
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

    def get_data_provider( self, name=None, raw=False, original_dataset=None ):
        """
        Returns data provider class by name and/or original dataset.
        """

        # If getting raw data, use original dataset type to get data provider.
        if raw:
            if isinstance( original_dataset.datatype, Gff ):
                return RawGFFDataProvider
            elif isinstance( original_dataset.datatype, Bed ):
                return RawBedDataProvider
            elif isinstance( original_dataset.datatype, Vcf ):
                return RawVcfDataProvider
            elif isinstance( original_dataset.datatype, Tabular ):
                return ColumnDataProvider

        # Using converted dataset, so get corrsponding data provider.
        data_provider = None
        if name:
            value = self.dataset_type_name_to_data_provider[ name ]
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