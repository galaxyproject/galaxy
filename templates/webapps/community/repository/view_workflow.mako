<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from galaxy.webapps.community.controllers.common import encode

    in_tool_shed = webapp == 'community'
    is_admin = trans.user_is_admin()
    is_new = repository.is_new
    can_manage = is_admin or trans.user == repository.user
    can_contact_owner = in_tool_shed and trans.user and trans.user != repository.user
    can_push = in_tool_shed and trans.app.security_agent.can_push( trans.user, repository )
    can_upload = can_push
    can_download = in_tool_shed and not is_new and ( not is_malicious or can_push )
    can_browse_contents = in_tool_shed and not is_new
    can_set_metadata = in_tool_shed and not is_new
    can_rate = in_tool_shed and not is_new and trans.user and repository.user != trans.user
    can_view_change_log = in_tool_shed and not is_new
    if can_push:
        browse_label = 'Browse or delete repository tip files'
    else:
        browse_label = 'Browse repository tip files'
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="render_workflow( repository_metadata_id, workflow_name, webapp )">
    <% center_url = h.url_for( controller='workflow', action='generate_workflow_image', repository_metadata_id=repository_metadata_id, workflow_name=encode( workflow_name ), webapp=webapp ) %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>

<br/><br/>
<ul class="manage-table-actions">
    %if in_tool_shed:
        %if is_new and can_upload:
            <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
        %else:
            <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
            <div popupmenu="repository-${repository.id}-popup">
                %if can_upload:
                    <a class="action-button" href="${h.url_for( controller='upload', action='upload', repository_id=trans.security.encode_id( repository.id ), webapp='community' )}">Upload files to repository</a>
                %endif
                %if can_manage:
                    <a class="action-button" href="${h.url_for( controller='repository', action='manage_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip )}">Manage repository</a>
                %else:
                    <a class="action-button" href="${h.url_for( controller='repository', action='view_repository', id=trans.app.security.encode_id( repository.id ), changeset_revision=repository.tip, webapp='community' )}">View repository</a>
                %endif
                %if can_view_change_log:
                    <a class="action-button" href="${h.url_for( controller='repository', action='view_changelog', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">View change log</a>
                %endif
                %if can_rate:
                    <a class="action-button" href="${h.url_for( controller='repository', action='rate_repository', id=trans.app.security.encode_id( repository.id ) )}">Rate repository</a>
                %endif
                %if can_browse_contents:
                    <a class="action-button" href="${h.url_for( controller='repository', action='browse_repository', id=trans.app.security.encode_id( repository.id ), webapp='community' )}">${browse_label}</a>
                %endif
                %if can_contact_owner:
                    <a class="action-button" href="${h.url_for( controller='repository', action='contact_owner', id=trans.security.encode_id( repository.id ), webapp='community' )}">Contact repository owner</a>
                %endif
                %if can_download:
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='gz' )}">Download as a .tar.gz file</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='bz2' )}">Download as a .tar.bz2 file</a>
                    <a class="action-button" href="${h.url_for( controller='repository', action='download', repository_id=trans.app.security.encode_id( repository.id ), changeset_revision=changeset_revision, file_type='zip' )}">Download as a zip file</a>
                %endif
            </div>
        %endif
    %else:
        <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
        <div popupmenu="repository-${repository.id}-popup">
            <li><a class="action-button" href="${h.url_for( controller='workflow', action='import_workflow', repository_metadata_id=repository_metadata_id, workflow_name=encode( workflow_name ), webapp=webapp )}">Import workflow to local Galaxy</a></li>
            <li><a class="action-button" href="${h.url_for( controller='repository', action='install_repository_revision', repository_id=trans.security.encode_id( repository.id ), webapp=webapp, changeset_revision=changeset_revision )}">Install repository to local Galaxy</a></li>
        </div>
        <li><a class="action-button" id="toolshed-${repository.id}-popup" class="menubutton">Tool Shed Actions</a></li>
        <div popupmenu="toolshed-${repository.id}-popup">
            <a class="action-button" href="${h.url_for( controller='repository', action='browse_valid_repositories', webapp=webapp )}">Browse valid repositories</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='find_tools', webapp=webapp )}">Search for valid tools</a>
            <a class="action-button" href="${h.url_for( controller='repository', action='find_workflows', webapp=webapp )}">Search for workflows</a>
        </div>
    %endif
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolFormTitle">${workflow_name}</div>
<div class="form-row">
    <b>Boxes are red when tools are not available in this repository</b>
    <div class="toolParamHelp" style="clear: both;">
        (this page displays SVG graphics)
    </div>
</div>
<br clear="left"/>

${render_workflow( repository_metadata_id, workflow_name, webapp )}
