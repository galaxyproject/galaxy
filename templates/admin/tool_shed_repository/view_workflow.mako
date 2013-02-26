<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from tool_shed.util.encoding_util import tool_shed_encode
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/tool_shed/base_panels.mako'
       else:
           return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%def name="render_workflow( workflow_name, repository_id )">
    <% center_url = h.url_for( controller='admin_toolshed', action='generate_workflow_image', workflow_name=tool_shed_encode( workflow_name ), repository_id=repository_id ) %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>

<br/><br/>
<ul class="manage-table-actions">
    <li><a class="action-button" id="repository-${repository.id}-popup" class="menubutton">Repository Actions</a></li>
    <div popupmenu="repository-${repository.id}-popup">
        <li><a class="action-button" href="${h.url_for( controller='admin_toolshed', action='import_workflow', workflow_name=tool_shed_encode( workflow_name ), repository_id=repository_id )}">Import workflow to Galaxy</a></li>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_repository', id=trans.security.encode_id( repository.id ) )}">Browse repository files</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( repository.id ) )}">Manage repository</a>
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='check_for_updates', id=trans.security.encode_id( repository.id ) )}">Get repository updates</a>
        %if repository.can_reset_metadata:
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='reset_repository_metadata', id=trans.security.encode_id( repository.id ) )}">Reset repository metadata</a>
        %endif
        %if repository.tool_dependencies:
            <% tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in repository.tool_dependencies ] %>
            <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='manage_tool_dependencies', tool_dependency_ids=tool_dependency_ids )}">Manage tool dependencies</a>
        %endif
        <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) )}">Deactivate or uninstall repository</a>
    </div>
</ul>

%if message:
    ${render_msg( message, status )}
%endif

<div class="toolFormTitle">${workflow_name | h}</div>
<div class="form-row">
    <div class="toolParamHelp" style="clear: both;">
        (this page displays SVG graphics)
    </div>
</div>
<br clear="left"/>

${render_workflow( workflow_name, repository_id )}
