<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/community/common/common.mako" import="*" />
<%namespace file="/webapps/community/repository/common.mako" import="*" />

<%
    from galaxy.web.framework.helpers import time_ago
    from galaxy.tool_shed.encoding_util import tool_shed_encode
%>

<%!
   def inherit(context):
       if context.get('use_panels'):
           return '/webapps/community/base_panels.mako'
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
