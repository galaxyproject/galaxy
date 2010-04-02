<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Events for Sample ${sample_name}</%def>


<h2>Events for Sample "${sample_name}"</h2>

<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests', action='list', operation='show_request', id=trans.security.encode_id(request.id) )}">
        <span>Browse this request</span></a>
    </li>
    <li>
        <a class="action-button"  href="${h.url_for( controller='requests', action='list')}">
        <span>Browse requests</span></a>
    </li>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <table class="grid">
        <thead>
            <tr>
                <th>State</th>
                <th>Description</th>
                <th>Updated</th>
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
</div>