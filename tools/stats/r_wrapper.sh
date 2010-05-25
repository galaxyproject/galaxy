#!/bin/sh

### Run R providing the R script in $1 as standard input and passing 
### the remaining arguments on the command line

# Function that writes a message to stderr and exits
function fail
{
    echo "$@" >&2
    exit 1
}

# Ensure R executable is found
which R > /dev/null || fail "'R' is required by this tool but was not found on path" 

# Extract first argument
infile=$1; shift

# Ensure the file exists
test -f $infile || fail "R input file '$infile' does not exist"

# Invoke R passing file named by first argument to stdin
R --vanilla --slave $* < $infile
