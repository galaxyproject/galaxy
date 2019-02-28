import re

from galaxy.datatypes.text import Text
from galaxy.datatypes.metadata import MetadataElement, ListParameter


class TextGrid( Text ):
    """Praat Textgrid file for speech annotations

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('1_1119_2_22_001.TextGrid')
    >>> TextGrid().sniff(fname)
    True

    >>> fname = get_test_fname('drugbank_drugs.cml')
    >>> TextGrid().sniff(fname)
    False

    """

    file_ext = "textgrid"
    header = 'File type = "ooTextFile"\nObject class = "TextGrid"\n'

    blurb = "Praat TextGrid file"

    MetadataElement( name="annotations", default=[], desc="Annotation types", param=ListParameter, readonly=True, visible=True, optional=True, no_value=[] )

    def sniff(self, filename):

        with open(filename, 'r') as fd:
            text = fd.read(len(self.header))

            return text == self.header

        return False


class BPF( Text ):
    """Munich BPF annotation format
    https://www.phonetik.uni-muenchen.de/Bas/BasFormatseng.html#Partitur

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('1_1119_2_22_001.par')
    >>> BPF().sniff(fname)
    True

    >>> fname = get_test_fname('drugbank_drugs.cml')
    >>> BPF().sniff(fname)
    False

    """

    file_ext = "par"

    MetadataElement( name="annotations", default=[], desc="Annotation types", param=ListParameter, readonly=True, visible=True, optional=True, no_value=[] )

    def set_meta( self, dataset, overwrite=True, **kwd ):
        """Set the metadata for this dataset from the file contents"""

        types = set()
        with open(dataset.dataset.file_name, 'r') as fd:
            for line in fd:
                match = re.match("([A-Z]+):\s", line)
                if match is None:
                    return False
                types.add(match.group(1))
        dataset.metadata.annotations = list(types)

    def sniff(self, filename):
        with open(filename, 'r') as fd:
            for line in fd:
                match = re.match("(LHD|REP|SNB|SAM|SBF|SSB|NCH|SPN|LBD|FIL|TYP|DBN|VOL|DIR|SRC|BEG|END|RED|RET|RCC|CMT|SPI|PCF|PCN|EXP|SYS|DAT|SPA|MAO|GPO|SAO|PTR|ORT|TRL|TR2|SUP|PHO|SAP|TRS|GES|USH|USM|OCC|USP|TLN|PRM|TRW|MAS|SPK):\s", line)
                return match is not None
        # in case the file is empty
        return False
