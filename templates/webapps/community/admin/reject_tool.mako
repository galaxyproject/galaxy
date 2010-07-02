<%namespace file="/message.mako" import="render_msg" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="title()">Reject Tool</%def>

<h2>Reject Tool</h2>

<ul class="manage-table-actions">
    <li><a class="action-button" id="tool-${tool.id}-popup" class="menubutton">Tool Actions</a></li>
    <div popupmenu="tool-${tool.id}-popup">
        <a class="action-button" href="${h.url_for( controller='common', action='view_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">View tool</a>
        <a class="action-button" href="${h.url_for( controller='common', action='view_tool_history', id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Tool history</a>
        <a class="action-button" href="${h.url_for( controller='common', action='download_tool', id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Download tool</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${tool.name}</div>
        <form name="reject_tool" action="${h.url_for( controller='admin', action='reject_tool', id=trans.security.encode_id( tool.id ) )}" method="post" >
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
            <div class="form-row">
                <label>Reason for rejection</label>
                <textarea name="comments" rows="5" cols="40"></textarea>
                <div class="toolParamHelp" style="clear: both;">
                    Required
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="reject_button" value="Reject"/>
                <input type="submit" name="cancel_reject_button" value="Cancel"/>
            </div>
        </form>
    </div>
</div>
