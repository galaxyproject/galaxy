import sys
import string
import tempfile
import subprocess
from os import path

# -----------------------------------------------------------------------------------

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

# -----------------------------------------------------------------------------------
def gi_name_to_sorted_list(file_name, gi_col, name_col):
    """ Suppose input file looks like this:
        a       2
        b       4
        c       5
        d       5
        where column 1 is gi_col and column 0 is name_col
        output of this function will look like this:
        [[2, 'a'], [4, 'b'], [5, 'c'], [5, 'd']]
    """

    result = []
    try:
        F = open( file_name, 'r' )
        try:
            for line in F:
                file_cols = string.split(line.rstrip(), '\t')
                file_cols[gi_col] = int(  file_cols[gi_col] )
                result.append( [ file_cols[gi_col], file_cols[name_col] ] )
        except:
            print >>sys.stderr, 'Non numeric GI field...skipping'
            
    except Exception, e:
        stop_err('%s\n' % e)
    F.close()
    result.sort()
    return result   

# -----------------------------------------------------------------------------------

def collapse_repeating_gis( L ):
    """ Accepts 2-d array of gi-key pairs such as this
        L = [
                [gi1, 'key1'],
                [gi1, 'key2'],
                [gi2','key3']
            ]

         Returns this:
         [      [gi1, 'key1', 'key2'],
                [gi2, 'key3' ]
         ]
         
         The first value in each sublist MUST be int
    """
    gi = []
    i = 0
    result = []
    
    try:
        for item in L:
            if i == 0:
                prev = item[0]
            
            if prev != item[0]:
                prev_L = []
                prev_L.append( prev )
                result.append( prev_L + gi )
                prev = item[0]
                gi =[]
                
            gi.append( item[1] )
            i += 1
            
    except Exception, e:
        stop_err('%s\n' % e)
        
    prev_L = []
    prev_L.append( prev )
    result.append( prev_L + gi )
    del(L)
    return result

# -----------------------------------------------------------------------------------

def get_taxId( gi2tax_file, gi_name_list, out_file ):
    """ Maps GI numbers from gi_name_list to TaxId identifiers from gi2tax_file and
        prints result to out_file

        gi2tax_file MUST be sorted on GI column

        gi_name_list is a list that look slike this:
        [[1,'a'], [2,'b','x'], [7,'c'], [10,'d'], [90,'f']]
        where the first element of each sublist is a GI number
        this list MUST also be sorted on GI

        This function searches through 117,000,000 rows of gi2taxId file from NCBI
        in approximately 4 minutes. This time is not dependent on the length of
        gi_name_list
    """

    L = gi_name_list.pop(0)
    my_gi = L[0]
    F = open( out_file, 'w' )
    gi = 0
    for line in file( gi2tax_file ):
        line = line.rstrip()
        gi, taxId = string.split( line, '\t' )
        gi = int( gi )
        
        if gi > my_gi:
            try:
                while ( my_gi < gi ):
                    L = gi_name_list.pop(0)
                    my_gi = L[0]
            except:
                break
    
        if  gi == my_gi:
            for i in range( 1,len( L ) ):
                print >>F, '%s\t%s\t%d' % (L[i], taxId, gi)
            try:
                L = gi_name_list.pop(0)
                my_gi = L[0]
            except:
                break

# -----------------------------------------------------------------------------------


try:
    in_f          = sys.argv[1]            # input file with GIs
    gi_col        = int( sys.argv[2] ) - 1 # column in input containing GIs
    name_col      = int( sys.argv[3] ) - 1 # column containing sequence names
    out_f         = sys.argv[4]            # output file
    tool_data     = sys.argv[5]
except:
    stop_err('Check arguments\n')

#  GI2TAX point to a file produced by concatenation of:
#  ftp://ftp.ncbi.nih.gov/pub/taxonomy/gi_taxid_nucl.zip
#  and
#  ftp://ftp.ncbi.nih.gov/pub/taxonomy/gi_taxid_prot.zip
#  a sorting using this command:
#  sort -n -k 1

GI2TAX = path.join( tool_data, 'taxonomy', 'gi_taxid_sorted.txt' )

#  NAME_FILE and NODE_FILE point to names.dmg and nodes.dmg
#  files contained within:
#  ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz

NAME_FILE = path.join( tool_data, 'taxonomy', 'names.dmp' )
NODE_FILE = path.join( tool_data, 'taxonomy', 'nodes.dmp' )

g2n =  gi_name_to_sorted_list(in_f, gi_col, name_col)

if len(g2n) == 0:
    stop_err('No valid GI-containing fields. Please, check your column assignments.\n')

tb_F = tempfile.NamedTemporaryFile('w')

get_taxId( GI2TAX, collapse_repeating_gis( g2n ), tb_F.name )

try:
    tb_cmd = 'taxBuilder %s %s %s %s' % ( NAME_FILE, NODE_FILE, tb_F.name, out_f )
    retcode = subprocess.call( tb_cmd, shell=True )
    if retcode < 0:
        print >>sys.stderr, "Execution of taxBuilder terminated by signal", -retcode
except OSError, e:
    print >>sys.stderr, "Execution of taxBuilder2tree failed:", e
