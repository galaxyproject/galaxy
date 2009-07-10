<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Events for Sample ${sample_name}</%def>

<h2>Events for Sample "${sample_name}" of Request: ${request}</h2>

%if msg:
    ${render_msg( msg, messagetype )}
%endif


<table class="grid">
    <thead>
        <tr>
            <th>State</th>
            <th>Updated</th>
            <th>Description</th>
            <th>Comments</th>
        </tr>
    </thead>
    <tbody>
        %for state, updated, desc, comments in events_list:    
            <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                <td><b><a>${state}</a></b></td>
                <td><a>${updated}</a></td>
                <td><a>${desc}</a></td>
                <td><a>${comments}</a></td>
            </tr>             
        %endfor
    </tbody>
</table>