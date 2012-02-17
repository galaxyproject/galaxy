"""
Sequence classes
"""

import gzip
import data
import logging
import re
import string
import os
from cgi import escape
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
import galaxy.model
from galaxy import util
from sniff import *

import pkg_resources
pkg_resources.require("simplejson")
import simplejson

log = logging.getLogger(__name__)

class SequenceSplitLocations( data.Text ):
    """
    Class storing information about a sequence file composed of multiple gzip files concatenated as
    one OR an uncompressed file. In the GZIP case, each sub-file's location is stored in start and end. 
    The format of the file is JSON:
    { "sections" : [
            { "start" : "x", "end" : "y", "sequences" : "z" },
            ...
    ]}
    """
    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            try:
                parsed_data = simplejson.load(open(dataset.file_name))
                # dataset.peek = simplejson.dumps(data, sort_keys=True, indent=4)
                dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
                dataset.blurb = '%d sections' % len(parsed_data['sections'])
            except Exception, e:
                dataset.peek = 'Not FQTOC file'
                dataset.blurb = 'Not FQTOC file'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    file_ext = "fqtoc"

    def sniff( self, filename ):
        if os.path.getsize(filename) < 50000:
            try:
                data = simplejson.load(open(filename))
                sections = data['sections']
                for section in sections:
                    if 'start' not in section or 'end' not in section or 'sequences' not in section:
                        return False
                return True
            except:
                pass
        return False


class Sequence( data.Text ):
    """Class describing a sequence"""

    """Add metadata elements"""
    MetadataElement( name="sequences", default=0, desc="Number of sequences", readonly=True, visible=False, optional=True, no_value=0 )

    def set_meta( self, dataset, **kwd ):
        """
        Set the number of sequences and the number of data lines in dataset.
        """
        data_lines = 0
        sequences = 0
        for line in file( dataset.file_name ):
            line = line.strip()
            if line and line.startswith( '#' ):
                # We don't count comment lines for sequence data types
                continue
            if line and line.startswith( '>' ):
                sequences += 1
                data_lines +=1
            else:
                data_lines += 1
        dataset.metadata.data_lines = data_lines
        dataset.metadata.sequences = sequences
    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            if dataset.metadata.sequences:
                dataset.blurb = "%s sequences" % util.commaify( str( dataset.metadata.sequences ) )
            else:
                dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def get_sequences_per_file(total_sequences, split_params):
        if split_params['split_mode'] == 'number_of_parts':
            # legacy basic mode - split into a specified number of parts
            parts = int(split_params['split_size'])
            sequences_per_file = [total_sequences/parts for i in range(parts)]
            for i in range(total_sequences % parts):
                sequences_per_file[i] += 1
        elif split_params['split_mode'] == 'to_size':
            # loop through the sections and calculate the number of sequences
            chunk_size = long(split_params['split_size'])

            chunks = total_sequences / chunk_size
            rem = total_sequences % chunk_size
            sequences_per_file = [chunk_size for i in range(total_sequences / chunk_size)]
            # TODO: Should we invest the time in a better way to handle small remainders?
            if rem > 0:
                sequences_per_file.append(rem)
        else:
            raise Exception('Unsupported split mode %s' % split_params['split_mode'])
        return sequences_per_file
    get_sequences_per_file = staticmethod(get_sequences_per_file)

    def do_slow_split( cls, input_datasets, subdir_generator_function, split_params):
        # count the sequences so we can split
        # TODO: if metadata is present, take the number of lines / 4
        if input_datasets[0].metadata is not None and input_datasets[0].metadata.sequences is not None:
            total_sequences = input_datasets[0].metadata.sequences
        else:
            input_file = input_datasets[0].file_name
            compress = is_gzip(input_file)
            if compress:
                # gzip is really slow before python 2.7!
                in_file = gzip.GzipFile(input_file, 'r')
            else:
                # TODO
                # if a file is not compressed, seek locations can be calculated and stored
                # ideally, this would be done in metadata
                # TODO
                # Add BufferedReader if python 2.7?
                in_file = open(input_file, 'rt')
            total_sequences = long(0)
            for i, line in enumerate(in_file):
                total_sequences += 1
            in_file.close()
            total_sequences /= 4

        sequences_per_file = cls.get_sequences_per_file(total_sequences, split_params)
        return cls.write_split_files(input_datasets, None, subdir_generator_function, sequences_per_file)
    do_slow_split = classmethod(do_slow_split)

    def do_fast_split( cls, input_datasets, toc_file_datasets, subdir_generator_function, split_params):
        data = simplejson.load(open(toc_file_datasets[0].file_name))
        sections = data['sections']
        total_sequences = long(0)
        for section in sections:
            total_sequences += long(section['sequences'])
        sequences_per_file = cls.get_sequences_per_file(total_sequences, split_params)
        return cls.write_split_files(input_datasets, toc_file_datasets, subdir_generator_function, sequences_per_file)
    do_fast_split = classmethod(do_fast_split)

    def write_split_files(cls, input_datasets, toc_file_datasets, subdir_generator_function, sequences_per_file):
        directories = []
        def get_subdir(idx):
            if idx < len(directories):
                return directories[idx]
            dir = subdir_generator_function()
            directories.append(dir)
            return dir

        # we know how many splits and how many sequences in each. What remains is to write out instructions for the 
        # splitting of all the input files. To decouple the format of those instructions from this code, the exact format of
        # those instructions is delegated to scripts
        start_sequence=0
        for part_no in range(len(sequences_per_file)):
            dir = get_subdir(part_no)
            for ds_no in range(len(input_datasets)):
                ds = input_datasets[ds_no]
                base_name = os.path.basename(ds.file_name)
                part_path = os.path.join(dir, base_name)
                split_data = dict(class_name='%s.%s' % (cls.__module__, cls.__name__),
                                  output_name=part_path,
                                  input_name=ds.file_name,
                                  args=dict(start_sequence=start_sequence, num_sequences=sequences_per_file[part_no]))
                if toc_file_datasets is not None:
                    toc = toc_file_datasets[ds_no]
                    split_data['args']['toc_file'] = toc.file_name
                f = open(os.path.join(dir, 'split_info_%s.json' % base_name), 'w')
                simplejson.dump(split_data, f)
                f.close()
            start_sequence += sequences_per_file[part_no]
        return directories
    write_split_files = classmethod(write_split_files)
    
    def split( cls, input_datasets, subdir_generator_function, split_params):
        """Split a generic sequence file (not sensible or possible, see subclasses)."""
        if split_params is None:
            return None
        raise NotImplementedError("Can't split generic sequence files")


class Alignment( data.Text ):
    """Class describing an alignment"""

    """Add metadata elements"""
    MetadataElement( name="species", desc="Species", default=[], param=metadata.SelectParameter, multiple=True, readonly=True, no_value=None )

    def split( cls, input_datasets, subdir_generator_function, split_params):
        """Split a generic alignment file (not sensible or possible, see subclasses)."""
        if split_params is None:
            return None
        raise NotImplementedError("Can't split generic alignment files")

                                
class Fasta( Sequence ):
    """Class representing a FASTA sequence"""
    file_ext = "fasta"

    def sniff( self, filename ):
        """
        Determines whether the file is in fasta format
        
        A sequence in FASTA format consists of a single-line description, followed by lines of sequence data. 
        The first character of the description line is a greater-than (">") symbol in the first column. 
        All lines should be shorter than 80 characters
        
        For complete details see http://www.ncbi.nlm.nih.gov/blast/fasta.shtml
        
        Rules for sniffing as True:
            We don't care about line length (other than empty lines).
            The first non-empty line must start with '>' and the Very Next line.strip() must have sequence data and not be a header.
                'sequence data' here is loosely defined as non-empty lines which do not start with '>'
                This will cause Color Space FASTA (csfasta) to be detected as True (they are, after all, still FASTA files - they have a header line followed by sequence data)
                    Previously this method did some checking to determine if the sequence data had integers (presumably to differentiate between fasta and csfasta)
                    This should be done through sniff order, where csfasta (currently has a null sniff function) is detected for first (stricter definition) followed sometime after by fasta
            We will only check that the first purported sequence is correctly formatted.
        
        >>> fname = get_test_fname( 'sequence.maf' )
        >>> Fasta().sniff( fname )
        False
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> Fasta().sniff( fname )
        True
        """
        
        try:
            fh = open( filename )
            while True:
                line = fh.readline()
                if not line:
                    break #EOF
                line = line.strip()
                if line: #first non-empty line
                    if line.startswith( '>' ):
                        #The next line.strip() must not be '', nor startwith '>'
                        line = fh.readline().strip()
                        if line == '' or line.startswith( '>' ):
                            break
                        return True
                    else:
                        break #we found a non-empty line, but its not a fasta header
            fh.close()
        except:
            pass
        return False

    def split(cls, input_datasets, subdir_generator_function, split_params):
        """Split a FASTA file sequence by sequence.

        Note that even if split_mode="number_of_parts", the actual number of
        sub-files produced may not match that requested by split_size.

        If split_mode="to_size" then split_size is treated as the number of
        FASTA records to put in each sub-file (not size in bytes).
        """
        if split_params is None:
            return
        if len(input_datasets) > 1:
            raise Exception("FASTA file splitting does not support multiple files")
        input_file = input_datasets[0].file_name

        #Counting chunk size as number of sequences.
        if 'split_mode' not in split_params:
            raise Exception('Tool does not define a split mode')
        elif split_params['split_mode'] == 'number_of_parts':
            split_size = int(split_params['split_size'])
            log.debug("Split %s into %i parts..." % (input_file, split_size))
            #if split_mode = number_of_parts, and split_size = 10, and
            #we know the number of sequences (say 1234), then divide by
            #by ten, giving ten files of approx 123 sequences each.
            if input_datasets[0].metadata is not None \
            and input_datasets[0].metadata.sequences:
                #Galaxy has already counted/estimated the number
                batch_size = 1 + input_datasets[0].metadata.sequences // split_size
                cls._count_split(input_file, batch_size, subdir_generator_function)
            else:
                #OK, if Galaxy hasn't counted them, it may be a big file.
                #We're not going to count the records which would be slow
                #and a waste of disk IO time - instead we'll split using
                #the file size.
                chunk_size = os.path.getsize(input_file) // split_size
                cls._size_split(input_file, chunk_size, subdir_generator_function)
        elif split_params['split_mode'] == 'to_size':
            #Split the input file into as many sub-files as required,
            #each containing to_size many sequences
            batch_size = int(split_params['split_size'])
            log.debug("Split %s into batches of %i records..." % (input_file, batch_size))
            cls._count_split(input_file, batch_size, subdir_generator_function)
        else:
            raise Exception('Unsupported split mode %s' % split_params['split_mode'])
    split = classmethod(split)

    def _size_split(cls, input_file, chunk_size, subdir_generator_function):
        """Split a FASTA file into chunks based on size on disk.

        This does of course preserve complete records - it only splits at the
        start of a new FASTQ sequence record.
        """
        log.debug("Attemping to split FASTA file %s into chunks of %i bytes" \
                  % (input_file, chunk_size))
        f = open(input_file, "rU")
        part_file = None
        try:
            #Note if the input FASTA file has no sequences, we will
            #produce just one sub-file which will be a copy of it.
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_file))
            part_file = open(part_path, 'w')
            log.debug("Writing %s part to %s" % (input_file, part_path))
            start_offset = 0
            while True:
                offset = f.tell()
                line = f.readline()
                if not line:
                    break
                if line[0]==">" and offset - start_offset >= chunk_size:
                    #Start a new sub-file
                    part_file.close()
                    part_dir = subdir_generator_function()
                    part_path = os.path.join(part_dir, os.path.basename(input_file))
                    part_file = open(part_path, 'w')
                    log.debug("Writing %s part to %s" % (input_file, part_path))
                    start_offset = f.tell()
                part_file.write(line)
        except Exception, e:
            log.error('Unable to size split FASTA file: %s' % str(e))
            f.close()
            if part_file is not None:
                part_file.close()
            raise
        f.close()
    _size_split = classmethod(_size_split)

    def _count_split(cls, input_file, chunk_size, subdir_generator_function):
        """Split a FASTA file into chunks based on counting records."""
        log.debug("Attemping to split FASTA file %s into chunks of %i sequences" \
                  % (input_file, chunk_size))
        f = open(input_file, "rU")
        part_file = None
        try:
            #Note if the input FASTA file has no sequences, we will
            #produce just one sub-file which will be a copy of it.
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_file))
            part_file = open(part_path, 'w')
            log.debug("Writing %s part to %s" % (input_file, part_path))
            rec_count = 0
            while True:
                line = f.readline()
                if not line:
                    break
                if line[0]==">":
                    rec_count += 1
                    if rec_count > chunk_size:
                        #Start a new sub-file
                        part_file.close()
                        part_dir = subdir_generator_function()
                        part_path = os.path.join(part_dir, os.path.basename(input_file))
                        part_file = open(part_path, 'w')
                        log.debug("Writing %s part to %s" % (input_file, part_path))
                        rec_count = 1
                part_file.write(line)
            part_file.close()
        except Exception, e:
            log.error('Unable to count split FASTA file: %s' % str(e))
            f.close()
            if part_file is not None:
                part_file.close()
            raise
        f.close()
    _count_split = classmethod(_count_split)

class csFasta( Sequence ):
    """ Class representing the SOLID Color-Space sequence ( csfasta ) """
    file_ext = "csfasta"

    def sniff( self, filename ):
        """
        Color-space sequence: 
            >2_15_85_F3
            T213021013012303002332212012112221222112212222

        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> csFasta().sniff( fname )
        False
        >>> fname = get_test_fname( 'sequence.csfasta' )
        >>> csFasta().sniff( fname )
        True
        """
        try:
            fh = open( filename )
            while True:
                line = fh.readline()
                if not line:
                    break #EOF
                line = line.strip()
                if line and not line.startswith( '#' ): #first non-empty non-comment line
                    if line.startswith( '>' ):
                        line = fh.readline().strip()
                        if line == '' or line.startswith( '>' ):
                            break
                        elif line[0] not in string.ascii_uppercase:
                            return False
                        elif len( line ) > 1 and not re.search( '^[\d.]+$', line[1:] ):
                            return False
                        return True
                    else:
                        break #we found a non-empty line, but it's not a header
            fh.close()
        except:
            pass
        return False
    
    def set_meta( self, dataset, **kwd ):
        if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
            dataset.metadata.data_lines = None
            dataset.metadata.sequences = None
            return
        return Sequence.set_meta( self, dataset, **kwd )

class Fastq ( Sequence ):
    """Class representing a generic FASTQ sequence"""
    file_ext = "fastq"

    def set_meta( self, dataset, **kwd ):
        """
        Set the number of sequences and the number of data lines
        in dataset.
        """
        if self.max_optional_metadata_filesize >= 0 and dataset.get_size() > self.max_optional_metadata_filesize:
            dataset.metadata.data_lines = None
            dataset.metadata.sequences = None
            return
        data_lines = 0
        sequences = 0
        seq_counter = 0     # blocks should be 4 lines long
        for line in file( dataset.file_name ):
            line = line.strip()
            if line and line.startswith( '#' ) and not sequences:
                # We don't count comment lines for sequence data types
                continue
            if line and line.startswith( '@' ): 
                if seq_counter >= 4:
                    # count previous block
                    # blocks should be 4 lines long
                    sequences += 1
                    seq_counter = 1
                else:
                    # in case quality line starts with @
                    seq_counter += 1
                data_lines += 1
            else:
                data_lines += 1
                seq_counter += 1
        if seq_counter >= 4:
            # count final block
            sequences += 1
        dataset.metadata.data_lines = data_lines
        dataset.metadata.sequences = sequences
    def sniff ( self, filename ):
        """
        Determines whether the file is in generic fastq format
        For details, see http://maq.sourceforge.net/fastq.shtml

        Note: There are three kinds of FASTQ files, known as "Sanger" (sometimes called "Standard"), Solexa, and Illumina
              These differ in the representation of the quality scores

        >>> fname = get_test_fname( '1.fastqsanger' )
        >>> Fastq().sniff( fname )
        True
        >>> fname = get_test_fname( '2.fastqsanger' )
        >>> Fastq().sniff( fname )
        True
        """
        headers = get_headers( filename, None )
        bases_regexp = re.compile( "^[NGTAC]*" )
        # check that first block looks like a fastq block
        try:
            if len( headers ) >= 4 and headers[0][0] and headers[0][0][0] == "@" and headers[2][0] and headers[2][0][0] == "+" and headers[1][0]:
                # Check the sequence line, make sure it contains only G/C/A/T/N
                if not bases_regexp.match( headers[1][0] ):
                    return False
                return True 
            return False
        except:
            return False

    def split( cls, input_datasets, subdir_generator_function, split_params):
        """
        FASTQ files are split on cluster boundaries, in increments of 4 lines
        """
        if split_params is None:
            return None

        # first, see if there are any associated FQTOC files that will give us the split locations
        # if so, we don't need to read the files to do the splitting
        toc_file_datasets = []
        for ds in input_datasets:
            tmp_ds = ds
            fqtoc_file = None
            while fqtoc_file is None and tmp_ds is not None:
                fqtoc_file = tmp_ds.get_converted_files_by_type('fqtoc')
                tmp_ds = tmp_ds.copied_from_library_dataset_dataset_association

            if fqtoc_file is not None:
                toc_file_datasets.append(fqtoc_file)

        if len(toc_file_datasets) == len(input_datasets):
            return cls.do_fast_split(input_datasets, toc_file_datasets, subdir_generator_function, split_params)
        return cls.do_slow_split(input_datasets, subdir_generator_function, split_params)
    split = classmethod(split)

    def process_split_file(data):
        """
        This is called in the context of an external process launched by a Task (possibly not on the Galaxy machine)
        to create the input files for the Task. The parameters:
        data - a dict containing the contents of the split file
        """
        args = data['args']
        input_name = data['input_name']
        output_name = data['output_name']
        start_sequence = long(args['start_sequence'])
        sequence_count = long(args['num_sequences'])
        
        if 'toc_file' in args:
            toc_file = simplejson.load(open(args['toc_file'], 'r'))
            commands = Sequence.get_split_commands_with_toc(input_name, output_name, toc_file, start_sequence, sequence_count)
        else:
            commands = Sequence.get_split_commands_sequential(is_gzip(input_name), input_name, output_name, start_sequence, sequence_count)
        for cmd in commands:
            if 0 != os.system(cmd):
                raise Exception("Executing '%s' failed" % cmd)
        return True
    process_split_file = staticmethod(process_split_file)


class FastqSanger( Fastq ):
    """Class representing a FASTQ sequence ( the Sanger variant )"""
    file_ext = "fastqsanger"

class FastqSolexa( Fastq ):
    """Class representing a FASTQ sequence ( the Solexa variant )"""
    file_ext = "fastqsolexa"

class FastqIllumina( Fastq ):
    """Class representing a FASTQ sequence ( the Illumina 1.3+ variant )"""
    file_ext = "fastqillumina"

class FastqCSSanger( Fastq ):
    """Class representing a Color Space FASTQ sequence ( e.g a SOLiD variant )"""
    file_ext = "fastqcssanger"

try:
    from galaxy import eggs
    import pkg_resources; pkg_resources.require( "bx-python" )
    import bx.align.maf
except:
    pass

#trying to import maf_utilities here throws an ImportError due to a circular import between jobs and tools:
#from galaxy.tools.util.maf_utilities import build_maf_index_species_chromosomes
#Traceback (most recent call last):
#  File "./scripts/paster.py", line 27, in <module>
#    command.run()
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/script/command.py", line 78, in run
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/script/command.py", line 117, in invoke
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/script/command.py", line 212, in run
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/script/serve.py", line 227, in command
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/script/serve.py", line 250, in loadapp
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/deploy/loadwsgi.py", line 193, in loadapp
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/deploy/loadwsgi.py", line 213, in loadobj
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/deploy/loadwsgi.py", line 237, in loadcontext
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/deploy/loadwsgi.py", line 267, in _loadconfig
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/deploy/loadwsgi.py", line 397, in get_context
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/deploy/loadwsgi.py", line 439, in _context_from_explicit
#  File "build/bdist.solaris-2.11-i86pc/egg/paste/deploy/loadwsgi.py", line 18, in import_string
#  File "/afs/bx.psu.edu/home/dan/galaxy/central/lib/pkg_resources.py", line 1912, in load
#    entry = __import__(self.module_name, globals(),globals(), ['__name__'])
#  File "/afs/bx.psu.edu/home/dan/galaxy/central/lib/galaxy/web/buildapp.py", line 18, in <module>
#    from galaxy import config, jobs, util, tools
#  File "/afs/bx.psu.edu/home/dan/galaxy/central/lib/galaxy/jobs/__init__.py", line 3, in <module>
#    from galaxy import util, model
#  File "/afs/bx.psu.edu/home/dan/galaxy/central/lib/galaxy/model/__init__.py", line 13, in <module>
#    import galaxy.datatypes.registry
#  File "/afs/bx.psu.edu/home/dan/galaxy/central/lib/galaxy/datatypes/registry.py", line 6, in <module>
#    import data, tabular, interval, images, sequence, qualityscore, genetics, xml, coverage, tracks, chrominfo
#  File "/afs/bx.psu.edu/home/dan/galaxy/central/lib/galaxy/datatypes/sequence.py", line 344, in <module>
#    from galaxy.tools.util.maf_utilities import build_maf_index_species_chromosomes
#  File "/afs/bx.psu.edu/home/dan/galaxy/central/lib/galaxy/tools/__init__.py", line 15, in <module>
#    from galaxy import util, jobs, model
#ImportError: cannot import name jobs
#so we'll copy and paste for now...terribly icky
#*** ANYCHANGE TO THIS METHOD HERE OR IN maf_utilities MUST BE PROPAGATED ***
def COPIED_build_maf_index_species_chromosomes( filename, index_species = None ):
    species = []
    species_chromosomes = {}
    indexes = bx.interval_index_file.Indexes()
    blocks = 0
    try:
        maf_reader = bx.align.maf.Reader( open( filename ) )
        while True:
            pos = maf_reader.file.tell()
            block = maf_reader.next()
            if block is None:
                break
            blocks += 1
            for c in block.components:
                spec = c.src
                chrom = None
                if "." in spec:
                    spec, chrom = spec.split( ".", 1 )
                if spec not in species: 
                    species.append( spec )
                    species_chromosomes[spec] = []
                if chrom and chrom not in species_chromosomes[spec]:
                    species_chromosomes[spec].append( chrom )
                if index_species is None or spec in index_species:
                    forward_strand_start = c.forward_strand_start
                    forward_strand_end = c.forward_strand_end
                    try:
                        forward_strand_start = int( forward_strand_start )
                        forward_strand_end = int( forward_strand_end )
                    except ValueError:
                        continue #start and end are not integers, can't add component to index, goto next component
                        #this likely only occurs when parse_e_rows is True?
                        #could a species exist as only e rows? should the
                    if forward_strand_end > forward_strand_start:
                        #require positive length; i.e. certain lines have start = end = 0 and cannot be indexed
                        indexes.add( c.src, forward_strand_start, forward_strand_end, pos, max=c.src_size )
    except Exception, e:
        #most likely a bad MAF
        log.debug( 'Building MAF index on %s failed: %s' % ( filename, e ) )
        return ( None, [], {}, 0 )
    return ( indexes, species, species_chromosomes, blocks )

class Maf( Alignment ):
    """Class describing a Maf alignment"""
    file_ext = "maf"
    
    #Readonly and optional, users can't unset it, but if it is not set, we are generally ok; if required use a metadata validator in the tool definition
    MetadataElement( name="blocks", default=0, desc="Number of blocks", readonly=True, optional=True, visible=False, no_value=0 )
    MetadataElement( name="species_chromosomes", desc="Species Chromosomes", param=metadata.FileParameter, readonly=True, no_value=None, visible=False, optional=True )
    MetadataElement( name="maf_index", desc="MAF Index File", param=metadata.FileParameter, readonly=True, no_value=None, visible=False, optional=True )

    def init_meta( self, dataset, copy_from=None ):
        Alignment.init_meta( self, dataset, copy_from=copy_from )
    def set_meta( self, dataset, overwrite = True, **kwd ):
        """
        Parses and sets species, chromosomes, index from MAF file.
        """
        #these metadata values are not accessable by users, always overwrite
        indexes, species, species_chromosomes, blocks = COPIED_build_maf_index_species_chromosomes( dataset.file_name )
        if indexes is None:
            return #this is not a MAF file
        dataset.metadata.species = species
        dataset.metadata.blocks = blocks
        
        #write species chromosomes to a file
        chrom_file = dataset.metadata.species_chromosomes
        if not chrom_file:
            chrom_file = dataset.metadata.spec['species_chromosomes'].param.new_file( dataset = dataset )
        chrom_out = open( chrom_file.file_name, 'wb' )
        for spec, chroms in species_chromosomes.items():
            chrom_out.write( "%s\t%s\n" % ( spec, "\t".join( chroms ) ) )
        chrom_out.close()
        dataset.metadata.species_chromosomes = chrom_file
        
        index_file = dataset.metadata.maf_index
        if not index_file:
            index_file = dataset.metadata.spec['maf_index'].param.new_file( dataset = dataset )
        indexes.write( open( index_file.file_name, 'wb' ) )
        dataset.metadata.maf_index = index_file
    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            # The file must exist on disk for the get_file_peek() method
            dataset.peek = data.get_file_peek( dataset.file_name, is_multi_byte=is_multi_byte )
            if dataset.metadata.blocks:
                dataset.blurb = "%s blocks" % util.commaify( str( dataset.metadata.blocks ) )
            else:
                # Number of blocks is not known ( this should not happen ), and auto-detect is
                # needed to set metadata
                dataset.blurb = "? blocks"
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        return self.make_html_table( dataset )
    def make_html_table( self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        try:
            out.append('<tr><th>Species:&nbsp;')
            for species in dataset.metadata.species:
                out.append( '%s&nbsp;' % species )
            out.append( '</th></tr>' )
            if not dataset.peek:
                dataset.set_peek()
            data = dataset.peek
            lines =  data.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                out.append( '<tr><td>%s</td></tr>' % escape( line ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % exc
        return out
    def sniff( self, filename ):
        """
        Determines wether the file is in maf format
        
        The .maf format is line-oriented. Each multiple alignment ends with a blank line. 
        Each sequence in an alignment is on a single line, which can get quite long, but 
        there is no length limit. Words in a line are delimited by any white space. 
        Lines starting with # are considered to be comments. Lines starting with ## can 
        be ignored by most programs, but contain meta-data of one form or another.
        
        The first line of a .maf file begins with ##maf. This word is followed by white-space-separated 
        variable=value pairs. There should be no white space surrounding the "=".
     
        For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format5
        
        >>> fname = get_test_fname( 'sequence.maf' )
        >>> Maf().sniff( fname )
        True
        >>> fname = get_test_fname( 'sequence.fasta' )
        >>> Maf().sniff( fname )
        False
        """
        headers = get_headers( filename, None )
        try:
            if len(headers) > 1 and headers[0][0] and headers[0][0] == "##maf":
                return True
            else:
                return False
        except:
            return False

class MafCustomTrack( data.Text ):
    file_ext = "mafcustomtrack"
    
    MetadataElement( name="vp_chromosome", default='chr1', desc="Viewport Chromosome", readonly=True, optional=True, visible=False, no_value='' )
    MetadataElement( name="vp_start", default='1', desc="Viewport Start", readonly=True, optional=True, visible=False, no_value='' )
    MetadataElement( name="vp_end", default='100', desc="Viewport End", readonly=True, optional=True, visible=False, no_value='' )
    
    def set_meta( self, dataset, overwrite = True, **kwd ):
        """
        Parses and sets viewport metadata from MAF file.
        """
        max_block_check = 10
        chrom = None
        forward_strand_start = float( 'inf' )
        forward_strand_end = 0
        try:
            maf_file = open( dataset.file_name )
            maf_file.readline() #move past track line
            for i, block in enumerate( bx.align.maf.Reader( maf_file ) ):
                ref_comp = block.get_component_by_src_start( dataset.metadata.dbkey )
                if ref_comp:
                    ref_chrom = bx.align.maf.src_split( ref_comp.src )[-1]
                    if chrom is None:
                        chrom = ref_chrom
                    if chrom == ref_chrom:
                        forward_strand_start = min( forward_strand_start, ref_comp.forward_strand_start )
                        forward_strand_end = max( forward_strand_end, ref_comp.forward_strand_end )
                if i > max_block_check:
                    break
            
            if forward_strand_end > forward_strand_start:
                dataset.metadata.vp_chromosome = chrom
                dataset.metadata.vp_start = forward_strand_start
                dataset.metadata.vp_end = forward_strand_end
        except:
            pass

class Axt( data.Text ):
    """Class describing an axt alignment"""
    
    # gvk- 11/19/09 - This is really an alignment, but we no longer have tools that use this data type, and it is
    # here simply for backward compatibility ( although it is still in the datatypes registry ).  Subclassing
    # from data.Text eliminates managing metadata elements inherited from the Alignemnt class.

    file_ext = "axt"

    def sniff( self, filename ):
        """
        Determines whether the file is in axt format
        
        axt alignment files are produced from Blastz, an alignment tool available from Webb Miller's lab 
        at Penn State University.
        
        Each alignment block in an axt file contains three lines: a summary line and 2 sequence lines.
        Blocks are separated from one another by blank lines.
        
        The summary line contains chromosomal position and size information about the alignment. It
        consists of 9 required fields.
        
        The sequence lines contain the sequence of the primary assembly (line 2) and aligning assembly
        (line 3) with inserts.  Repeats are indicated by lower-case letters.
    
        For complete details see http://genome.ucsc.edu/goldenPath/help/axt.html
        
        >>> fname = get_test_fname( 'alignment.axt' )
        >>> Axt().sniff( fname )
        True
        >>> fname = get_test_fname( 'alignment.lav' )
        >>> Axt().sniff( fname )
        False
        """
        headers = get_headers( filename, None )
        if len(headers) < 4:
            return False
        for hdr in headers:
            if len(hdr) > 0 and hdr[0].startswith("##matrix=axt"):
                return True
            if len(hdr) > 0 and not hdr[0].startswith("#"):
                if len(hdr) != 9:
                    return False
                try:
                    map ( int, [hdr[0], hdr[2], hdr[3], hdr[5], hdr[6], hdr[8]] )
                except:
                    return False
                if hdr[7] not in data.valid_strand:
                    return False
                else:
                    return True

class Lav( data.Text ):
    """Class describing a LAV alignment"""

    file_ext = "lav"

    # gvk- 11/19/09 - This is really an alignment, but we no longer have tools that use this data type, and it is
    # here simply for backward compatibility ( although it is still in the datatypes registry ).  Subclassing
    # from data.Text eliminates managing metadata elements inherited from the Alignemnt class.

    def sniff( self, filename ):
        """
        Determines whether the file is in lav format
        
        LAV is an alignment format developed by Webb Miller's group. It is the primary output format for BLASTZ.
        The first line of a .lav file begins with #:lav.
    
        For complete details see http://www.bioperl.org/wiki/LAV_alignment_format
        
        >>> fname = get_test_fname( 'alignment.lav' )
        >>> Lav().sniff( fname )
        True
        >>> fname = get_test_fname( 'alignment.axt' )
        >>> Lav().sniff( fname )
        False
        """
        headers = get_headers( filename, None )
        try:
            if len(headers) > 1 and headers[0][0] and headers[0][0].startswith('#:lav'):
                return True
            else:
                return False
        except:
            return False

