#!/usr/bin/env python

'''
Mutation Visualizer tool
'''

from __future__ import division

import sys, csv, os, math
import optparse

from galaxy import eggs
import pkg_resources
pkg_resources.require( "SVGFig" )
import svgfig as svg

COLS_PER_SAMPLE = 7
HEADER_COLS = 4

HEIGHT = 6
WIDTH = 12
BAR_WIDTH = 1.5
GAP = 2


colors = {'A':'blue', 'C':'green', 'G':'orange', 'T':'red'}
bases = ['A', 'C', 'G', 'T' ]


def mainsvg(opts):
    s = svg.SVG('g', transform="translate(20,0)")
    
    # display legend
    for i, b in enumerate( bases ):
        bt = svg.SVG("tspan", b, style="font-family:Verdana;font-size:3")
        s.append(svg.SVG("text", bt, x=12+(i*10), y=8, stroke="none", fill="black"))
        s.append(svg.SVG("rect", x=13+(i*10), y=5, width=4, height=3, 
                         stroke="none", fill=colors[b], fill_opacity=0.5))
    
    # display labels
    bt = svg.SVG("tspan", "1's", style="font-family:Verdana;font-size:3")
    s.append(svg.SVG("text", bt, x=60, y=8, stroke="none", fill="black"))
    s.append(svg.SVG("rect", x=62, y=5, width=4, height=3, 
                     stroke="none", fill='grey', fill_opacity=0.1))
    bt = svg.SVG("tspan", "2's", style="font-family:Verdana;font-size:3")
    s.append(svg.SVG("text", bt, x=70, y=8, stroke="none", fill="black"))
    s.append(svg.SVG("rect", x=72, y=5, width=4, height=3, 
                     stroke="none", fill='grey', fill_opacity=0.2))

    
    reader = open(opts.input_file, 'U')

    headers = []
    if opts.header_row:
        headers = [yy for yy in reader.readline().split('\t') if yy.strip()]
    
    for i, h in enumerate(headers):
        x = 20+(i*10)
        y = 25
        t = svg.SVG("text", svg.SVG("tspan", h, style="font-family:Verdana;font-size:3"), 
                    x=x, y=y, transform="rotate(-90 %i,%i)" % (x, y), stroke="none", fill="black")
        s.append(t)
    
    count=1
    for line in reader:
        row = line.split('\t')
        highlighted_position = False
        show_pos = True
        position = int(row[1])
        ref = row[3]
        #print 'position', position, ref, count
        
        # display positions
        bt = svg.SVG("tspan", str(position), style="font-family:Verdana;font-size:4")
        s.append(svg.SVG("text", bt, x=7, y=34+(count*(HEIGHT+GAP)), stroke="none", fill="black"))
        s.append(svg.SVG("rect", x=0, y=30+(count*(HEIGHT+GAP)), width=14, height=HEIGHT, 
                         stroke='none', fill=colors[ref.upper()], fill_opacity=0.2))
        
        for sample_index in range(int((len(row)-HEADER_COLS)/COLS_PER_SAMPLE)):
            start_col = HEADER_COLS+(COLS_PER_SAMPLE*sample_index)
            n_a = int(row[start_col])
            n_c = int(row[start_col+1])
            n_g = int(row[start_col+2])
            n_t = int(row[start_col+3])
            total = int(row[start_col+4])
            diff = int(row[start_col+5])
            imp = int(row[start_col+6])
            
            #print 'sample_index', sample_index, total
            if total:
                x = 16+(sample_index*(WIDTH+GAP))
                y = 30+(count*(HEIGHT+GAP))
                width = WIDTH
                height = HEIGHT
                
                if imp == 1:
                    fill_opacity = 0.1
                elif imp == 2:
                    fill_opacity = 0.2
                else:
                    fill_opacity = 0.3
                
                s.append(svg.SVG("rect", x=x, y=y, width=width, height=height, 
                                 stroke='none', fill='grey', fill_opacity=fill_opacity))
                for base, value in enumerate([n_a, n_c, n_g, n_t]):
                    width = int(math.ceil(value / total * WIDTH))
                    s.append(svg.SVG("rect", x=x, y=y, width=width, height=BAR_WIDTH, 
                                     stroke='none', fill=colors[bases[base]], fill_opacity=0.6))
                    y = y + BAR_WIDTH
                    #print base, value, total, x, y, width
                    


        count=count+1
        
    #print x, y
    
    zoom = int(opts.zoom)
    w = "%ipx" % (x*(10+zoom))
    h = "%ipx" % (y*(2+zoom))
    canv = svg.canvas(s, width=w, height=h, viewBox="0 0 %i %i" %(x+100, y+100))
    canv.save(opts.output_file)

    
if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-i', '--input-file', dest='input_file', action='store')
    parser.add_option('-o', '--output-file', dest='output_file', action='store')
    parser.add_option('-z', '--zoom', dest='zoom', action='store', default='1')
    parser.add_option('-n', '--noheaders', dest='header_row', action='store_false', default=True)
    (opts, args) = parser.parse_args()
    mainsvg(opts)
    sys.exit(1)

    