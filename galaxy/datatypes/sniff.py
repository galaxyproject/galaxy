"""
File format detector
"""
import logging, sys, os, csv, tempfile, shutil, re

log = logging.getLogger(__name__)

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
        line = line.strip() + '\n' 
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
    (defaults to tab separator)
    
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
    
    count = len(headers[0])
    if count < 2:
        return False
    
    for hdr in headers:
        if len(hdr) != count:
            return False
    return True
        
def is_fasta(headers):
    """
    Determines wether the file is in fasta format
    
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
    
    >>> headers = get_headers(__file__, sep=' ')
    >>> is_fasta(headers)
    False
    >>> fname = get_test_fname('test.gff')
    >>> headers = get_headers(fname,sep=' ')
    >>> is_gff(headers)
    True
    """
    try:
        return len(headers) > 2 and headers[0][1] and headers[0][1].startswith('gff-version')
    except:
        return False

def is_maf(headers):
    """
    Determines wether the file is in maf format
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
    >>> headers = get_headers(__file__, sep=None)
    >>> is_axt(headers)
    False
    >>> fname = get_test_fname('alignment.axt')
    >>> headers = get_headers(fname, sep=None)
    >>> is_axt(headers)
    True
   """
    try:        
        return (len(headers) >= 4) and (headers[0][7] == '-' or headers[0][7] == '+') and (headers[3] == []) and (len(headers[0])==9 or len(headers[0])==10)    
    except:
        return False

def is_wiggle(headers):
    """
    Determines wether the file is in wiggle format
    
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
            if hdr and hdr[0] == "track":
                return True
            if idx > 10:
                break
        return False
    except:
        return False

def is_bed(headers, skip=0):
    """
    Checks for 'bedness'

    >>> fname = get_test_fname('test_tab.bed')
    >>> headers = get_headers(fname, sep='\\t')
    >>> is_bed(headers)
    True

    >>> fname = get_test_fname('interval.bed')
    >>> headers = get_headers(fname, sep='\\t')
    >>> is_bed(headers)
    False
    """
    try:
        if not headers:
            return False
        
        for hdr in headers[skip:]:
            try:   
                map(int, [ hdr[1], hdr[2] ])
            except:
                return False
        return True
    except:
        return False

def is_interval(headers):
    """
    Checks for 'intervalness'

    >>> fname = get_test_fname('test_space.bed')
    >>> headers = get_headers(fname, sep=' ')
    >>> is_interval(headers)
    False

    >>> fname = get_test_fname('interval.bed')
    >>> headers = get_headers(fname, sep='\\t')
    >>> is_interval(headers)
    True

    """
    try:
        return is_bed(headers, skip=1) and headers[0][0][0] == '#'
    except:
        return False

def guess_ext(fname):
    """
    Returns an extension that can be used in the datatype factory to
    generate a data for the 'fname' file

    >>> fname = get_test_fname('interval.bed')
    >>> guess_ext(fname)
    'interval'
    
    >>> fname = get_test_fname('test_tab.bed')
    >>> guess_ext(fname)
    'bed'
    
    >>> fname = get_test_fname('sequence.maf')
    >>> guess_ext(fname)
    'maf'
    
    >>> fname = get_test_fname('sequence.fasta')
    >>> guess_ext(fname)
    'fasta'

    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("a 2\\nc 1")
    >>> guess_ext(fname)
    'tabular'

    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("a  1  2  x\\nb  3  4  y")
    >>> guess_ext(fname)
    'bed'
    
    >>> fname = get_test_fname('test.gff')
    >>> guess_ext(fname)
    'gff'
    """
    try:
        #guess if data is binary
        for line in file(fname):
            for char in line:
                if ord(char) > 128:
                    return "data"
        
        headers = get_headers(fname, sep=None)
        if is_gff(headers):
            return 'gff'
        if is_maf(headers):
            return 'maf'
        elif is_fasta(headers):
            return 'fasta'
        elif is_wiggle(headers):
            return 'wig'
        elif is_axt(headers):
            return 'axt'
        elif is_lav(headers):
            return 'lav'
        
        # convert space to tabs
        if is_column_based(fname, sep=' '):
            sep2tabs(fname)

        if is_column_based(fname, sep='\t'):
            headers = get_headers(fname, sep='\t')
            if is_bed(headers):
                return 'bed'
            if is_interval(headers):
                return 'interval'
            
            return 'tabular'
    except:
        pass
    return 'text'

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
    
