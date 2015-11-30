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
%for category in categories:
    <tr>
        <td>
            <a href="${h.url_for(controller='admin_toolshed', action='browse_tool_shed_category', category_id=category['id'], tool_shed_url=tool_shed_url)}">${category['name']}</a>
        </td>
        <td>${category['description']}</td>
        <td>${category['repositories']}</td>
    </tr>
%endfor
</table>
