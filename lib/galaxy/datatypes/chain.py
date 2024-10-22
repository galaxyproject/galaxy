"""
Genome browser alignment formats
"""

import logging

from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    get_headers,
)
from galaxy.util import (
    commaify,
    compression_utils,
    nice_size,
)
from . import data

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class Chain(data.Text):
    """Class describing a chain format alignment file"""

    edam_format = "format_3982"
    file_ext = "chain"

    strands = ["+", "-"]

    MetadataElement(
        name="chains", default=0, desc="Number of chains", readonly=True, visible=False, optional=False, no_value=0
    )

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of chains and the number of data lines in dataset.
        """
        data_lines = 0
        chains = 0
        with compression_utils.get_fileobj(dataset.get_file_name()) as fh:
            for line in fh:
                line = line.strip()
                if line and line.startswith("#"):
                    # We don't count comment lines for sequence data types
                    continue
                if line and line.startswith("chain"):
                    chains += 1
                    data_lines += 1
                else:
                    data_lines += 1
            dataset.metadata.data_lines = data_lines
            dataset.metadata.chains = chains

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            if dataset.metadata.chains:
                dataset.blurb = f"{commaify(str(dataset.metadata.chains))} chains"
            else:
                dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in chain format

        For complete details see https://genome.ucsc.edu/goldenPath/help/chain.html

        Rules for sniffing as True:

            We don't care about line length (other than empty lines).

            The first non-empty line must start with 'chain' and the Very Next line.strip() must have an alignment data line
            which consists of either 1 or 3 integers separated by spaces.

            The chain line must have at least 12 tokens representing the chain attributes.
            The 2 strand attributes must have values + or -. We verify that some of the
            other numeric attributes such as sequence length start/stop positions are
            integers.

            We will only check that the first chain and alignment data lines are formatted correctly.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'sequence.maf' )
        >>> Chain().sniff( fname )
        False
        >>> fname = get_test_fname( '1.chain' )
        >>> Chain().sniff( fname )
        True
        >>> fname = get_test_fname( '2.chain' )
        >>> Chain().sniff( fname )
        True
        >>>
        """
        headers = get_headers(file_prefix, None, count=2, comment_designator="#")
        if not (
            len(headers) == 2
            and len(headers[0]) in [12, 13]
            and headers[0][0] == "chain"
            and headers[0][1].isdecimal()
            and headers[0][3].isdecimal()
            and headers[0][4] in self.strands
            and headers[0][5].isdecimal()
            and headers[0][6].isdecimal()
            and headers[0][8].isdecimal()
            and headers[0][9] in self.strands
            and headers[0][10].isdecimal()
            and headers[0][11].isdecimal()
            and headers[1][0].isdecimal()
            and len(headers[1]) in [1, 3]
        ):
            return False
        else:
            return True


@build_sniff_from_prefix
class Net(data.Text):
    """Class describing a net format alignment file"""

    edam_format = "format_3983"
    file_ext = "ucsc.net"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in net format

        For details see https://genome.ucsc.edu/goldenPath/help/net.html

        Rules for sniffing as True:

            We don't care about line length (other than empty lines).

            The first non-empty line must start with 'net' followed by chromName (str) and chromSize (int)

            We will only check that the first "net" line and the first data line are formatted correctly.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( '1.chain' )
        >>> Net().sniff( fname )
        False
        >>> fname = get_test_fname( '1.ucsc.net' )
        >>> Net().sniff( fname )
        True
        >>>
        """
        allowed_classes = ["fill", "gap"]
        strands = ["+", "-"]

        headers = get_headers(file_prefix, None, count=2, comment_designator="#")
        if not (
            len(headers) == 2
            and len(headers[0]) == 3
            and headers[0][0] == "net"
            and headers[0][2].isdecimal()
            and len(headers[1]) >= 7  # seven fixed fields
            and len(headers[1]) <= 41  # plus seventeen optional name/value pairs
            and headers[1][0] in allowed_classes
            and headers[1][1].isdecimal()
            and headers[1][2].isdecimal()
            and headers[1][4] in strands
            and headers[1][5].isdecimal()
            and headers[1][6].isdecimal()
        ):
            return False
        else:
            return True
