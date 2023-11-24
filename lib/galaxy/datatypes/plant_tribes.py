import logging
import re

from galaxy.datatypes.data import (
    get_file_peek,
    Text,
)
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    get_headers,
)
from galaxy.datatypes.tabular import Tabular
from galaxy.util import nice_size

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class Smat(Text):
    file_ext = "smat"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return f"ESTScan scores matrices ({nice_size(dataset.get_size())})"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "ESTScan scores matrices"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
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
        fh = file_prefix.string_io()
        for line in fh:
            line_no += 1
            if line_no > 10000:
                return True
            if line_no == 1 and not line.startswith("FORMAT"):
                # The first line is always the start of a format section.
                return False
            if not line.startswith("FORMAT"):
                if line.find("\t") >= 0:
                    # Smat files are not tabular.
                    return False
                items = line.split()
                if len(items) != 4:
                    return False
                for item in items:
                    # Make sure each item is an integer.
                    if re.match(r"[-+]?\d+$", item) is None:
                        return False
        # Ensure at least a few matching lines are found.
        return line_no > 2


class PlantTribesKsComponents(Tabular):
    file_ext = "ptkscmp"
    MetadataElement(
        name="number_comp",
        default=0,
        desc="Number of significant components in the Ks distribution",
        readonly=True,
        visible=True,
        no_value=0,
    )

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return f"Significant components in the Ks distribution ({nice_size(dataset.get_size())})"

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of significant components in the Ks distribution.
        The dataset will always be on the order of less than 10 lines.
        """
        super().set_meta(dataset, overwrite=overwrite, **kwd)
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

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            if dataset.metadata.number_comp == 1:
                dataset.blurb = "1 significant component"
            else:
                dataset.blurb = f"{dataset.metadata.number_comp} significant components"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff(self, filename: str) -> bool:
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
            line_item_str = get_headers(filename, "\\t", 1)[0][0]
            return line_item_str == "species\tn\tnumber_comp\tlnL\tAIC\tBIC\tmean\tvariance\tporportion"
        except Exception:
            return False
