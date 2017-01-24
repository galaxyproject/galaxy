<%inherit file="/base.mako"/>
<%namespace file="/webapps/tool_shed/repository/common.mako" import="render_dependency_status"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="render_tool_dependencies( requirements_status, ctr=False )">
    %for i, dependency in enumerate(requirements_status):
        %if i != 0:
            </tr>
            %if ctr % 2 == 1:
                <tr class="odd_row">
            %else:
                <tr class="tr">
            %endif
            <td></td>
            <td></td>
            <td></td>
        %endif
        ${render_dependency_status(dependency)}
    %endfor
</%def>

%if message:
    ${render_msg( message, status )}
%endif

    <form name="manage_tool_dependencies" action="${h.url_for( controller='admin', action='manage_tool_dependencies' )}">
    <div class="toolForm">
        <div class="toolFormTitle">Manage dependencies for loaded tools</div>
        <div class="toolFormBody">
            <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                <tr>
                    <th bgcolor="#D8D8D8">Install</th>
                    <th bgcolor="#D8D8D8">Name</th>
                    <th bgcolor="#D8D8D8">ID</th>
                    <th bgcolor="#D8D8D8">Requirement</th>
                    <th bgcolor="#D8D8D8">Version</th>
                    <th bgcolor="#D8D8D8">Resolver</th>
                    <th bgcolor="#D8D8D8">Exact</th>
                    <th bgcolor="#D8D8D8"></th>
                </tr>
                <% ctr = 0 %>
                %for tool in tools.values():
                    %if tool.tool_requirements:
                        %if ctr % 2 == 1:
                            <tr class="odd_row">
                        %else:
                            <tr class="tr">
                        %endif
                        <td>
                            <input type="checkbox" name="install_for_tools" value="${tool.id}"/>
                        </td>
                        <td>${ tool.name | h }</td>
                        <td>${ tool.id | h }</td>
                        ${render_tool_dependencies( tool._view.get_requirements_status({tool.id: tool.tool_requirements}, tool.installed_tool_dependencies), ctr=ctr) }
                        </tr>
                    <% ctr += 1 %>
                    %endif
                %endfor
            </table>
        </div>
    </div>
    <input type="submit" name="install_dependencies" value="Install checked dependencies using Conda"/>
    </form>
