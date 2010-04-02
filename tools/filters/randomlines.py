#!/usr/bin/env python
# Kanwei Li, 2010
# Selects N random lines from a file and outputs to another file

import random, sys

def main():
    infile = open(sys.argv[1], 'r')
    total_lines = int(sys.argv[2])
    
    if total_lines < 1:
        sys.stderr.write( "Must select at least one line." )
        sys.exit()
    
    kept = []
    n = 0
    for line in infile:
        line = line.rstrip("\n")
        n += 1
        if (n <= total_lines):
            kept.append(line)
        elif random.randint(1, n) <= total_lines:
            kept.pop(random.randint(0, total_lines-1))
            kept.append(line)
    
    if n < total_lines:
        sys.stderr.write( "Error: asked to select more lines than there were in the file." )
        sys.exit()
        
    open(sys.argv[3], 'w').write( "\n".join(kept) )
    
if __name__ == "__main__":
    main()
