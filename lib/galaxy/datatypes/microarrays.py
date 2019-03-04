import logging
import subprocess

from galaxy.datatypes import data
from galaxy.datatypes.data import get_file_peek
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.util.generic_util import count_special_lines

log = logging.getLogger(__name__)


def count_lines(filename, non_empty=False):
    """
        counting the number of lines from the 'filename' file
    """
    try:
        out = subprocess.Popen(['wc', '-l', filename], stdout=subprocess.PIPE)
        return int(out.communicate()[0].split()[0])
    except Exception:
        pass
    return 0


class GenericMicroarrayFile(data.Text):
    """
    Abstract class for most of the microarray files.
    """
    MetadataElement(name="number_of_comments", default=1, desc="Number of comments", readonly=True, visible=True,
                    optional=True, no_value=0)
    MetadataElement(name="number_of_blocks", default=1, desc="Number of blocks", readonly=True, visible=True,
                    optional=True, no_value=0)
    MetadataElement(name="number_of_records", default=1, desc="Number of records", readonly=True, visible=True,
                    optional=True, no_value=0)

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            if dataset.metadata.number_of_blocks == 1:
                dataset.blurb = "1 block %s recodrs" % dataset.metadata.number_of_records
            else:
                dataset.blurb = "%s blocks %s recodrs" % (dataset.metadata.number_of_blocks, dataset.metadata.number_of_records)
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
        found_genepix = count_special_lines("GenePix", filename) >= 1
        found_atf = count_special_lines("ATF", filename) >= 1
        found_blockcount = count_special_lines("BlockCount", filename) >= 1
        if found_atf * found_genepix * found_blockcount:
            return True
        else:
            return False

    def set_meta(self, dataset, **kwd):
        """
        Set the number of blocks, in the case of Gpr its always one.
        """
        dataset.metadata.number_of_blocks = count_special_lines('^"Block[0-9]', dataset.file_name)
        dataset.metadata.number_of_comments = count_special_lines('^"', dataset.file_name) + 1
        dataset.metadata.number_of_records = count_lines(dataset.file_name) - dataset.metadata.number_of_comments - 2


class Gpr(GenericMicroarrayFile):
    """ Gpr File format described at:
        http://mdc.custhelp.com/app/answers/detail/a_id/18883/#gpr
    """

    edam_format = "format_3829"
    edam_data = "data_3110"
    file_ext = "gpr"

    def sniff(self, filename):
        """
        Try to guess if the file is a GPR file.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test.gpr')
        >>> Gpr().sniff(fname)
        True
        >>> fname = get_test_fname('test.gal')
        >>> Gpr().sniff(fname)
        False
        """
        found_genepix = count_special_lines("GenePix", filename) >= 1
        found_atf = count_special_lines("ATF", filename) >= 1
        found_blockcount = count_special_lines("BlockCount", filename) == 0
        if found_atf * found_genepix * found_blockcount:
            return True
        else:
            return False

    def set_meta(self, dataset, **kwd):
        """
        Set the number of blocks, in the case of Gpr its always one.
        """
        dataset.metadata.number_of_blocks = count_special_lines('^"Block', dataset.file_name)
        dataset.metadata.number_of_comments = count_special_lines('^"', dataset.file_name) + 1
        dataset.metadata.number_of_records = count_lines(dataset.file_name) - dataset.metadata.number_of_comments - 1
