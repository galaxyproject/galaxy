"""
Middleware that profiles the request with cProfile and displays profiling
information at the bottom of each page.
"""

import threading
import cgi
import cProfile
import pstats

from paste import response


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
        stats = pstats.Stats( prof )
        stats.strip_dirs()
        stats.sort_stats( 'time', 'calls' )
        output = pstats_as_html( stats, self.limit )
        body += template % output
        return [body]


def pstats_as_html( stats, *sel_list ):
    """
    Return an HTML representation of a pstats.Stats object.
    """
    rval = []
    # Number of function calls, primitive calls, total time
    rval.append( "<div>%d function calls (%d primitive) in %0.3f CPU seconds</div>"
                 % ( stats.total_calls, stats.prim_calls, stats.total_tt ) )
    # Extract functions that match 'sel_list'
    funcs, order_message, select_message = get_func_list( stats, sel_list )
    # Deal with any ordering or selection messages
    if order_message:
        rval.append( "<div>%s</div>" % cgi.escape( order_message ) )
    if select_message:
        rval.append( "<div>%s</div>" % cgi.escape( select_message ) )
    # Build a table for the functions
    if list:
        rval.append( "<table>" )
        # Header
        rval.append( "<tr><th>ncalls</th>"
                     "<th>tottime</th>"
                     "<th>percall</th>"
                     "<th>cumtime</th>"
                     "<th>percall</th>"
                     "<th>filename:lineno(function)</th></tr>" )
        for func in funcs:
            rval.append( "<tr>" )
            # Calculate each field
            cc, nc, tt, ct, callers = stats.stats[ func ]
            # ncalls
            ncalls = str(nc)
            if nc != cc:
                ncalls = ncalls + '/' + str(cc)
            rval.append( "<td>%s</td>" % cgi.escape( ncalls ) )
            # tottime
            rval.append( "<td>%0.8f</td>" % tt )
            # percall
            if nc == 0:
                percall = ""
            else:
                percall = "%0.8f" % ( tt / nc )
            rval.append( "<td>%s</td>" % cgi.escape( percall ) )
            # cumtime
            rval.append( "<td>%0.8f</td>" % ct )
            # ctpercall
            if cc == 0:
                ctpercall = ""
            else:
                ctpercall = "%0.8f" % ( ct / cc )
            rval.append( "<td>%s</td>" % cgi.escape( ctpercall ) )
            # location
            rval.append( "<td>%s</td>" % cgi.escape( func_std_string( func ) ) )
            # row complete
            rval.append( "</tr>" )
        rval.append( "</table>")
        # Concatenate result
        return "".join( rval )


def get_func_list( stats, sel_list ):
    """
    Use 'sel_list' to select a list of functions to display.
    """
    # Determine if an ordering was applied
    if stats.fcn_list:
        list = stats.fcn_list[:]
        order_message = "Ordered by: " + stats.sort_type
    else:
        list = stats.stats.keys()
        order_message = "Random listing order was used"
    # Do the selection and accumulate messages
    select_message = ""
    for selection in sel_list:
        list, select_message = stats.eval_print_amount( selection, list, select_message )
    # Return the list of functions selected and the message
    return list, order_message, select_message


def func_std_string( func_name ):
    """
    Match what old profile produced
    """
    if func_name[:2] == ('~', 0):
        # special case for built-in functions
        name = func_name[2]
        if name.startswith('<') and name.endswith('>'):
            return '{%s}' % name[1:-1]
        else:
            return name
    else:
        return "%s:%d(%s)" % func_name
