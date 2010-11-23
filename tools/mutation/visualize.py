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


SVGPan = """
/**
 *  SVGPan library 1.2
 * ====================
 *
 * Given an unique existing element with id "viewport", including the
 * the library into any SVG adds the following capabilities:
 *
 *  - Mouse panning
 *  - Mouse zooming (using the wheel)
 *  - Object dargging
 *
 * Known issues:
 *
 *  - Zooming (while panning) on Safari has still some issues
 *
 * Releases:
 *
 * 1.2, Sat Mar 20 08:42:50 GMT 2010, Zeng Xiaohui
 *      Fixed a bug with browser mouse handler interaction
 *
 * 1.1, Wed Feb  3 17:39:33 GMT 2010, Zeng Xiaohui
 *      Updated the zoom code to support the mouse wheel on Safari/Chrome
 *
 * 1.0, Andrea Leofreddi
 *      First release
 *
 * This code is licensed under the following BSD license:
 *
 * Copyright 2009-2010 Andrea Leofreddi (a.leofreddi@itcharm.com). All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without modification, are
 * permitted provided that the following conditions are met:
 *
 *    1. Redistributions of source code must retain the above copyright notice, this list of
 *       conditions and the following disclaimer.
 *
 *    2. Redistributions in binary form must reproduce the above copyright notice, this list
 *       of conditions and the following disclaimer in the documentation and/or other materials
 *       provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY Andrea Leofreddi ``AS IS'' AND ANY EXPRESS OR IMPLIED
 * WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
 * FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL Andrea Leofreddi OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
 * ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
 * NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
 * ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * The views and conclusions contained in the software and documentation are those of the
 * authors and should not be interpreted as representing official policies, either expressed
 * or implied, of Andrea Leofreddi.
 */

var root = document.documentElement;

var state = 'none', stateTarget, stateOrigin, stateTf;

setupHandlers(root);

/**
 * Register handlers
 */
function setupHandlers(root){
        setAttributes(root, {
                "onmouseup" : "add(evt)",
                "onmousedown" : "handleMouseDown(evt)",
                "onmousemove" : "handleMouseMove(evt)",
                "onmouseup" : "handleMouseUp(evt)",
                //"onmouseout" : "handleMouseUp(evt)", // Decomment this to stop the pan functionality when dragging out of the SVG element
        });

        if(navigator.userAgent.toLowerCase().indexOf('webkit') >= 0)
                window.addEventListener('mousewheel', handleMouseWheel, false); // Chrome/Safari
        else
                window.addEventListener('DOMMouseScroll', handleMouseWheel, false); // Others
}

/**
 * Instance an SVGPoint object with given event coordinates.
 */
function getEventPoint(evt) {
        var p = root.createSVGPoint();

        p.x = evt.clientX;
        p.y = evt.clientY;

        return p;
}

/**
 * Sets the current transform matrix of an element.
 */
function setCTM(element, matrix) {
        var s = "matrix(" + matrix.a + "," + matrix.b + "," + matrix.c + "," + matrix.d + "," + matrix.e + "," + matrix.f + ")";

        element.setAttribute("transform", s);
}

/**
 * Dumps a matrix to a string (useful for debug).
 */
function dumpMatrix(matrix) {
        var s = "[ " + matrix.a + ", " + matrix.c + ", " + matrix.e + "\\n  " + matrix.b + ", " + matrix.d + ", " + matrix.f + "\\n  0, 0, 1 ]";

        return s;
}

/**
 * Sets attributes of an element.
 */
function setAttributes(element, attributes){
        for (i in attributes)
                element.setAttributeNS(null, i, attributes[i]);
}

/**
 * Handle mouse move event.
 */
function handleMouseWheel(evt) {
        if(evt.preventDefault)
                evt.preventDefault();

        evt.returnValue = false;

        var svgDoc = evt.target.ownerDocument;

        var delta;

        if(evt.wheelDelta)
                delta = evt.wheelDelta / 3600; // Chrome/Safari
        else
                delta = evt.detail / -90; // Mozilla

        var z = 1 + delta; // Zoom factor: 0.9/1.1

        var g = svgDoc.getElementById("viewport");
       
        var p = getEventPoint(evt);

        p = p.matrixTransform(g.getCTM().inverse());

        // Compute new scale matrix in current mouse position
        var k = root.createSVGMatrix().translate(p.x, p.y).scale(z).translate(-p.x, -p.y);

        setCTM(g, g.getCTM().multiply(k));

        stateTf = stateTf.multiply(k.inverse());
}

/**
 * Handle mouse move event.
 */
function handleMouseMove(evt) {
        if(evt.preventDefault)
                evt.preventDefault();

        evt.returnValue = false;

        var svgDoc = evt.target.ownerDocument;

        var g = svgDoc.getElementById("viewport");

        if(state == 'pan') {
                // Pan mode
                var p = getEventPoint(evt).matrixTransform(stateTf);

                setCTM(g, stateTf.inverse().translate(p.x - stateOrigin.x, p.y - stateOrigin.y));
        } else if(state == 'move') {
                // Move mode
                var p = getEventPoint(evt).matrixTransform(g.getCTM().inverse());

                setCTM(stateTarget, root.createSVGMatrix().translate(p.x - stateOrigin.x, p.y - stateOrigin.y).multiply(g.getCTM().inverse()).multiply(stateTarget.getCTM()));

                stateOrigin = p;
        }
}

/**
 * Handle click event.
 */
function handleMouseDown(evt) {
        if(evt.preventDefault)
                evt.preventDefault();

        evt.returnValue = false;

        var svgDoc = evt.target.ownerDocument;

        var g = svgDoc.getElementById("viewport");

        if(evt.target.tagName == "svg") {
                // Pan mode
                state = 'pan';

                stateTf = g.getCTM().inverse();

                stateOrigin = getEventPoint(evt).matrixTransform(stateTf);
        }
        /*else {
                // Move mode
                state = 'move';

                stateTarget = evt.target;

                stateTf = g.getCTM().inverse();

                stateOrigin = getEventPoint(evt).matrixTransform(stateTf);
        }*/
}
/**
 * Handle mouse button release event.
 */
function handleMouseUp(evt) {
        if(evt.preventDefault)
                evt.preventDefault();

        evt.returnValue = false;

        var svgDoc = evt.target.ownerDocument;

        if(state == 'pan' || state == 'move') {
                // Quit pan mode
                state = '';
        }
}
"""

COLS_PER_SAMPLE = 7
HEADER_COLS = 4

HEIGHT = 6
WIDTH = 12
BAR_WIDTH = 1.5
GAP = 2


colors = {'A':'blue', 'C':'green', 'G':'orange', 'T':'red'}
bases = ['A', 'C', 'G', 'T' ]

def stop_error(message):
    print >> sys.stderr, message
    sys.exit(1)

def validate_bases(n_a, n_c, n_g, n_t, total):
    if n_a > total:
        return 'A'
    elif n_c > total:
        return 'C'
    elif n_g > total:
        return 'G'
    elif n_t > total:
        return 'T'
    return None

def main(opts, args):
    s = svg.SVG('g', id='viewport')
    
    # display legend
    for i, b in enumerate( bases ):
        bt = svg.SVG("tspan", b, style="font-family:Verdana;font-size:20%")
        s.append(svg.SVG("text", bt, x=12+(i*10), y=3, stroke="none", fill="black"))
        s.append(svg.SVG("rect", x=14+(i*10), y=0, width=4, height=3, 
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
        ref = row[int(opts.ref_col)-1].strip().upper()
        # validate
        if ref not in bases: 
            stop_error( "The reference column (col%s) contains invalid character '%s' at row %i of the dataset." % ( opts.ref_col, ref, count ) )
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
            # validate
            base_error = validate_bases(n_a, n_c, n_g, n_t, total)
            if base_error:
                stop_error("For sample %i (%s), the number of base %s reads is more than the coverage on row %i." % (sample_index+1, 
                                                                                                                     sample['name'], 
                                                                                                                     base_error, 
                                                                                                                     count))
 
            if total:
                x = 16+(sample_index*(WIDTH+GAP))
                y = 30+(count*(HEIGHT+GAP))
                width = WIDTH
                height = HEIGHT
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
                    print '<script type="text/javascript">%s</script>' % SVGPan
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
    (opts, args) = parser.parse_args()
    main(opts, args)
    sys.exit(1)

    