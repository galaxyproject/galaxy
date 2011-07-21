<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%
    from galaxy.web.form_builder import TextField
    is_new = repository.is_new
    can_push = trans.app.security_agent.can_push( trans.user, repository )
    can_upload = can_push
    can_browse_contents = not is_new
    can_set_metadata = not is_new
    can_rate = not is_new and trans.user and repository.user != trans.user
    can_view_change_log = not is_new
    if can_push:
        browse_label = 'Browse or delete repository files'
    else:
        browse_label = 'Browse repository files'
%>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        $(function(){
            $("input:text:first").focus();
        })
    </script>
</%def>

<br/><br/>
<ul class="manage-table-actions">
    %if is_new and can_upload:
        <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
    %else:
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            %if can_upload:
                <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
            %endif
            %if can_view_change_log:
                <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ) )}">View change log</a>
            %endif
            %if can_rate:
                <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
            %endif
            %if can_browse_contents:
                <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ) )}">${browse_label}</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='gz' )}">Download as a .tar.gz file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='bz2' )}">Download as a .tar.bz2 file</a>
                <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), file_type='zip' )}">Download as a zip file</a>
            %endif
        </div>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<%def name="render_field( index, field_tup )">
    <h4 class="msg_head"> 
        <div class="form-row">Column ${index + 1}</div>
    </h4>
    <div class="msg_body2">
        <div class="repeat-group-item">
            <div class="form-row">
                <% column_field = TextField( field_tup[0], 40, field_tup[1] ) %>
                ${column_field.get_html()}
                <div class="toolParamHelp" style="clear: both;">
                    Enter the name of the location file column (e.g., value, dbkey, name, path, etc).  See the tool_data_table_conf.xml file for examples.
                </div>
            </div>
            <div class="form-row">
                <input type="submit" name="remove_button" value="Remove field ${index + 1}"/>
            </div>
        </div>
    </div>
</%def>

<div class="toolForm">
    <div class="toolFormTitle">Add tool data table entry</div>
    <div class="toolFormBody">
        <form name="add_tool_data_table_entry" id="add_tool_data_table_entry" action="${h.url_for( controller='repository', action='add_tool_data_table_entry', name_attr=name_attr, repository_id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Table name:</label>
                ${name_attr}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Comment lines begin with:</label>
                <input  name="comment_char" type="textfield" value="${comment_char}" size="8"/>
                <div class="toolParamHelp" style="clear: both;">
                    Enter the character that designates comments lines in the location file (default is #).
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Location file name:</label>
                <input  name="loc_filename" type="textfield" value="${loc_filename}" size="80"/>
                <div class="toolParamHelp" style="clear: both;">
                    Enter the name of the location file (e.g., bwa_index.loc).
                </div>
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Location file columns:</label>
            </div>
            %for ctr, field_tup in enumerate( column_fields ):
                ${render_field( ctr, field_tup )}
            %endfor
            <div class="form-row">
                <input type="submit" name="add_field_button" value="Add field"/>
            </div>
            <div class="form-row">
                <input type="submit" name="add_tool_data_table_entry_button" value="Save"/>
            </div>
        </form>
    </div>
</div>
