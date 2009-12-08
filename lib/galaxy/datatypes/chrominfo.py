import data
from galaxy import util
from galaxy.datatypes.sniff import *
from galaxy.web import url_for
from tabular import Tabular
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement


class ChromInfo( Tabular ):
    file_ext = "len"
    MetadataElement( name="chrom", default=1, desc="Chrom column", param=metadata.ColumnParameter )
    MetadataElement( name="length", default=2, desc="Length column", param=metadata.ColumnParameter )

