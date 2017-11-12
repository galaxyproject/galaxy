import logging
import os
import re

from galaxy.datatypes.data import get_file_peek, Text
from galaxy.datatypes.metadata import MetadataElement, MetadataParameter
from galaxy.datatypes.sniff import get_headers
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.text import Html
from galaxy.util import nice_size

log = logging.getLogger(__name__)


class Smat(Text):
    file_ext = "smat"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "ESTScan scores matrices (%s)" % (nice_size(dataset.get_size()))

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name, is_multi_byte=is_multi_byte)
            dataset.blurb = "ESTScan scores matrices"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff(self, filename):
        """
        The use of ESTScan implies the creation of scores matrices which
        reflect the codons preferences in the studied organisms.  The
        ESTScan package includes scripts for generating these files.  The
        output of these scripts consists of the matrices, one for each
        isochor, and which look like this:

        FORMAT: hse_4is.conf CODING REGION 6 3 1 s C+G: 0 44
        -1 0 2 -2
        2 1 -8 0

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test_space.txt')
        >>> Smat().sniff(fname)
        False
        >>> fname = get_test_fname('test_tab.bed')
        >>> Smat().sniff(fname)
        False
        >>> fname = get_test_fname('1.smat')
        >>> Smat().sniff(fname)
        True
        """
        line_no = 0
        with open(filename, "r") as fh:
            for line in fh:
                line_no += 1
                if line_no > 10000:
                    return True
                if line_no == 1 and not line.startswith('FORMAT'):
                    # The first line is always the start of a format section.
                    return False
                if not line.startswith('FORMAT'):
                    if line.find('\t') >= 0:
                        # Smat files are not tabular.
                        return False
                    items = line.split()
                    if len(items) != 4:
                        return False
                    for item in items:
                        # Make sure each item is an integer.
                        if re.match(r"[-+]?\d+$", item) is None:
                            return False
        return True


class PlantTribes(Html):
    """
    PlantTribes abstract class.
    """
    composite_type = 'basic'
    MetadataElement(name="num_files", default=0, desc="Number of files in files_path directory", param=MetadataParameter, readonly=True, visible=False, no_value=0)

    def set_meta(self, dataset, overwrite=True, **kwd):
        try:
            efp = dataset.extra_files_path
            if os.path.exists(efp):
                dataset.metadata.num_files = len(os.listdir(efp))
        except Exception as e:
            log.warning("set_meta fname: %s %s" % (dataset.file_name if dataset and dataset.file_name else 'Unkwown', str(e)))


class PlantTribesKsComponents(Tabular):
    file_ext = "ptkscmp"
    MetadataElement(name="number_comp", default=0, desc="Number of significant components in the Ks distribution", readonly=True, visible=True, no_value=0)

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Significant components in the Ks distribution (%s)" % (nice_size(dataset.get_size()))

    def set_meta(self, dataset, **kwd):
        """
        Set the number of significant components in the Ks distribution.
        The dataset will always be on the order of less than 10 lines.
        """
        super(PlantTribesKsComponents, self).set_meta(dataset, **kwd)
        significant_components = []
        with open(dataset.file_name) as fh:
            for i, line in enumerate(fh):
                if i == 0:
                    # Skip the first line.
                    continue
                line = line.strip()
                items = line.split()
                try:
                    # Could be \t.
                    significant_components.append(int(items[2]))
                except Exception:
                    continue
        if len(significant_components) > 0:
            dataset.metadata.number_comp = max(significant_components)

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name, is_multi_byte=is_multi_byte)
            if (dataset.metadata.number_comp == 1):
                dataset.blurb = "1 significant component"
            else:
                dataset.blurb = "%s significant components" % dataset.metadata.number_comp
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff(self, filename):
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test_tab.bed')
        >>> PlantTribesKsComponents().sniff(fname)
        False
        >>> fname = get_test_fname('1.ptkscmp')
        >>> PlantTribesKsComponents().sniff(fname)
        True
        """
        try:
            line_item_str = get_headers(filename, '\\t', 1)[0][0]
            return line_item_str == 'species\tn\tnumber_comp\tlnL\tAIC\tBIC\tmean\tvariance\tporportion'
        except Exception:
            return False
