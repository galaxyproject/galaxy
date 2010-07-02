<%namespace file="/message.mako" import="render_msg" />

<%
    from galaxy.web.framework.helpers import time_ago
    from urllib import quote_plus

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

<h2>View Tool</h2>

${tool.get_state_message()}
<p/>

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
        <a class="action-button" href="${h.url_for( controller='common', action='view_tool_history', id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Tool history</a>
        %if can_download:
            <a class="action-button" href="${h.url_for( controller='common', action='download_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Download tool</a>
        %endif
        %if can_delete:
            <a class="action-button" href="${h.url_for( controller='common', action='delete_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}" confirm="Are you sure you want to delete this tool?">Delete tool</a>
        %endif
        %if can_upload_new_version:
            <a class="action-button" href="${h.url_for( controller='common', action='upload_new_tool_version', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Upload a new version</a>
        %endif
        %if can_purge:
            <li><a class="action-button" href="${h.url_for( controller='admin', action='purge_tool', id=trans.security.encode_id( tool.id ), cntrller=cntrller )}" confirm="Purging removes records from the database, are you sure you want to purge this tool?">Purge tool</a></li>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

%if can_view:
    %if tool.is_rejected():
        <div class="toolForm">
            <div class="toolFormTitle">Reason for rejection</div>
            <div class="toolFormBody">
                <div class="form-row">
                    ${reason_for_rejection}
                    <div style="clear: both"></div>
                </div>
            </div>
        </div>
        <p/>
    %endif
    <div class="toolForm">
        <div class="toolFormTitle">${tool.name}</div>
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
                ${tool.description}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>User Description:</label>
                %if tool.user_description:
                    <pre>${tool.user_description}</pre>
                %endif
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
%endif
