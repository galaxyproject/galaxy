#!/usr/bin/env python
#Greg Von Kuster
"""
This tool takes a tab-delimited textfile as input and creates filters on columns based on certain properties.
The tool will skip over invalid lines within the file, informing the user about the number of lines skipped.
Invalid lines are those that do not follow the standard defined when the get_wrap_func function (immediately below)
is applied to the first uncommented line in the input file.
"""
import sys, sets, re, os.path

def get_wrap_func(value):
    """
    Determine the data type of each column in the input file
    (valid data types for columns are either string or float)
    """
    try:
        check = float(value)
        return 'float(%s)'
    except:
        return 'str(%s)'

def get_operands(astring):
    # Note that the order of all_operators is important
    items_to_strip = ['+', '-', '**', '*', '//', '/', '%', '<<', '>>', '&', '|', '^', '~', '<=', '<', '>=', '>', '==', '!=', '<>', ' and ', ' or ', ' not ', ' is ', ' is not ', ' in ', ' not in ']
    for item in items_to_strip:
        if astring.find(item) >= 0:
            astring = astring.replace(item, ' ')
    operands = sets.Set(astring.split(' '))
    return operands

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

# we expect 4 parameters
if len(sys.argv) != 4:
    print sys.argv
    stop_err('Usage: python filtering.py input_file ouput_file condition')
#debug 
#cond_text = "(c2-c3) < 115487120 and c1=='chr7' "
#sys.argv.extend( [ 'a.txt', 'b.txt', cond_text ])

inp_file  = sys.argv[1]
out_file  = sys.argv[2]
cond_text = sys.argv[3]

if cond_text == '' or cond_text == None:
    print 'Empty filtering condition'
    sys.exit()
        
# replace if input has been escaped
mapped_str = {
    '__lt__': '<',
    '__le__': '<=',
    '__eq__': '==',
    '__ne__': '!=',
    '__gt__': '>',
    '__ge__': '>=',
    '__sq__': '\'',
    '__dq__': '"',
}
for key, value in mapped_str.items():
    cond_text = cond_text.replace(key, value)

"""
We'll attempt to determine if the condition includes executable stuff and, if so, exit
"""
secured = dir()
operands = get_operands(cond_text)

for operand in operands:
    try:
        map(int, operand)
    except:
        if operand == '=':
            print 'Syntax error in "%s" - make sure to use proper operators (e.g., <=, ==, >=)' %cond_text
            sys.exit()
        if operand in secured:
            stop_err("Illegal value %s in condition %s" % (operand, cond_text) )

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
    print 'The data file you selected for filtering does not exist.'
    sys.exit()

if not elems:
    print 'No non-blank or non-comment lines in the data you selected for filtering'
    sys.exit()

if len(elems) == 1:
    if len(line.split()) != 1:
        print 'This tool can only be run on tab delimited data'
        sys.exit()

"""
Prepare the column variable names and wrappers for column data types
"""
cols, funcs = [], []
for ind, elem in enumerate(elems):
    name = 'c%d' % ( ind + 1 )
    cols.append(name)
    funcs.append(get_wrap_func(elem) % name)

col = ', '.join(cols)
func = ', '.join(funcs)
assign = "%s = line.split('\\t')" % col
wrap = "%s = %s" % (col, func)
skipped_lines = 0
first_invalid_line = 0
invalid_line = None
flags = []

# Read and filter input file, skipping invalid lines
code = '''
for i, line in enumerate( open( inp_file )):
    line = line.strip()
    if line and not line.startswith( '#' ):
        try:
            %s
            %s
            if %s:
                flags.append(True)
            else:
                flags.append(False)
        except:
            skipped_lines += 1
            flags.append(False)
            if not invalid_line:
                first_invalid_line = i + 1
                invalid_line = line
    else:
        flags.append(False)
''' % (assign, wrap, cond_text)

exec code

# Write filtered output file
fp = open(out_file, 'wt')
keep = 0
total = 0
for flag, line in zip(flags, file(inp_file)):
    total += 1
    if flag:
        fp.write(line)
        keep  += 1
fp.close()

print 'Filtering with %s, ' % cond_text
print 'kept %4.2f%% of %d lines.' % ( 100.0*keep/len(flags), total )
if skipped_lines > 0:
    print 'Condition/data issue: skipped %d invalid lines starting at line #%d which is "%s"-valid lines are %s' % ( skipped_lines, first_invalid_line, invalid_line, func )
    
    
