<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${container_javascripts()}
</%def>

${render_galaxy_repository_actions( repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="card">
    <div class="card-header">Installed tool shed repository '${repository.name|h}'</div>
    <div class="card-body">
        <form name="edit_repository" id="edit_repository" action="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}" method="post" >
            <div class="form-row">
                <label>Tool shed:</label>
                ${repository.tool_shed|h}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Name:</label>
                ${repository.name|h}
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Description:</label>
                %if repository.in_error_state:
                    ${description|h}
                %else:
                    <input name="description" type="textfield" value="${description|h}" size="80"/>
                %endif
                <div style="clear: both"></div>
            </div>
            <div class="form-row">
                <label>Revision:</label>
                ${repository.changeset_revision|h}
            </div>
            <div class="form-row">
                <label>Owner:</label>
                ${repository.owner|h}
            </div>
            %if repository.in_error_state:
                <div class="form-row">
                    <label>Repository installation error:</label>
                    ${repository.error_message|h}
                </div>
            %else:
                <div class="form-row">
                    <label>Location:</label>
                    ${repo_files_dir|h}
                </div>
            %endif
            <div class="form-row">
                <label>Deleted:</label>
                ${repository.deleted|h}
            </div>
            %if not repository.in_error_state:
                <div class="form-row">
                    <input type="submit" name="edit_repository_button" value="Save"/>
                </div>
            %endif
        </form>
    </div>
</div>
<p/>
${render_resolver_dependencies(requirements_status)}
%if not repository.in_error_state:
    ${render_repository_items( repository.metadata, containers_dict, can_set_metadata=False, render_repository_actions_for='galaxy' )}
%endif
