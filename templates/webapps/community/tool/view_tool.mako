<%namespace file="/message.mako" import="render_msg" />

<%
    from galaxy.web.framework.helpers import time_ago
    
    if cntrller in [ 'tool' ]:
        can_edit = trans.app.security_agent.can_edit_item( trans.user, tool )
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="title()">View Tool</%def>

<h2>View ${tool.name} <em>${tool.description}</em></h2>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${tool.name}
        <a id="tool-${tool.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
        <div popupmenu="tool-${tool.id}-popup">
            %if cntrller=='admin' or can_edit:
                <a class="action-button" href="${h.url_for( controller='common', action='edit_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Edit information</a>
                <a class="action-button" href="${h.url_for( controller='common', action='manage_categories', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Manage categories</a>
                <a class="action-button" href="${h.url_for( controller='common', action='upload_new_tool_version', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Upload a new version</a>
            %endif
            <a class="action-button" href="${h.url_for( controller='tool', action='download_tool', id=trans.app.security.encode_id( tool.id ) )}">Download tool</a>
        </div>
    </div>
    <div class="toolFormBody">
        <div class="form-row">
            <label>Description:</label>
            ${tool.user_description}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Tool Id:</label>
            ${tool.tool_id}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Version:</label>
            ${tool.version}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Uploaded by:</label>
            ${tool.user.username}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Date uploaded:</label>
            ${time_ago( tool.create_time )}
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <label>Categories:</label>
            %for category in categories:
                ${category.name}
            %endfor
            <div style="clear: both"></div>
        </div>
    </div>
</div>
