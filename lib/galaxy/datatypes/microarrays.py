import logging

from galaxy.datatypes import data
from galaxy.datatypes.data import get_file_peek
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.sniff import iter_headers

log = logging.getLogger(__name__)


class GenericMicroarrayFile(data.Text):
    """
    Abstract class for most of the microarray files.
    """
    MetadataElement(name="version_number", default="1.0", desc="Version number", readonly=True, visible=True,
                    optional=True, no_value="1.0")
    MetadataElement(name="file_format", default="ATF", desc="File format", readonly=True, visible=True,
                    optional=True, no_value="ATF")
    MetadataElement(name="number_of_optional_header_records", default=1, desc="Number of optional header records",
                    readonly=True, visible=True, optional=True, no_value=1)
    MetadataElement(name="number_of_data_columns", default=1, desc="Number of data columns",
                    readonly=True, visible=True,
                    optional=True, no_value=1)
    MetadataElement(name="file_type", default="GenePix", desc="File type",
                    readonly=True, visible=True,
                    optional=True, no_value="GenePix")
    MetadataElement(name="block_count", default=1, desc="Number of blocks described in the file",
                    readonly=True, visible=True,
                    optional=True, no_value=1)
    MetadataElement(name="block_type", default=0, desc="Type of block",
                    readonly=True, visible=True,
                    optional=True, no_value=0)

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            if dataset.metadata.block_count == 1:
                dataset.blurb = "%s %s: Format %s, 1 block, %s headers and %s columns" % (dataset.metadata.file_type, dataset.metadata.version_number, dataset.metadata.file_format, dataset.metadata.number_of_optional_header_records, dataset.metadata.number_of_data_columns)
            else:
                dataset.blurb = "%s %s: Format %s, %s blocks, %s headers and %s columns" % (dataset.metadata.file_type, dataset.metadata.version_number, dataset.metadata.file_format, dataset.metadata.block_count, dataset.metadata.number_of_optional_header_records, dataset.metadata.number_of_data_columns)
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def get_mime(self):
        return 'text/plain'


class Gal(GenericMicroarrayFile):
    """ Gal File format described at:
            http://mdc.custhelp.com/app/answers/detail/a_id/18883/#gal
    """

    edam_format = "format_3829"
    edam_data = "data_3110"
    file_ext = "gal"

    def sniff(self, filename):
        """
        Try to guess if the file is a Gal file.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test.gal')
        >>> Gal().sniff(fname)
        True
        >>> fname = get_test_fname('test.gpr')
        >>> Gal().sniff(fname)
        False
        """
        header = iter_headers(filename, sep="\t", count=3)
        count = 0
        found_gal = False
        found_atf = False
        for line in header:
            if count == 0:
                if "ATF" in line[0]:
                    found_atf = True
            elif count == 2:
                if "GenePix ArrayList" in line[0]:
                    found_gal = True
            count += 1
        return found_gal and found_atf

    def set_meta(self, dataset, **kwd):
        """
        Set metadata for Gal file.
        """
        super(Gal, self).set_meta(dataset, **kwd)
        header = iter_headers(dataset.file_name, sep="\t", count=5)
        count = 0
        for line in header:
            if count == 0:
                dataset.metadata.file_format = str(line[0])
                dataset.metadata.version_number = str(line[1])
            elif count == 1:
                dataset.metadata.number_of_optional_header_records = int(line[0])
                dataset.metadata.number_of_data_columns = int(line[1])
            elif count == 2:
                dataset.metadata.file_type = str(line[0].strip().replace('"', '').split("=")[1])
            elif count == 3:
                if "BlockCount" in line[0]:
                    dataset.metadata.block_count = int(line[0].strip().replace('"', '').split("=")[1])
            elif count == 4:
                if "BlockType" in line[0]:
                    dataset.metadata.block_type = int(line[0].strip().replace('"', '').split("=")[1])
            count += 1


class Gpr(GenericMicroarrayFile):
    """ Gpr File format described at:
            http://mdc.custhelp.com/app/answers/detail/a_id/18883/#gpr
    """

    edam_format = "format_3829"
    edam_data = "data_3110"
    file_ext = "gpr"

    def sniff(self, filename):
        """
        Try to guess if the file is a Gpr file.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test.gpr')
        >>> Gpr().sniff(fname)
        True
        >>> fname = get_test_fname('test.gal')
        >>> Gpr().sniff(fname)
        False
        """
        header = iter_headers(filename, sep="\t", count=3)
        count = 0
        found_gpr = False
        found_atf = False
        for line in header:
            if count == 0:
                if "ATF" in line[0]:
                    found_atf = True
            elif count == 2:
                if "GenePix Results" in line[0]:
                    found_gpr = True
            count += 1
        return found_atf and found_gpr

    def set_meta(self, dataset, **kwd):
        """
        Set metadata for Gpr file.
        """
        super(Gpr, self).set_meta(dataset, **kwd)
        header = iter_headers(dataset.file_name, sep="\t", count=5)
        count = 0
        for line in header:
            if count == 0:
                dataset.metadata.file_format = str(line[0])
                dataset.metadata.version_number = str(line[1])
            elif count == 1:
                dataset.metadata.number_of_optional_header_records = int(line[0])
                dataset.metadata.number_of_data_columns = int(line[1])
            elif count == 2:
                dataset.metadata.file_type = str(line[0].strip().replace('"', '').split("=")[1])
            count += 1
