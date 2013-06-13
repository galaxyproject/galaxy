<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Memory Profiling</%def>
<%
    import re
    from xml.sax.saxutils import escape, unescape
%>

<style type="text/css">
    a.breadcrumb:link,
    a.breadcrumb:visited,
    a.breadcrumb:active {
        text-decoration: none;
    }
    a.breadcrumb:hover {
        text-decoration: underline;
    }
</style>

<h2>Memory Profiling</h2>

<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='admin', action='memdump', dump=True )}">Dump memory (warning: hangs server!)</a></li>
    <li><a class="action-button" href="${h.url_for( controller='admin', action='memdump', setref=True )}">Set reference point</a></li>
</ul>

<%def name="htmlize( heap )">
<%
    s = escape( str( heap ) )
    new_s = ""
    id_re = re.compile('^(\s+)([0-9]+)')
    for line in s.split( '\n' ):
        try:
            id = id_re.search( line ).group( 2 )
        except:
            id = None
        new_s += re.sub( id_re, r'\1<a href="' + h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_id=id ) + r'">\2</a>', line )
        if id and heap[int(id)].count == 1:
            new_s += " <a href='%s'>theone</a>\n" % h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_id=id, theone=True )
        else:
            new_s += "\n"
    return new_s
%>
</%def>

%if message:
    ${render_msg( message, status )}
%endif

%if heap is None:
    No memory dump available.  Click "Dump memory" to create one.
%else:
    <pre>
    <br/>
You are here: ${breadcrumb}<br/>
    %if breadcrumb.endswith( 'theone' ):
        ${heap}
    %else:
    <nobr>
Sort:
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Class')}">Class</a> |
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Clodo' )}">Clodo</a> |
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Id' )}">Id</a> |
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Idset' )}">Idset</a> |
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Module' )}">Module</a> |
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Unity' )}">Unity</a> |
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Rcs' )}">Rcs</a> |
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Size' )}">Size</a> |
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Type' )}">Type</a> |
        <a href="${h.url_for( controller='admin', action='memdump', ids=ids, sorts=sorts, new_sort='Via' )}">Via</a>
    </nobr>
    ${htmlize( heap )}
    %endif
    </pre>
%endif
