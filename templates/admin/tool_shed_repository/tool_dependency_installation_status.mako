<%def name="render_tool_dependency_status( tool_dependency )">
    <%
        if tool_dependency.status == trans.model.ToolDependency.installation_status.INSTALLING:
            bgcolor = trans.model.ToolDependency.states.INSTALLING
            rval = '<div class="count-box state-color-%s" id="ToolDependencyStatus-%s">' % ( bgcolor, trans.security.encode_id( tool_dependency.id ) )
            rval += '%s</div>' % tool_dependency.status
        else:
            rval = tool_dependency.status
    %>    
    ${rval}
</%def>

${render_tool_dependency_status( tool_dependency )}
