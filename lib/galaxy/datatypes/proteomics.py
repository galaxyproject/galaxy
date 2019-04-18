"""
Proteomics Datatypes
"""
import logging
import re

from galaxy.datatypes import data
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.data import Text
from galaxy.datatypes.sniff import build_sniff_from_prefix
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.xml import GenericXml
from galaxy.util import nice_size


log = logging.getLogger(__name__)


class Wiff(Binary):
    """Class for wiff files."""
    edam_data = "data_2536"
    edam_format = "format_3710"
    file_ext = 'wiff'
    allow_datatype_change = False
    composite_type = 'auto_primary_file'

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)

        self.add_composite_file(
            'wiff',
            description='AB SCIEX files in .wiff format. This can contain all needed information or only metadata.',
            is_binary=True)

        self.add_composite_file(
            'wiff_scan',
            description='AB SCIEX spectra file (wiff.scan), if the corresponding .wiff file only contains metadata.',
            optional='True', is_binary=True)

    def generate_primary_file(self, dataset=None):
        rval = ['<html><head><title>Wiff Composite Dataset </title></head><p/>']
        rval.append('<div>This composite dataset is composed of the following files:<p/><ul>')
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            if composite_file.get('description'):
                rval.append('<li><a href="%s" type="text/plain">%s (%s)</a>%s</li>' % (fn, fn, composite_file.get('description'), opt_text))
            else:
                rval.append('<li><a href="%s" type="text/plain">%s</a>%s</li>' % (fn, fn, opt_text))
        rval.append('</ul></div></html>')
        return "\n".join(rval)


class PepXmlReport(Tabular):
    """pepxml converted to tabular report"""
    edam_data = "data_2536"
    file_ext = "pepxml.tsv"

    def __init__(self, **kwd):
        super(PepXmlReport, self).__init__(**kwd)
        self.column_names = ['Protein', 'Peptide', 'Assumed Charge', 'Neutral Pep Mass (calculated)', 'Neutral Mass', 'Retention Time', 'Start Scan', 'End Scan', 'Search Engine', 'PeptideProphet Probability', 'Interprophet Probability']

    def display_peek(self, dataset):
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)


class ProtXmlReport(Tabular):
    """protxml converted to tabular report"""
    edam_data = "data_2536"
    file_ext = "protxml.tsv"
    comment_lines = 1

    def __init__(self, **kwd):
        super(ProtXmlReport, self).__init__(**kwd)
        self.column_names = [
            "Entry Number", "Group Probability",
            "Protein", "Protein Link", "Protein Probability",
            "Percent Coverage", "Number of Unique Peptides",
            "Total Independent Spectra", "Percent Share of Spectrum ID's",
            "Description", "Protein Molecular Weight", "Protein Length",
            "Is Nondegenerate Evidence", "Weight", "Precursor Ion Charge",
            "Peptide sequence", "Peptide Link", "NSP Adjusted Probability",
            "Initial Probability", "Number of Total Termini",
            "Number of Sibling Peptides Bin", "Number of Instances",
            "Peptide Group Designator", "Is Evidence?"]

    def display_peek(self, dataset):
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)


class ProteomicsXml(GenericXml):
    """ An enhanced XML datatype used to reuse code across several
    proteomic/mass-spec datatypes. """
    edam_data = "data_2536"
    edam_format = "format_2032"

    def sniff_prefix(self, file_prefix):
        """ Determines whether the file is the correct XML type. """
        contents = file_prefix.string_io()
        while True:
            line = contents.readline()
            if line is None or not line.startswith('<?'):
                break
        # pattern match <root or <ns:root for any ns string
        pattern = r'^<(\w*:)?%s' % self.root
        return line is not None and re.match(pattern, line) is not None

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = self.blurb
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'


class PepXml(ProteomicsXml):
    """pepXML data"""
    edam_format = "format_3655"
    file_ext = "pepxml"
    blurb = 'pepXML data'
    root = "msms_pipeline_analysis"


class MzML(ProteomicsXml):
    """mzML data"""
    edam_format = "format_3244"
    file_ext = "mzml"
    blurb = 'mzML Mass Spectrometry data'
    root = "(mzML|indexedmzML)"


class NmrML(ProteomicsXml):
    """nmrML data"""
    # No edam format number yet.
    file_ext = "nmrml"
    blurb = 'nmrML NMR data'
    root = "nmrML"


class ProtXML(ProteomicsXml):
    """protXML data"""
    file_ext = "protxml"
    blurb = 'prot XML Search Results'
    root = "protein_summary"


class MzXML(ProteomicsXml):
    """mzXML data"""
    edam_format = "format_3654"
    file_ext = "mzxml"
    blurb = "mzXML Mass Spectrometry data"
    root = "mzXML"


class MzData(ProteomicsXml):
    """mzData data"""
    edam_format = "format_3245"
    file_ext = "mzdata"
    blurb = "mzData Mass Spectrometry data"
    root = "mzData"


class MzIdentML(ProteomicsXml):
    edam_format = "format_3247"
    file_ext = "mzid"
    blurb = "XML identified peptides and proteins."
    root = "MzIdentML"


class TraML(ProteomicsXml):
    edam_format = "format_3246"
    file_ext = "traml"
    blurb = "TraML transition list"
    root = "TraML"


class MzQuantML(ProteomicsXml):
    edam_format = "format_3248"
    file_ext = "mzq"
    blurb = "XML quantification data"
    root = "MzQuantML"


class ConsensusXML(ProteomicsXml):
    file_ext = "consensusxml"
    blurb = "OpenMS multiple LC-MS map alignment file"
    root = "consensusXML"


class FeatureXML(ProteomicsXml):
    file_ext = "featurexml"
    blurb = "OpenMS feature file"
    root = "featureMap"


class IdXML(ProteomicsXml):
    file_ext = "idxml"
    blurb = "OpenMS identification file"
    root = "IdXML"


class TandemXML(ProteomicsXml):
    edam_format = "format_3711"
    file_ext = "tandem"
    blurb = "X!Tandem search results file"
    root = "bioml"


class UniProtXML(ProteomicsXml):
    file_ext = "uniprotxml"
    blurb = "UniProt Proteome file"
    root = "uniprot"


class Mgf(Text):
    """Mascot Generic Format data"""
    edam_data = "data_2536"
    edam_format = "format_3651"
    file_ext = "mgf"

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = 'mgf Mascot Generic Format'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff(self, filename):
        mgf_begin_ions = "BEGIN IONS"
        max_lines = 100

        with open(filename) as handle:
            for i, line in enumerate(handle):
                line = line.rstrip()
                if line == mgf_begin_ions:
                    return True
                if i > max_lines:
                    return False


class MascotDat(Text):
    """Mascot search results """
    edam_data = "data_2536"
    edam_format = "format_3713"
    file_ext = "mascotdat"

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = 'mascotdat Mascot Search Results'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff(self, filename):
        mime_version = "MIME-Version: 1.0 (Generated by Mascot version 1.0)"
        max_lines = 10

        with open(filename) as handle:
            for i, line in enumerate(handle):
                line = line.rstrip()
                if line == mime_version:
                    return True
                if i > max_lines:
                    return False


class ThermoRAW(Binary):
    """Class describing a Thermo Finnigan binary RAW file"""
    edam_data = "data_2536"
    edam_format = "format_3712"
    file_ext = "raw"

    def sniff(self, filename):
        # Thermo Finnigan RAW format is proprietary and hence not well documented.
        # Files start with 2 bytes that seem to differ followed by F\0i\0n\0n\0i\0g\0a\0n
        # This combination represents 17 bytes, but to play safe we read 20 bytes from
        # the start of the file.
        try:
            header = open(filename, 'rb').read(20)
            finnigan = b'F\0i\0n\0n\0i\0g\0a\0n'
            if header.find(finnigan) != -1:
                return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Thermo Finnigan RAW file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Thermo Finnigan RAW file (%s)" % (nice_size(dataset.get_size()))


@build_sniff_from_prefix
class Msp(Text):
    """ Output of NIST MS Search Program chemdata.nist.gov/mass-spc/ftp/mass-spc/PepLib.pdf """
    file_ext = "msp"

    @staticmethod
    def next_line_starts_with(contents, prefix):
        next_line = contents.readline()
        return next_line is not None and next_line.startswith(prefix)

    def sniff_prefix(self, file_prefix):
        """ Determines whether the file is a NIST MSP output file."""
        begin_contents = file_prefix.contents_header
        if "\n" not in begin_contents:
            return False
        lines = begin_contents.splitlines()
        if len(lines) < 2:
            return False
        return lines[0].startswith("Name:") and lines[1].startswith("MW:")


class SPLibNoIndex(Text):
    """SPlib without index file """
    file_ext = "splib_noindex"

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = 'Spectral Library without index files'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'


@build_sniff_from_prefix
class SPLib(Msp):
    """SpectraST Spectral Library. Closely related to msp format"""
    file_ext = "splib"
    composite_type = 'auto_primary_file'

    def __init__(self, **kwd):
        Msp.__init__(self, **kwd)
        self.add_composite_file('library.splib',
                                description='Spectral Library. Contains actual library spectra',
                                is_binary=False)
        self.add_composite_file('library.spidx',
                                description='Spectrum index', is_binary=False)
        self.add_composite_file('library.pepidx',
                                description='Peptide index', is_binary=False)

    def generate_primary_file(self, dataset=None):
        rval = ['<html><head><title>Spectral Library Composite Dataset </title></head><p/>']
        rval.append('<div>This composite dataset is composed of the following files:<p/><ul>')
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            if composite_file.get('description'):
                rval.append('<li><a href="%s" type="text/plain">%s (%s)</a>%s</li>' % (fn, fn, composite_file.get('description'), opt_text))
            else:
                rval.append('<li><a href="%s" type="text/plain">%s</a>%s</li>' % (fn, fn, opt_text))
        rval.append('</ul></div></html>')
        return "\n".join(rval)

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = 'splib Spectral Library Format'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff_prefix(self, file_prefix):
        """ Determines whether the file is a SpectraST generated file.
        """
        contents = file_prefix.string_io()
        return Msp.next_line_starts_with(contents, "Name:") and Msp.next_line_starts_with(contents, "LibID:")


@build_sniff_from_prefix
class Ms2(Text):
    file_ext = "ms2"

    def sniff_prefix(self, file_prefix):
        """ Determines whether the file is a valid ms2 file."""
        contents = file_prefix.string_io()
        header_lines = []
        while True:
            line = contents.readline()
            if not line:
                return False
            if line.strip() == "":
                continue
            elif line.startswith('H\t'):
                header_lines.append(line)
            else:
                break

        for header_field in ['CreationDate', 'Extractor', 'ExtractorVersion', 'ExtractorOptions']:
            found_header = False
            for header_line in header_lines:
                if header_line.startswith('H\t%s' % (header_field)):
                    found_header = True
                    break
            if not found_header:
                return False

        return True


# unsniffable binary format, should do something about this
class XHunterAslFormat(Binary):
    """ Annotated Spectra in the HLF format http://www.thegpm.org/HUNTER/format_2006_09_15.html """
    file_ext = "hlf"


class Sf3(Binary):
    """Class describing a Scaffold SF3 files"""
    file_ext = "sf3"


class ImzML(Binary):
    """
        Class for imzML files.
        http://www.imzml.org
    """
    edam_format = "format_3682"
    file_ext = 'imzml'
    allow_datatype_change = False
    composite_type = 'auto_primary_file'

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)

        """The metadata"""
        self.add_composite_file(
            'imzml',
            description='The imzML metadata component.',
            is_binary=False)

        """The mass spectral data"""
        self.add_composite_file(
            'ibd',
            description='The mass spectral data component.',
            is_binary=True)

    def generate_primary_file(self, dataset=None):
        rval = ['<html><head><title>imzML Composite Dataset </title></head><p/>']
        rval.append('<div>This composite dataset is composed of the following files:<p/><ul>')
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ''
            if composite_file.get('description'):
                rval.append('<li><a href="%s" type="text/plain">%s (%s)</a>%s</li>' % (fn, fn, composite_file.get('description'), opt_text))
            else:
                rval.append('<li><a href="%s" type="text/plain">%s</a>%s</li>' % (fn, fn, opt_text))
        rval.append('</ul></div></html>')
        return "\n".join(rval)


class Analyze75(Binary):
    """
        Mayo Analyze 7.5 files
        http://www.imzml.org
    """
    file_ext = 'analyze75'
    allow_datatype_change = False
    composite_type = 'auto_primary_file'

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)

        """The header file. Provides information about dimensions, identification, and processing history."""
        self.add_composite_file(
            'hdr',
            description='The Analyze75 header file.',
            is_binary=True)

        """The image file.  Image data, whose data type and ordering are described by the header file."""
        self.add_composite_file(
            'img',
            description='The Analyze75 image file.',
            is_binary=True)

        """The optional t2m file."""
        self.add_composite_file(
            't2m',
            description='The Analyze75 t2m file.',
            optional=True,
            is_binary=True)

    def generate_primary_file(self, dataset=None):
        rval = ['<html><head><title>Analyze75 Composite Dataset.</title></head><p/>']
        rval.append('<div>This composite dataset is composed of the following files:<p/><ul>')
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            if composite_file.get('description'):
                rval.append('<li><a href="%s" type="text/plain">%s (%s)</a>%s</li>' % (fn, fn, composite_file.get('description'), opt_text))
            else:
                rval.append('<li><a href="%s" type="text/plain">%s</a>%s</li>' % (fn, fn, opt_text))
        rval.append('</ul></div></html>')
        return "\n".join(rval)
