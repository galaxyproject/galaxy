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


def mainsvg(opts, args):
    s = svg.SVG('g', id='viewport')
    
    # display legend
    for i, b in enumerate( bases ):
        bt = svg.SVG("tspan", b, style="font-family:Verdana;font-size:20%")
        s.append(svg.SVG("text", bt, x=12+(i*10), y=4, stroke="none", fill="black"))
        s.append(svg.SVG("rect", x=14+(i*10), y=1, width=4, height=3, 
                         stroke="none", fill=colors[b], fill_opacity=0.5))

    reader = open(opts.input_file, 'U')

    samples = []
    for i in range(int(len(args)/3)):
        index = i*3
        samples.append(dict(name=args[index],
                            a_col=args[index+1],
                            totals_col=args[index+2]))

    if opts.zoom == 'interactive':
        y = 35
    else:
        y = 25
    for i, sample in enumerate(samples):
        x = 23+(i*(WIDTH+GAP))
        t = svg.SVG("text", svg.SVG("tspan", sample['name'], style="font-family:Verdana;font-size:25%"), 
                    x=x, y=y, transform="rotate(-90 %i,%i)" % (x, y), stroke="none", fill="black")
        s.append(t)
    
    count=1
    for line in reader:
        row = line.split('\t')
        highlighted_position = False
        show_pos = True
        position = row[int(opts.position_col)-1]
        ref = row[int(opts.ref_col)-1]
        # display positions
        if opts.zoom == 'interactive':
            textx = 0
        else:
            textx = 7
        bt = svg.SVG("tspan", str(position), style="font-family:Verdana;font-size:25%")
        s.append(svg.SVG("text", bt, x=textx, y=34+(count*(HEIGHT+GAP)), stroke="none", fill="black"))
        s.append(svg.SVG("rect", x=0, y=30+(count*(HEIGHT+GAP)), width=14, height=HEIGHT, 
                         stroke='none', fill=colors[ref.upper()], fill_opacity=0.2))
        
        for sample_index, sample in enumerate(samples):
            n_a = int(row[int(sample['a_col'])-1])
            n_c = int(row[int(sample['a_col'])+1-1])
            n_g = int(row[int(sample['a_col'])+2-1])
            n_t = int(row[int(sample['a_col'])+3-1])
            total = int(row[int(sample['totals_col'])-1])
            imp = 1 #int(row[start_col+6])
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

                if count%2:
                    s.append(svg.SVG("rect", x=x, y=y, width=width, height=height, 
                                     stroke='none', fill='grey', fill_opacity=0.25))
                else:
                    s.append(svg.SVG("rect", x=x, y=y, width=width, height=height, 
                                     stroke='none', fill='grey', fill_opacity=0.25))
                
                for base, value in enumerate([n_a, n_c, n_g, n_t]):
                    width = int(math.ceil(value / total * WIDTH))
                    s.append(svg.SVG("rect", x=x, y=y, width=width, height=BAR_WIDTH, 
                                     stroke='none', fill=colors[bases[base]], fill_opacity=0.6))
                    y = y + BAR_WIDTH

        count=count+1
        
    if opts.zoom == 'interactive':
        canv = svg.canvas(s)
        canv.save(opts.output_file)
        import fileinput
        flag = False
        for line in fileinput.input(opts.output_file, inplace=1):
            if line.startswith('<svg'):
                print '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1">'
                flag = True
                continue
            else:
                if flag:
                    print '<script xlink:href="/static/scripts/SVGPan.js"/>\r\n<defs id="defs4" />\r\n<script xlink:href="/static/scripts/SVGPan.js"/>'
                flag = False
            print line,
    else:
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
    parser.add_option('-p', '--position_col', dest='position_col', action='store', default='c0')
    parser.add_option('-r', '--ref_col', dest='ref_col', action='store', default='c1')
    #parser.add_option('-n', '--interactive', dest='interactive', action='store_false', default='True')
    (opts, args) = parser.parse_args()
    mainsvg(opts, args)
    sys.exit(1)

    