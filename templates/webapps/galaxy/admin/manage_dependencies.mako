<%inherit file="/base.mako"/>
<%namespace file="/webapps/tool_shed/repository/common.mako" import="render_dependency_status"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="render_tool_dependencies( requirements_status, ctr=False, ncols_extra=4, show_environment_path=False )">
    %for i, dependency in enumerate(requirements_status):
        %if i != 0:
            </tr>
            %if ctr % 2 == 1:
                <tr class="odd_row">
            %else:
                <tr class="tr">
            %endif
            %for i in range(ncols_extra-1):
                <td></td>
            %endfor
        %endif
        %if show_environment_path:
            <td>${dependency.get('environment_path', '') | h}</td>
        %endif
        ${render_dependency_status(dependency)}
    %endfor
</%def>

<%def name="render_tool_centric_table( tools, requirements_status)">
     <tr>
         <th>Select</th>
         <th>Name</th>
         <th>ID</th>
         <th>Requirement</th>
         <th>Version</th>
         <th>Resolver</th>
         <th>Exact</th>
         <th></th>
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
                 <input type="checkbox" name="selected_tool_ids" value="${tool.id}"/>
             </td>
             <td>${ tool.name | h }</td>
             <td>${ tool.id | h }</td>
             ${render_tool_dependencies( requirements_status[tool.tool_requirements], ctr=ctr) }
             </tr>
         <% ctr += 1 %>
         %endif
     %endfor
 </%def>

<%def name="render_unused_dependencies(unused_environments)">
    <tr>
        <th>Select</th>
        <th>Environment Path</th>
    </tr>
    <% ctr = 0 %>
    %for path in unused_environments:
        %if ctr % 2 == 1:
            <tr class="odd_row">
        %else:
            <tr class="tr">
        %endif
        <td>
            <input type="checkbox" name="selected_environments_to_uninstall" value="${path}"/>
        </td>
        <td>${ path | h }</td>
        </tr>
        <% ctr += 1 %>
    %endfor
</%def>

<%def name="render_dependencies_details(tools, requirements_status, tool_ids_by_requirements)">
    <tr>
        <th>Select</th>
        <th>Used by</th>
        <th>Environment Path</th>
        <th>Requirement</th>
        <th>Version</th>
        <th>Resolver</th>
        <th>Exact</th>
        <th></th>
    </tr>
    <% ctr = 0 %>
    %for requirements, r_status in requirements_status.items():
        %if requirements:
            <% tool_ids = tool_ids_by_requirements[requirements] %>
            %if ctr % 2 == 1:
                <tr class="odd_row">
            %else:
                <tr class="tr">
            %endif
            <td>
                <input type="checkbox" name="selected_tool_ids" value="${tool_ids[0]}"/>
            </td>
            <td>${ ", ".join([tools[tid].name for tid in tool_ids]) | h }</td>
            ${render_tool_dependencies( r_status, ctr=ctr, show_environment_path=True, ncols_extra=3) }
            </tr>
        %endif
        <% ctr += 1 %>
    %endfor
</%def>

<%def name="render_dependencies_details(tools, requirements_status, tool_ids_by_requirements)">
    <tr>
        <th>Select</th>
        <th>Used by</th>
        <th>Environment Path</th>
        <th>Requirement</th>
        <th>Version</th>
        <th>Resolver</th>
        <th>Exact</th>
        <th></th>
    </tr>
    <% ctr = 0 %>
    %for requirements, r_status in requirements_status.items():
        %if requirements:
            <% tool_ids = tool_ids_by_requirements[requirements] %>
            %if ctr % 2 == 1:
                <tr class="odd_row">
            %else:
                <tr class="tr">
            %endif
            <td>
                <input type="checkbox" name="selected_tool_ids" value="${tool_ids[0]}"/>
            </td>
            <td>${ ", ".join([tools[tid].name for tid in tool_ids]) | h }</td>
            ${render_tool_dependencies( r_status, ctr=ctr, show_environment_path=True, ncols_extra=3) }
            </tr>
        %endif
        <% ctr += 1 %>
    %endfor
</%def>

%if message:
    ${render_msg( message, status )}
%endif

<h2>Manage Tool Dependencies</h2>
<p>This page gives an overview of all tool dependencies required by all tools currently loaded, including tools not installed through the Tool Shed.</p>

<form name="manage_tool_dependencies" action="${h.url_for( controller='admin', action='manage_tool_dependencies' )}">
%if viewkey == "Switch to tool-centric view":
    <input type="submit" name="viewkey" value="Switch to details view"/>
    <input type="submit" name="viewkey" value="Switch to unused dependencies view"/>
    <div class="card mt-2 mb-2">
        <div class="card-header">Tool-centric dependencies</div>
        <div class="card-body overflow-auto">
            <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                ${render_tool_centric_table(tools, requirements_status)}
%elif viewkey == "Switch to unused dependencies view":
    <input type="submit" name="viewkey" value="Switch to details view"/>
    <input type="submit" name="viewkey" value="Switch to tool-centric view"/>
        <div class="card mt-2 mb-2">
        <div class="card-header">Unused dependency environments</div>
        <div class="card-body overflow-auto">
            <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                ${render_unused_dependencies(unused_environments)}
%else:
    <input type="submit" name="viewkey" value="Switch to tool-centric view"/>
    <input type="submit" name="viewkey" value="Switch to unused dependencies view"/>
    <div class="card mt-2 mb-2">
        <div class="card-header">Dependency details</div>
        <div class="card-body overflow-auto">
            <table class="manage-table colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                ${render_dependencies_details(tools, requirements_status, tool_ids_by_requirements)}
%endif
            </table>
        </div>
    </div>
    %if viewkey =="Switch to unused dependencies view":
        <input type="submit" name="remove_unused_dependencies" value="Remove checked paths"/>
    %else:
        <input type="submit" name="install_dependencies" value="Install checked dependencies using Conda"/>
        <input type="submit" name="uninstall_dependencies" value="Uninstall checked dependencies using Conda"/>
    %endif
</form>
