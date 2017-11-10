# -*- coding: utf-8 -*-

from galaxy.datatypes.data import Text
from galaxy.datatypes.sniff import get_headers, get_test_fname
from galaxy.datatypes.data import get_file_peek
import subprocess
import os

from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata

def count_special_lines( word, filename, invert = False ):
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

def count_lines( filename, non_empty = False):
    """
        counting the number of lines from the 'filename' file
    """
    try:
        if non_empty:
            out = subprocess.Popen(['grep', '-cve', '^\s*$', filename], stdout=subprocess.PIPE)
        else:
            out = subprocess.Popen(['wc', '-l', filename], stdout=subprocess.PIPE)
        return int(out.communicate()[0].split()[0])
    except:
        pass
    return 0


class Infernal_CM_1_1( Text ):
    file_ext = "cm"

    MetadataElement( name="number_of_models", default=0, desc="Number of covariance models", readonly=True, visible=True, optional=True, no_value=0 )

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            if (dataset.metadata.number_of_models == 1):
                dataset.blurb = "1 model"
            else:
                dataset.blurb = "%s models" % dataset.metadata.number_of_models
            dataset.peek = get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def sniff( self, filename ):
        if count_special_lines("^INFERNAL1/a", filename) > 0:
            return True
        else:
            return False

    def set_meta( self, dataset, **kwd ):
        """
        Set the number of models in dataset.
        """
        dataset.metadata.number_of_models = count_special_lines("^INFERNAL1/a", dataset.file_name)

    def split( cls, input_datasets, subdir_generator_function, split_params):
        """
        Split the input files by model records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("CM-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params['split_mode'] == 'number_of_parts':
            raise Exception('Split mode "%s" is currently not implemented for CM-files.' % split_params['split_mode'])
        elif split_params['split_mode'] == 'to_size':
            chunk_size = int(split_params['split_size'])
        else:
            raise Exception('Unsupported split mode %s' % split_params['split_mode'])

        def _read_cm_records( filename ):
            lines = []
            with open(filename) as handle:
                for line in handle:
                    if line.startswith("INFERNAL1/a") and lines:
                        yield lines
                        lines = [line]
                    else:
                        lines.append( line )
            yield lines

        def _write_part_cm_file( accumulated_lines ):
            part_dir = subdir_generator_function()
            part_path = os.path.join( part_dir, os.path.basename( input_files[0] ) )
            part_file = open( part_path, 'w' )
            part_file.writelines( accumulated_lines )
            part_file.close()

        try:
            cm_records = _read_cm_records( input_files[0] )
            cm_lines_accumulated = []
            for counter, cm_record in enumerate( cm_records, start = 1):
                cm_lines_accumulated.extend( cm_record )
                if counter % chunk_size == 0:
                    _write_part_cm_file( cm_lines_accumulated )
                    cm_lines_accumulated = []
            if cm_lines_accumulated:
                _write_part_cm_file( cm_lines_accumulated )
        except Exception,  e:
            log.error('Unable to split files: %s' % str(e))
            raise
    split = classmethod(split)

if __name__ == '__main__':
    Infernal_CM_1_1()
    Stockholm_1_0()

