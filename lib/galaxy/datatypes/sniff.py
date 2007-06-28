"""
File format detector
"""
import logging, sys, os, csv, tempfile, shutil, re

log = logging.getLogger(__name__)
valid_strand = ['+', '-', '.']
valid_gff3_strand = ['+', '-', '.', '?']
valid_gff3_phase = ['.', '0', '1', '2']
        
def get_test_fname(fname):
    """Returns test data filename"""
    path, name = os.path.split(__file__)
    full_path = os.path.join(path, 'test', fname)
    return full_path

def stream_to_file(stream):
    """
    Writes a stream to a temporary file, returns the temporary file's name
    """
    fd, temp_name = tempfile.mkstemp()
    while 1:
        chunk = stream.read(1048576)
        if not chunk:
            break
        os.write(fd, chunk)
    os.close(fd)
    return temp_name

def convert_newlines(fname):
    """
    Converts in place a file from universal line endings 
    to line endings for the current platform

    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("1 2\\r3 4")
    >>> convert_newlines(fname)
    >>> file(fname).read()
    '1 2\\n3 4\\n'
    """
    fd, temp_name = tempfile.mkstemp()
    os.close(fd)
    shutil.copyfile(fname, temp_name)
    fp = open(fname, "wt")
    for line in file(temp_name, "U"):
        line = line.rstrip() + '\n' 
        fp.write(line)
    fp.close()
    os.remove(temp_name)

def sep2tabs(fname, patt="\\s+"):
    """
    Transforms in place a 'sep' separated file to a tab separated one

    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("1 2\\n3 4\\n")
    >>> sep2tabs(fname)
    >>> file(fname).read()
    '1\\t2\\n3\\t4\\n'
    """
    fd, temp_name = tempfile.mkstemp()
    os.close(fd)
    shutil.copyfile(fname, temp_name)
    
    regexp = re.compile(patt)
    fp = open(fname, 'wt')
    for line in file(temp_name):
        line  = line.strip()
        elems = regexp.split(line)
        fp.write('\t'.join(elems) + '\n')
    fp.close()
    os.remove(temp_name)

def get_headers(fname, sep, count=30):
    """
    Returns a list with the first 'count' lines split by 'sep'
    
    >>> fname = get_test_fname('interval.bed')
    >>> get_headers(fname, sep='\\t', count=2)
    [['#chrom', 'start', 'end', 'name', 'value', 'strand'], ['chr7', '115444712', '115444739', 'CCDS5763.1_cds_0_0_chr7_115444713_f', '0', '+']]
    """
    headers = []
    for idx, line in enumerate(file(fname)):
        line = line.strip()
        if idx == count:
            break
        headers.append( line.split(sep) )
    return headers
    
def is_column_based(fname, sep='\t'):
    """
    Checks whether the file is column based with respect to a separator 
    (defaults to tab separator).
    
    >>> fname = get_test_fname('test.gff')
    >>> is_column_based(fname)
    True
    >>> fname = get_test_fname('test_tab.bed')
    >>> is_column_based(fname)
    True
    >>> is_column_based(fname, sep=' ')
    False
    >>> fname = get_test_fname('test_space.bed')
    >>> is_column_based(fname)
    False
    >>> is_column_based(fname, sep=' ')
    True
    """
    headers  = get_headers(fname, sep=sep)
    
    if not headers:
        return False
    
    for hdr in headers:
        if hdr[0] and not (hdr[0] == '' or hdr[0].startswith( '#' )):
            count = len(hdr)
            break
    
    if count < 2:
        return False
    
    for hdr in headers:
        if hdr[0] and not (hdr[0] == '' or hdr[0].startswith( '#' )) and len(hdr) != count:
            return False
    return True
        
def is_fasta(headers):
    """
    Determines wether the file is in fasta format
    
    A sequence in FASTA format consists of a single-line description, followed by lines of sequence data. 
    The first character of the description line is a greater-than (">") symbol in the first column. 
    All lines should be shorter than 80 charcters
    
    For complete details see http://www.g2l.bio.uni-goettingen.de/blast/fastades.html
    
    >>> headers = get_headers(__file__, sep=' ')
    >>> is_fasta(headers)
    False
    >>> fname = get_test_fname('sequence.fasta')
    >>> headers = get_headers(fname,sep=' ')
    >>> is_fasta(headers)
    True
    """
    try:
        return len(headers) > 1 and headers[0][0] and headers[0][0][0] == ">"
    except:
        return False

def is_gff(headers):
    """
    Determines wether the file is in gff format
    
    GFF lines have nine required fields that must be tab-separated.
    
    For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format3
    
    >>> headers = get_headers(__file__, sep=' ')
    >>> is_fasta(headers)
    False
    >>> fname = get_test_fname('test.gff')
    >>> headers = get_headers(fname,sep='\\t')
    >>> is_gff(headers)
    True
    """
    try:
        if len(headers) < 2:
            return False
        for idx, hdr in enumerate(headers):
            if len(hdr) > 1 and hdr[0] != '' and not hdr[0].startswith( '#' ):
                if len(hdr) != 9: 
                    return False
                try:
                    map( int, [hdr[3], hdr[4]] )
                except:
                    return False
                if hdr[5] != '.':
                    try:
                        score = int(hdr[5])
                    except:
                        return False
                    if (score < 0 or score > 1000):
                        return False
                if hdr[6] not in valid_strand:
                    return False
            if idx > 29:
                break
        return True
    except:
        return False

def is_gff3(headers):
    """
    Determines wether the file is in gff version 3 format
    
    GFF 3 format:

    1) adds a mechanism for representing more than one level 
       of hierarchical grouping of features and subfeatures.
    2) separates the ideas of group membership and feature name/id
    3) constrains the feature type field to be taken from a controlled
       vocabulary.
    4) allows a single feature, such as an exon, to belong to more than
       one group at a time.
    5) provides an explicit convention for pairwise alignments
    6) provides an explicit convention for features that occupy disjunct regions
    
    The format consists of 9 columns, separated by tabs (NOT spaces).
    
    Undefined fields are replaced with the "." character, as described in the original GFF spec.

    For complete details see http://song.sourceforge.net/gff3.shtml
    
    >>> headers = get_headers(__file__, sep=' ')
    >>> is_fasta(headers)
    False
    >>> fname = get_test_fname('gff_version_3.gff')
    >>> headers = get_headers(fname,sep='\\t')
    >>> is_gff3(headers)
    True
    """
    try:
        if len(headers) < 2:
            return False
        for idx, hdr in enumerate(headers):
            if len(hdr) > 1 and hdr[0] != '' and not hdr[0].startswith( '#' ):
                if len(hdr) != 9: 
                    return False
                try:
                    map( int, [hdr[3]] )
                except:
                    if hdr[3] != '.':
                        return False
                try:
                    map( int, [hdr[4]] )
                except:
                    if hdr[4] != '.':
                        return False
                if hdr[5] != '.':
                    try:
                        score = int(hdr[5])
                    except:
                        return False
                    if (score < 0 or score > 1000):
                        return False
                if hdr[6] not in valid_gff3_strand:
                    return False
                if hdr[7] not in valid_gff3_phase:
                    return False
            if idx > 29:
                break
        return True
    except:
        return False

def is_maf(headers):
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
    
    >>> headers = get_headers(__file__, sep=' ')
    >>> is_maf(headers)
    False
    >>> fname = get_test_fname('sequence.maf')
    >>> headers = get_headers(fname, sep=' ')
    >>> is_maf(headers)
    True
    """
    try:
        return len(headers) > 1 and headers[0][0] and headers[0][0] == "##maf"
    except:
        return False

def is_lav(headers):
    """
    Determines wether the file is in lav format
    
    LAV is an alignment format developed by Webb Miller's group. It is the primary output format for BLASTZ.
    The first line of a .lav file begins with #:lav.

    For complete details see http://www.bioperl.org/wiki/LAV_alignment_format
    
    >>> headers = get_headers(__file__, sep=' ')
    >>> is_lav(headers)
    False
    >>> fname = get_test_fname('alignment.lav')
    >>> headers = get_headers(fname, sep=' ')
    >>> is_lav(headers)
    True
    """
    try:
        return len(headers) > 1 and headers[0][0] and headers[0][0].startswith('#:lav')
    except:
        return False

def is_axt(headers):
    """
    Determines wether the file is in axt format
    
    axt alignment files are produced from Blastz, an alignment tool available from Webb Miller's lab 
    at Penn State University.  Each alignment block in an axt file contains three lines: a summary 
    line and 2 sequence lines. Blocks are separated from one another by blank lines.
    
    The summary line contains chromosomal position and size information about the alignment. It consists of 9 required fields:

    For complete details see http://genome.ucsc.edu/goldenPath/help/axt.html
    
    >>> headers = get_headers(__file__, sep=None)
    >>> is_axt(headers)
    False
    >>> fname = get_test_fname('alignment.axt')
    >>> headers = get_headers(fname, sep=None)
    >>> is_axt(headers)
    True
   """
    try:     
        #return (len(headers) >= 4) and (headers[0][7] == '-' or headers[0][7] == '+') and (headers[3] == []) and (len(headers[0])==9 or len(headers[0])==10) 
        if len(headers) < 4:
            return False
        """
        Assume the summary line is the first line of the file.
        """   
        line = headers[0]
        
        if len(line) != 9:
            return False
        try:
            map ( int, [line[0], line[2], line[3], line[5], line[6], line[8]] )
        except:
            return False
        if line[7] not in valid_strand:
            return False
        return True
    except:
        return False

def is_wiggle(headers):
    """
    Determines wether the file is in wiggle format

    The .wig format is line-oriented. Wiggle data is preceeded by a track definition line,
    which adds a number of options for controlling the default display of this track.
    Following the track definition line is the track data, which can be entered in several
    different formats.

    The track definition line begins with the word 'track' followed by the track type.
    The track type with version is REQUIRED, and it currently must be wiggle_0.  For example,
    track type=wiggle_0...
    
    For complete details see http://genome.ucsc.edu/goldenPath/help/wiggle.html
    
    >>> headers = get_headers(__file__, sep=' ')
    >>> is_wiggle(headers)
    False
    >>> fname = get_test_fname('wiggle.wig')
    >>> headers = get_headers(fname, sep=' ')
    >>> is_wiggle(headers)
    True
    """
    try:
        for idx, hdr in enumerate(headers):
            if hdr and hdr[0] == 'track' and hdr[1].startswith('type=wiggle'):
                return True
            if idx > 29:
                break
        return False
    except:
        return False

def is_bed(headers, skip=1):
    """
    Checks for 'bedness'
    
    BED lines have three required fields and nine additional optional fields. 
    The number of fields per line must be consistent throughout any single set of data in 
    an annotation track.
    
    For complete details see http://genome.ucsc.edu/FAQ/FAQformat#format1
    
    >>> fname = get_test_fname('test_tab.bed')
    >>> headers = get_headers(fname, sep='\\t')
    >>> is_bed(headers)
    True
    >>> fname = get_test_fname('interval.bed')
    >>> headers = get_headers(fname, sep='\\t')
    >>> is_bed(headers)
    True
    >>> fname = get_test_fname('complete.bed')
    >>> headers = get_headers(fname, sep='\\t')
    >>> is_bed(headers)
    True
    """
    try:
        if not headers:
            return False
        for hdr in headers[skip:]:
            if len(hdr) < 3 or len(hdr) > 12:
                return False
            if hdr[0].startswith('chr') or hdr[0].startswith('scaffold'):
                try:
                    map( int, [hdr[1], hdr[2]] )
                except:
                    return False
                if len(hdr) > 3:
                    """
                    Since all 9 of these fields are optional, it is difficult to test
                    for specific column values...
                    """
                    optionals = hdr[3:]
                    """
                    ...we can, however, test complete BED definitions fairly easily.
                    """
                    if len(optionals) == 9:
                        try:
                            map ( int, [optionals[1], optionals[3], optionals[4], optionals[5], optionals[6]] )
                        except:
                            return False
                        score = int(optionals[1])
                        if score < 0 or score > 1000:
                            return False
                        if optionals[2] not in ['+', '-']:
                            return False
                        if int(optionals[5]) != 0:
                            return False
                        block_count = int(optionals[6])
                        """
                        Sometime the blosck_sizes and block_starts lists end in extra commas
                        """
                        block_sizes = optionals[7].rstrip(',').split(',')
                        block_starts = optionals[8].rstrip(',').split(',')
                        if len(block_sizes) != block_count or len(block_starts) != block_count:
                            return False
                    elif len(optionals) > 4 and len(optionals) < 9:
                        """
                        Here it gets a bit trickier, but in this case, we can be somewhat confident 
                        that optionals will include a strand column
                        """
                        is_valid_strand = False
                        for ele in optionals:
                            if ele in valid_bed_strand:
                                is_valid_strand = True
                        if not is_valid_strand:
                            return False
        return True
    except:
        return False

def is_interval(headers, skip=1):
    """
    Checks for 'intervalness'

    This is the most loosely defined format and is mostly used by galaxy itself.  In general, if
    the format is_column_based, but not any of the other formats, then it must be interval.
    
    >>> fname = get_test_fname('test_space.bed')
    >>> headers = get_headers(fname, sep='\\t')
    >>> is_interval(headers)
    False
    >>> fname = get_test_fname('interval.interval')
    >>> headers = get_headers(fname, sep='\\t')
    >>> is_interval(headers)
    True
    """
    
    try:
        #return is_bed(headers, skip=1) and headers[0][0][0] == '#'
        """
        If we got here, we already know the file is_column_based and is not bed,
        so we'll just look for some valid data.
        """
        for hdr in headers[skip:]:
            if not (hdr[0] == '' or hdr[0].startswith( '#' )):
                if len(hdr) < 3:
                    return False
                try:
                    map( int, [hdr[1], hdr[2]] )
                except:
                    return False
        return True
    except:
        return False

def is_html(headers):
    """
    Determines wether the file is in html format
    
    >>> headers = get_headers(__file__, sep=' ')
    >>> is_html(headers)
    False
    >>> fname = get_test_fname('file.html')
    >>> headers = get_headers(fname, sep=' ')
    >>> is_html(headers)
    True
    """
    try:
        for idx, hdr in enumerate(headers):
            if hdr and hdr[0].lower() == '<html>':
                return True
            if idx > 29:
                """
                This is a weakness since it assumes < 29 blank lines, comments, etc.
                """
                break
        return False
    except:
        return False

def guess_ext(fname):
    """
    Returns an extension that can be used in the datatype factory to
    generate a data for the 'fname' file

    >>> fname = get_test_fname('interval.interval')
    >>> guess_ext(fname)
    'interval'
    >>> fname = get_test_fname('interval.bed')
    >>> guess_ext(fname)
    'bed'
    >>> fname = get_test_fname('test_tab.bed')
    >>> guess_ext(fname)
    'bed'
    >>> fname = get_test_fname('sequence.maf')
    >>> guess_ext(fname)
    'maf'
    >>> fname = get_test_fname('sequence.fasta')
    >>> guess_ext(fname)
    'fasta'
    >>> fname = get_test_fname('file.html')
    >>> guess_ext(fname)
    'html'
    >>> fname = get_test_fname('test.gff')
    >>> guess_ext(fname)
    'gff'
    >>> fname = get_test_fname('gff_version_3.gff')
    >>> guess_ext(fname)
    'gff'
    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("a 2\\nc 1")
    >>> guess_ext(fname)
    'tabular'
    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("a  1  2  x\\nb  3  4  y")
    >>> guess_ext(fname)
    'bed'
    
    """
    try:
        """
        The order in which we attempt to determine data format is pretty important
        because some formats are much more flexibly defined than others.  Interval format
        is the most loosely defined, so it should be that last format we check.
        """
        #guess if data is binary
        for line in file(fname):
            for char in line:
                if ord(char) > 128:
                    return "data"
        
        headers = get_headers(fname, sep=None)
        if is_maf(headers):
            return 'maf'
        elif is_lav(headers):
            return 'lav'
        elif is_fasta(headers):
            return 'fasta'
        elif is_wiggle(headers):
            return 'wig'
        elif is_html(headers):
            return 'html'
        elif is_axt(headers):
            return 'axt'

        if is_column_based(fname, sep='\t'):
            headers = get_headers(fname, sep='\t')
            if is_gff(headers) or is_gff3(headers):
                return 'gff'
        elif is_column_based(fname, sep=' '):
            sep2tabs(fname)

        if is_column_based(fname, sep='\t'):
            headers = get_headers(fname, sep='\t')
            if is_bed(headers):
                return 'bed'
            elif is_interval(headers):
                return 'interval'
            else:
                return 'tabular'
    except:
        pass
    return 'text'

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
    
