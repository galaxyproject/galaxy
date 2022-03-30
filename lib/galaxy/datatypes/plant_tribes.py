import logging
import re

from galaxy.datatypes.data import (
    get_file_peek,
    Text,
)
from galaxy.datatypes.metadata import MetadataElement
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

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"ESTScan scores matrices ({nice_size(dataset.get_size())})"

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "ESTScan scores matrices"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disc"

    def sniff_prefix(self, file_prefix: FilePrefix):
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


# These commented classes are required by versions 1.0.0, 1.0.1 and 1.0.2 of the
# PlantTribes tools in the MTS Phylogenetics category, and are not required by
# version 1.0.3 or later.  These datatypes will be removed in a future Galaxy release.
#
# class PlantTribes(Html):
#    """
#    PlantTribes abstract class.
#    """
#    composite_type = 'basic'
#    MetadataElement(name="num_files", default=0, desc="Number of files in files_path directory", param=MetadataParameter, readonly=True, visible=False, no_value=0)
#
#    def set_meta(self, dataset, overwrite=True, **kwd):
#        try:
#            efp = dataset.extra_files_path
#            if os.path.exists(efp):
#                dataset.metadata.num_files = len(os.listdir(efp))
#        except Exception as e:
#            log.warning("set_meta fname: %s %s" % (dataset.file_name if dataset and dataset.file_name else 'Unkwown', str(e)))


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

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return f"Significant components in the Ks distribution ({nice_size(dataset.get_size())})"

    def set_meta(self, dataset, **kwd):
        """
        Set the number of significant components in the Ks distribution.
        The dataset will always be on the order of less than 10 lines.
        """
        super().set_meta(dataset, **kwd)
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

    def set_peek(self, dataset):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            if dataset.metadata.number_comp == 1:
                dataset.blurb = "1 significant component"
            else:
                dataset.blurb = f"{dataset.metadata.number_comp} significant components"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

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
            line_item_str = get_headers(filename, "\\t", 1)[0][0]
            return line_item_str == "species\tn\tnumber_comp\tlnL\tAIC\tBIC\tmean\tvariance\tporportion"
        except Exception:
            return False


# class PlantTribesOrtho(PlantTribes):
#    """
#    PlantTribes sequences classified into precomputed, orthologous gene family
#    clusters.
#    """
#    file_ext = "ptortho"
#
#    def set_peek(self, dataset):
#        super(PlantTribesOrtho, self).set_peek(dataset)
#        dataset.blurb = "Proteins orthogroup fasta files: %d items" % dataset.metadata.num_files
#
#
# class PlantTribesOrthoCodingSequence(PlantTribes):
#    """
#    PlantTribes sequences classified into precomputed, orthologous gene family
#    clusters and corresponding coding sequences.
#    """
#    file_ext = "ptorthocs"
#
#    def set_peek(self, dataset):
#        super(PlantTribesOrthoCodingSequence, self).set_peek(dataset)
#        dataset.blurb = "Protein and coding sequences orthogroup fasta files: %d items" % dataset.metadata.num_files
#
#
# class PlantTribesTargetedGeneFamilies(PlantTribes):
#    """
#    PlantTribes targeted gene families.
#    """
#    file_ext = "pttgf"
#
#    def set_peek(self, dataset):
#        super(PlantTribesTargetedGeneFamilies, self).set_peek(dataset)
#        dataset.blurb = "Targeted gene families"
#
#
# class PlantTribesPhylogeneticTree(PlantTribes):
#    """
#    PlantTribes multiple sequence alignments and inferred maximum likelihood
#    phylogenies for orthogroups.
#    """
#    file_ext = "pttree"
#
#    def set_peek(self, dataset):
#        super(PlantTribesPhylogeneticTree, self).set_peek(dataset)
#        dataset.blurb = "Phylogenetic trees: %d items" % dataset.metadata.num_files
#
#
# class PlantTribesPhylip(PlantTribes):
#    """
#    PlantTribes orthogroup phylip multiple sequence alignments.
#    """
#    file_ext = "ptphylip"
#
#    def set_peek(self, dataset):
#        super(PlantTribesPhylip, self).set_peek(dataset)
#        dataset.blurb = "Orthogroup phylip multiple sequence alignments: %d items" % dataset.metadata.num_files
#
#
# class PlantTribesMultipleSequenceAlignment(PlantTribes):
#    """
#    PlantTribes multiple sequence alignments.
#    """
#    file_ext = "ptalign"
#
#    def set_peek(self, dataset):
#        super(PlantTribesMultipleSequenceAlignment, self).set_peek(dataset)
#        dataset.blurb = "Proteins orthogroup alignments: %d items" % dataset.metadata.num_files
#
#
# class PlantTribesMultipleSequenceAlignmentCodonAlignment(PlantTribes):
#    """
#    PlantTribes multiple sequence alignments with codon alignments.
#    """
#    file_ext = "ptalignca"
#
#    def set_peek(self, dataset:
#        super(PlantTribesMultipleSequenceAlignmentCodonAlignment, self).set_peek(dataset)
#        dataset.blurb = "Protein and coding sequences orthogroup alignments: %d items" % dataset.metadata.num_files
#
#
# class PlantTribesMultipleSequenceAlignmentTrimmed(PlantTribes):
#    """
#    PlantTribes trimmed multiple sequence alignments.
#    """
#    file_ext = "ptaligntrimmed"
#
#    def set_peek(self, dataset):
#        super(PlantTribesMultipleSequenceAlignmentTrimmed, self).set_peek(dataset)
#        dataset.blurb = "Trimmed proteins orthogroup alignments: %d items" % dataset.metadata.num_files
#
#
# class PlantTribesMultipleSequenceAlignmentTrimmedCodonAlignment(PlantTribes):
#    """
#    PlantTribes trimmed multiple sequence alignments with codon alignments.
#    """
#    file_ext = "ptaligntrimmedca"
#
#    def set_peek(self, dataset):
#        super(PlantTribesMultipleSequenceAlignmentTrimmedCodonAlignment, self).set_peek(dataset)
#        dataset.blurb = "Trimmed protein and coding sequences orthogroup alignments: %d items" % dataset.metadata.num_files
#
#
# class PlantTribesMultipleSequenceAlignmentFiltered(PlantTribes):
#    """
#    PlantTribes filtered multiple sequence alignments.
#    """
#    file_ext = "ptalignfiltered"
#
#    def set_peek(self, dataset):
#        super(PlantTribesMultipleSequenceAlignmentFiltered, self).set_peek(dataset)
#        dataset.blurb = "Filtered proteins orthogroup alignments: %d items" % dataset.metadata.num_files
#
#
# class PlantTribesMultipleSequenceAlignmentFilteredCodonAlignment(PlantTribes):
#    """
#    PlantTribes filtered multiple sequence alignments with codon alignments.
#    """
#    file_ext = "ptalignfilteredca"
#
#    def set_peek(self, dataset):
#        super(PlantTribesMultipleSequenceAlignmentFilteredCodonAlignment, self).set_peek(dataset)
#        dataset.blurb = "Filtered protein and coding sequences orthogroup alignments: %d items" % dataset.metadata.num_files
