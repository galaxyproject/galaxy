import logging
import os
import re
import tempfile

from galaxy.datatypes.data import get_file_peek, Text
from galaxy.datatypes.metadata import MetadataElement, MetadataParameter
from galaxy.datatypes.text import Html
from galaxy.util import nice_size

log = logging.getLogger(__name__)


class Smat(Text):
    file_ext = "smat"

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
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
            line_no += 1
            if line_no > 10000:
                return True
            line = fh.readline(500)
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

    def display_data(self, trans, data, preview=False, filename=None, to_ext=None, **kwd):
        file_path = trans.app.object_store.get_filename(data.dataset, extra_dir='dataset_%s_files' % data.dataset.id, alt_name=filename)
        if os.path.isdir(file_path):
            fh = tempfile.NamedTemporaryFile(delete=False)
            fn = fh.name
            dir_items = sorted(os.listdir(file_path))
            # Directories can only contain either files or directories, but not both.
            item_path = os.path.join(file_path, dir_items[0])
            if os.path.isdir(item_path):
                header = 'Directories'
            else:
                header = 'Datasets'
            base_path, item_name = os.path.split(file_path)
            fh.write('<html><head><h3>Directory %s contents: %d items</h3></head>\n' % (item_name, len(dir_items)))
            fh.write('<body><p/><table cellpadding="2">\n')
            fh.write('<tr><b>%s</b></tr>\n' % header)
            for index, fname in enumerate(dir_items):
                if index % 2 == 0:
                    bgcolor = '#D8D8D8'
                else:
                    bgcolor = '#FFFFFF'
                # Can't have an href link here because there is no route
                # defined for files contained within multiple subdirectory
                # levels of the primary dataset.  Something like this is
                # close, but not quite correct:
                # href = url_for(controller='dataset', action='display',
                # dataset_id=trans.security.encode_id(data.dataset.id),
                # preview=preview, filename=fname, to_ext=to_ext)
                fh.write('<tr bgcolor="%s"><td>%s</td></tr>\n' % (bgcolor, fname))
            fh.write('</table></body></html>\n')
            fh.close()
            return open(fn)
        else:
            return super(PlantTribes, self).display_data(trans, data, preview=preview, filename=filename, to_ext=to_ext, **kwd)

    def set_meta(self, dataset, overwrite=True, **kwd):
        try:
            efp = dataset.extra_files_path
            if os.path.exists(efp):
                dataset.metadata.num_files = len(os.listdir(efp))
        except Exception as e:
            log.warning("set_meta fname: %s %s" % (dataset.file_name if dataset and dataset.file_name else 'Unkwown', str(e)))


class PlantTribesOrtho(PlantTribes):
    """
    PlantTribes sequences classified into precomputed, orthologous gene family
    clusters.
    """
    file_ext = "ptortho"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesOrtho, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Proteins orthogroup fasta files: %d items" % dataset.metadata.num_files


class PlantTribesOrthoCodingSequence(PlantTribes):
    """
    PlantTribes sequences classified into precomputed, orthologous gene family
    clusters and corresponding coding sequences.
    """
    file_ext = "ptorthocs"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesOrthoCodingSequence, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Protein and coding sequences orthogroup fasta files: %d items" % dataset.metadata.num_files


class PlantTribesTargetedGeneFamilies(PlantTribes):
    """
    PlantTribes targeted gene families.
    """
    file_ext = "pttgf"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesTargetedGeneFamilies, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Targeted gene families"


class PlantTribesPhylogeneticTree(PlantTribes):
    """
    PlantTribes multiple sequence alignments and inferred maximum likelihood
    phylogenies for orthogroups.
    """
    file_ext = "pttree"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesPhylogeneticTree, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Phylogenetic trees: %d items" % dataset.metadata.num_files


class PlantTribesPhylip(PlantTribes):
    """
    PlantTribes orthogroup phylip multiple sequence alignments.
    """
    file_ext = "ptphylip"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesPhylip, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Orthogroup phylip multiple sequence alignments: %d items" % dataset.metadata.num_files


class PlantTribesMultipleSequenceAlignment(PlantTribes):
    """
    PlantTribes multiple sequence alignments.
    """
    file_ext = "ptalign"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesMultipleSequenceAlignment, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Proteins orthogroup alignments: %d items" % dataset.metadata.num_files


class PlantTribesMultipleSequenceAlignmentCodonAlignment(PlantTribes):
    """
    PlantTribes multiple sequence alignments with codon alignments.
    """
    file_ext = "ptalignca"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesMultipleSequenceAlignmentCodonAlignment, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Protein and coding sequences orthogroup alignments: %d items" % dataset.metadata.num_files


class PlantTribesMultipleSequenceAlignmentTrimmed(PlantTribes):
    """
    PlantTribes trimmed multiple sequence alignments.
    """
    file_ext = "ptaligntrimmed"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesMultipleSequenceAlignmentTrimmed, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Trimmed proteins orthogroup alignments: %d items" % dataset.metadata.num_files


class PlantTribesMultipleSequenceAlignmentTrimmedCodonAlignment(PlantTribes):
    """
    PlantTribes trimmed multiple sequence alignments with codon alignments.
    """
    file_ext = "ptaligntrimmedca"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesMultipleSequenceAlignmentTrimmedCodonAlignment, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Trimmed protein and coding sequences orthogroup alignments: %d items" % dataset.metadata.num_files


class PlantTribesMultipleSequenceAlignmentFiltered(PlantTribes):
    """
    PlantTribes filtered multiple sequence alignments.
    """
    file_ext = "ptalignfiltered"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesMultipleSequenceAlignmentFiltered, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Filtered proteins orthogroup alignments: %d items" % dataset.metadata.num_files


class PlantTribesMultipleSequenceAlignmentFilteredCodonAlignment(PlantTribes):
    """
    PlantTribes filtered multiple sequence alignments with codon alignments.
    """
    file_ext = "ptalignfilteredca"

    def set_peek(self, dataset, is_multi_byte=False):
        super(PlantTribesMultipleSequenceAlignmentFilteredCodonAlignment, self).set_peek(dataset, is_multi_byte=is_multi_byte)
        dataset.blurb = "Filtered protein and coding sequences orthogroup alignments: %d items" % dataset.metadata.num_files
