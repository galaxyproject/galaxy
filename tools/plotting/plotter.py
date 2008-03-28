#!/usr/bin/env python

# python histogram input_file output_file column bins 
import sys, os
import matplotlib; matplotlib.use('Agg')

from pylab import *

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

if __name__ == '__main__':
    # parse the arguments
    
    if len(sys.argv) != 6:
        stop_err('Usage: python histogram.py input_file column bins output_file style')
        sys.exit()

    mode = sys.argv[5]
    HIST = mode == 'hist'
    try:
        col =  int(float(sys.argv[2]))
        if HIST:
            bin = int(float(sys.argv[3]))
        else:
            # hack, this parameter is the plotting style for scatter plots
            if sys.argv[3] == 'P':
                style = 'o'
            elif sys.argv[3] == 'LP':
                style = 'o-'
            else:
                style = '-'

    except:
        msg = 'Parameter were not numbers %s, %s' % (sys.argv[3], sys.argv[4])
        stop_err(msg)

    # validate arguments
    inp_file = sys.argv[1]
    out_file = sys.argv[4]

    if HIST:
        print "Histogram on column %s (%s bins)" % (col, bin)
    else:
        print "Scatterplot on column %s" % (col)

    xcol= col -1
    # read the file
    values = []
    try:
        count = 0
        for line in file(inp_file):
            count += 1
            line = line.strip()
            if line and line[0] != '#':
                values.append(float(line.split()[xcol]))
    except Exception, e:
        stop_err('%s' % e)
        stop_err("Non numerical data at line %d, column %d" % (count, col) )

    # plot the data

    if HIST:
        n, bins, patches = hist(values, bins=bin, normed=0)
    else:
        plot(values, style)
    
    xlabel('values')
    ylabel('counts')

    if HIST:
        title('Histogram of values over column %s (%s bins)' % (col, len(bins)) )
    else:
        title('Scatterplot over column %s' % col )        
    grid(True)
    
    # the plotter detects types by file extension
    png_out = out_file + '.png' # force it to png
    savefig(png_out)

    # shuffle it back and clean up
    data = file(png_out, 'rb').read() 
    fp = open(out_file, 'wb')
    fp.write(data)
    fp.close()
    os.remove(png_out)
