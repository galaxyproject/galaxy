"""
File format detector
"""
import logging, sys, os, csv, tempfile, shutil, re
import registry

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
        line  = line.rstrip('\r\n')
        elems = regexp.split(line)
        fp.write('\t'.join(elems) + '\n')
    fp.close()
    os.remove(temp_name)

def get_headers(fname, sep, count=60):
    """
    Returns a list with the first 'count' lines split by 'sep'
    
    >>> fname = get_test_fname('complete.bed')
    >>> get_headers(fname,'\\t')
    [['chr7', '127475281', '127491632', 'NM_000230', '0', '+', '127486022', '127488767', '0', '3', '29,172,3225,', '0,10713,13126,'], ['chr7', '127486011', '127488900', 'D49487', '0', '+', '127486022', '127488767', '0', '2', '155,490,', '0,2399']]
    """
    headers = []
    for idx, line in enumerate(file(fname)):
        line = line.rstrip('\n\r')
        headers.append( line.split(sep) )
        if idx == count:
            break
    return headers
    
def is_column_based(fname, sep='\t', skip=0):
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
    >>> fname = get_test_fname('test_ensembl.tab')
    >>> is_column_based(fname)
    True
    """
    headers = get_headers(fname, sep)
    count = 0
    
    if not headers:
        return False
    for hdr in headers[skip:]:
        if hdr and hdr[0] and not hdr[0].startswith('#'):
            if len(hdr) > 1:
                count = len(hdr)
            break
    if count < 2:
        return False
    for hdr in headers[skip:]:
        if hdr and hdr[0] and not hdr[0].startswith('#'):
            if len(hdr) != count:
                return False
    return True

def guess_ext( fname ):
    """
    Returns an extension that can be used in the datatype factory to
    generate a data for the 'fname' file

    >>> fname = get_test_fname('interval.interval')
    >>> guess_ext(fname)
    'interval'
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
    >>> fname = get_test_fname('file.html')
    >>> guess_ext(fname)
    'html'
    >>> fname = get_test_fname('test.gff')
    >>> guess_ext(fname)
    'gff'
    >>> fname = get_test_fname('gff_version_3.gff')
    >>> guess_ext(fname)
    'gff3'
    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("a 2\\nc 1\\nd 0")
    >>> guess_ext(fname)
    'tabular'
    >>> fname = get_test_fname('temp.txt')
    >>> file(fname, 'wt').write("a 1 2 x\\nb 3 4 y\\nc 5 6 z")
    >>> guess_ext(fname)
    'tabular'
    """ 
    datatypes_registry = registry.Registry()
    for datatype in datatypes_registry.sniff_order:
        """
        Some classes may not have a sniff function, which is ok.  In fact, the
        Tabular and Text classes are 2 examples of classes that should never have
        a sniff function.  Since these classes are default classes, they contain 
        few rules to filter out data of other formats, so they should be called
        from this function after all other datatypes in sniff_order have not been
        successfully discovered.
        """
        try:
            format = datatype.sniff( fname )
        except:
            format = ''
        if format:
            return format

    """Default binary file extension"""
    for line in file( fname ):
        for char in line:
            if ord(char) > 128:
                return "data"
            else:
                break
        break
    if is_column_based( fname, ' ', 1 ):
        sep2tabs(fname)
    if is_column_based( fname, '\t', 1):
        return "tabular"
    return 'txt'

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
    
