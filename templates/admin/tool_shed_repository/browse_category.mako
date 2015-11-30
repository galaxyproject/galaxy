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
</%def>

%if message:
    ${render_msg( message, status )}
%endif

<table>
%for repository in category['repositories']:
	<tr>
		<td>
			<a href="${h.url_for( controller='admin_toolshed', action='preview_repository', tool_shed_url=tool_shed_url, tsr_id=repository['id'] )}">${repository['name']}</a>
		</td>
        <td>${repository['description']}</td>
        <td>${repository['type']}</td>
        <td>${repository['owner']}</td>
	</tr>
%endfor
</table>
