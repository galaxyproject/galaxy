#!/usr/bin/env python
# Greg Von Kuster
"""
This tool takes a tab-delimited textfile as input and creates another column in the file which is the result of
a computation performed on every row in the original file.  The tool will skip over invalid lines within the file,
informing the user about the number of lines skipped.  Invalid lines are those that do not follow the standard 
defined when the get_wrap_func function (immediately below) is applied to the first uncommented line in the input file.
"""
import sys, sets, re, os.path

def get_wrap_func(value, round):
    """
    Determine the data type of each column in the input file
    (valid data types for columns are either string or float)
    """
    try:
        if round == 'no':
            check = float(value)
            return 'float(%s)'
        else:
            check = int(value)
            return 'int(%s)'
    except:
        return 'str(%s)'

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

# we expect 4 parameters
if len(sys.argv) != 5:
    print sys.argv
    stop_err('Usage: python column_maker.py input_file ouput_file condition round')

inp_file = sys.argv[1]
out_file = sys.argv[2]
cond_text = sys.argv[3]
round = sys.argv[4]

# replace if input has been escaped
mapped_str = {
    '__lt__': '<',
    '__le__': '<=',
    '__gt__': '>',
    '__ge__': '>=',
    '__sq__': '\'',
    '__dq__': '"',
}
for key, value in mapped_str.items():
    cond_text = cond_text.replace(key, value)

# safety measures
safe_words = sets.Set( "c chr str float int split map lambda and or len".split() )
try:
    # filter on words
    patt = re.compile('[a-z]+')
    for word in patt.findall(cond_text):
        if word not in safe_words:
            raise Exception, word
except Exception, e:
    stop_err("Cannot recognize the word %s in condition %s" % (e, cond_text) )

"""
Determine the number of columns in the input file and the data type for each
"""
elems = []
if os.path.exists( inp_file ):
    for line in open( inp_file ):
        line = line.strip()
        if line and not line.startswith( '#' ):
            elems = line.split( '\t' )
            break
else:
    stop_err('The input data file "%s" does not exist.' % inp_file)

if not elems:
    stop_err('No non-blank or non-comment lines in input data file "%s"' % inp_file)    

if len(elems) == 1:
    if len(line.split()) != 1:
        stop_err('This tool can only be run on tab delimited files')

"""
Prepare the column variable names and wrappers for column data types
"""
cols, funcs = [], []
for ind, elem in enumerate(elems):
    name = 'c%d' % ( ind + 1 )
    cols.append(name)
    funcs.append(get_wrap_func(elem, round) % name)

col   = ', '.join(cols)
func  = ', '.join(funcs)
assign = "%s = line.split('\\t')" % col
wrap   = "%s = %s" % (col, func)
skipped_lines = 0
first_invalid_line = 0
invalid_line = None
flags = []
cols = []

# Read input file, skipping invalid lines, and perform computation that will result in a new column
code = '''
for i, line in enumerate( open( inp_file )):
    line = line.strip()
    if line and not line.startswith( '#' ):
        try:
            %s
            %s
            cols.append(%s)
            flags.append(True)
        except:
            skipped_lines += 1
            cols.append('')
            flags.append(False)
            if not invalid_line:
                first_invalid_line = i + 1
                invalid_line = line
    else:
        cols.append('')
        flags.append(False)
''' % (assign, wrap, cond_text)

exec code

# Write output file
fp = open(out_file, 'wt')
keep = 0
total = 0
for flag, value, line in zip(flags, cols, file(inp_file)):
    total += 1
    if flag:
        line = line.strip()
        line = '%s\t%s\n' % (line, value)
        fp.write(line)
        keep += 1
fp.close()

print 'Creating column %d with expression %s' % (len(elems)+1, cond_text)
if skipped_lines > 0:
    print ', kept %d of %d original lines.  ' % ( keep, total )
    print 'Skipped %d invalid lines in file starting with line # %d, data: %s' % ( skipped_lines, first_invalid_line, invalid_line )
    
