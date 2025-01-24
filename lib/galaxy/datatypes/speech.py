from galaxy.datatypes.data import Text
from galaxy.datatypes.metadata import (
    ListParameter,
    MetadataElement,
)
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import get_headers


class TextGrid(Text):
    """Praat Textgrid file for speech annotations

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('1_1119_2_22_001.textgrid')
    >>> TextGrid().sniff(fname)
    True
    >>> fname = get_test_fname('drugbank_drugs.cml')
    >>> TextGrid().sniff(fname)
    False

    """

    file_ext = "textgrid"
    header = 'File type = "ooTextFile"\nObject class = "TextGrid"\n'

    blurb = "Praat TextGrid file"

    MetadataElement(
        name="annotations",
        default=[],
        desc="Annotation types",
        param=ListParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )

    def sniff(self, filename: str) -> bool:
        with open(filename) as fd:
            text = fd.read(len(self.header))
            return text == self.header


class BPF(Text):
    """Munich BPF annotation format
    https://www.phonetik.uni-muenchen.de/Bas/BasFormatseng.html#Partitur

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('1_1119_2_22_001.par')
    >>> BPF().sniff(fname)
    True
    >>> fname = get_test_fname('1_1119_2_22_001-1.par')
    >>> BPF().sniff(fname)
    True
    >>> fname = get_test_fname('drugbank_drugs.cml')
    >>> BPF().sniff(fname)
    False

    """

    file_ext = "par"

    MetadataElement(
        name="annotations",
        default=[],
        desc="Annotation types",
        param=ListParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )
    mandatory_headers = ["LHD", "REP", "SNB", "SAM", "SBF", "SSB", "NCH", "SPN", "LBD"]
    optional_headers = [
        "FIL",
        "TYP",
        "DBN",
        "VOL",
        "DIR",
        "SRC",
        "BEG",
        "END",
        "RED",
        "RET",
        "RCC",
        "CMT",
        "SPI",
        "PCF",
        "PCN",
        "EXP",
        "SYS",
        "DAT",
        "SPA",
        "MAO",
        "GPO",
        "SAO",
    ]

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """Set the metadata for this dataset from the file contents"""
        types = set()
        with open(dataset.dataset.get_file_name()) as fd:
            for line in fd:
                # Split the line on a colon rather than regexing it
                parts = line.split(":")

                # And if the first part is a 3 character string, then it's
                # interesting.
                if len(parts) and len(parts[0]) == 3:
                    types.add(parts[0])
                else:
                    return

        dataset.metadata.annotations = list(types)

    def sniff(self, filename: str) -> bool:
        # We loop over 30 as there are 9 mandatory headers (the last should be
        # `LBD:`), while there are 21 optional headers that can be
        # interspersed.
        seen_headers = [line[0] for line in get_headers(filename, sep=":", count=40)]

        # We cut everything after LBD, where the headers end and contents
        # start. We choose not to validate contents.
        if "LBD" in seen_headers:
            seen_headers = seen_headers[0 : seen_headers.index("LBD") + 1]

        # Check that every mandatory header is present in the seen headers
        for header in self.mandatory_headers:
            if header not in seen_headers:
                return False

        # Check that every seen header is either in mandatory or optional
        for header in seen_headers:
            if not (header in self.mandatory_headers or header in self.optional_headers):
                return False

        return True
