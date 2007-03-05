"""
Middleware that profiles the request with cProfile and displays profiling
information at the bottom of each page.
"""

import sys
import os
import threading
import cgi
import time
from cStringIO import StringIO
from paste import response

try:
    # Included in Python 2.5 
    import cProfile
except:
    # Included in lsprof packae for Python 2.4
    import pkg_resources
    pkg_resources.require( "lsprof" )
    import cProfile

import pstats

template = """
<script>
function show_profile_output()
{
var win = window.open("", "win"); // a window object
var doc = win.document;
doc.open("text/html", "replace");
doc.write("<HTML><HEAD><TITLE>Profiler output</TITLE></HEAD><BODY>")
doc.write(document.getElementById( 'profile_output' ).innerHTML)
doc.write("</BODY></HTML>");
doc.close();
}
function show_inline()
{
document.getElementById( 'profile_output' ).style.display="block";
}
</script>
<div style="background-color: #ff9; color: #000; border: 2px solid #000; padding: 5px;">
show profile output: <a href="javascript:show_inline();">inline</a> | <a href="javascript:show_profile_output();">new window</a>
<div id="profile_output" style="display: none">
<hr />
%s
</div>
</div>
"""

class ProfileMiddleware(object):

    """
    Middleware that profiles all requests.

    All HTML pages will have profiling information appended to them.
    The data is isolated to that single request, and does not include
    data from previous requests.
    """

    def __init__( self, app, global_conf=None, limit=40 ):
        self.app = app
        self.lock = threading.Lock()
        self.limit = limit

    def __call__(self, environ, start_response):
        catch_response = []
        body = []
        def replace_start_response(status, headers, exc_info=None):
            catch_response.extend([status, headers])
            start_response(status, headers, exc_info)
            return body.append
        def run_app():
            body.extend(self.app(environ, replace_start_response))
        #self.lock.acquire()
        try:
            # Run in profiler
            prof = cProfile.Profile()
            prof.runctx( "run_app()", globals(), locals() )
            # Build up body with stats
            body = ''.join(body)
            headers = catch_response[1]
            content_type = response.header_value(headers, 'content-type')
            if not content_type.startswith('text/html'):
                # We can't add info to non-HTML output
                return [body]
            stats = Stats( prof )
            stats.strip_dirs()
            stats.sort_stats('time', 'calls')
            #output = capture_output(stats.print_stats, self.limit)
            #output_callers = capture_output(
            #    stats.print_callers, self.limit)
            stats.f = StringIO()
            stats.print_stats( self.limit )
            output = stats.f.getvalue()
            output_callers = ""
            #body += '<div style="%s">%s\n%s</div>' % (
            #    self.style, output, cgi.escape(output_callers))
            body += template % output
            return [body]
        finally:
            pass
            # self.lock.release()
        
# pstats.Stats annoyingly assumes you want to print to stdout, to avoid this 
# we have to duplicate the whole thing here. Since we're at it, also format
# as HTML and escape values.
    
class Stats( pstats.Stats ):    
    
    def print_cell( self, val, tag="td" ):
        print >> self.f, "<%s>%s</%s>" % ( tag, cgi.escape( val ), tag )
    
    def get_print_list(self, sel_list):
        width = self.max_name_len
        if self.fcn_list:
            list = self.fcn_list[:]
            msg = "   Ordered by: " + self.sort_type + '\n'
        else:
            list = self.stats.keys()
            msg = "   Random listing order was used\n"

        for selection in sel_list:
            list, msg = self.eval_print_amount(selection, list, msg)

        count = len(list)

        if not list:
            return 0, list
        print >> self.f, "<div>", cgi.escape( msg ), "</div>"
        if count < len(self.stats):
            width = 0
            for func in list:
                if  len(func_std_string(func)) > width:
                    width = len(func_std_string(func))
        return width+2, list
    
    def print_stats( self, *amount ):
        for filename in self.files:
            print >> self.f, filename
        if self.files: print >> self.f, ""
        indent = ' ' * 8
        for func in self.top_level:
            print >> self.f, indent, func_get_function_name(func)

        print >> self.f, indent, self.total_calls, "function calls",
        if self.total_calls != self.prim_calls:
            print >> self.f, "(%d primitive calls)" % self.prim_calls,
        print >> self.f, "in %.3f CPU seconds" % self.total_tt
        print >> self.f, ""
        width, list = self.get_print_list(amount)
        if list:
            print >> self.f, "<table>"
            print >> self.f, '<tr><th>ncalls</th><th>tottime</th><th>percall</th>' \
                             '<th>cumtime</th><th>percall</th><th>filename:lineno(function)</th></tr>'
            for func in list:
                self.print_line(func)
            print >> self.f, "</table>"
        return self
    
    def print_line( self, func ):  # hack : should print percentages
        print >> self.f, "<tr>"
        cc, nc, tt, ct, callers = self.stats[func]
        c = str(nc)
        if nc != cc:
            c = c + '/' + str(cc)
        self.print_cell( c )
        self.print_cell( f8(tt) )
        if nc == 0:
            self.print_cell( "" )
        else:
            self.print_cell( f8(tt/nc) )
        self.print_cell( f8(ct) )
        if cc == 0:
            self.print_cell( "" )
        else:
            self.print_cell( f8(ct/cc) )
        self.print_cell( func_std_string(func) )
        print >> self.f, "<tr>"

def func_get_function_name(func):
    return func[2]

def func_std_string(func_name): # match what old profile produced
    if func_name[:2] == ('~', 0):
        # special case for built-in functions
        name = func_name[2]
        if name.startswith('<') and name.endswith('>'):
            return '{%s}' % name[1:-1]
        else:
            return name
    else:
        return "%s:%d(%s)" % func_name

def add_func_stats(target, source):
    """Add together all the stats for two profile entries."""
    cc, nc, tt, ct, callers = source
    t_cc, t_nc, t_tt, t_ct, t_callers = target
    return (cc+t_cc, nc+t_nc, tt+t_tt, ct+t_ct,
              add_callers(t_callers, callers))

def add_callers(target, source):
    """Combine two caller lists in a single list."""
    new_callers = {}
    for func, caller in target.iteritems():
        new_callers[func] = caller
    for func, caller in source.iteritems():
        if func in new_callers:
            new_callers[func] = caller + new_callers[func]
        else:
            new_callers[func] = caller
    return new_callers

def count_calls(callers):
    """Sum the caller statistics to get total number of calls received."""
    nc = 0
    for calls in callers.itervalues():
        nc += calls
    return nc

def f8(x):
    return "%8.3f" % x