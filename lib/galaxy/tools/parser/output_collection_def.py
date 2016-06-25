""" This module define an abstract class for reasoning about Galaxy's
dataset collection after jobs are finished.
"""

from galaxy.util import asbool

DEFAULT_EXTRA_FILENAME_PATTERN = r"primary_DATASET_ID_(?P<designation>[^_]+)_(?P<visible>[^_]+)_(?P<ext>[^_]+)(_(?P<dbkey>[^_]+))?"
DEFAULT_SORT_BY = "filename"
DEFAULT_SORT_COMP = "lexical"


# XML can describe custom patterns, but these literals describe named
# patterns that will be replaced.
NAMED_PATTERNS = {
    "__default__": DEFAULT_EXTRA_FILENAME_PATTERN,
    "__name__": r"(?P<name>.*)",
    "__designation__": r"(?P<designation>.*)",
    "__name_and_ext__": r"(?P<name>.*)\.(?P<ext>[^\.]+)?",
    "__designation_and_ext__": r"(?P<designation>.*)\.(?P<ext>[^\._]+)?",
}

INPUT_DBKEY_TOKEN = "__input__"
LEGACY_DEFAULT_DBKEY = None  # don't use __input__ for legacy default collection


def dataset_collector_descriptions_from_elem( elem, legacy=True ):
    primary_dataset_elems = elem.findall( "discover_datasets" )
    if len(primary_dataset_elems) == 0 and legacy:
        return [ DEFAULT_DATASET_COLLECTOR_DESCRIPTION ]
    else:
        return map( lambda elem: DatasetCollectionDescription( **elem.attrib ), primary_dataset_elems )


def dataset_collector_descriptions_from_list( discover_datasets_dicts ):
    return map( lambda kwds: DatasetCollectionDescription( **kwds ), discover_datasets_dicts )


class DatasetCollectionDescription(object):

    def __init__( self, **kwargs ):
        pattern = kwargs.get( "pattern", "__default__" )
        if pattern in NAMED_PATTERNS:
            pattern = NAMED_PATTERNS.get( pattern )
        self.pattern = pattern
        self.default_dbkey = kwargs.get( "dbkey", INPUT_DBKEY_TOKEN )
        self.default_ext = kwargs.get( "ext", None )
        if self.default_ext is None and "format" in kwargs:
            self.default_ext = kwargs.get( "format" )
        self.default_visible = asbool( kwargs.get( "visible", None ) )
        self.directory = kwargs.get( "directory", None )
        self.assign_primary_output = asbool( kwargs.get( 'assign_primary_output', False ) )
        sort_by = kwargs.get( "sort_by", DEFAULT_SORT_BY )
        if sort_by.startswith("reverse_"):
            self.sort_reverse = True
            sort_by = sort_by[len("reverse_"):]
        else:
            self.sort_reverse = False
        if "_" in sort_by:
            sort_comp, sort_by = sort_by.split("_", 1)
            assert sort_comp in ["lexical", "numeric"]
        else:
            sort_comp = DEFAULT_SORT_COMP
        assert sort_by in [
            "filename",
            "name",
            "designation",
            "dbkey"
        ]
        self.sort_key = sort_by
        self.sort_comp = sort_comp

DEFAULT_DATASET_COLLECTOR_DESCRIPTION = DatasetCollectionDescription(
    default_dbkey=LEGACY_DEFAULT_DBKEY,
)
