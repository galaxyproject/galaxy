<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Configured Galaxy tool sheds</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    ${h.css( "library" )}
</%def>

%if message:
    ${render_msg( message, status )}
%endif

<div class="card">
    <div class="card-header">Accessible Galaxy tool sheds</div>
    <div class="card-body">
        <% shed_id = 0 %>
        %for name, url in trans.app.tool_shed_registry.tool_sheds.items():
            <% margin_cls = "mt-2" if shed_id > 0 else "" %>
            <div class="menubutton split popup ${margin_cls}" id="dataset-${shed_id}-popup">
                <a class="view-info" href="${h.url_for( controller='admin_toolshed', action='browse_tool_shed', tool_shed_url=url )}">${name|h}</a>
            </div>
            <div popupmenu="dataset-${shed_id}-popup">
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_tool_shed', tool_shed_url=url )}">Browse valid repositories</a>
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='find_tools_in_tool_shed', tool_shed_url=url )}">Search for valid tools</a>
                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='find_workflows_in_tool_shed', tool_shed_url=url )}">Search for workflows</a>
            </div>
            <br/>
            <% shed_id += 1 %>
        %endfor
    </div>
</div>
