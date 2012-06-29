<%def name="render_repository_status( repository )">
    <%
        if repository.status in [ trans.model.ToolShedRepository.installation_status.CLONING,
                                  trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                  trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                  trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES ]:
            bgcolor = trans.model.ToolShedRepository.states.INSTALLING
        elif repository.status in [ trans.model.ToolShedRepository.installation_status.NEW,
                                    trans.model.ToolShedRepository.installation_status.UNINSTALLED ]:
            bgcolor = trans.model.ToolShedRepository.states.UNINSTALLED
        elif repository.status in [ trans.model.ToolShedRepository.installation_status.ERROR ]:
            bgcolor = trans.model.ToolShedRepository.states.ERROR
        elif repository.status in [ trans.model.ToolShedRepository.installation_status.DEACTIVATED ]:
            bgcolor = trans.model.ToolShedRepository.states.WARNING
        elif repository.status in [ trans.model.ToolShedRepository.installation_status.INSTALLED ]:
            if repository.missing_tool_dependencies:
                bgcolor = trans.model.ToolShedRepository.states.WARNING
            else:
                bgcolor = trans.model.ToolShedRepository.states.OK
        else:
            bgcolor = trans.model.ToolShedRepository.states.ERROR
        rval = '<div class="count-box state-color-%s" id="ToolShedRepositoryStatus-%s">' % ( bgcolor, trans.security.encode_id( repository.id ) )
        rval += '%s</div>' % repository.status
        return rval
    %>    
    ${rval}
</%def>

${render_repository_status( repository )}
