"""
Datatypes for Anvi'o
https://github.com/merenlab/anvio
"""
import glob
import logging
import os
import sys

from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.text import Html

log = logging.getLogger(__name__)


class AnvioComposite(Html):
    """
    Base class to use for Anvi'o composite datatypes.
    Generally consist of a sqlite database, plus optional additional files
    """
    file_ext = "anvio_composite"
    composite_type = 'auto_primary_file'

    def generate_primary_file(self, dataset=None):
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        defined_files = self.get_composite_files(dataset=dataset).items()
        rval = ["<html><head><title>Files for Anvi'o Composite Dataset (%s)</title></head>" % (self.file_ext)]
        if defined_files:
            rval.append("<p/>This composite dataset is composed of the following defined files:<p/><ul>")
            for composite_name, composite_file in defined_files:
                opt_text = ''
                if composite_file.optional:
                    opt_text = ' (optional)'
                missing_text = ''
                if not os.path.exists(os.path.join(dataset.extra_files_path, composite_name)):
                    missing_text = ' (missing)'
                rval.append('<li><a href="%s">%s</a>%s%s</li>' % (composite_name, composite_name, opt_text, missing_text))
            rval.append("</ul>")
        defined_files = map(lambda x: x[0], defined_files)
        extra_files = []
        for (dirpath, dirnames, filenames) in os.walk(dataset.extra_files_path, followlinks=True):
            for filename in filenames:
                rel_path = os.path.relpath(os.path.join(dirpath, filename), dataset.extra_files_path)
                if rel_path not in defined_files:
                    extra_files.append(rel_path)
        if extra_files:
            rval.append("<p/>This composite dataset contains these undefined files:<p/><ul>")
            for rel_path in extra_files:
                rval.append('<li><a href="%s">%s</a></li>' % (rel_path, rel_path))
            rval.append('</ul>')
        if not (defined_files or extra_files):
            rval.append("<p/>This composite dataset does not contain any files!<p/><ul>")
        rval.append('</html>')
        return "\n".join(rval)

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/html'

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = 'Anvio database (multiple files)'
            dataset.blurb = 'Anvio database (multiple files)'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "Anvio database (multiple files)"


class AnvioDB(AnvioComposite):
    """Class for AnvioDB database files."""
    _anvio_basename = None
    MetadataElement(name="anvio_basename", default=_anvio_basename, desc="Basename", readonly=True)
    file_ext = 'anvio_db'
    composite_type = 'auto_primary_file'
    allow_datatype_change = False

    def __init__(self, *args, **kwd):
        super(AnvioDB, self).__init__(*args, **kwd)
        if self._anvio_basename is not None:
            self.add_composite_file(self._anvio_basename, is_binary=True, optional=False)

    def set_meta(self, dataset, **kwd):
        """
        Set the anvio_basename based upon actual extra_files_path contents.
        """
        super(AnvioDB, self).set_meta(dataset, **kwd)
        if dataset.metadata.anvio_basename is not None and os.path.exists(os.path.join(dataset.extra_files_path, dataset.metadata.anvio_basename)):
            return
        found = False
        for basename in [dataset.metadata.anvio_basename, self._anvio_basename]:
            if found:
                break
            if basename is not None and not os.path.exists(os.path.join(dataset.extra_files_path, basename)):
                for name in glob.glob(os.path.join(dataset.extra_files_path, "*%s" % (basename))):
                    dataset.metadata.anvio_basename = os.path.basename(name)
                    found = True
                    break


class AnvioStructureDB(AnvioDB):
    """Class for Anvio Structure DB database files."""
    _anvio_basename = 'STRUCTURE.db'
    MetadataElement(name="anvio_basename", default=_anvio_basename, desc="Basename", readonly=True)
    file_ext = 'anvio_structure_db'
    composite_type = 'auto_primary_file'
    allow_datatype_change = False


class AnvioGenomesDB(AnvioDB):
    """Class for Anvio Genomes DB database files."""
    _anvio_basename = '-GENOMES.db'
    MetadataElement(name="anvio_basename", default=_anvio_basename, desc="Basename", readonly=True)
    file_ext = 'anvio_genomes_db'
    composite_type = 'auto_primary_file'
    allow_datatype_change = False


class AnvioContigsDB(AnvioDB):
    """Class for Anvio Contigs DB database files."""
    _anvio_basename = 'CONTIGS.db'
    MetadataElement(name="anvio_basename", default=_anvio_basename, desc="Basename", readonly=True)
    file_ext = 'anvio_contigs_db'
    composite_type = 'auto_primary_file'
    allow_datatype_change = False

    def __init__(self, *args, **kwd):
        super(AnvioContigsDB, self).__init__(*args, **kwd)
        self.add_composite_file('CONTIGS.h5', is_binary=True, optional=True)


class AnvioProfileDB(AnvioDB):
    """Class for Anvio Profile DB database files."""
    _anvio_basename = 'PROFILE.db'
    MetadataElement(name="anvio_basename", default=_anvio_basename, desc="Basename", readonly=True)
    file_ext = 'anvio_profile_db'
    composite_type = 'auto_primary_file'
    allow_datatype_change = False

    def __init__(self, *args, **kwd):
        super(AnvioProfileDB, self).__init__(*args, **kwd)
        self.add_composite_file('RUNINFO.cp', is_binary=True, optional=True)
        self.add_composite_file('RUNINFO.mcp', is_binary=True, optional=True)
        self.add_composite_file('AUXILIARY_DATA.db', is_binary=True, optional=True)
        self.add_composite_file('RUNLOG.txt', is_binary=False, optional=True)


class AnvioPanDB(AnvioDB):
    """Class for Anvio Pan DB database files."""
    _anvio_basename = 'PAN.db'
    MetadataElement(name="anvio_basename", default=_anvio_basename, desc="Basename", readonly=True)
    file_ext = 'anvio_pan_db'
    composite_type = 'auto_primary_file'
    allow_datatype_change = False


class AnvioSamplesDB(AnvioDB):
    """Class for Anvio Samples DB database files."""
    _anvio_basename = 'SAMPLES.db'
    MetadataElement(name="anvio_basename", default=_anvio_basename, desc="Basename", readonly=True)
    file_ext = 'anvio_samples_db'
    composite_type = 'auto_primary_file'
    allow_datatype_change = False


if __name__ == '__main__':
    import doctest
    doctest.testmod(sys.modules[__name__])
