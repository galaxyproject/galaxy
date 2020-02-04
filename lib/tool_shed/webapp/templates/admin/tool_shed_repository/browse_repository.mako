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
    ${browse_files(repository.name, repository.repo_files_directory(trans.app))}
</%def>

${render_galaxy_repository_actions( repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="card">
    <div class="card-header">Browse ${repository.name|h} revision ${repository.changeset_revision} files</div>
    <div class="card-body">
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
