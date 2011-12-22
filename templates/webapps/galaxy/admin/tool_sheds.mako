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

<div class="toolForm">
    <div class="toolFormTitle">Accessible Galaxy tool sheds</div>
    <div class="toolFormBody">
        <div class="form-row">
            <table class="grid">
                <% shed_id = 0 %>
                %for name, url in trans.app.tool_shed_registry.tool_sheds.items():
                    <tr class="libraryTitle">
                        <td>
                            <div style="float: left; margin-left: 1px;" class="menubutton split popup" id="dataset-${shed_id}-popup">
                                <a class="view-info" href="${h.url_for( controller='admin_toolshed', action='browse_tool_shed', tool_shed_url=url )}">${name}</a>
                            </div>
                            <div popupmenu="dataset-${shed_id}-popup">
                                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='browse_tool_shed', tool_shed_url=url )}">Browse valid repositories</a>
                                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='find_tools_in_tool_shed', tool_shed_url=url )}">Search for valid tools</a>
                                <a class="action-button" href="${h.url_for( controller='admin_toolshed', action='find_workflows_in_tool_shed', tool_shed_url=url )}">Search for workflows</a>
                            </div>
                        </td>
                    </tr>
                    <% shed_id += 1 %>
                %endfor
                </tr>
            </table>
        </div>
        <div style="clear: both"></div>
    </div>
</div>
