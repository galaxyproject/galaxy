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

    def get_data_provider( self, trans, name=None, source='data', raw=False, original_dataset=None ):
        """
        Returns data provider matching parameter values. For standalone data 
        sources, source parameter is ignored.
        """

        data_provider = None
        if raw:
            # Working with raw data.
            if isinstance( original_dataset.datatype, Gff ):
                data_provider_class = RawGFFDataProvider
            elif isinstance( original_dataset.datatype, Bed ):
                data_provider_class = RawBedDataProvider
            elif isinstance( original_dataset.datatype, Vcf ):
                data_provider_class = RawVcfDataProvider
            elif isinstance( original_dataset.datatype, Tabular ):
                data_provider_class = ColumnDataProvider

            data_provider = data_provider_class( original_dataset=original_dataset )

        else:
            # Working with converted or standalone dataset.

            if name:
                # Provider requested by name; get from mappings.
                value = self.dataset_type_name_to_data_provider[ name ]
                if isinstance( value, dict ):
                    # Get converter by dataset extension; if there is no data provider,
                    # get the default.
                    data_provider_class = value.get( original_dataset.datatype.__class__, value.get( "default" ) )
                else:
                    data_provider_class = value

                # If name is the same as original dataset's type, dataset is standalone.
                # Otherwise, a converted dataset is being used.
                if name == original_dataset.ext:
                    data_provider = data_provider_class( original_dataset=original_dataset )
                else:
                    converted_dataset = original_dataset.get_converted_dataset( trans, name )
                    deps = original_dataset.get_converted_dataset_deps( trans, name )
                    data_provider = data_provider_class( original_dataset=original_dataset, 
                                                         converted_dataset=converted_dataset,
                                                         dependencies=deps )
                
            elif original_dataset:
                # No name, so look up a provider name from datatype's information.

                # Dataset must have get_track_type function to get data.
                if not hasattr( original_dataset.datatype, 'get_track_type'):
                    return None
                
                # Get data provider mapping and data provider.
                _ , data_provider_mapping = original_dataset.datatype.get_track_type()
                if 'data_standalone' in data_provider_mapping:
                    data_provider_name = data_provider_mapping[ 'data_standalone' ]
                else:
                    data_provider_name = data_provider_mapping[ source ]
                
                data_provider = self.get_data_provider( trans, name=data_provider_name, original_dataset=original_dataset )

        return data_provider