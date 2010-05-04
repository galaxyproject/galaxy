<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

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

<h2>Edit Tool: ${tool.name} <em>${tool.description}</em></h2>

%if message:
    ${render_msg( message, status )}
%endif

%if cntrller == 'admin' or trans.user == tool.user:
    <form id="edit_tool" name="edit_tool" action="${h.url_for( controller='common', action='edit_tool' )}" method="post">
        <div class="toolForm">
            <div class="toolFormTitle">${tool.name}
                %if not tool.deleted:
                    <a id="tool-${tool.id}-popup" class="popup-arrow" style="display: none;">&#9660;</a>
                    <div popupmenu="tool-${tool.id}-popup">
                        <a class="action-button" href="${h.url_for( controller='common', action='view_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">View information</a>
                        <a class="action-button" href="${h.url_for( controller='tool', action='download_tool', id=trans.app.security.encode_id( tool.id ) )}">Download tool</a>
                        <a class="action-button" href="${h.url_for( controller='common', action='delete_tool', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Delete tool</a>
                        %if not tool.is_new() and not tool.is_waiting():
                            <a class="action-button" href="${h.url_for( controller='common', action='upload_new_tool_version', id=trans.app.security.encode_id( tool.id ), cntrller=cntrller )}">Upload a new version</a>
                        %endif
                    </div>
                %endif
            </div>
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
                    <div class="form-row-input"><textarea name="description" rows="5" cols="35">${tool.user_description}</textarea></div>
                    <div style="clear: both"></div>
                </div>
                <div class="form-row">
                    <input type="submit" id="edit_tool_button" name="edit_tool_button" value="Save">
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
    </form>
    <p/>
    <div class="toolForm">
        %if tool.is_new():
            <div class="toolFormTitle">Get approval for publishing</div>
            <div class="toolFormBody">
                <form name="get_approval" id="get_approval" action="${h.url_for( controller='common', action='edit_tool' )}" method="post" >
                    <input type="hidden" name="id" value="${trans.app.security.encode_id( tool.id )}"/>
                    <input type="hidden" name="cntrller" value="${cntrller}"/>
                    <div class="form-row">
                        <input type="submit" name="approval_button" value="Submit for approval"/>
                    </div>
                    <div class="form-row">
                        <div class="toolParamHelp" style="clear: both;">
                            Tools must be approved before they are made available to others in the community.  After you have submitted
                            your tool to be published, you will no longer be able to modify it, so make sure the information above is
                            correct and and save any changes before submitting for approval.
                        </div>  
                    </div>
                </form>
            </div>
        %endif
    </div>
%else:
    ${render_msg( "You are not allowed to edit this tool", "error" )}
%endif
