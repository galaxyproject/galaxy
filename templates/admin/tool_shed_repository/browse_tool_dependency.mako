<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

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

${render_galaxy_repository_actions( repository )}

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
