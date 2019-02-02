<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/common/repository_actions_menu.mako" import="render_tool_shed_repository_actions" />

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}
    ${container_javascripts()}
</%def>

${render_tool_shed_repository_actions( repository, metadata=metadata, changeset_revision=changeset_revision )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolForm">
    <div class="toolFormTitle">Repository '${repository.name | h}'</div>
    <div class="toolFormBody">
        <form name="export_repository" id="export_repository" action="${h.url_for( controller='repository', action='export', repository_id=trans.security.encode_id( repository.id ), changeset_revision=changeset_revision )}" method="post" >
            %if containers_dict is not None and export_repository_dependencies_check_box is not None:
                ${render_dependencies_section( export_repository_dependencies_check_box, None, containers_dict, revision_label=revision_label, export=True )}
                <div style="clear: both"></div>
            %else:
                No repository dependencies are defined for revision <b>${revision_label}</b> of this repository, so click <b>Export</b> to export the selected revision.
            %endif
            <div class="form-row">
                <input type="submit" name="export_repository_button" value="Export"/>
            </div>
        </form>
    </div>
</div>
