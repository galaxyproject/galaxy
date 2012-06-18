<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "dynatree_skin/ui.dynatree" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js( "ui.core", "jquery.dynatree" )}
    ${common_javascripts(repository.name, repository.repo_files_directory(trans.app))}
</%def>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}">Manage repository</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get updates</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or uninstall repository</a>
        %if repository.tool_dependencies:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', id=trans.security.encode_id( repository.id ) )}">Manage tool dependencies</a>
        %endif
        %if repository.missing_tool_dependencies:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='install_missing_tool_dependencies', id=trans.security.encode_id( repository.id ) )}">Install missing tool dependencies</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Browse ${repository.name} revision ${repository.changeset_revision} files</div>
    <div class="toolFormBody">
        <div class="form-row" >
            <label>Contents:</label>
            <div id="tree" >
                Loading...
            </div>
        </div>
        <div class="form-row">
            <div id="file_contents" class="toolParamHelp" style="clear: both;background-color:#FAFAFA;"></div>
        </div>
    </div>
</div>
