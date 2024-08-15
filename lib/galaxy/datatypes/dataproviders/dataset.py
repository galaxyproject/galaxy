"""
Dataproviders that use either:
    - the file contents and/or metadata from a Galaxy DatasetInstance as
        their source.
    - or provide data in some way relevant to bioinformatic data
        (e.g. parsing genomic regions from their source)
"""

import logging
import sys

from bx import (
    seq as bx_seq,
    wiggle as bx_wig,
)

from galaxy.util import sqlite
from galaxy.util.compression_utils import get_fileobj
from . import (
    base,
    column,
    external,
    line,
)

_TODO = """
use bx as much as possible
gff3 hierarchies

change SamtoolsDataProvider to use pysam
"""

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------------- base for using a Glx dataset
class DatasetDataProvider(base.DataProvider):
    """
    Class that uses the file contents and/or metadata from a Galaxy DatasetInstance
    as its source.

    DatasetDataProvider can be seen as the intersection between a datatype's
    metadata and a dataset's file contents. It (so far) mainly provides helper
    and conv. methods for using dataset metadata to set up and control how
    the data is provided.
    """

    def __init__(self, dataset, **kwargs):
        """
        :param dataset: the Galaxy dataset whose file will be the source
        :type dataset: model.DatasetInstance
        """
        # precondition: dataset is a galaxy.model.DatasetInstance
        self.dataset = dataset
        # this dataset file is obviously the source
        # TODO: this might be a good place to interface with the object_store...
        mode = "rb" if dataset.datatype.is_binary else "r"
        super().__init__(get_fileobj(dataset.get_file_name(), mode))

    # TODO: this is a bit of a mess
    @classmethod
    def get_column_metadata_from_dataset(cls, dataset):
        """
        Convenience class method to get column metadata from a dataset.

        :returns: a dictionary of `column_count`, `column_types`, and `column_names`
            if they're available, setting each to `None` if not.
        """
        # re-map keys to fit ColumnarProvider.__init__ kwargs
        params = {}
        params["column_count"] = dataset.metadata.columns
        params["column_types"] = dataset.metadata.column_types
        params["column_names"] = dataset.metadata.column_names or getattr(dataset.datatype, "column_names", None)
        return params

    def get_metadata_column_types(self, indeces=None):
        """
        Return the list of `column_types` for this dataset or `None` if unavailable.

        :param indeces: the indeces for the columns of which to return the types.
            Optional: defaults to None (return all types)
        :type indeces: list of ints
        """
        metadata_column_types = (
            self.dataset.metadata.column_types or getattr(self.dataset.datatype, "column_types", None) or None
        )
        if not metadata_column_types:
            return metadata_column_types
        if indeces:
            column_types = []
            for index in indeces:
                column_type = metadata_column_types[index] if index < len(metadata_column_types) else None
                column_types.append(column_type)
            return column_types
        return metadata_column_types

    def get_metadata_column_names(self, indeces=None):
        """
        Return the list of `column_names` for this dataset or `None` if unavailable.

        :param indeces: the indeces for the columns of which to return the names.
            Optional: defaults to None (return all names)
        :type indeces: list of ints
        """
        metadata_column_names = (
            self.dataset.metadata.column_names or getattr(self.dataset.datatype, "column_names", None) or None
        )
        if not metadata_column_names:
            return metadata_column_names
        if indeces:
            column_names = []
            for index in indeces:
                column_type = metadata_column_names[index] if index < len(metadata_column_names) else None
                column_names.append(column_type)
            return column_names
        return metadata_column_names

    # TODO: merge the next two
    def get_indeces_by_column_names(self, list_of_column_names):
        """
        Return the list of column indeces when given a list of column_names.

        :param list_of_column_names: the names of the columns of which to get indeces.
        :type list_of_column_names: list of strs

        :raises KeyError: if column_names are not found
        :raises ValueError: if an entry in list_of_column_names is not in column_names
        """
        metadata_column_names = (
            self.dataset.metadata.column_names or getattr(self.dataset.datatype, "column_names", None) or None
        )
        if not metadata_column_names:
            raise KeyError(
                "No column_names found for " + f"datatype: {str(self.dataset.datatype)}, dataset: {str(self.dataset)}"
            )
        indeces = []  # if indeces and column_names:
        # pull using indeces and re-name with given names - no need to alter (does as super would)
        #    pass
        for column_name in list_of_column_names:
            indeces.append(metadata_column_names.index(column_name))
        return indeces

    def get_metadata_column_index_by_name(self, name):
        """
        Return the 1-base index of a sources column with the given `name`.
        """
        # metadata columns are 1-based indeces
        column = getattr(self.dataset.metadata, name)
        return (column - 1) if (isinstance(column, int) and column > 0) else None

    def get_genomic_region_indeces(self, check=False):
        """
        Return a list of column indeces for 'chromCol', 'startCol', 'endCol' from
        a source representing a genomic region.

        :param check: if True will raise a ValueError if any were not found.
        :type check: bool
        :raises ValueError: if check is `True` and one or more indeces were not found.
        :returns: list of column indeces for the named columns.
        """
        region_column_names = ("chromCol", "startCol", "endCol")
        region_indices = [self.get_metadata_column_index_by_name(name) for name in region_column_names]
        if check and not all(_ is not None for _ in region_indices):
            raise ValueError(f"Could not determine proper column indices for chrom, start, end: {str(region_indices)}")
        return region_indices


class ConvertedDatasetDataProvider(DatasetDataProvider):
    """
    Class that uses the file contents of a dataset after conversion to a different
    format.
    """

    def __init__(self, dataset, **kwargs):
        raise NotImplementedError("Abstract class")
        # self.original_dataset = dataset
        # self.converted_dataset = self.convert_dataset(dataset, **kwargs)
        # super(ConvertedDatasetDataProvider, self).__init__(self.converted_dataset, **kwargs)
        # NOTE: now self.converted_dataset == self.dataset

    def convert_dataset(self, dataset, **kwargs):
        """
        Convert the given dataset in some way.
        """
        return dataset


# ----------------------------------------------------------------------------- uses metadata for settings
class DatasetColumnarDataProvider(column.ColumnarDataProvider):
    """
    Data provider that uses a DatasetDataProvider as its source and the
    dataset's metadata to buuild settings for the ColumnarDataProvider it's
    inherited from.
    """

    def __init__(self, dataset, **kwargs):
        """
        All kwargs are inherited from ColumnarDataProvider.
        .. seealso:: column.ColumnarDataProvider

        If no kwargs are given, this class will attempt to get those kwargs
        from the dataset source's metadata.
        If any kwarg is given, it will override and be used in place of
        any metadata available.
        """
        dataset_source = DatasetDataProvider(dataset)
        if not kwargs.get("column_types", None):
            indeces = kwargs.get("indeces", None)
            kwargs["column_types"] = dataset_source.get_metadata_column_types(indeces=indeces)
        super().__init__(dataset_source, **kwargs)


class DatasetDictDataProvider(column.DictDataProvider):
    """
    Data provider that uses a DatasetDataProvider as its source and the
    dataset's metadata to buuild settings for the DictDataProvider it's
    inherited from.
    """

    def __init__(self, dataset, **kwargs):
        """
        All kwargs are inherited from DictDataProvider.
        .. seealso:: column.DictDataProvider

        If no kwargs are given, this class will attempt to get those kwargs
        from the dataset source's metadata.
        If any kwarg is given, it will override and be used in place of
        any metadata available.

        The relationship between column_names and indeces is more complex:
        +-----------------+-------------------------------+-----------------------+
        |                 | Indeces given                 | Indeces NOT given     |
        +=================+===============================+=======================+
        | Names given     | pull indeces, rename w/ names | pull by name          |
        +=================+-------------------------------+-----------------------+
        | Names NOT given | pull indeces, name w/ meta    | pull all, name w/meta |
        +=================+-------------------------------+-----------------------+
        """
        dataset_source = DatasetDataProvider(dataset)

        # TODO: getting too complicated - simplify at some lvl, somehow
        # if no column_types given, get column_types from indeces (or all if indeces == None)
        indeces = kwargs.get("indeces", None)
        column_names = kwargs.get("column_names", None)

        if not indeces and column_names:
            # pull columns by name
            indeces = kwargs["indeces"] = dataset_source.get_indeces_by_column_names(column_names)

        elif indeces and not column_names:
            # pull using indeces, name with meta
            column_names = kwargs["column_names"] = dataset_source.get_metadata_column_names(indeces=indeces)

        elif not indeces and not column_names:
            # pull all indeces and name using metadata
            column_names = kwargs["column_names"] = dataset_source.get_metadata_column_names(indeces=indeces)

        # if no column_types given, use metadata column_types
        if not kwargs.get("column_types", None):
            kwargs["column_types"] = dataset_source.get_metadata_column_types(indeces=indeces)

        super().__init__(dataset_source, **kwargs)


# ----------------------------------------------------------------------------- provides a bio-relevant datum
class GenomicRegionDataProvider(column.ColumnarDataProvider):
    """
    Data provider that parses chromosome, start, and end data from a file
    using the datasets metadata settings.

    Is a ColumnarDataProvider that uses a DatasetDataProvider as its source.

    If `named_columns` is true, will return dictionaries with the keys
    'chrom', 'start', 'end'.
    """

    # dictionary keys when named_columns=True
    COLUMN_NAMES = ["chrom", "start", "end"]
    settings = {
        "chrom_column": "int",
        "start_column": "int",
        "end_column": "int",
        "named_columns": "bool",
    }

    def __init__(self, dataset, chrom_column=None, start_column=None, end_column=None, named_columns=False, **kwargs):
        """
        :param dataset: the Galaxy dataset whose file will be the source
        :type dataset: model.DatasetInstance

        :param chrom_column: optionally specify the chrom column index
        :type chrom_column: int
        :param start_column: optionally specify the start column index
        :type start_column: int
        :param end_column: optionally specify the end column index
        :type end_column: int

        :param named_columns: optionally return dictionaries keying each column
            with 'chrom', 'start', or 'end'.
            Optional: defaults to False
        :type named_columns: bool
        """
        # TODO: allow passing in a string format e.g. "{chrom}:{start}-{end}"
        dataset_source = DatasetDataProvider(dataset)

        if chrom_column is None:
            chrom_column = dataset_source.get_metadata_column_index_by_name("chromCol")
        if start_column is None:
            start_column = dataset_source.get_metadata_column_index_by_name("startCol")
        if end_column is None:
            end_column = dataset_source.get_metadata_column_index_by_name("endCol")
        indeces = [chrom_column, start_column, end_column]
        if not all(_ is not None for _ in indeces):
            raise ValueError("Could not determine proper column indeces for" + f" chrom, start, end: {str(indeces)}")
        kwargs.update({"indeces": indeces})

        if not kwargs.get("column_types", None):
            kwargs.update({"column_types": dataset_source.get_metadata_column_types(indeces=indeces)})

        self.named_columns = named_columns
        if self.named_columns:
            self.column_names = self.COLUMN_NAMES

        super().__init__(dataset_source, **kwargs)

    def __iter__(self):
        parent_gen = super().__iter__()
        for column_values in parent_gen:
            if self.named_columns:
                yield dict(zip(self.column_names, column_values))
            else:
                yield column_values


# TODO: this optionally provides the same data as the above and makes GenomicRegionDataProvider redundant
#   GenomicRegionDataProvider is a better name, tho
class IntervalDataProvider(column.ColumnarDataProvider):
    """
    Data provider that parses chromosome, start, and end data (as well as strand
    and name if set in the metadata) using the dataset's metadata settings.

    If `named_columns` is true, will return dictionaries with the keys
    'chrom', 'start', 'end' (and 'strand' and 'name' if available).
    """

    COLUMN_NAMES = ["chrom", "start", "end", "strand", "name"]
    settings = {
        "chrom_column": "int",
        "start_column": "int",
        "end_column": "int",
        "strand_column": "int",
        "name_column": "int",
        "named_columns": "bool",
    }

    def __init__(
        self,
        dataset,
        chrom_column=None,
        start_column=None,
        end_column=None,
        strand_column=None,
        name_column=None,
        named_columns=False,
        **kwargs,
    ):
        """
        :param dataset: the Galaxy dataset whose file will be the source
        :type dataset: model.DatasetInstance

        :param named_columns: optionally return dictionaries keying each column
            with 'chrom', 'start', 'end', 'strand', or 'name'.
            Optional: defaults to False
        :type named_columns: bool
        """
        # TODO: allow passing in a string format e.g. "{chrom}:{start}-{end}"
        dataset_source = DatasetDataProvider(dataset)

        # get genomic indeces and add strand and name
        self.column_names = []
        indeces = []
        # TODO: this is sort of involved and oogly
        if chrom_column is None:
            chrom_column = dataset_source.get_metadata_column_index_by_name("chromCol")
            if chrom_column is not None:
                self.column_names.append("chrom")
                indeces.append(chrom_column)
        if start_column is None:
            start_column = dataset_source.get_metadata_column_index_by_name("startCol")
            if start_column is not None:
                self.column_names.append("start")
                indeces.append(start_column)
        if end_column is None:
            end_column = dataset_source.get_metadata_column_index_by_name("endCol")
            if end_column is not None:
                self.column_names.append("end")
                indeces.append(end_column)
        if strand_column is None:
            strand_column = dataset_source.get_metadata_column_index_by_name("strandCol")
            if strand_column is not None:
                self.column_names.append("strand")
                indeces.append(strand_column)
        if name_column is None:
            name_column = dataset_source.get_metadata_column_index_by_name("nameCol")
            if name_column is not None:
                self.column_names.append("name")
                indeces.append(name_column)

        kwargs.update({"indeces": indeces})
        if not kwargs.get("column_types", None):
            kwargs.update({"column_types": dataset_source.get_metadata_column_types(indeces=indeces)})

        self.named_columns = named_columns

        super().__init__(dataset_source, **kwargs)

    def __iter__(self):
        parent_gen = super().__iter__()
        for column_values in parent_gen:
            if self.named_columns:
                yield dict(zip(self.column_names, column_values))
            else:
                yield column_values


# TODO: ideally with these next two - you'd allow pulling some region from the sequence
#   WITHOUT reading the entire seq into memory - possibly apply some version of limit/offset
class FastaDataProvider(base.FilteredDataProvider):
    """
    Class that returns fasta format data in a list of maps of the form::

        {
            id: <fasta header id>,
            sequence: <joined lines of nucleotide/amino data>
        }
    """

    settings = {
        "ids": "list:str",
    }

    def __init__(self, source, ids=None, **kwargs):
        """
        :param ids: optionally return only ids (and sequences) that are in this list.
            Optional: defaults to None (provide all ids)
        :type ids: list or None
        """
        source = bx_seq.fasta.FastaReader(source)
        # TODO: validate is a fasta
        super().__init__(source, **kwargs)
        self.ids = ids
        # how to do ids?

    def __iter__(self):
        parent_gen = super().__iter__()
        for fasta_record in parent_gen:
            yield {"id": fasta_record.name, "seq": fasta_record.text}


class TwoBitFastaDataProvider(DatasetDataProvider):
    """
    Class that returns fasta format data in a list of maps of the form::

        {
            id: <fasta header id>,
            sequence: <joined lines of nucleotide/amino data>
        }
    """

    settings = {
        "ids": "list:str",
    }

    def __init__(self, source, ids=None, **kwargs):
        """
        :param ids: optionally return only ids (and sequences) that are in this list.
            Optional: defaults to None (provide all ids)
        :type ids: list or None
        """
        source = bx_seq.twobit.TwoBitFile(source)
        # TODO: validate is a 2bit
        super(FastaDataProvider, self).__init__(source, **kwargs)
        # could do in order provided with twobit
        self.ids = ids or self.source.keys()

    def __iter__(self):
        for id_ in self.ids:
            yield {"id": id_, "seq": self.source[id_]}


# TODO:
class WiggleDataProvider(base.LimitedOffsetDataProvider):
    """
    Class that returns chrom, pos, data from a wiggle source.
    """

    COLUMN_NAMES = ["chrom", "pos", "value"]
    settings = {
        "named_columns": "bool",
        "column_names": "list:str",
    }

    def __init__(self, source, named_columns=False, column_names=None, **kwargs):
        """
        :param named_columns: optionally return dictionaries keying each column
            with 'chrom', 'start', 'end', 'strand', or 'name'.
            Optional: defaults to False
        :type named_columns: bool

        :param column_names: an ordered list of strings that will be used as the keys
            for each column in the returned dictionaries.
            The number of key, value pairs each returned dictionary has will
            be as short as the number of column names provided.
        :type column_names:
        """
        # TODO: validate is a wig
        # still good to maintain a ref to the raw source bc Reader won't
        self.raw_source = source
        self.parser = bx_wig.Reader(source)
        super().__init__(self.parser, **kwargs)

        self.named_columns = named_columns
        self.column_names = column_names or self.COLUMN_NAMES

    def __iter__(self):
        parent_gen = super().__iter__()
        for three_tuple in parent_gen:
            if self.named_columns:
                yield dict(zip(self.column_names, three_tuple))
            else:
                # list is not strictly necessary - but consistent
                yield list(three_tuple)


class BigWigDataProvider(base.LimitedOffsetDataProvider):
    """
    Class that returns chrom, pos, data from a wiggle source.
    """

    COLUMN_NAMES = ["chrom", "pos", "value"]
    settings = {
        "named_columns": "bool",
        "column_names": "list:str",
    }

    def __init__(self, source, chrom, start, end, named_columns=False, column_names=None, **kwargs):
        """

        :param chrom: which chromosome within the bigbed file to extract data for
        :type chrom: str
        :param start: the start of the region from which to extract data
        :type start: int
        :param end: the end of the region from which to extract data
        :type end: int

        :param named_columns: optionally return dictionaries keying each column
                              with 'chrom', 'start', 'end', 'strand', or 'name'.
                              Optional: defaults to False
        :type named_columns: bool

        :param column_names: an ordered list of strings that will be used as the keys
                             for each column in the returned dictionaries.
                             The number of key, value pairs each returned dictionary has will
                             be as short as the number of column names provided.
        :type column_names:

        """
        raise NotImplementedError("Work in progress")
        # TODO: validate is a wig
        # still good to maintain a ref to the raw source bc Reader won't
        # self.raw_source = source
        # self.parser = bx_bbi.bigwig_file.BigWigFile(source)
        # super(BigWigDataProvider, self).__init__(self.parser, **kwargs)

        # self.named_columns = named_columns
        # self.column_names = column_names or self.COLUMN_NAMES

    def __iter__(self):
        parent_gen = super().__iter__()
        for three_tuple in parent_gen:
            if self.named_columns:
                yield dict(zip(self.column_names, three_tuple))
            else:
                # list is not strictly necessary - but consistent
                yield list(three_tuple)


# ----------------------------------------------------------------------------- binary, external conversion or tool
class DatasetSubprocessDataProvider(external.SubprocessDataProvider):
    """
    Create a source from running a subprocess on a dataset's file.

    Uses a subprocess as its source and has a dataset (gen. as an input file
    for the process).
    """

    # TODO: below should be a subclass of this and not RegexSubprocess

    def __init__(self, dataset, *args, **kwargs):
        """
        :param args: the list of strings used to build commands.
        :type args: variadic function args
        """
        raise NotImplementedError("Abstract class")
        # super(DatasetSubprocessDataProvider, self).__init__(*args, **kwargs)
        # self.dataset = dataset


class SamtoolsDataProvider(line.RegexLineDataProvider):
    """
    Data provider that uses samtools on a Sam or Bam file as its source.

    This can be piped through other providers (column, map, genome region, etc.).

    .. note:: that only the samtools 'view' command is currently implemented.
    """

    FLAGS_WO_ARGS = "bhHSu1xXcB"
    FLAGS_W_ARGS = "fFqlrs"
    VALID_FLAGS = FLAGS_WO_ARGS + FLAGS_W_ARGS

    def __init__(self, dataset, options_string="", options_dict=None, regions=None, **kwargs):
        """
        :param options_string: samtools options in string form (flags separated
            by spaces)
            Optional: defaults to ''
        :type options_string: str
        :param options_dict: dictionary of samtools options
            Optional: defaults to None
        :type options_dict: dict or None
        :param regions: list of samtools regions strings
            Optional: defaults to None
        :type regions: list of str or None
        """
        # TODO: into validate_source

        # precondition: dataset.datatype is a tabular.Sam or binary.Bam
        self.dataset = dataset

        options_dict = options_dict or {}
        # ensure regions are strings
        regions = [str(r) for r in regions] if regions else []

        # TODO: view only for now
        # TODO: not properly using overriding super's validate_opts, command here
        subcommand = "view"
        # TODO:?? do we need a path to samtools?
        subproc_args = self.build_command_list(subcommand, options_string, options_dict, regions)
        # TODO: the composition/inheritance here doesn't make a lot sense
        subproc_provider = external.SubprocessDataProvider(*subproc_args)
        super().__init__(subproc_provider, **kwargs)

    def build_command_list(self, subcommand, options_string, options_dict, regions):
        """
        Convert all init args to list form.
        """
        command = ["samtools", subcommand]
        # add options and switches, input file, regions list (if any)
        command.extend(self.to_options_list(options_string, options_dict))
        command.append(self.dataset.get_file_name())
        command.extend(regions)
        return command

    def to_options_list(self, options_string, options_dict):
        """
        Convert both options_string and options_dict to list form
        while filtering out non-'valid' options.
        """
        opt_list = []

        # strip out any user supplied bash switch formating -> string of option chars
        #   then compress to single option string of unique, VALID flags with prefixed bash switch char '-'
        options_string = options_string.strip("- ")
        validated_flag_list = {flag for flag in options_string if flag in self.FLAGS_WO_ARGS}

        # if sam add -S
        # TODO: not the best test in the world...
        if (self.dataset.ext == "sam") and ("S" not in validated_flag_list):
            validated_flag_list.append("S")

        if validated_flag_list:
            opt_list.append(f"-{''.join(validated_flag_list)}")

        for flag, arg in options_dict.items():
            if flag in self.FLAGS_W_ARGS:
                opt_list.extend([f"-{flag}", str(arg)])

        return opt_list

    @classmethod
    def extract_options_from_dict(cls, dictionary):
        """
        Separrates valid samtools key/value pair options from a dictionary and
        returns both as a 2-tuple.
        """
        # handy for extracting options from kwargs - but otherwise...
        # TODO: could be abstracted to util.extract( dict, valid_keys_list )
        options_dict = {}
        new_kwargs = {}
        for key, value in dictionary.items():
            if key in cls.FLAGS_W_ARGS:
                options_dict[key] = value
            else:
                new_kwargs[key] = value
        return options_dict, new_kwargs


class SQliteDataProvider(base.DataProvider):
    """
    Data provider that uses a sqlite database file as its source.

    Allows any query to be run and returns the resulting rows as sqlite3 row objects
    """

    settings = {"query": "str"}

    def __init__(self, source, query=None, **kwargs):
        self.query = query
        self.connection = sqlite.connect(source.dataset.get_file_name())
        super().__init__(source, **kwargs)

    def __iter__(self):
        if (self.query is not None) and sqlite.is_read_only_query(self.query):
            yield from self.connection.cursor().execute(self.query)
        else:
            yield


class SQliteDataTableProvider(base.DataProvider):
    """
    Data provider that uses a sqlite database file as its source.
    Allows any query to be run and returns the resulting rows as arrays of arrays
    """

    settings = {"query": "str", "headers": "bool", "limit": "int"}

    def __init__(self, source, query=None, headers=False, limit=sys.maxsize, **kwargs):
        self.query = query
        self.headers = headers
        self.limit = limit
        self.connection = sqlite.connect(source.dataset.get_file_name())
        super().__init__(source, **kwargs)

    def __iter__(self):
        if (self.query is not None) and sqlite.is_read_only_query(self.query):
            cur = self.connection.cursor()
            results = cur.execute(self.query)
            if self.headers:
                yield [col[0] for col in cur.description]
            for i, row in enumerate(results):
                if i >= self.limit:
                    break
                yield list(row)
        else:
            yield


class SQliteDataDictProvider(base.DataProvider):
    """
    Data provider that uses a sqlite database file as its source.
    Allows any query to be run and returns the resulting rows as arrays of dicts
    """

    settings = {"query": "str"}

    def __init__(self, source, query=None, **kwargs):
        self.query = query
        self.connection = sqlite.connect(source.dataset.get_file_name())
        super().__init__(source, **kwargs)

    def __iter__(self):
        if (self.query is not None) and sqlite.is_read_only_query(self.query):
            cur = self.connection.cursor()
            for row in cur.execute(self.query):
                yield [{cur.description[i][0]: value for i, value in enumerate(row)}]
        else:
            yield
