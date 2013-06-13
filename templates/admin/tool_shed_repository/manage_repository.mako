<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${h.js("libs/jquery/jquery.rating", "libs/jquery/jstorage" )}
    ${container_javascripts()}
</%def>

<%
    in_error_state = repository.in_error_state
%>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        %if repository.can_reinstall_or_activate:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repositories', operation='activate or reinstall', id=trans.security.encode_id( repository.id ) )}">Activate or reinstall repository</a>
        %endif
        %if in_error_state:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='reset_to_install', id=trans.security.encode_id( repository.id ), reset_repository=True )}">Reset to install</a>
        %elif repository.can_install:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ), operation='install' )}">Install</a>
        %elif repository.can_uninstall:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository files</a>
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get repository updates</a>
            %if repository.can_reset_metadata:
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='reset_repository_metadata', id=trans.security.encode_id( repository.id ) )}">Reset repository metadata</a>
            %endif
            %if repository.includes_tools:
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='set_tool_versions', id=trans.security.encode_id( repository.id ) )}">Set tool versions</a>
            %endif
            %if repository.tool_dependencies:
                <% tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in repository.tool_dependencies ] %>
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', tool_dependency_ids=tool_dependency_ids )}">Manage tool dependencies</a>
            %endif
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or uninstall repository</a>
        %endif
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Installed tool shed repository '${repository.name}'</div>
    <div class="toolFormBody">
        <form name="edit_repository" id="edit_repository" action="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Tool shed:</label>
                ${repository.tool_shed}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Name:</label>
                ${repository.name}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                %if in_error_state:
                    ${description}
                %else:
                    <input name="description" type="textfield" value="${description}" size="80"/>
                %endif
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Revision:</label>
                ${repository.changeset_revision}
            </div>
            <div class="form-row">
                <label>Owner:</label>
                ${repository.owner}
            </div>
            %if in_error_state:
                <div class="form-row">
                    <label>Repository installation error:</label>
                    ${repository.error_message}
                </div>
            %else:
                <div class="form-row">
                    <label>Location:</label>
                    ${repo_files_dir}
                </div>
            %endif
            <div class="form-row">
                <label>Deleted:</label>
                ${repository.deleted}
            </div>
            %if not in_error_state:
                <div class="form-row">
                    <input type="submit" name="edit_repository_button" value="Save"/>
                </div>
            %endif
        </form>
    </div>
</div>
<p/>
%if not in_error_state:
    ${render_repository_items( repository.metadata, containers_dict, can_set_metadata=False )}
%endif
