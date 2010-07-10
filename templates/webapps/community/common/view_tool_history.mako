<%namespace file="/message.mako" import="render_msg" />

<%
    if cntrller in [ 'tool' ] and can_edit:
        menu_label = 'Edit information or submit for approval'
    else:
        menu_label = 'Edit information'
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<h2>Tool history</h2>
<ul class="manage-table-actions">
    %if can_approve_or_reject:
        <li><a class="action-button" href="${h.url_for( controller='admin', action='set_tool_state', state=trans.model.Tool.states.APPROVED, id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Approve</a></li>
        <li><a class="action-button" href="${h.url_for( controller='admin', action='set_tool_state', state=trans.model.Tool.states.REJECTED, id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Reject</a></li>
    %endif
    <li><a class="action-button" id="tool-${tool.id}-popup" class="menubutton">Tool Actions</a></li>
    <div popupmenu="tool-${tool.id}-popup">
        %if can_edit:
            <a class="action-button" href="${h.url_for( controller='common', action='edit_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">${menu_label}</a>
        %endif
        %if can_view:
            <a class="action-button" href="${h.url_for( controller='common', action='view_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">View tool</a>
        %endif
        %if can_delete:
            <a class="action-button" href="${h.url_for( controller='common', action='delete_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}" confirm="Are you sure you want to delete this tool?">Delete tool</a>
        %endif
        %if can_download:
            <a class="action-button" href="${h.url_for( controller='common', action='download_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Download tool</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${tool.name}</div>
    <div class="form-row">
        <label>Tool id:</label>
        ${tool.tool_id}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Version:</label>
        ${tool.version}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Description:</label>
        ${tool.description}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>User description:</label>
        ${tool.user_description}
        <div style="clear: both"></div>
    </div>
    <div class="form-row">
        <label>Uploaded by:</label>
        ${tool.user.username}
        <div style="clear: both"></div>
    </div>
</div>
<p/>
<table class="grid">
    <thead>
        <tr>
            <th>State</th>
            <th>Last Update</th>
            <th>Comments</th>
        </tr>
    </thead>
    <tbody>
        %for state, updated, comments in events:    
            <tr class="libraryRow libraryOrFolderRow" id="libraryRow">
                <td><b><a>${state}</a></b></td>
                <td><a>${updated}</a></td>
                <td><a>${comments}</a></td>
            </tr>             
        %endfor
    </tbody>
</table>
