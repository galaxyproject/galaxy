<%def name="render_tool_dependency_status( tool_dependency )">
    <%
        if tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLING ]:
            bgcolor = trans.model.ToolDependency.states.INSTALLING
        elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                         trans.model.ToolDependency.installation_status.UNINSTALLED ]:
            bgcolor = trans.model.ToolDependency.states.UNINSTALLED
        elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.ERROR ]:
            bgcolor = trans.model.ToolDependency.states.ERROR
        elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLED ]:
            bgcolor = trans.model.ToolDependency.states.OK
        rval = '<div class="count-box state-color-%s" id="ToolDependencyStatus-%s">%s</div>' % \
            ( bgcolor, trans.security.encode_id( tool_dependency.id, tool_dependency.status ) )
        return rval
    %>    
    ${rval}
</%def>

${render_tool_dependency_status( tool_dependency )}
