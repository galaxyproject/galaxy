<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Events for Sample ${sample.name}</%def>

<h2>Events for Sample "${sample.name}"</h2>
<ul class="manage-table-actions">
    <li>
        <a class="action-button" href="${h.url_for( controller='requests_common', action='manage_request', cntrller=cntrller, id=trans.security.encode_id( sample.request.id ) )}">
        <span>Browse this request</span></a>
    </li>
</ul>
<h3>Sequencing Request "${sample.request.name}"</h3>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="form-row">
    <div class="toolParamHelp" style="clear: both;">
    <b>Possible states: </b>
    <% states = " > ".join([ ss.name for ss in sample.request.type.states ]) %>
    ${states}
    </div>
    </div>
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
</div>
