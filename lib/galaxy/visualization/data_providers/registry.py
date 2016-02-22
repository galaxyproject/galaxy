from six import string_types

from galaxy.visualization.data_providers.basic import ColumnDataProvider
from galaxy.visualization.data_providers import genome
from galaxy.model import NoConverterException
from galaxy.visualization.data_providers.phyloviz import PhylovizDataProvider
from galaxy.datatypes.tabular import Tabular, Vcf
from galaxy.datatypes.interval import Interval, ENCODEPeak, ChromatinInteractions, Gtf, Gff, Bed
from galaxy.datatypes.xml import Phyloxml
from galaxy.datatypes.data import Newick, Nexus


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
                Vcf: genome.VcfTabixDataProvider,
                Bed: genome.BedTabixDataProvider,
                Gtf: genome.GtfTabixDataProvider,
                ENCODEPeak: genome.ENCODEPeakTabixDataProvider,
                Interval: genome.IntervalTabixDataProvider,
                ChromatinInteractions: genome.ChromatinInteractionsTabixDataProvider,
                "default" : genome.TabixDataProvider
            },
            "interval_index": genome.IntervalIndexDataProvider,
            "bai": genome.BamDataProvider,
            "bam": genome.SamDataProvider,
            "bigwig": genome.BigWigDataProvider,
            "bigbed": genome.BigBedDataProvider,

            "column_with_stats": ColumnDataProvider
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
                data_provider_class = genome.RawGFFDataProvider
            elif isinstance( original_dataset.datatype, Bed ):
                data_provider_class = genome.RawBedDataProvider
            elif isinstance( original_dataset.datatype, Vcf ):
                data_provider_class = genome.RawVcfDataProvider
            elif isinstance( original_dataset.datatype, Tabular ):
                data_provider_class = ColumnDataProvider
            elif isinstance( original_dataset.datatype, ( Nexus, Newick, Phyloxml ) ):
                data_provider_class = PhylovizDataProvider

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

                # Dataset must have data sources to get data.
                if not original_dataset.datatype.data_sources:
                    return None

                # Get data provider mapping and data provider.
                data_provider_mapping = original_dataset.datatype.data_sources
                if 'data_standalone' in data_provider_mapping:
                    data_provider = self.get_data_provider( trans,
                                                            name=data_provider_mapping[ 'data_standalone' ],
                                                            original_dataset=original_dataset )
                else:
                    source_list = data_provider_mapping[ source ]
                    if isinstance( source_list, string_types ):
                        source_list = [ source_list ]

                    # Find a valid data provider in the source list.
                    for source in source_list:
                        try:
                            data_provider = self.get_data_provider( trans, name=source, original_dataset=original_dataset )
                            break
                        except NoConverterException:
                            pass

        return data_provider
