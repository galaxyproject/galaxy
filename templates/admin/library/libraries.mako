<%inherit file="/base.mako"/>

<%def name="title()">Libraries</%def>

%if msg:
<div class="donemessage">${msg}</div>
%endif

<h2>Libraries</h2>

<ul class="manage-table-actions">
    <li><a class="action-button" href="${h.url_for( controller='admin', action='library' )}">Create a new library</a></li>
</ul>

%if len(libraries) == 0:

    There are no libraries
    
%else:

    <table class="mange-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
        <tr class="header">
            <th>Name</th>
            <th>Description</th>
        </tr>
        %for library in libraries:
            <tr>
                <td><a href="${h.url_for( controller='admin', action='library', id=library.id )}">${library.name}</a></td>
                <td>${library.description}</td>
            </tr>
        %endfor
    </table>

%endif