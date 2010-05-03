<%namespace file="/message.mako" import="render_msg" />

<%
    from galaxy.web.framework.helpers import time_ago
    from urllib import quote_plus
    
    if cntrller in [ 'tool' ]:
        can_edit = trans.app.security_agent.can_edit_item( trans.user, tool )
        can_upload_new_version = trans.app.security_agent.can_upload_new_version( trans.user, tool, versions )

    visible_versions = []
    for version in versions:
        if version.is_approved() or version.is_archived() or version.user == trans.user:
            visible_versions.append( version )
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style type="text/css">
    ul.fileBrowser,
    ul.toolFile {
        margin-left: 0;
        padding-left: 0;
        list-style: none;
    }
    ul.fileBrowser {
        margin-left: 20px;
    }
    .fileBrowser li,
    .toolFile li {
        padding-left: 20px;
        background-repeat: no-repeat;
        background-position: 0;
        min-height: 20px;
    }
    .toolFile li {
        background-image: url( ${h.url_for( '/static/images/silk/page_white_compressed.png' )} );
    }
    .fileBrowser li {
        background-image: url( ${h.url_for( '/static/images/silk/page_white.png' )} );
    }
    </style>
</%def>

<%def name="title()">View Tool</%def>

<h2>View Tool: ${tool.name} <em>${tool.description}</em></h2>

%if tool.is_approved():
    <b><i>This is the latest approved version of this tool</i></b>
%elif tool.is_deleted():
    <font color="red"><b><i>This is a deleted version of this tool</i></b></font>
%elif tool.is_archived():
    <font color="red"><b><i>This is an archived version of this tool</i></b></font>
%elif tool.is_new():
    <font color="red"><b><i>This is an unsubmitted version of this tool</i></b></font>
%elif tool.is_waiting():
    <font color="red"><b><i>This version of this tool is awaiting administrative approval</i></b></font>
%elif tool.is_rejected():
    <font color="red"><b><i>This version of this tool has been rejected by an administrator</i></b></font>
%endif
<p/>

%if cntrller=='admin' and tool.is_waiting():
    <p>
       <ul class="manage-table-actions">
            <li><a class="action-button" href="${h.url_for( controller='admin', action='set_tool_state', state=trans.model.Tool.states.APPROVED, id=trans.security.encode_id( tool.id ), cntrller=cntrller )}"><span>Approve</span></a></li>
            <li><a class="action-button" href="${h.url_for( controller='admin', action='set_tool_state', state=trans.model.Tool.states.REJECTED, id=trans.security.encode_id( tool.id ), cntrller=cntrller )}"><span>Reject</span></a></li>
       </ul>
    </p>
%endif

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">${tool.name}
        <a id="tool-${tool.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
        <div popupmenu="tool-${tool.id}-popup">
            %if cntrller=='admin' or can_edit:
                <a class="action-button" href="${h.url_for( controller='common', action='edit_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Edit information</a>
            %endif
            %if cntrller=='admin' or can_upload_new_version:
                <a class="action-button" href="${h.url_for( controller='common', action='upload_new_tool_version', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Upload a new version</a>
            %endif
            <a class="action-button" href="${h.url_for( controller='tool', action='download_tool', id=trans.app.security.encode_id( tool.id ) )}">Download tool</a>
        </div>
    </div>
    <div class="toolFormBody">
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
            <label>Description:</label>
            ${tool.user_description}
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
            %if categories:
                <ul>
                    %for category in categories:
                        <li>${category.name}</li>
                    %endfor
                </ul>
            %else:
                none set
            %endif
            <div style="clear: both"></div>
        </div>
        %if len( visible_versions ) > 1:
            <div class="form-row">
                <label>All Versions:</label>
                <ul>
                    %for version in visible_versions:
                        %if version == tool:
                            <li><strong>${version.version} (this version)</strong></li>
                        %else:
                            <li><a href="${h.url_for( controller='common', action='view_tool', id=trans.app.security.encode_id( version.id ), cntrller=cntrller )}">${version.version}</a></li>
                        %endif
                    %endfor
                </ul>
                <div style="clear: both"></div>
            </div>
        %endif
    </div>
</div>

<p/>

<div class="toolForm">
    <div class="toolFormTitle">Tool Contents</div>
    <div class="toolFormBody">
        <div class="form-row">
            <ul class="toolFile">
                <li><a href="${h.url_for( controller='tool', action='download_tool', id=trans.app.security.encode_id( tool.id ) )}">${tool.download_file_name}</a></li>
                <ul class="fileBrowser">
                    %for name in tool_file_contents:
                        <li><a href="${h.url_for( controller='tool', action='view_tool_file', id=trans.app.security.encode_id( tool.id ), file_name=quote_plus( name ) )}">${name}</a></li>
                    %endfor
                </ul>
            </ul>
        </div>
    </div>
</div>
