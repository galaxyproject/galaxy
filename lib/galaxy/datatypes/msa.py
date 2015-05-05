from galaxy.datatypes.data import Text
from galaxy.datatypes.data import get_file_peek
from galaxy.datatypes.data import nice_size
from galaxy.datatypes.metadata import MetadataElement
import subprocess
import os


import logging
log = logging.getLogger(__name__)


def count_special_lines( word, filename, invert=False ):
    """
        searching for special 'words' using the grep tool
        grep is used to speed up the searching and counting
        The number of hits is returned.
    """
    try:
        cmd = ["grep", "-c"]
        if invert:
            cmd.append('-v')
        cmd.extend([word, filename])
        out = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        return int(out.communicate()[0].split()[0])
    except:
        pass
    return 0


class Hmmer( Text ):
    file_ext = "hmm"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            dataset.blurb = "HMMER Database"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "HMMER database (%s)" % ( nice_size( dataset.get_size() ) )


class Hmmer2( Hmmer ):

    def sniff(self, filename):
        """HMMER2 files start with HMMER2.0
        """
        with open(filename, 'r') as handle:
            return handle.read(8) == 'HMMER2.0'
        return False


class Hmmer3( Hmmer ):

    def sniff(self, filename):
        """HMMER3 files start with HMMER3/f
        """
        with open(filename, 'r') as handle:
            return handle.read(8) == 'HMMER3/f'
        return False


class Stockholm_1_0( Text ):
    file_ext = "stockholm"

    MetadataElement( name="number_of_alignments", default=0, desc="Number of multiple alignments", readonly=True, visible=True, optional=True, no_value=0 )

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            if (dataset.metadata.number_of_models == 1):
                dataset.blurb = "1 alignment"
            else:
                dataset.blurb = "%s alignments" % dataset.metadata.number_of_models
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff( self, filename ):
        if count_special_lines('^#[[:space:]+]STOCKHOLM[[:space:]+]1.0', filename) > 0:
            return True
        else:
            return False

    def set_meta( self, dataset, **kwd ):
        """

        Set the number of models in dataset.
        """
        dataset.metadata.number_of_models = count_special_lines('^#[[:space:]+]STOCKHOLM[[:space:]+]1.0', dataset.file_name)

    def split( cls, input_datasets, subdir_generator_function, split_params):
        """

        Split the input files by model records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("STOCKHOLM-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params['split_mode'] == 'number_of_parts':
            raise Exception('Split mode "%s" is currently not implemented for STOCKHOLM-files.' % split_params['split_mode'])
        elif split_params['split_mode'] == 'to_size':
            chunk_size = int(split_params['split_size'])
        else:
            raise Exception('Unsupported split mode %s' % split_params['split_mode'])

        def _read_stockholm_records( filename ):
            lines = []
            with open(filename) as handle:
                for line in handle:
                    lines.append( line )
                    if line.strip() == '//':
                        yield lines
                        lines = []

        def _write_part_stockholm_file( accumulated_lines ):
            part_dir = subdir_generator_function()
            part_path = os.path.join( part_dir, os.path.basename( input_files[0] ) )
            part_file = open( part_path, 'w' )
            part_file.writelines( accumulated_lines )
            part_file.close()

        try:

            stockholm_records = _read_stockholm_records( input_files[0] )
            stockholm_lines_accumulated = []
            for counter, stockholm_record in enumerate( stockholm_records, start=1):
                stockholm_lines_accumulated.extend( stockholm_record )
                if counter % chunk_size == 0:
                    _write_part_stockholm_file( stockholm_lines_accumulated )
                    stockholm_lines_accumulated = []
            if stockholm_lines_accumulated:
                _write_part_stockholm_file( stockholm_lines_accumulated )
        except Exception, e:
            log.error('Unable to split files: %s' % str(e))
            raise
    split = classmethod(split)
