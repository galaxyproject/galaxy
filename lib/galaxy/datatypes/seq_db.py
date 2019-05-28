"""Sequence database datatypes (e.g. kmer fingerprints)."""
from .data import Data


class KaijuDB(Data):
    """Compound datatype for multi-file Kaiju database."""
    file_ext = 'kaiju_db'
    allow_datatype_change = False
    composite_type = 'basic'

    def __init__(self, **kwd):
        Data.__init__(self, **kwd)
        self.add_composite_file('kaiju_library.fmi', is_binary=True)  # database
        self.add_composite_file('nodes.dmp', optional=True)  # NCBI taxonomy
        self.add_composite_file('names.dmp', optional=True)  # NCBI taxonomy

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "Kaiju database (multiple files)"
            dataset.blurb = "Kaiju database (multiple files)"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "Kaiju database (multiple files)"

    def display_data(self, trans, data, preview=False, filename=None,
                     to_ext=None, size=None, offset=None, **kwd):
        """Display data in the central pane via the "eye" icon."""
        return "Kaiju database (multiple files)"

    def merge(split_files, output_file):
        """Merge Kaiju databases (not implemented)."""
        raise NotImplementedError("Merging Kaiju databases is not supported")

    def split(cls, input_datasets, subdir_generator_function, split_params):
        """Split a Kaiju database (not implemented)."""
        if split_params is None:
            return None
        raise NotImplementedError("Can't split Kaiju databases")


class KrakenDB(Data):
    """Compound datatype for multi-file Kraken database."""
    file_ext = 'kraken_db'
    allow_datatype_change = False
    composite_type = 'basic'

    def __init__(self, **kwd):
        Data.__init__(self, **kwd)
        self.add_composite_file('database.kdb', is_binary=True)  # kmer database
        self.add_composite_file('database.idx', is_binary=True)  # index
        # TODO: Can we add taxonomy/names.dmp and taxonomy/nodes.dmp here?

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "Kraken database (multiple files)"
            dataset.blurb = "Kraken database (multiple files)"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "Kraken database (multiple files)"

    def display_data(self, trans, data, preview=False, filename=None,
                     to_ext=None, size=None, offset=None, **kwd):
        """Display data in the central pane via the "eye" icon."""
        return "Kraken database (multiple files)"

    def merge(split_files, output_file):
        """Merge Kraken databases (not implemented)."""
        raise NotImplementedError("Merging Kraken databases is not supported")

    def split(cls, input_datasets, subdir_generator_function, split_params):
        """Split a Kraken database (not implemented)."""
        if split_params is None:
            return None
        raise NotImplementedError("Can't split Kraken databases")
