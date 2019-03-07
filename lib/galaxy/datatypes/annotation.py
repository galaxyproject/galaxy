import logging
import tarfile

from galaxy.datatypes.binary import CompressedArchive
from galaxy.datatypes.data import get_file_peek, Text
from galaxy.datatypes.sniff import build_sniff_from_prefix
from galaxy.util import nice_size

log = logging.getLogger(__name__)


@build_sniff_from_prefix
class SnapHmm(Text):
    file_ext = "snaphmm"
    edam_data = "data_1364"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "SNAP HMM model"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "SNAP HMM model (%s)" % (nice_size(dataset.get_size()))

    def sniff_prefix(self, file_prefix):
        """
        SNAP model files start with zoeHMM
        """
        return file_prefix.startswith('zoeHMM')


class Augustus(CompressedArchive):
    """
        Class describing an Augustus prediction model
    """
    file_ext = "augustus"
    edam_data = "data_0950"
    compressed = True

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Augustus model"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Augustus model (%s)" % (nice_size(dataset.get_size()))

    def sniff(self, filename):
        """
        Augustus archives always contain the same files
        """
        try:
            if filename and tarfile.is_tarfile(filename):
                with tarfile.open(filename, 'r') as temptar:
                    for f in temptar:
                        if not f.isfile():
                            continue
                        if f.name.endswith('_exon_probs.pbl') \
                           or f.name.endswith('_igenic_probs.pbl') \
                           or f.name.endswith('_intron_probs.pbl') \
                           or f.name.endswith('_metapars.cfg') \
                           or f.name.endswith('_metapars.utr.cfg') \
                           or f.name.endswith('_parameters.cfg') \
                           or f.name.endswith('_parameters.cgp.cfg') \
                           or f.name.endswith('_utr_probs.pbl') \
                           or f.name.endswith('_weightmatrix.txt'):
                            return True
                        else:
                            return False
        except Exception as e:
            log.warning('%s, sniff Exception: %s', self, e)
        return False
