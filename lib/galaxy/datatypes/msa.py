from galaxy.datatypes.data import Text
from galaxy.datatypes.data import get_file_peek
from galaxy.datatypes.data import nice_size

import logging
log = logging.getLogger(__name__)


class Hmmer3( Text ):
    file_ext = "hmm"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = "HMMER3 Database"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff(self, filename):
        """HMMER3 files start with HMMER3/f
        """
        with open(filename, 'r') as handle:
            return handle.read(8) == 'HMMER3/f'
        return False

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "HMMER3 database (%s)" % ( nice_size( dataset.get_size() ) )
