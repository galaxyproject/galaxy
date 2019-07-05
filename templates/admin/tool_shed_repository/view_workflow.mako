<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />
<%namespace file="/webapps/tool_shed/common/common.mako" import="*" />
<%namespace file="/webapps/tool_shed/repository/common.mako" import="*" />
<%namespace file="/admin/tool_shed_repository/repository_actions_menu.mako" import="*" />

<% from tool_shed.util.encoding_util import tool_shed_encode %>

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
    <iframe name="workflow_image" id="workflow_image" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url|h}"> </iframe>
</%def>

${render_galaxy_repository_actions( repository )}

%if message:
    ${render_msg( message, status )}
%endif

<div class="card-header">${workflow_name | h}</div>
<div class="form-row">
    <div class="toolParamHelp" style="clear: both;">
        (this page displays SVG graphics)
    </div>
</div>
<br clear="left"/>

${render_workflow( workflow_name, repository_id )}
