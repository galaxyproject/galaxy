"""
Wrapper for tree2PS-fast
Requires ps2pdf (a part of ghostscript package) to be installed

t2ps_wrapper.py <taxonomy file> <output PDF file> <max_tree_level> <font_size> <max_leaves> <count_duplicate_tax_id>

    taxonomy file    - tree file produced by taxonomy2tree program written by Sergei Kosakovski Pond
    output PDF file  - tree image
    max_tree_level   - integer from 0 to 21; 0 = show all levels
    font_size        - integer from 2 to 255 (8 is the best)
    max_leaves       - integer from 0 to infinity (0 = show all)
    count_duplicate  - 0 (do not count) or 1 (count)
    
anton nekrutenko | anton@bx.psu.edu
tree2PS-fast is written by Sergei Kosakovski Pond | sergeilkp@mac.com
"""

import string, sys, tempfile, subprocess

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


try:
    tree_file = sys.argv[1]
    pdf_file  = sys.argv[2]
    max_tree_level = sys.argv[3]
    font_size = sys.argv[4]
    max_leaves = sys.argv[5]
    dups = sys.argv[6]
except:
    stop_err('Check arguments\n')

newick_file = tempfile.NamedTemporaryFile('w')    
ps_file = tempfile.NamedTemporaryFile('w')

# Execute taxonomy2tree
    
try:
    t2t_cmd = 'taxonomy2tree %s %s %s /dev/null 1 > /dev/null 2>&1' % ( tree_file, max_tree_level, newick_file.name )
    retcode = subprocess.call( t2t_cmd, shell=True )
    if retcode < 0:
        print >>sys.stderr, "Execution of taxonomy2tree terminated by signal", -retcode
except OSError, e:
    print >>sys.stderr, "Execution of taxonomy2tree failed:", e


# Execute tree2PS-fast
    
try:
    t2ps_cmd = 'tree2PS-fast %s %s %s %s %s %s' % ( newick_file.name, ps_file.name, max_tree_level, font_size, max_leaves, dups )
    retcode = subprocess.call( t2ps_cmd, shell=True )
    if retcode < 0:
        print >>sys.stderr, "Execution of tree2PS-fast terminated by signal", -retcode
except OSError, e:
    print >>sys.stderr, "Execution of tree2PS-fast failed:", e
    
# Convert PS to PDF

try:
    ps2pdf_cmd = 'ps2pdf %s %s' % ( ps_file.name, pdf_file )
    retcode = subprocess.call( ps2pdf_cmd, shell=True )
    if retcode < 0:
        print >>sys.stderr, "Execution of ps2pdf terminated by signal", -retcode
except OSError, e:
    print >>sys.stderr, "Execution of ps2pdf failed:", e
