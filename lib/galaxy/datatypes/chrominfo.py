import galaxy.datatypes.metadata
import galaxy.datatypes.tabular
from galaxy.datatypes.metadata import MetadataElement


class ChromInfo(galaxy.datatypes.tabular.Tabular):
    file_ext = "len"
    MetadataElement(name="chrom", default=1, desc="Chrom column", param=galaxy.datatypes.metadata.ColumnParameter)
    MetadataElement(name="length", default=2, desc="Length column", param=galaxy.datatypes.metadata.ColumnParameter)
