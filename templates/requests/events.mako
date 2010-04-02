<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<h2>History of Sequencing Request "${request.name}"</h2>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests', action='list', operation='show_request', id=trans.security.encode_id(request.id) )}">
        <span>Browse this request</span></a>
    </li>
    <li>
        <a class="action-button"  href="${h.url_for( controller='requests', action='list')}">
        <span>Browse all requests</span></a>
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
                <th>Last Update</th>
                <th>Comments</th>
            </tr>
        </thead>
        <tbody>
            %for state, updated, comments in events_list:    
                <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                    <td><b><a>${state}</a></b></td>
                    <td><a>${updated}</a></td>
                    <td><a>${comments}</a></td>
                </tr>             
            %endfor
        </tbody>
    </table>
</div>
