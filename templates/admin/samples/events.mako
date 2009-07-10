<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Events for Sample ${sample_name}</%def>

<h2>Events for Sample "${sample_name}" of Request: ${request}</h2>
<h3>User: ${user.email}</h3>

%if msg:
    ${render_msg( msg, messagetype )}
%endif


<table class="grid">
    <thead>
        <tr>
            <th>State</th>
            <th>Description</th>
            <th>Last Update</th>
            <th>Comments</th>
        </tr>
    </thead>
    <tbody>
        %for state, desc, updated, comments in events_list:    
            <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                <td><b><a>${state}</a></b></td>
                <td><a>${desc}</a></td>
                <td><a>${updated}</a></td>
                <td><a>${comments}</a></td>
            </tr>             
        %endfor
    </tbody>
</table>