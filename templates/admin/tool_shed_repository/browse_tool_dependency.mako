<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "dynatree_skin/ui.dynatree" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "libs/jquery/jquery-ui", "libs/jquery/jquery.dynatree" )}
    ${browse_files(tool_dependency.name, tool_dependency.installation_directory( trans.app ))}
</%def>

<% tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in repository.tool_dependencies ] %>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="tool_dependency-${tool_dependency.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="tool_dependency-${tool_dependency.id}-popup">
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}">Manage repository</a>
        %if repository.has_readme:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='view_readme', id=trans.security.encode_id( repository.id ) )}">View README</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository files</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get repository updates</a>
        %if repository.can_reset_metadata:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='reset_repository_metadata', id=trans.security.encode_id( repository.id ) )}">Reset repository metadata</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or uninstall repository</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', tool_dependency_ids=tool_dependency_ids )}">Manage tool dependencies</a>
        %if tool_dependency.can_uninstall:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='uninstall_tool_dependencies', tool_dependency_ids=trans.security.encode_id( tool_dependency.id ) )}">Uninstall this tool dependency</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Browse tool dependency ${tool_dependency.name} installation directory</div>
    <div class="toolFormBody">
        <div class="form-row" >
            <label>Tool shed repository:</label>
            ${repository.name}
            <div style="clear: both"></div>
        </div>
        <div class="form-row" >
            <label>Tool shed repository changeset revision:</label>
            ${repository.changeset_revision}
            <div style="clear: both"></div>
        </div>
        <div class="form-row" >
            <label>Tool dependency status:</label>
            ${tool_dependency.status}
            <div style="clear: both"></div>
        </div>
        %if tool_dependency.in_error_state:
            <div class="form-row" >
                <label>Tool dependency installation error:</label>
                ${tool_dependency.error_message}
                <div style="clear: both"></div>
            </div>
        %endif
        <div class="form-row" >
            <label>Tool dependency installation directory:</label>
            ${tool_dependency.installation_directory( trans.app )}
            <div style="clear: both"></div>
        </div>
        <div class="form-row" >
            <label>Contents:</label>
            <div id="tree" >
                Loading...
            </div>
            <div style="clear: both"></div>
        </div>
        <div class="form-row">
            <div id="file_contents" class="toolParamHelp" style="clear: both;background-color:#FAFAFA;"></div>
        </div>
    </div>
</div>
