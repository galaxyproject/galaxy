<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    from galaxy.web.framework.helpers import time_ago
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        $(function(){
            $("input:text:first").focus();
        })
        function confirmSubmit() {
            if ( confirm( "Make sure you have filled in the User Description field.  After you have submitted your tool to be published, you will no longer be able to modify it.  Click OK to submit it." ) ) {
                return true;
            } else {
                return false;
            }
        }
    </script>
</%def>

<%def name="render_select( name, options )">
    <select name="${name}" id="${name}" style="min-width: 250px; height: 150px;" multiple>
        %for option in options:
            <option value="${option[0]}">${option[1]}</option>
        %endfor
    </select>
</%def>

<script type="text/javascript">
$().ready(function() {  
    $('#categories_add_button').click(function() {
        return !$('#out_categories option:selected').remove().appendTo('#in_categories');
    });
    $('#categories_remove_button').click(function() {
        return !$('#in_categories option:selected').remove().appendTo('#out_categories');
    });
    $('form#edit_tool').submit(function() {
        $('#in_categories option').each(function(i) {
            $(this).attr("selected", "selected");
        });
    });
});
</script>

<%def name="title()">Edit Tool</%def>

<h2>Edit Tool</h2>

${tool.get_state_message()}
<p/>

<ul class="manage-table-actions">
    %if can_approve_or_reject:
        <li><a class="action-button" href="${h.url_for( controller='admin', action='set_tool_state', state=trans.model.Tool.states.APPROVED, id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Approve</a></li>
        <li><a class="action-button" href="${h.url_for( controller='admin', action='set_tool_state', state=trans.model.Tool.states.REJECTED, id=trans.security.encode_id( tool.id ), cntrller=cntrller )}">Reject</a></li>
    %endif
    <li><a class="action-button" id="tool-${tool.id}-popup" class="menubutton">Tool Actions</a></li>
    <div popupmenu="tool-${tool.id}-popup">
        %if can_view:
            <a class="action-button" href="${h.url_for( controller='common', action='view_tool_history', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Tool history</a>
            <a class="action-button" href="${h.url_for( controller='common', action='view_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">View tool</a>
        %endif
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

%if can_edit:
    <form id="edit_tool" name="edit_tool" action="${h.url_for( controller='common', action='edit_tool' )}" method="post">
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
                <input type="hidden" name="id" value="${trans.app.security.encode_id( tool.id )}"/>
                <input type="hidden" name="cntrller" value="${cntrller}"/>
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
                        <div class="form-row-input"><pre><textarea name="user_description" rows="5" cols="35">${tool.user_description}</textarea></pre></div>
                    %else:
                        <div class="form-row-input"><textarea name="user_description" rows="5" cols="35"></textarea></div>
                    %endif
                    <div class="toolParamHelp" style="clear: both;">Required when submitting for approval</div>
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
            </div>
        </div>
        <p/>
        <div class="toolForm">
            <div class="toolFormTitle">Manage categories</div>
            <div class="toolFormBody">
                <div class="form-row">
                    <div style="float: left; margin-right: 10px;">
                        <label>Categories associated with '${tool.name}'</label>
                        ${render_select( "in_categories", in_categories )}<br/>
                        <input type="submit" id="categories_remove_button" value=">>"/>
                    </div>
                    <div>
                        <label>Categories not associated with '${tool.name}'</label>
                        ${render_select( "out_categories", out_categories )}<br/>
                        <input type="submit" id="categories_add_button" value="<<"/>
                    </div>
                </div>
                <div class="form-row">
                    <input type="submit" id="edit_tool_button" name="edit_tool_button" value="Save"/>
                </div>
            </div>
        </div>
        <p/>
        %if tool.is_new() or tool.is_rejected():
            <div class="toolForm">
                <div class="toolFormTitle">Get approval for publishing</div>
                <div class="toolFormBody">
                    <div class="form-row">
                        <input type="submit" name="approval_button" id="approval_button" value="Submit for approval" onClick="return confirmSubmit()" />
                    </div>
                    <div class="form-row">
                        <div class="toolParamHelp" style="clear: both;">
                            Tools must be approved before they are made available to others in the community.  After you have submitted
                            your tool to be published, you will no longer be able to modify it, so make sure the information above is
                            correct before submitting for approval.
                        </div>  
                    </div>
                </div>
            </div>
        %endif
    </form>
%else:
    ${render_msg( "You are not allowed to edit this tool", "error" )}
%endif
